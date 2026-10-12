"""Gate-discovered pytest: stub models vs the six C-line contract YAML headers."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from tb.mem.stub_models.contract_encodings import (
    ENC_BLOCK,
    ENC_CLASSES,
    ENC_INVALID,
    ENC_TBL_PG,
    encodings_from_header,
    load_enc_class_table,
)
from tb.mem.stub_models.contract_yaml import (
    ContractHeaderMissing,
    extract_yaml_header,
    find_contracts_dir,
    load_contract_document,
    load_contract_file,
    parse_assertions,
    parse_contract_yaml,
)
from tb.mem.stub_models.derived import collect_live, live_matches_derived
from tb.mem.stub_models.leaves import LEAF_NAMES, load_leaf_header, make_stub

SEED = 0xC11E5
N_CYCLES = 64
PTW = "ub_mem_ptw_desc_dec"
NON_PTW = tuple(name for name in LEAF_NAMES if name != PTW)


def _contracts() -> Path:
    return find_contracts_dir()


def _idle(header, *, rst: int = 0, in_valid: int = 0, out_ready: int = 1, **side) -> dict[str, int]:
    ins = {p.name: 0 for p in header.in_ports()}
    ins[header.clock.reset] = rst
    ins["in_valid"] = in_valid
    ins["out_ready"] = out_ready
    ins.update(side)
    return ins


def _release(model) -> None:
    header = model.header
    for _ in range(3):
        model.step(_idle(header, rst=1, out_ready=0))
    first = model.step(_idle(header, rst=0, out_ready=1))
    assert first["in_ready"] == 0
    second = model.step(_idle(header, rst=0, out_ready=1))
    assert second["in_ready"] == 1


def _rand_raw(header, rng: random.Random) -> int:
    port = header.port("raw")
    if port.width_unknown or port.width is None:
        return rng.getrandbits(32)
    return rng.getrandbits(port.width)


def _rand_legal_in(header, rng: random.Random, name: str) -> int:
    port = header.port(name)
    if port.legal is not None:
        return rng.randint(port.legal[0], port.legal[1])
    width = port.width or 2
    return rng.randrange(1 << width)


def _take_result(model, header, ins):
    first = model.step(ins)
    if header.latency.cycles == 0 and not ins.get("src_l1"):
        return first
    return model.step(_idle(header, in_valid=0, out_ready=1))


def test_loader_parses_all_real_headers():
    root = _contracts()
    for leaf in LEAF_NAMES:
        path = root / f"{leaf}.md"
        assert path.is_file(), path
        raw = extract_yaml_header(path.read_text(encoding="utf-8"))
        assert raw is not None, f"{leaf} missing YAML header"
        header = load_contract_file(path)
        assert header.leaf == leaf
        assert header.clock.name == "core_clk"
        assert header.clock.reset == "rst_pyc"
        assert header.clock.period_ns == pytest.approx(12.412)
        assert header.ill_cause_width == 4
        assert header.has_port("raw")
        assert header.has_port("in_valid")
        assert header.has_port("out_ready")


def test_derived_yaml_digests_match_this_head():
    ok, detail = live_matches_derived()
    assert ok, detail
    live = collect_live()
    assert set(live["ptw_enc_classes"]) == set(ENC_CLASSES)
    assert len(live["ptw_enc_cross"]) == 4
    for level in live["ptw_enc_cross"].values():
        assert set(level) == set(ENC_CLASSES)


def test_loader_assertions_field_one_per_line():
    text = """
leaf: ub_mem_ptw_desc_dec
parent: ub_mem_ptw
clock: {name: core_clk, period_ns: 12.412, reset: rst_pyc, reset_type: sync}
latency: {kind: registered, cycles: 1, max_cycles: 1}
ports:
  - {name: core_clk, dir: in, width: 1, desc: clk}
  - {name: rst_pyc, dir: in, width: 1, desc: rst}
  - {name: in_valid, dir: in, width: 1, desc: v}
  - {name: in_ready, dir: out, width: 1, desc: r}
  - {name: raw, dir: in, width: 64, desc: raw}
  - {name: out_valid, dir: out, width: 1, desc: ov}
  - {name: out_ready, dir: in, width: 1, desc: or}
  - {name: desc_illegal, dir: out, width: 1, desc: ill}
  - {name: desc_ill_cause, dir: out, width: 4, desc: cause}
params: []
ill_cause_width: 4
status: draft
assertions: |
  AP_PTW_CLK: only core_clk
  AP_PTW_RDY: ready independent of valid
  AP_PTW_OUT_HOLD: hold under backpressure
"""
    header = parse_contract_yaml(text, source="sample-assertions")
    assert [a.name for a in header.assertions] == [
        "AP_PTW_CLK",
        "AP_PTW_RDY",
        "AP_PTW_OUT_HOLD",
    ]
    model = make_stub(PTW, header=header, seed=1)
    assert model.checker.enabled == header.assertion_names()


def test_parse_assertions_shapes():
    assert [a.name for a in parse_assertions("AP_A: x\nAP_B: y")] == ["AP_A", "AP_B"]
    assert [a.name for a in parse_assertions({"AP_A": "x"})] == ["AP_A"]
    assert [a.name for a in parse_assertions([{"name": "AP_A", "text": "x"}])] == ["AP_A"]


@pytest.mark.parametrize("leaf", LEAF_NAMES)
def test_ports_widths_latency_match_contract(leaf):
    header = load_leaf_header(leaf)
    model = make_stub(leaf, header=header, seed=SEED)
    assert model.port_names == tuple(p.name for p in header.ports)
    assert model.port_widths == {p.name: p.width for p in header.ports}
    assert model.latency_cycles == header.latency.cycles
    assert model.latency_upper_bound == header.latency.max_cycles
    if header.latency.kind == "combinational":
        assert header.comb_budget_ns == pytest.approx(5.0)
        assert model.latency_cycles == 0
    else:
        assert model.latency_cycles == 1
        assert model.latency_upper_bound == 1


def test_tecte_raw_width_comes_from_yaml():
    header = load_leaf_header("ub_mem_tecte_dec")
    raw = header.port("raw")
    assert not raw.width_unknown
    assert raw.width == int(raw.width_expr)


def test_mapte_lvl_legal_span_from_yaml_desc():
    header = load_leaf_header("ub_mem_mapte_dec")
    assert header.port("lvl").width == 2
    assert header.port("lvl").legal == (0, 3)


def test_tcte_bb_sz_legal_span_from_yaml_desc():
    header = load_leaf_header("ub_mem_tcte_dec")
    assert header.port("ctx_mapt_bb_sz").legal == (0, 9)


def test_encodings_come_from_contract_readme_or_yaml():
    header = load_leaf_header(PTW)
    enc = encodings_from_header(header)
    assert enc.ill_cause["ILL_NONE"] == 0
    assert enc.ill_cause["ILL_MAP_2MB"] == 1
    assert enc.ill_cause["ILL_HW_AD"] == 2
    assert enc.desc_kind["invalid"] == 0
    assert enc.desc_kind["table"] == 1
    assert enc.desc_kind["block"] == 2
    assert enc.desc_kind["page"] == 3
    assert enc.zero_outputs_on_illegal is True
    assert "README.md" in enc.source or "ill_cause" in enc.source


def test_ptw_enc_cross_is_exactly_twelve_cells():
    doc = load_contract_document(_contracts() / f"{PTW}.md")
    table = load_enc_class_table(doc.header, body=doc.body, yaml_digest=doc.yaml_digest)
    assert table is not None
    assert table.yaml_digest == doc.yaml_digest
    assert table.classes == ENC_CLASSES
    assert table.keys() == tuple((level, enc) for level in range(4) for enc in ENC_CLASSES)
    assert table.cell(0, ENC_TBL_PG).kind == "table" and not table.cell(0, ENC_TBL_PG).fault
    assert table.cell(0, ENC_BLOCK).fault
    assert table.cell(1, ENC_BLOCK).kind == "block" and table.cell(1, ENC_BLOCK).note == "1 GB"
    assert table.cell(2, ENC_BLOCK).kind == "block" and table.cell(2, ENC_BLOCK).note == "2 MB"
    assert table.cell(3, ENC_TBL_PG).kind == "page"
    assert table.cell(3, ENC_BLOCK).fault
    for level in range(4):
        assert table.cell(level, ENC_INVALID).fault


@pytest.mark.parametrize("leaf", LEAF_NAMES)
@pytest.mark.parametrize("seed", [SEED, SEED + 7, 11])
def test_random_handshake_with_backpressure(leaf, seed):
    header = load_leaf_header(leaf)
    model = make_stub(leaf, header=header, seed=seed)
    rng = random.Random(seed)
    _release(model)
    held = None
    accepts = 0
    for _ in range(N_CYCLES):
        if held is None:
            ins = _idle(
                header,
                in_valid=rng.randrange(2),
                out_ready=rng.randrange(2),
                raw=_rand_raw(header, rng),
            )
            if header.has_port("src_l1"):
                ins["src_l1"] = rng.randrange(2)
            if header.has_port("mode_multi"):
                ins["mode_multi"] = rng.randrange(2)
            if header.has_port("pte_sel"):
                ins["pte_sel"] = rng.randrange(8)
            if header.has_port("lvl"):
                ins["lvl"] = _rand_legal_in(header, rng, "lvl")
            if header.has_port("desc_lvl"):
                ins["desc_lvl"] = rng.randrange(4)
        else:
            ins = dict(held)
            ins["out_ready"] = rng.randrange(2)
        outs = model.step(ins)
        if ins["in_valid"] and not outs["in_ready"]:
            held = {k: ins[k] for k in ins}
        else:
            if ins["in_valid"] and outs["in_ready"]:
                accepts += 1
            held = None
    assert accepts > 0
    assert model.coverage.category == "stub_model"
    assert any(k.startswith("stub_model.") for k in model.coverage.as_dict())


@pytest.mark.parametrize("leaf", LEAF_NAMES)
def test_inject_hw_ad_zeros_payload(leaf):
    header = load_leaf_header(leaf)
    model = make_stub(leaf, header=header, seed=SEED)
    model.set_inject("ILL_HW_AD")
    _release(model)
    beat = _take_result(model, header, _idle(header, in_valid=1, out_ready=1, raw=0x11))
    assert beat["out_valid"] == 1
    illegal = next(n for n in beat if n.endswith("_illegal"))
    cause = next(n for n in beat if n.endswith("_ill_cause"))
    assert beat[illegal] == 1
    assert beat[cause] == model.encoding.ill_code("ILL_HW_AD")
    for port in header.out_ports():
        if port.name in {illegal, cause, "in_ready", "out_valid"}:
            continue
        assert beat[port.name] == 0, port.name


@pytest.mark.parametrize("leaf", NON_PTW)
def test_inject_map_2mb_on_non_ptw(leaf):
    header = load_leaf_header(leaf)
    model = make_stub(leaf, header=header, seed=SEED)
    model.set_inject("ILL_MAP_2MB")
    _release(model)
    beat = _take_result(model, header, _idle(header, in_valid=1, out_ready=1, raw=0x22))
    cause = next(n for n in beat if n.endswith("_ill_cause"))
    assert beat[cause] == model.encoding.ill_code("ILL_MAP_2MB")


@pytest.mark.parametrize("level", [0, 1, 2, 3])
@pytest.mark.parametrize("enc", list(ENC_CLASSES))
def test_ptw_twelve_cell_cross(level, enc):
    header = load_leaf_header(PTW)
    model = make_stub(PTW, header=header, seed=2)
    model.set_enc_class(enc)
    _release(model)
    beat = _take_result(
        model,
        header,
        _idle(header, in_valid=1, out_ready=1, raw=0x5A, desc_lvl=level),
    )
    cell = model.enc_table.cell(level, enc)
    assert beat["out_valid"] == 1
    assert beat["desc_illegal"] == 0
    assert beat["desc_ill_cause"] == 0
    if cell.fault:
        assert beat["desc_v"] == 0
        assert beat["desc_kind"] == 0
    else:
        assert beat["desc_v"] == 1
        assert beat["desc_kind"] == model.encoding.kind_code(cell.kind)
    assert model.coverage.category == "stub_model"
    assert model.coverage.cross[(level, enc)] >= 1


def test_ptw_coverage_cross_is_exactly_the_twelve_cells():
    header = load_leaf_header(PTW)
    model = make_stub(PTW, header=header, seed=9)
    _release(model)
    for level in range(4):
        for enc in ENC_CLASSES:
            model.set_enc_class(enc)
            _take_result(
                model,
                header,
                _idle(header, in_valid=1, out_ready=1, raw=level + 1, desc_lvl=level),
            )
    assert model.coverage.expected_cells() == frozenset((lv, enc) for lv in range(4) for enc in ENC_CLASSES)
    assert model.coverage.missing_cells() == frozenset()
    assert set(model.coverage.cross) == set(model.coverage.expected_cells())
    assert all(k.startswith("stub_model.") for k in model.coverage.as_dict())


def test_ptw_l1_block_and_l2_block_are_legal():
    header = load_leaf_header(PTW)
    model = make_stub(PTW, header=header, seed=2)
    model.set_enc_class(ENC_BLOCK)
    _release(model)
    l1 = _take_result(model, header, _idle(header, in_valid=1, out_ready=1, raw=1, desc_lvl=1))
    assert l1["desc_kind"] == model.encoding.kind_code("block")
    assert l1["desc_v"] == 1
    assert l1["desc_illegal"] == 0
    l2 = _take_result(model, header, _idle(header, in_valid=1, out_ready=1, raw=2, desc_lvl=2))
    assert l2["desc_kind"] == model.encoding.kind_code("block")
    assert l2["desc_illegal"] == 0


def test_ptw_config_illegal_precedes_translation_fault():
    header = load_leaf_header(PTW)
    model = make_stub(PTW, header=header, seed=3)
    model.set_enc_class(ENC_INVALID)
    model.set_inject("ILL_HW_AD")
    _release(model)
    beat = _take_result(model, header, _idle(header, in_valid=1, out_ready=1, raw=0, desc_lvl=0))
    assert beat["desc_illegal"] == 1
    assert beat["desc_ill_cause"] == model.encoding.ill_code("ILL_HW_AD")
    assert beat["desc_v"] == 0
    assert beat["desc_kind"] == 0


def test_dent_l0_is_combinational_l1_is_registered():
    header = load_leaf_header("ub_mem_dec_ent_dec")
    model = make_stub("ub_mem_dec_ent_dec", header=header, seed=3)
    _release(model)
    l0 = model.step(_idle(header, in_valid=1, out_ready=1, raw=1, src_l1=0, pte_sel=1))
    assert l0["out_valid"] == 1
    model.step(_idle(header, in_valid=0, out_ready=1))
    acc = model.step(_idle(header, in_valid=1, out_ready=1, raw=2, src_l1=1, pte_sel=0))
    assert acc["out_valid"] == 0
    nxt = model.step(_idle(header, in_valid=0, out_ready=1))
    assert nxt["out_valid"] == 1


def test_hold_under_backpressure():
    header = load_leaf_header("ub_mem_l1tct_dec")
    model = make_stub("ub_mem_l1tct_dec", header=header, seed=4)
    _release(model)
    model.step(_idle(header, in_valid=1, out_ready=1, raw=9))
    shown = model.step(_idle(header, in_valid=0, out_ready=0))
    assert shown["out_valid"] == 1
    held = model.step(_idle(header, in_valid=0, out_ready=0))
    assert held["out_valid"] == 1
    for name in header.port_map():
        if name in {"in_ready", "core_clk", "rst_pyc", "in_valid", "out_ready", "raw"}:
            continue
        assert held[name] == shown[name]


def test_ready_does_not_follow_in_valid():
    header = load_leaf_header("ub_mem_tcte_dec")
    model = make_stub("ub_mem_tcte_dec", header=header, seed=5)
    _release(model)
    a = model.step(_idle(header, in_valid=0, out_ready=1, raw=0))
    b = model.step(_idle(header, in_valid=1, out_ready=1, raw=0))
    assert a["in_ready"] == 1
    assert b["in_ready"] == 1


def test_missing_header_is_none_and_load_raises(tmp_path: Path):
    assert extract_yaml_header("# no yaml here\n\n## 1\n") is None
    dest = tmp_path / "ub_mem_ptw_desc_dec.md"
    dest.write_text("# prose only\n", encoding="utf-8")
    with pytest.raises(ContractHeaderMissing):
        load_contract_file(dest)


def test_yaml_overrides_readme_when_header_carries_maps():
    text = """
leaf: ub_mem_ptw_desc_dec
parent: ub_mem_ptw
clock: {name: core_clk, period_ns: 12.412, reset: rst_pyc, reset_type: sync}
latency: {kind: registered, cycles: 1, max_cycles: 1}
ports:
  - {name: core_clk, dir: in, width: 1, desc: clk}
  - {name: rst_pyc, dir: in, width: 1, desc: rst}
  - {name: in_valid, dir: in, width: 1, desc: v}
  - {name: in_ready, dir: out, width: 1, desc: r}
  - {name: raw, dir: in, width: 64, desc: raw}
  - {name: out_valid, dir: out, width: 1, desc: ov}
  - {name: out_ready, dir: in, width: 1, desc: or}
  - {name: desc_kind, dir: out, width: 2, desc: kind}
  - {name: desc_illegal, dir: out, width: 1, desc: ill}
  - {name: desc_ill_cause, dir: out, width: 4, desc: cause}
params: []
ill_cause_width: 4
status: draft
ill_cause: {ILL_NONE: 0, ILL_MAP_2MB: 1, ILL_HW_AD: 2}
desc_kind: {invalid: 0, table: 1, block: 2, page: 3}
zero_outputs_on_illegal: true
"""
    header = parse_contract_yaml(text, source="override")
    enc = encodings_from_header(header)
    assert "override:ill_cause" in enc.source
    assert enc.desc_kind["block"] == 2
