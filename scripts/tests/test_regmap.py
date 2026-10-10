"""Semantic checks on docs/regmap/regmap.yaml (no overlapping fields, etc.)."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from regmap_lib import (  # noqa: E402
    DEFAULT_YAML,
    WORD_ALIGN,
    field_mask,
    field_width,
    load_regmap,
    parse_int,
    reset_int,
    validate_regmap,
)


def test_yaml_loads():
    data = load_regmap(DEFAULT_YAML)
    assert data["registers"]
    assert data["windows"]


def test_no_validation_errors():
    errors = validate_regmap(load_regmap())
    assert errors == [], "\n".join(errors)


def test_addresses_unique_and_word_aligned():
    seen: dict[int, str] = {}
    for reg in load_regmap()["registers"]:
        off = parse_int(reg["offset"])
        assert off is not None
        assert off % WORD_ALIGN == 0, f"{reg['name']} offset 0x{off:04X} not aligned"
        assert off not in seen, f"duplicate offset 0x{off:04X}"
        seen[off] = reg["name"]


def test_fields_within_32_bits_and_no_overlap():
    for reg in load_regmap()["registers"]:
        occupied = 0
        for field in reg["fields"]:
            msb = int(field["msb"])
            lsb = int(field["lsb"])
            assert 0 <= lsb <= msb <= 31, f"{reg['name']}.{field['name']} [{msb}:{lsb}]"
            bits = field_mask(field)
            assert occupied & bits == 0, f"{reg['name']}.{field['name']} overlaps"
            occupied |= bits


def test_reset_values_fit_width():
    for reg in load_regmap()["registers"]:
        for field in reg["fields"]:
            rst = reset_int(field)
            if rst is None:
                continue
            width = field_width(field)
            assert rst == (rst & ((1 << width) - 1)), (
                f"{reg['name']}.{field['name']} reset {field.get('reset')!r} "
                f"does not fit width {width}"
            )


def test_enum_and_legal_values_fit_widths():
    for reg in load_regmap()["registers"]:
        for field in reg["fields"]:
            width = field_width(field)
            mask = (1 << width) - 1
            for enum in field.get("enums") or []:
                val = int(enum["value"])
                assert val == (val & mask), (
                    f"{reg['name']}.{field['name']} enum {enum['name']}={val}"
                )
            for val in field.get("legal_values") or []:
                ival = int(val)
                assert ival == (ival & mask)
            for val in field.get("reserved_values") or []:
                ival = int(val)
                assert ival == (ival & mask)


def test_num_lanes_legal_set():
    data = load_regmap()
    for name in ("NUM_LANES_TX", "NUM_LANES_RX"):
        field = next(
            f
            for r in data["registers"]
            if r["name"] == "PARAM_PHY"
            for f in r["fields"]
            if f["name"] == name
        )
        assert list(field["legal_values"]) == [1, 2, 4, 8]


def test_port_rst_pulse_cycles():
    field = next(
        f
        for r in load_regmap()["registers"]
        if r["name"] == "CTRL"
        for f in r["fields"]
        if f["name"] == "PORT_RST"
    )
    assert field["pulse_cycles"] == 16
    assert field["self_clearing"] is True
    assert field["pulse_output"] == "port_rst_pulse"


def test_cnt_clr_bits_0_through_8():
    clr = next(r for r in load_regmap()["registers"] if r["name"] == "CNT_CLR")
    assert parse_int(clr["offset"]) == 0x0224
    bits = [f for f in clr["fields"] if f["name"] != "RSVD"]
    assert [f["lsb"] for f in bits] == list(range(9))
    assert all(f["access"] == "WO" and f.get("self_clearing") for f in bits)


def test_global_rules():
    data = load_regmap()
    rules = data["global_rules"]
    bus = data["meta"]["bus"]
    assert rules["full_word_writes_only"] is True
    assert rules["read_latency_cycles"] == 1
    assert rules["unmapped_csr_err"] is True
    assert rules["write_rvalid_next_cycle"] == 0
    assert bus["write_rvalid"] == 0
    assert bus["write_latency_cycles"] == 1


def test_csr_uses_pycircuit_api_not_string_verilog():
    """D5: leaf imports Circuit API; no string-templated Verilog in the source."""
    from gen_csr import emit_ub_csr_regs

    src = emit_ub_csr_regs(load_regmap())
    assert "from pycircuit import Circuit, compile, module, u" in src
    assert "compile(fn, name=\"ub_csr\")" in src
    assert "--emit=verilog" in src
    assert "def _csr_circuit(" in src
    assert "@module(name=\"ub_csr\")" in src
    for banned in (
        "always @(posedge",
        "assign irq =",
        "module ub_csr (",
        "csr_rvalid <= req_fire",
        "|(irq_sticky & ~irq_mask_w)",
        "5'd16",
        "write cycle: next csr_rvalid=0",
    ):
        assert banned not in src, banned


def test_csr_compile_ports_and_hooks_split():
    """compile() ports for PRODUCT/HOOKS; pycc Verilog when the backend is present."""
    import runpy
    import shutil

    path = SCRIPT_DIR.parent / "pycircuit" / "csr" / "ub_csr_regs.py"
    ns = runpy.run_path(str(path))
    s0 = ns["elaborate"](0)
    s1 = ns["elaborate"](1)
    assert s0["elaborated"], s0.get("reason")
    assert s1["elaborated"], s1.get("reason")
    assert "ub_csr" in s0["modules"]
    assert "tb_test_mode" not in s0["arg_names"]
    assert "tb_test_mode" in s1["arg_names"]
    for name in (
        "port_rst_pulse",
        "ev_fec_uncorr",
        "inc_fec_uncorr",
        "inc_crd_uf",
        "csr_lmsm_start",
        "csr_err",
        "irq",
        "csr_rvalid",
    ):
        ports = list(s0["arg_names"]) + list(s0["result_names"])
        assert name in ports, name
    if not shutil.which("pycc") and not ns["_find_pycc"]():
        return
    v0 = ns["emit_verilog"](False)
    v1 = ns["emit_verilog"](True)
    assert "module ub_csr" in v0
    assert "tb_test_mode" not in v0
    assert "tb_test_mode" in v1
    for token in (
        "port_rst_pulse",
        "ev_fec_uncorr",
        "inc_fec_uncorr",
        "inc_crd_uf",
        "csr_lmsm_start",
        "csr_err",
        "irq",
    ):
        assert token in v0, token
    assert "`ifdef" not in v0 and "`ifdef" not in v1


def test_ral_lives_under_tb_ral():
    from gen_regmap import OUTPUT_PATHS

    assert "tb/ral/ub_regmodel.py" in OUTPUT_PATHS
    assert "pycircuit/csr/ub_csr_regs.py" in OUTPUT_PATHS
    assert "gen/tb_ral/ub_regmodel.py" not in OUTPUT_PATHS
    assert "rtl/csr/ub_csr_regs.py" not in OUTPUT_PATHS
