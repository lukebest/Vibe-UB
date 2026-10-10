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
    csr_module_name,
    default_variant,
    field_mask,
    field_width,
    load_regmap,
    parse_int,
    reset_int,
    resolve_reset,
    validate_regmap,
    variant_tags,
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
    assert 'compile(fn, name=f"ub_csr_{tag}")' in src
    assert "--emit=verilog" in src
    assert "def _csr_circuit(" in src
    assert '@module(name="ub_csr")' in src
    assert "DEFAULT_VARIANT" in src
    assert "VARIANTS" in src
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
    for tag in ns["VARIANTS"]:
        mod = ns["csr_module_name"](tag)
        s0 = ns["elaborate"](0, variant=tag)
        s1 = ns["elaborate"](1, variant=tag)
        assert s0["elaborated"], s0.get("reason")
        assert s1["elaborated"], s1.get("reason")
        assert mod in s0["modules"], s0["modules"]
        assert s0["variant"] == tag
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
            continue
        v0 = ns["emit_verilog"](False, variant=tag)
        v1 = ns["emit_verilog"](True, variant=tag)
        assert f"module {mod}" in v0
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


def test_param_variant_reuses_num_lanes():
    data = load_regmap()
    reg = next(r for r in data["registers"] if r["name"] == "PARAM_VARIANT")
    assert parse_int(reg["offset"]) == 0x011C
    names = [f["name"] for f in reg["fields"]]
    assert names == ["NUM_VL", "SCR_PLACEHOLDER", "RSVD"]
    assert "NUM_LANES" not in names
    nvl = next(f for f in reg["fields"] if f["name"] == "NUM_VL")
    scr = next(f for f in reg["fields"] if f["name"] == "SCR_PLACEHOLDER")
    rsvd = next(f for f in reg["fields"] if f["name"] == "RSVD")
    assert (nvl["msb"], nvl["lsb"]) == (3, 0)
    assert (scr["msb"], scr["lsb"]) == (4, 4)
    assert (rsvd["msb"], rsvd["lsb"]) == (31, 5)
    assert nvl["access"] == "RO" and scr["access"] == "RO"
    assert nvl.get("reset_from") == "variant"
    assert scr.get("reset_from") == "variant"
    assert "reset" not in nvl and "reset" not in scr
    phy = next(r for r in data["registers"] if r["name"] == "PARAM_PHY")
    assert {f["name"] for f in phy["fields"]} >= {"NUM_LANES_TX", "NUM_LANES_RX"}


def test_variant_reset_matches_tag_name():
    """Reset values come from variants: and match the tag (xN_vlM)."""
    import re

    from gen_regmap import emit_c_header, emit_py_constants, emit_ral, emit_regmap_md

    data = load_regmap()
    tags = variant_tags(data)
    assert default_variant(data) == "product_x4_vl2"
    assert "product_x4_vl2" in tags and "product_x8_vl2" in tags
    assert tags["product_x4_vl2"] == {"NUM_LANES": 4, "NUM_VL": 2, "SCR_PLACEHOLDER": 1}
    assert tags["product_x8_vl2"]["NUM_LANES"] == 8
    assert tags["product_x8_vl2"]["NUM_VL"] == 2
    assert tags["product_x8_vl2"]["SCR_PLACEHOLDER"] == 1

    phy_tx = next(
        f
        for r in data["registers"]
        if r["name"] == "PARAM_PHY"
        for f in r["fields"]
        if f["name"] == "NUM_LANES_TX"
    )
    phy_rx = next(
        f
        for r in data["registers"]
        if r["name"] == "PARAM_PHY"
        for f in r["fields"]
        if f["name"] == "NUM_LANES_RX"
    )
    dll_vl = next(
        f
        for r in data["registers"]
        if r["name"] == "PARAM_DLL"
        for f in r["fields"]
        if f["name"] == "NUM_VL"
    )
    pvar_vl = next(
        f
        for r in data["registers"]
        if r["name"] == "PARAM_VARIANT"
        for f in r["fields"]
        if f["name"] == "NUM_VL"
    )
    pvar_scr = next(
        f
        for r in data["registers"]
        if r["name"] == "PARAM_VARIANT"
        for f in r["fields"]
        if f["name"] == "SCR_PLACEHOLDER"
    )

    for tag, params in tags.items():
        parsed = re.search(r"x(\d+)_vl(\d+)", tag)
        assert parsed, tag
        assert params["NUM_LANES"] == int(parsed.group(1))
        assert params["NUM_VL"] == int(parsed.group(2))
        assert resolve_reset(phy_tx, params) == params["NUM_LANES"]
        assert resolve_reset(phy_rx, params) == params["NUM_LANES"]
        assert resolve_reset(dll_vl, params) == params["NUM_VL"]
        assert resolve_reset(pvar_vl, params) == params["NUM_VL"]
        assert resolve_reset(pvar_scr, params) == params["SCR_PLACEHOLDER"]
        assert csr_module_name(tag) == f"ub_csr_{tag}"

        # no handwritten reset on variant-driven fields
        for field in (phy_tx, phy_rx, dll_vl, pvar_vl, pvar_scr):
            assert field.get("reset_from") == "variant"
            assert "reset" not in field

    md = emit_regmap_md(data)
    assert "ub_csr_product_x4_vl2" in md
    assert "ub_csr_product_x8_vl2" in md
    assert "| `product_x4_vl2`" in md
    assert "0x12" in md  # NUM_VL=2 | SCR_PLACEHOLDER<<4

    py = emit_py_constants(data)
    assert "VARIANT_PRODUCT_X4_VL2_NUM_LANES = 4" in py
    assert "VARIANT_PRODUCT_X8_VL2_NUM_LANES = 8" in py
    assert "PARAM_PHY_NUM_LANES_TX_RESET = None  # reset_from: variant" in py

    hdr = emit_c_header(data)
    assert "#define UB_REG_PARAM_VARIANT  0x011c" in hdr
    assert "#define UB_VARIANT_PRODUCT_X4_VL2_NUM_LANES  4u" in hdr
    assert "#define UB_VARIANT_PRODUCT_X8_VL2_NUM_LANES  8u" in hdr
    assert "UB_CSR_VARIANTS[]" in hdr
    assert '"ub_csr_product_x4_vl2"' in hdr
    assert "UB_PHY_NUM_LANES_TX_RESET" not in hdr

    ral_src = emit_ral(data)
    ral_ns: dict = {}
    exec(ral_src, ral_ns)  # noqa: S102 — generated RAL, no uvm required
    for tag, params in ral_ns["VARIANTS"].items():
        model = ral_ns["create_ub_regmodel"](variant=tag)
        assert model.variant == tag
        assert model.param_variant.NUM_VL.reset == params["NUM_VL"]
        assert model.param_variant.SCR_PLACEHOLDER.reset == params["SCR_PLACEHOLDER"]
        assert model.param_phy.NUM_LANES_TX.reset == params["NUM_LANES"]
        assert model.param_phy.NUM_LANES_RX.reset == params["NUM_LANES"]
        assert model.param_dll.NUM_VL.reset == params["NUM_VL"]
        word = (params["NUM_VL"] & 0xF) | ((params["SCR_PLACEHOLDER"] & 1) << 4)
        got = model.param_variant.NUM_VL.reset | (
            model.param_variant.SCR_PLACEHOLDER.reset << 4
        )
        assert got == word
