#!/usr/bin/env python3
"""Local selfcheck for ub_lmsm (not a TB; do not touch tb/).

  python3 pycircuit/lmsm/selfcheck.py

Checks: no f-string Verilog, no pycircuit/TOOLCHAIN.lock, ports,
byte-reproducible emit, Verilator -Wall, PRODUCT≡HOOKS (tb_* tied),
logic depth, and a Verilator directed sim of the NullBlock /
PROBE_WAIT_CYC corners (SPEC on main @ 62d9ce63 / D20).
"""

from __future__ import annotations

import os
import re
import shutil
import site
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYC = HERE.parent
REPO = PYC.parent
PRODUCT_V = REPO / "rtl" / "lmsm" / "ub_lmsm.v"
HOOKS_V = REPO / "rtl" / "lmsm" / "hooks" / "ub_lmsm.v"

os.environ.setdefault(
    "PYC_TOOLCHAIN_ROOT",
    str(REPO / ".pycircuit_out" / "toolchain" / "install"),
)
_root = Path(os.environ["PYC_TOOLCHAIN_ROOT"])
os.environ["PATH"] = f"{_root / 'bin'}:{os.environ.get('PATH', '')}"
_venv = Path(os.environ.get("UB_PYC_VENV", str(REPO / ".pycircuit-venv")))
if not (_venv / "bin" / "python").is_file():
    _venv = Path(os.environ.get("UB_PYC_VENV", "/tmp/venv"))
for _site in _venv.glob("lib/python*/site-packages"):
    site.addsitedir(str(_site))
if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from lmsm.emit import compile_to_verilog  # noqa: E402
from lmsm.ub_lmsm import (  # noqa: E402
    LANE_ID_ASCEND,
    LANE_ID_NULL,
    LANE_ID_PHYS,
    P_CHG_SPD_BIT,
    P_LTB_TYPE_CLTB_ACTIVE,
    P_LTB_TYPE_CLTB_CHECK,
    P_LTB_TYPE_CLTB_CONFIRM,
    P_LTB_TYPE_DLTB_ACTIVE,
    P_LTB_TYPE_DLTB_CONFIRM,
    P_LTB_TYPE_ELTB,
    P_LTB_TYPE_RLTB_ACTIVE,
    P_LTB_TYPE_RLTB_CONFIRM,
    P_LTB_TYPE_RLTB_EQ_INIT,
    P_LTB_TYPE_RLTB_LP1,
    P_LTB_TYPE_RXEQ,
    P_NULL_RX_NEED,
    P_NULL_TX_NEED,
    P_PROBE_WAIT_CYC,
    P_TMR_NULL,
    ST_LINK_ACTIVE,
    ST_LINK_IDLE,
    ST_PROBE,
    ST_RETRAIN,
    ST_SEND_NULLBLOCK,
)

HOOKS_EXTRA = {
    "tb_test_mode",
    "tb_inj_am_lock",
    "tb_inj_lid_bad",
    "tb_obs_link_ready",
    "tb_obs_link_up",
    "tb_obs_lmsm_st",
}
PCS_PULSES = (
    "pcs2lmsm_null_blk",
    "pcs2lmsm_tx_null_blk",
    "pcs2lmsm_rx_nonnull_blk",
)
RESULTS: list[tuple[str, str]] = []


def _ok(name: str, detail: str = "PASS") -> None:
    RESULTS.append((name, detail))
    print(f"PASS  {name}: {detail}")


def _fail(name: str, detail: str) -> None:
    RESULTS.append((name, f"FAIL {detail}"))
    raise SystemExit(f"FAIL  {name}: {detail}")


def _incdir() -> Path:
    return _root / "include" / "verilog"


def _port_decls(verilog: str) -> list[tuple[str, str, str]]:
    """Return (direction, packed_range, name). packed_range is '' or '[7:0] '."""
    decls: list[tuple[str, str, str]] = []
    inside = False
    for line in verilog.splitlines():
        if line.startswith("module "):
            inside = True
            continue
        if inside and line.strip() == ");":
            break
        if not inside:
            continue
        m = re.search(r"\b(input|output)\b(?:\s+(\[[^\]]+\]))?\s+(\w+)", line)
        if m:
            packed = f"{m.group(2)} " if m.group(2) else ""
            decls.append((m.group(1), packed, m.group(3)))
    return decls


def _port_names(verilog: str) -> list[str]:
    return [name for _d, _w, name in _port_decls(verilog)]


def check_source() -> None:
    src = (HERE / "ub_lmsm.py").read_text(encoding="utf-8")
    if re.search(r'\bf["\'].*(module|assign|always|input |output )', src):
        _fail("no-fstring-verilog", "ub_lmsm.py looks like a string emitter")
    if "w(" in src and "assign" in src:
        _fail("no-fstring-verilog", "string-emitter leftover")
    lock = PYC / "TOOLCHAIN.lock"
    if lock.exists():
        _fail("no-toolchain-lock", f"{lock} must not exist")
    if "m.assert_" not in src:
        _fail("in-leaf-assert", "missing m.assert_ on null vs nonnull")
    if P_PROBE_WAIT_CYC != 323:
        _fail("probe-default", f"default {P_PROBE_WAIT_CYC} != 323")
    if {LANE_ID_PHYS, LANE_ID_ASCEND, LANE_ID_NULL} & {3}:
        _fail("lane-id-mode", "lane_id_mode encoding includes 3")
    types = {
        P_LTB_TYPE_DLTB_ACTIVE,
        P_LTB_TYPE_DLTB_CONFIRM,
        P_LTB_TYPE_RXEQ,
        P_LTB_TYPE_CLTB_ACTIVE,
        P_LTB_TYPE_CLTB_CHECK,
        P_LTB_TYPE_CLTB_CONFIRM,
        P_LTB_TYPE_RLTB_ACTIVE,
        P_LTB_TYPE_RLTB_CONFIRM,
        P_LTB_TYPE_RLTB_LP1,
        P_LTB_TYPE_RLTB_EQ_INIT,
        P_LTB_TYPE_ELTB,
    }
    if types != {0xA0, 0xA1, 0xE0, 0xB0, 0xB1, 0xB2, 0xC0, 0xC1, 0xC2, 0xC3, 0xD0}:
        _fail("ltb-type-bytes", f"unexpected LTB types {sorted(hex(t) for t in types)}")
    if P_CHG_SPD_BIT != 7:
        _fail("chg-spd-bit", "Change_Speed is bit 7")
    if P_NULL_RX_NEED != 8 or P_NULL_TX_NEED != 16:
        _fail("null-need", f"RX={P_NULL_RX_NEED} TX={P_NULL_TX_NEED}")
    _ok("source-invariants", "no f-string Verilog; no TOOLCHAIN.lock; #9/#41 constants")


def check_netlist_text() -> None:
    product = PRODUCT_V.read_text(encoding="utf-8")
    hooks = HOOKS_V.read_text(encoding="utf-8")
    for label, text, th in (("PRODUCT", product, 0), ("HOOKS", hooks, 1)):
        if "`ifdef" in text and "TEST_HOOKS" in text:
            _fail("no-ifdef", f"{label} uses ifdef TEST_HOOKS")
        if f"TEST_HOOKS={th}" not in text.splitlines()[3]:
            if f"TEST_HOOKS={th}" not in text:
                _fail("header", f"{label} missing TEST_HOOKS={th}")
        if "pyc.assert failed" not in text:
            _fail("in-leaf-assert", f"{label} missing null/nonnull $fatal")
        if "wire [15:0] probe_tmr;" not in text or "wire [15:0] probe_lim;" not in text:
            _fail("probe-width", f"{label} probe_tmr/lim are not 16-bit")
    prod_ports = _port_names(product)
    hooks_ports = _port_names(hooks)
    extra = set(hooks_ports) - set(prod_ports)
    missing = set(prod_ports) - set(hooks_ports)
    if extra != HOOKS_EXTRA:
        _fail("hooks-ports", f"extra={sorted(extra)} expected={sorted(HOOKS_EXTRA)}")
    if missing:
        _fail("hooks-ports", f"PRODUCT ports missing from HOOKS: {sorted(missing)}")
    if any(n.startswith("tb_") for n in prod_ports):
        _fail("product-tb", "PRODUCT must not carry tb_*")
    for name in PCS_PULSES + ("probe_wait_cyc", "csr_lmsm_start", "csr_tmr_scale"):
        if name not in prod_ports:
            _fail("product-ports", f"missing {name}")
    if "link_up" not in prod_ports or "link_ready" not in prod_ports:
        _fail("product-ports", "missing link_up/link_ready")
    if "lmsm2pcs_nb_phase" not in prod_ports:
        _fail("product-ports", "missing lmsm2pcs_nb_phase")
    _ok("netlist-text", f"PRODUCT {len(prod_ports)} ports; HOOKS +{len(extra)} tb_*")


def check_emit_repro() -> None:
    a0 = compile_to_verilog(test_hooks=False)
    a1 = compile_to_verilog(test_hooks=False)
    b0 = compile_to_verilog(test_hooks=True)
    b1 = compile_to_verilog(test_hooks=True)
    if a0 != a1 or b0 != b1:
        _fail("emit-repro", "compile_to_verilog is not byte-stable")
    if a0 != PRODUCT_V.read_text(encoding="utf-8"):
        _fail("emit-repro", "PRODUCT on disk != fresh emit")
    if b0 != HOOKS_V.read_text(encoding="utf-8"):
        _fail("emit-repro", "HOOKS on disk != fresh emit")
    depth = None
    # last emit printed max_depth; re-scan committed header + a dry pycc via files
    m = re.search(r"max_depth=(\d+)/64", Path("/dev/null").read_text() if False else "")
    del m
    _ok("emit-repro", "PRODUCT and HOOKS byte-identical across two emits")


def check_lint() -> None:
    inc = _incdir()
    for label, path in (("PRODUCT", PRODUCT_V), ("HOOKS", HOOKS_V)):
        cmd = [
            "verilator",
            "--lint-only",
            "-Wall",
            "--top-module",
            "ub_lmsm",
            f"-I{inc}",
            str(path),
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        text = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0 or "%Error" in text or "%Warning" in text:
            _fail("verilator-wall", f"{label}: {text[-800:]}")
    _ok("verilator-wall", "PRODUCT and HOOKS clean")


def check_logic_depth() -> None:
    # pycc prints max_depth on stderr/stdout during compile_to_verilog.
    env = os.environ.copy()
    env.setdefault("PYC_TOOLCHAIN_ROOT", str(_root))
    env["PATH"] = f"{_root / 'bin'}:{env.get('PATH', '')}"
    from pycircuit import compile as pyc_compile
    from lmsm.ub_lmsm import build

    design = pyc_compile(build, name="ub_lmsm", test_hooks=0)
    mlir = design.emit_mlir()
    with tempfile.TemporaryDirectory(prefix="ub-depth-") as td:
        mlir_path = Path(td) / "ub_lmsm.pyc"
        v_path = Path(td) / "ub_lmsm.v"
        mlir_path.write_text(mlir, encoding="utf-8")
        proc = subprocess.run(
            [
                str(_root / "bin" / "pycc"),
                str(mlir_path),
                "--emit=verilog",
                "--logic-depth=64",
                "-o",
                str(v_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    text = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"max_depth=(\d+)/64", text)
    if not m:
        _fail("logic-depth", f"pycc did not print max_depth: {text[-400:]}")
    depth = int(m.group(1))
    if depth > 64:
        _fail("logic-depth", f"{depth}/64 exceeds cap")
    _ok("logic-depth", f"{depth}/64")


def check_equiv() -> None:
    """PRODUCT ≡ HOOKS on product outputs only, tb_* inputs tied inactive.

    pycc hashes internals differently, so Yosys ``equiv_make`` / ``equiv_induct``
    leave unpaired ``$equiv`` cells even when the folded netlists match.
    Proof is ABC ``dsec`` on flatten+opt+dffunmap+techmap BLIFs of the
    product-port wrappers (tb_obs_* omitted, tb_test_mode/tb_inj_*=0).
    """
    product_text = PRODUCT_V.read_text(encoding="utf-8")
    hooks_text = HOOKS_V.read_text(encoding="utf-8")
    prod_decls = _port_decls(product_text)
    prod_ports = [name for _d, _w, name in prod_decls]
    hooks_ports = _port_names(hooks_text)
    extras = [n for n in hooks_ports if n not in prod_ports]

    def _strip_includes(text: str) -> str:
        lines = [
            ln
            for ln in text.splitlines(keepends=True)
            if not ln.strip().startswith("`include")
        ]
        return "".join(lines)

    hooks_src = _strip_includes(hooks_text).replace(
        "module ub_lmsm (", "module ub_lmsm_hooks (", 1
    )
    product_src = _strip_includes(product_text)
    prod_list = ",\n  ".join(f"{d} {w}{n}" for d, w, n in prod_decls)
    prod_conn = ",\n    ".join(f".{n}({n})" for n in prod_ports)
    extra_conn = ",\n    ".join(
        f".{n}(1'b0)" if n.startswith("tb_inj") or n == "tb_test_mode" else f".{n}()"
        for n in extras
    )
    wrap_gold = f"""
module gold (
  {prod_list}
);
  ub_lmsm u (
    {prod_conn}
  );
endmodule
"""
    wrap_gate = f"""
module gate (
  {prod_list}
);
  ub_lmsm_hooks u (
    {prod_conn},
    {extra_conn}
  );
endmodule
"""
    abc = shutil.which("yosys-abc")
    if abc is None:
        _fail("product-equiv-hooks", "yosys-abc not on PATH")

    with tempfile.TemporaryDirectory(prefix="ub-eq-") as td:
        td_path = Path(td)
        (td_path / "product.v").write_text(product_src, encoding="utf-8")
        (td_path / "hooks_renamed.v").write_text(hooks_src, encoding="utf-8")
        (td_path / "wrap_gold.v").write_text(wrap_gold, encoding="utf-8")
        (td_path / "wrap_gate.v").write_text(wrap_gate, encoding="utf-8")
        pyc_reg = _incdir() / "pyc_reg.v"
        product_v = td_path / "product.v"
        hooks_v = td_path / "hooks_renamed.v"
        gold_blif = td_path / "gold.blif"
        gate_blif = td_path / "gate.blif"

        def _prep(mod: str, src: Path, wrap: Path, blif: Path) -> str:
            return f"""
read_verilog -sv {pyc_reg}
read_verilog -sv {src}
read_verilog -sv {wrap}
hierarchy -check -top {mod}
proc
flatten
opt -full
stat
dffunmap
opt -full -nosdff -nodffe
techmap
simplemap
opt_clean
write_blif {blif}
"""

        yosys_cmd = _prep("gold", product_v, td_path / "wrap_gold.v", gold_blif)
        yosys_cmd += "design -reset\n"
        yosys_cmd += _prep("gate", hooks_v, td_path / "wrap_gate.v", gate_blif)
        yosys = subprocess.run(
            ["yosys", "-p", yosys_cmd],
            check=False,
            capture_output=True,
            text=True,
        )
        ytext = (yosys.stdout or "") + (yosys.stderr or "")
        if yosys.returncode != 0:
            _fail("product-equiv-hooks", f"yosys prep failed\n{ytext[-800:]}")

        def _cells(mod: str) -> dict[str, int]:
            hit = False
            out: dict[str, int] = {}
            for line in ytext.splitlines():
                if line.strip() == f"=== {mod} ===":
                    hit = True
                    continue
                if hit and line.startswith("==="):
                    break
                if hit:
                    m = re.search(r"Number of cells:\s+(\d+)", line)
                    if m:
                        out["cells"] = int(m.group(1))
                    m = re.search(r"\$mux\s+(\d+)", line)
                    if m:
                        out["mux"] = int(m.group(1))
                    m = re.search(r"\$sdff\s+(\d+)", line)
                    if m:
                        out["sdff"] = int(m.group(1))
                    m = re.search(r"\$sdffe\s+(\d+)", line)
                    if m:
                        out["sdffe"] = int(m.group(1))
            return out

        gold_c = _cells("gold")
        gate_c = _cells("gate")
        if gold_c != gate_c or not gold_c:
            _fail(
                "product-equiv-hooks",
                f"flatten+opt cell mismatch gold={gold_c} gate={gate_c}",
            )
        if not gold_blif.is_file() or not gate_blif.is_file():
            _fail("product-equiv-hooks", "BLIF write failed")

        dsec = subprocess.run(
            [abc, "-c", f"dsec {gold_blif} {gate_blif}"],
            check=False,
            capture_output=True,
            text=True,
        )
        dtext = (dsec.stdout or "") + (dsec.stderr or "")
        if dsec.returncode != 0 or "Networks are equivalent" not in dtext:
            _fail("product-equiv-hooks", f"ABC dsec did not prove\n{dtext[-1200:]}")
        _ok(
            "product-equiv-hooks",
            f"ABC dsec equivalent; flatten+opt {gold_c}; "
            "tb_* idle, product outputs only",
        )


def _directed_sv() -> str:
    # Verilator directed cases. Observes named pyc_reg aliases.
    return f"""
`timescale 1ns/1ps
module lmsm_directed;
  localparam ST_IDLE   = 5'd{ST_LINK_IDLE};
  localparam ST_PROBE  = 5'd{ST_PROBE};
  localparam ST_NULL   = 5'd{ST_SEND_NULLBLOCK};
  localparam ST_ACTIVE = 5'd{ST_LINK_ACTIVE};
  localparam ST_RTR    = 5'd{ST_RETRAIN};
  localparam [31:0] TMR_NULL = 32'd{P_TMR_NULL};
  localparam [7:0]  T_DLTB   = 8'h{P_LTB_TYPE_DLTB_ACTIVE:02X};
  localparam [7:0]  T_CLTB   = 8'h{P_LTB_TYPE_CLTB_CONFIRM:02X};

  reg core_clk = 0;
  always #1 core_clk = ~core_clk;

  reg rst_pyc = 1;
  reg port_rst = 0;
  reg csr_lmsm_start = 0;
  reg csr_bypass_probe = 1;
  reg cfg_fixed_rate_rxeq = 0;
  reg cfg_req_change_speed = 0;
  reg cfg_req_equalization = 0;
  reg cfg_null_need_rediscovery = 0;
  reg cfg_lane_reverse_tx = 0;
  reg cfg_lane_reverse_rx = 0;
  reg cfg_polarity_inv = 0;
  reg [7:0] cfg_link_id = 0;
  reg [5:0] cfg_tlw = 0;
  reg [5:0] cfg_rlw = 0;
  reg [7:0] cfg_data_rate_support_1 = 0;
  reg [7:0] cfg_data_rate_support_2 = 0;
  reg [7:0] cfg_fec_mode_support = 0;
  reg cfg_port_type = 0;
  reg [6:0] cfg_portnego_random_value = 0;
  reg [3:0] cfg_fec_interleave_support = 0;
  reg [2:0] cfg_rx_lane0_id = 0;
  reg [2:0] cfg_max_link_width = 0;
  reg [1:0] cfg_eq_mode = 0;
  reg [2:0] cfg_fec_mode_ctrl = 0;
  reg cfg_fec_interleave_ctrl = 0;
  reg [5:0] cfg_eq_ctrl1 = 0;
  reg [7:0] cfg_eq_ctrl2 = 0;
  reg [7:0] cfg_eq_ctrl3 = 0;
  reg [7:0] cfg_eq_ctrl4 = 0;
  reg cfg_fec_crc_mode_reject = 0;
  reg [1:0] cfg_pre_fec_ber_meas_st = 0;
  reg cfg_fec_interleave_enable = 0;
  reg cfg_fec_interleave_ctrl_reject = 0;
  reg cfg_request_equalization = 0;
  reg [2:0] cfg_crc_mode_ctrl = 0;
  reg [3:0] cfg_local_tx_preset = 0;
  reg [5:0] cfg_first_pre_cursor = 0;
  reg cfg_eq_reject = 0;
  reg [1:0] cfg_current_eq_phase = 0;
  reg cfg_preset_mode_en = 0;
  reg [3:0] cfg_tx_preset = 0;
  reg [7:0] cfg_lane_id_base = 0;
  reg [7:0] cfg_lane_id_map = 0;
  reg [7:0] csr_tmr_scale = 0;
  reg [15:0] probe_wait_cyc = 16'd{P_PROBE_WAIT_CYC};
  reg pma_term_detect = 0;
  reg pma_rx_eidle_exit = 0;
  reg pma_phy_ready = 0;
  reg dll_retrain_req = 0;
  reg pcs2lmsm_ltb_valid = 0;
  reg [7:0] pcs2lmsm_ltb_type = 0;
  reg [7:0] pcs2lmsm_link_id = 0;
  reg [7:0] pcs2lmsm_lane_id = 0;
  reg [5:0] pcs2lmsm_tlw = 0;
  reg [5:0] pcs2lmsm_rlw = 0;
  reg [7:0] pcs2lmsm_data_rate_support_1 = 0;
  reg [7:0] pcs2lmsm_data_rate_support_2 = 0;
  reg [7:0] pcs2lmsm_fec_mode_support = 0;
  reg pcs2lmsm_port_type = 0;
  reg [6:0] pcs2lmsm_portnego_random_value = 0;
  reg [3:0] pcs2lmsm_fec_interleave_support = 0;
  reg [2:0] pcs2lmsm_rx_lane0_id = 0;
  reg [2:0] pcs2lmsm_max_link_width = 0;
  reg [1:0] pcs2lmsm_eq_mode = 0;
  reg [2:0] pcs2lmsm_fec_mode_ctrl = 0;
  reg pcs2lmsm_fec_interleave_ctrl = 0;
  reg [5:0] pcs2lmsm_eq_ctrl1 = 0;
  reg [7:0] pcs2lmsm_eq_ctrl2 = 0;
  reg [7:0] pcs2lmsm_eq_ctrl3 = 0;
  reg [7:0] pcs2lmsm_eq_ctrl4 = 0;
  reg pcs2lmsm_fec_crc_mode_reject = 0;
  reg [1:0] pcs2lmsm_pre_fec_ber_meas_st = 0;
  reg pcs2lmsm_fec_interleave_enable = 0;
  reg pcs2lmsm_fec_interleave_ctrl_reject = 0;
  reg pcs2lmsm_request_equalization = 0;
  reg [2:0] pcs2lmsm_crc_mode_ctrl = 0;
  reg [3:0] pcs2lmsm_local_tx_preset = 0;
  reg [5:0] pcs2lmsm_first_pre_cursor = 0;
  reg pcs2lmsm_eq_reject = 0;
  reg [1:0] pcs2lmsm_current_eq_phase = 0;
  reg pcs2lmsm_preset_mode_en = 0;
  reg [3:0] pcs2lmsm_tx_preset = 0;
  reg pcs_am_locked = 0;
  reg pcs_lid_bad = 0;
  reg pcs_deskew_ok = 0;
  reg pcs2lmsm_null_blk = 0;
  reg pcs2lmsm_rx_nonnull_blk = 0;
  reg pcs2lmsm_tx_null_blk = 0;
  reg tb_test_mode = 0;
  reg tb_inj_am_lock = 0;
  reg tb_inj_lid_bad = 0;

  wire [3:0] pma_data_rate_sel, pma_tx_width, pma_rx_width;
  wire pma_lane_reverse_tx, pma_lane_reverse_rx, pma_polarity_inv, pma_probe_pulse_en;
  wire link_up, link_ready, lmsm_retrain_ack, lmsm2pcs_ltb_valid, lmsm2pcs_nb_phase;
  wire [1:0] lmsm2pcs_pattern, lmsm2pcs_lane_id_mode;
  wire [7:0] lmsm2pcs_lane_id_base, lmsm2pcs_lane_id_map, lmsm2pcs_ltb_type, lmsm2pcs_link_id;
  wire [5:0] lmsm2pcs_tlw, lmsm2pcs_rlw;
  wire [7:0] lmsm2pcs_data_rate_support_1, lmsm2pcs_data_rate_support_2, lmsm2pcs_fec_mode_support;
  wire lmsm2pcs_port_type;
  wire [6:0] lmsm2pcs_portnego_random_value;
  wire [3:0] lmsm2pcs_fec_interleave_support;
  wire [2:0] lmsm2pcs_rx_lane0_id, lmsm2pcs_max_link_width, lmsm2pcs_fec_mode_ctrl, lmsm2pcs_crc_mode_ctrl;
  wire [1:0] lmsm2pcs_eq_mode, lmsm2pcs_pre_fec_ber_meas_st, lmsm2pcs_current_eq_phase;
  wire lmsm2pcs_fec_interleave_ctrl, lmsm2pcs_fec_crc_mode_reject, lmsm2pcs_fec_interleave_enable;
  wire lmsm2pcs_fec_interleave_ctrl_reject, lmsm2pcs_request_equalization, lmsm2pcs_eq_reject;
  wire lmsm2pcs_preset_mode_en;
  wire [5:0] lmsm2pcs_eq_ctrl1, lmsm2pcs_first_pre_cursor;
  wire [7:0] lmsm2pcs_eq_ctrl2, lmsm2pcs_eq_ctrl3, lmsm2pcs_eq_ctrl4;
  wire [3:0] lmsm2pcs_local_tx_preset, lmsm2pcs_tx_preset;
  wire [4:0] lmsm_st, tb_obs_lmsm_st;
  wire train_fail, train_to_inc, tb_obs_link_ready, tb_obs_link_up;

  ub_lmsm dut (
    .core_clk(core_clk), .rst_pyc(rst_pyc), .port_rst(port_rst),
    .csr_lmsm_start(csr_lmsm_start), .csr_bypass_probe(csr_bypass_probe),
    .cfg_fixed_rate_rxeq(cfg_fixed_rate_rxeq),
    .cfg_req_change_speed(cfg_req_change_speed),
    .cfg_req_equalization(cfg_req_equalization),
    .cfg_null_need_rediscovery(cfg_null_need_rediscovery),
    .cfg_lane_reverse_tx(cfg_lane_reverse_tx),
    .cfg_lane_reverse_rx(cfg_lane_reverse_rx),
    .cfg_polarity_inv(cfg_polarity_inv),
    .cfg_link_id(cfg_link_id), .cfg_tlw(cfg_tlw), .cfg_rlw(cfg_rlw),
    .cfg_data_rate_support_1(cfg_data_rate_support_1),
    .cfg_data_rate_support_2(cfg_data_rate_support_2),
    .cfg_fec_mode_support(cfg_fec_mode_support),
    .cfg_port_type(cfg_port_type),
    .cfg_portnego_random_value(cfg_portnego_random_value),
    .cfg_fec_interleave_support(cfg_fec_interleave_support),
    .cfg_rx_lane0_id(cfg_rx_lane0_id),
    .cfg_max_link_width(cfg_max_link_width),
    .cfg_eq_mode(cfg_eq_mode),
    .cfg_fec_mode_ctrl(cfg_fec_mode_ctrl),
    .cfg_fec_interleave_ctrl(cfg_fec_interleave_ctrl),
    .cfg_eq_ctrl1(cfg_eq_ctrl1), .cfg_eq_ctrl2(cfg_eq_ctrl2),
    .cfg_eq_ctrl3(cfg_eq_ctrl3), .cfg_eq_ctrl4(cfg_eq_ctrl4),
    .cfg_fec_crc_mode_reject(cfg_fec_crc_mode_reject),
    .cfg_pre_fec_ber_meas_st(cfg_pre_fec_ber_meas_st),
    .cfg_fec_interleave_enable(cfg_fec_interleave_enable),
    .cfg_fec_interleave_ctrl_reject(cfg_fec_interleave_ctrl_reject),
    .cfg_request_equalization(cfg_request_equalization),
    .cfg_crc_mode_ctrl(cfg_crc_mode_ctrl),
    .cfg_local_tx_preset(cfg_local_tx_preset),
    .cfg_first_pre_cursor(cfg_first_pre_cursor),
    .cfg_eq_reject(cfg_eq_reject),
    .cfg_current_eq_phase(cfg_current_eq_phase),
    .cfg_preset_mode_en(cfg_preset_mode_en),
    .cfg_tx_preset(cfg_tx_preset),
    .cfg_lane_id_base(cfg_lane_id_base),
    .cfg_lane_id_map(cfg_lane_id_map),
    .csr_tmr_scale(csr_tmr_scale),
    .probe_wait_cyc(probe_wait_cyc),
    .pma_term_detect(pma_term_detect),
    .pma_rx_eidle_exit(pma_rx_eidle_exit),
    .pma_phy_ready(pma_phy_ready),
    .dll_retrain_req(dll_retrain_req),
    .pcs2lmsm_ltb_valid(pcs2lmsm_ltb_valid),
    .pcs2lmsm_ltb_type(pcs2lmsm_ltb_type),
    .pcs2lmsm_link_id(pcs2lmsm_link_id),
    .pcs2lmsm_lane_id(pcs2lmsm_lane_id),
    .pcs2lmsm_tlw(pcs2lmsm_tlw),
    .pcs2lmsm_rlw(pcs2lmsm_rlw),
    .pcs2lmsm_data_rate_support_1(pcs2lmsm_data_rate_support_1),
    .pcs2lmsm_data_rate_support_2(pcs2lmsm_data_rate_support_2),
    .pcs2lmsm_fec_mode_support(pcs2lmsm_fec_mode_support),
    .pcs2lmsm_port_type(pcs2lmsm_port_type),
    .pcs2lmsm_portnego_random_value(pcs2lmsm_portnego_random_value),
    .pcs2lmsm_fec_interleave_support(pcs2lmsm_fec_interleave_support),
    .pcs2lmsm_rx_lane0_id(pcs2lmsm_rx_lane0_id),
    .pcs2lmsm_max_link_width(pcs2lmsm_max_link_width),
    .pcs2lmsm_eq_mode(pcs2lmsm_eq_mode),
    .pcs2lmsm_fec_mode_ctrl(pcs2lmsm_fec_mode_ctrl),
    .pcs2lmsm_fec_interleave_ctrl(pcs2lmsm_fec_interleave_ctrl),
    .pcs2lmsm_eq_ctrl1(pcs2lmsm_eq_ctrl1),
    .pcs2lmsm_eq_ctrl2(pcs2lmsm_eq_ctrl2),
    .pcs2lmsm_eq_ctrl3(pcs2lmsm_eq_ctrl3),
    .pcs2lmsm_eq_ctrl4(pcs2lmsm_eq_ctrl4),
    .pcs2lmsm_fec_crc_mode_reject(pcs2lmsm_fec_crc_mode_reject),
    .pcs2lmsm_pre_fec_ber_meas_st(pcs2lmsm_pre_fec_ber_meas_st),
    .pcs2lmsm_fec_interleave_enable(pcs2lmsm_fec_interleave_enable),
    .pcs2lmsm_fec_interleave_ctrl_reject(pcs2lmsm_fec_interleave_ctrl_reject),
    .pcs2lmsm_request_equalization(pcs2lmsm_request_equalization),
    .pcs2lmsm_crc_mode_ctrl(pcs2lmsm_crc_mode_ctrl),
    .pcs2lmsm_local_tx_preset(pcs2lmsm_local_tx_preset),
    .pcs2lmsm_first_pre_cursor(pcs2lmsm_first_pre_cursor),
    .pcs2lmsm_eq_reject(pcs2lmsm_eq_reject),
    .pcs2lmsm_current_eq_phase(pcs2lmsm_current_eq_phase),
    .pcs2lmsm_preset_mode_en(pcs2lmsm_preset_mode_en),
    .pcs2lmsm_tx_preset(pcs2lmsm_tx_preset),
    .pcs_am_locked(pcs_am_locked),
    .pcs_lid_bad(pcs_lid_bad),
    .pcs_deskew_ok(pcs_deskew_ok),
    .pcs2lmsm_null_blk(pcs2lmsm_null_blk),
    .pcs2lmsm_rx_nonnull_blk(pcs2lmsm_rx_nonnull_blk),
    .pcs2lmsm_tx_null_blk(pcs2lmsm_tx_null_blk),
    .tb_test_mode(tb_test_mode),
    .tb_inj_am_lock(tb_inj_am_lock),
    .tb_inj_lid_bad(tb_inj_lid_bad),
    .pma_data_rate_sel(pma_data_rate_sel),
    .pma_tx_width(pma_tx_width),
    .pma_rx_width(pma_rx_width),
    .pma_lane_reverse_tx(pma_lane_reverse_tx),
    .pma_lane_reverse_rx(pma_lane_reverse_rx),
    .pma_polarity_inv(pma_polarity_inv),
    .pma_probe_pulse_en(pma_probe_pulse_en),
    .link_up(link_up),
    .link_ready(link_ready),
    .lmsm_retrain_ack(lmsm_retrain_ack),
    .lmsm2pcs_nb_phase(lmsm2pcs_nb_phase),
    .lmsm2pcs_pattern(lmsm2pcs_pattern),
    .lmsm2pcs_ltb_valid(lmsm2pcs_ltb_valid),
    .lmsm2pcs_lane_id_mode(lmsm2pcs_lane_id_mode),
    .lmsm2pcs_lane_id_base(lmsm2pcs_lane_id_base),
    .lmsm2pcs_lane_id_map(lmsm2pcs_lane_id_map),
    .lmsm2pcs_ltb_type(lmsm2pcs_ltb_type),
    .lmsm2pcs_link_id(lmsm2pcs_link_id),
    .lmsm2pcs_tlw(lmsm2pcs_tlw),
    .lmsm2pcs_rlw(lmsm2pcs_rlw),
    .lmsm2pcs_data_rate_support_1(lmsm2pcs_data_rate_support_1),
    .lmsm2pcs_data_rate_support_2(lmsm2pcs_data_rate_support_2),
    .lmsm2pcs_fec_mode_support(lmsm2pcs_fec_mode_support),
    .lmsm2pcs_port_type(lmsm2pcs_port_type),
    .lmsm2pcs_portnego_random_value(lmsm2pcs_portnego_random_value),
    .lmsm2pcs_fec_interleave_support(lmsm2pcs_fec_interleave_support),
    .lmsm2pcs_rx_lane0_id(lmsm2pcs_rx_lane0_id),
    .lmsm2pcs_max_link_width(lmsm2pcs_max_link_width),
    .lmsm2pcs_eq_mode(lmsm2pcs_eq_mode),
    .lmsm2pcs_fec_mode_ctrl(lmsm2pcs_fec_mode_ctrl),
    .lmsm2pcs_fec_interleave_ctrl(lmsm2pcs_fec_interleave_ctrl),
    .lmsm2pcs_eq_ctrl1(lmsm2pcs_eq_ctrl1),
    .lmsm2pcs_eq_ctrl2(lmsm2pcs_eq_ctrl2),
    .lmsm2pcs_eq_ctrl3(lmsm2pcs_eq_ctrl3),
    .lmsm2pcs_eq_ctrl4(lmsm2pcs_eq_ctrl4),
    .lmsm2pcs_fec_crc_mode_reject(lmsm2pcs_fec_crc_mode_reject),
    .lmsm2pcs_pre_fec_ber_meas_st(lmsm2pcs_pre_fec_ber_meas_st),
    .lmsm2pcs_fec_interleave_enable(lmsm2pcs_fec_interleave_enable),
    .lmsm2pcs_fec_interleave_ctrl_reject(lmsm2pcs_fec_interleave_ctrl_reject),
    .lmsm2pcs_request_equalization(lmsm2pcs_request_equalization),
    .lmsm2pcs_crc_mode_ctrl(lmsm2pcs_crc_mode_ctrl),
    .lmsm2pcs_local_tx_preset(lmsm2pcs_local_tx_preset),
    .lmsm2pcs_first_pre_cursor(lmsm2pcs_first_pre_cursor),
    .lmsm2pcs_eq_reject(lmsm2pcs_eq_reject),
    .lmsm2pcs_current_eq_phase(lmsm2pcs_current_eq_phase),
    .lmsm2pcs_preset_mode_en(lmsm2pcs_preset_mode_en),
    .lmsm2pcs_tx_preset(lmsm2pcs_tx_preset),
    .lmsm_st(lmsm_st),
    .train_fail(train_fail),
    .train_to_inc(train_to_inc),
    .tb_obs_link_ready(tb_obs_link_ready),
    .tb_obs_link_up(tb_obs_link_up),
    .tb_obs_lmsm_st(tb_obs_lmsm_st)
  );

  task tick;
    begin
      @(posedge core_clk);
      #0;
    end
  endtask

  task clr_pulses;
    begin
      pcs2lmsm_null_blk = 0;
      pcs2lmsm_tx_null_blk = 0;
      pcs2lmsm_rx_nonnull_blk = 0;
      pcs2lmsm_ltb_valid = 0;
    end
  endtask

  task do_reset;
    begin
      rst_pyc = 1;
      port_rst = 0;
      csr_lmsm_start = 0;
      pma_phy_ready = 0;
      clr_pulses();
      tick();
      tick();
      rst_pyc = 0;
      tick();
    end
  endtask

  task walk_to_null;
    begin
      csr_bypass_probe = 1;
      cfg_fixed_rate_rxeq = 0;
      cfg_null_need_rediscovery = 0;
      pma_phy_ready = 1;
      csr_lmsm_start = 1;
      pcs_am_locked = 1;
      pcs_deskew_ok = 1;
      pcs_lid_bad = 0;
      tick(); // Idle -> Discovery
      pcs2lmsm_ltb_valid = 1;
      pcs2lmsm_ltb_type = T_DLTB;
      tick(); // Disc sub0 -> sub1, capture DLTB
      tick(); // Disc sub1 -> Config
      pcs2lmsm_ltb_type = T_CLTB;
      tick(); // Config sub0 -> sub1, capture CLTB
      tick(); // Config sub1 -> sub2
      tick(); // Config sub2 -> Send_NullBlock
      clr_pulses();
      if (lmsm_st !== ST_NULL) begin
        $fatal(1, "walk_to_null: st=%0d", lmsm_st);
      end
      if (lmsm2pcs_nb_phase !== 1'b1)
        $fatal(1, "nb_phase must already be 1 on entry cycle s");
    end
  endtask

  integer i;
  reg seen_to;

  initial begin
    // ---- 7 vs 8 RX ----
    do_reset();
    walk_to_null();
    // entry cycle: pulses must be ignored
    pcs2lmsm_null_blk = 1;
    pcs2lmsm_tx_null_blk = 1;
    tick();
    if (dut.rx_cnt !== 0 || dut.tx_cnt !== 0 || dut.first_rx !== 0)
      $fatal(1, "entry-cycle pulses counted rx=%0d tx=%0d f=%0d",
             dut.rx_cnt, dut.tx_cnt, dut.first_rx);
    clr_pulses();
    // 7 RX + 16 TX
    for (i = 0; i < 7; i = i + 1) begin
      pcs2lmsm_null_blk = 1;
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    for (i = 0; i < 9; i = i + 1) begin
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    if (lmsm_st !== ST_NULL || dut.rx_cnt !== 7 || dut.tx_cnt < 16)
      $fatal(1, "7 RX must stay Null st=%0d rx=%0d tx=%0d",
             lmsm_st, dut.rx_cnt, dut.tx_cnt);
    pcs2lmsm_null_blk = 1;
    tick();
    clr_pulses();
    if (lmsm_st !== ST_ACTIVE)
      $fatal(1, "8th RX should go Active next edge st=%0d", lmsm_st);
    if (lmsm2pcs_nb_phase !== 1'b1)
      $fatal(1, "nb_phase must stay 1 through Link_Active");
    $display("PASS  sim-7-vs-8-rx");

    // ---- 15 vs 16 TX + same-cycle fill ----
    do_reset();
    walk_to_null();
    tick(); // consume entry
    for (i = 0; i < 8; i = i + 1) begin
      pcs2lmsm_null_blk = 1;
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    for (i = 0; i < 7; i = i + 1) begin
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    if (lmsm_st !== ST_NULL || dut.tx_cnt !== 15 || dut.rx_cnt !== 8)
      $fatal(1, "15 TX must stay Null st=%0d rx=%0d tx=%0d",
             lmsm_st, dut.rx_cnt, dut.tx_cnt);
    pcs2lmsm_tx_null_blk = 1;
    tick();
    clr_pulses();
    if (lmsm_st !== ST_ACTIVE)
      $fatal(1, "16th TX same-cycle fill -> Active next edge st=%0d", lmsm_st);
    $display("PASS  sim-15-vs-16-tx-and-same-cycle-fill");

    // ---- mid-count nonnull clears RX only ----
    do_reset();
    walk_to_null();
    tick();
    for (i = 0; i < 5; i = i + 1) begin
      pcs2lmsm_null_blk = 1;
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    if (dut.rx_cnt !== 5 || dut.tx_cnt !== 5 || dut.first_rx !== 1)
      $fatal(1, "pre-nonnull rx=%0d tx=%0d f=%0d", dut.rx_cnt, dut.tx_cnt, dut.first_rx);
    pcs2lmsm_rx_nonnull_blk = 1;
    tick();
    clr_pulses();
    if (dut.rx_cnt !== 0 || dut.tx_cnt !== 5 || dut.first_rx !== 1)
      $fatal(1, "nonnull should clear RX only rx=%0d tx=%0d f=%0d",
             dut.rx_cnt, dut.tx_cnt, dut.first_rx);
    $display("PASS  sim-nonnull-clears-rx-only");

    // ---- leave and re-enter resets to 0 ----
    cfg_null_need_rediscovery = 1;
    tick();
    cfg_null_need_rediscovery = 0;
    if (lmsm_st === ST_NULL)
      $fatal(1, "rediscovery should leave Null");
    if (lmsm2pcs_nb_phase !== 1'b0)
      $fatal(1, "nb_phase must drop the cycle st leaves Null|Active");
    if (dut.rx_cnt !== 0 || dut.tx_cnt !== 0 || dut.first_rx !== 0)
      $fatal(1, "leave Null must clear counts");
    // re-walk Config: already in Discovery after rediscovery
    pcs_am_locked = 1;
    pcs_deskew_ok = 1;
    pcs2lmsm_ltb_valid = 1;
    pcs2lmsm_ltb_type = T_DLTB;
    tick();
    tick();
    pcs2lmsm_ltb_type = T_CLTB;
    tick();
    tick();
    tick();
    clr_pulses();
    if (lmsm_st !== ST_NULL)
      $fatal(1, "re-enter Null failed st=%0d", lmsm_st);
    pcs2lmsm_null_blk = 1;
    pcs2lmsm_tx_null_blk = 1;
    tick();
    if (dut.rx_cnt !== 0 || dut.tx_cnt !== 0 || dut.first_rx !== 0)
      $fatal(1, "re-entry cycle must hold 0");
    $display("PASS  sim-leave-reenter-reset");

    // ---- timeout wins over same-cycle fill (HOOKS scale) ----
    do_reset();
    tb_test_mode = 1;
    csr_tmr_scale = 8'd255;
    tb_inj_am_lock = 1;
    tb_inj_lid_bad = 0;
    walk_to_null();
    // entry cycle
    tick();
    // wait until the timeout cycle, completing 8/16 on that cycle
    while (dut.tmr + 32'd255 * 15 < TMR_NULL) begin
      tick();
      if (lmsm_st !== ST_NULL) $fatal(1, "left Null early tmr=%0d", dut.tmr);
    end
    for (i = 0; i < 8; i = i + 1) begin
      pcs2lmsm_null_blk = 1;
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    for (i = 0; i < 7; i = i + 1) begin
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    // 16th TX on the first 2 ms timeout cycle (tmr_q already >= lim)
    pcs2lmsm_tx_null_blk = 1;
    if (dut.tmr < TMR_NULL)
      $fatal(1, "16th TX must share the timeout cycle tmr=%0d lim=%0d", dut.tmr, TMR_NULL);
    tick();
    clr_pulses();
    if (lmsm_st !== ST_RTR)
      $fatal(1, "timeout must win over fill st=%0d", lmsm_st);
    if (link_up !== 1'b1)
      $fatal(1, "A-22: link_up must stay 1 in Retrain");
    if (tb_obs_link_up !== 1'b0)
      $fatal(1, "tb_obs_link_up stays Null|Active, not Retrain");
    tb_test_mode = 0;
    csr_tmr_scale = 0;
    $display("PASS  sim-timeout-wins-fill");

    // ---- nb_phase: 1 on entry cycle s, hold through Active, drop on leave ----
    do_reset();
    if (lmsm2pcs_nb_phase !== 1'b0)
      $fatal(1, "nb_phase reset 0 got %0d", lmsm2pcs_nb_phase);
    walk_to_null();
    if (lmsm_st !== ST_NULL || lmsm2pcs_nb_phase !== 1'b1)
      $fatal(1, "nb_phase rises on entry cycle s st=%0d ph=%0d",
             lmsm_st, lmsm2pcs_nb_phase);
    tick();
    if (lmsm2pcs_nb_phase !== 1'b1)
      $fatal(1, "nb_phase must hold 1 while still Null");
    for (i = 0; i < 8; i = i + 1) begin
      pcs2lmsm_null_blk = 1;
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    for (i = 0; i < 8; i = i + 1) begin
      pcs2lmsm_tx_null_blk = 1;
      tick();
    end
    clr_pulses();
    if (lmsm_st !== ST_ACTIVE)
      $fatal(1, "nb_phase walk: expected Active st=%0d", lmsm_st);
    if (lmsm2pcs_nb_phase !== 1'b1)
      $fatal(1, "nb_phase must stay 1 through Link_Active");
    dll_retrain_req = 1;
    tick();
    dll_retrain_req = 0;
    if (lmsm_st !== ST_RTR)
      $fatal(1, "nb_phase leave: expected Retrain st=%0d", lmsm_st);
    if (lmsm2pcs_nb_phase !== 1'b0)
      $fatal(1, "nb_phase must drop the cycle st leaves Null|Active");
    $display("PASS  sim-nb-phase");

    // ---- PROBE_WAIT_CYC 323 / 1 / 0->323 and mid-wait rewrite ----
    do_reset();
    csr_bypass_probe = 0;
    pma_phy_ready = 1;
    csr_lmsm_start = 1;
    probe_wait_cyc = 16'd323;
    tick(); // Idle -> Probe, sample 323
    if (lmsm_st !== ST_PROBE) $fatal(1, "did not enter Probe");
    if (dut.probe_lim !== 16'd323)
      $fatal(1, "sample 323 failed lim=%0d", dut.probe_lim);
    seen_to = 0;
    for (i = 0; i < 400; i = i + 1) begin
      if (dut.probe_tmr >= dut.probe_lim) begin
        seen_to = 1;
        if (dut.probe_tmr !== 16'd323)
          $fatal(1, "323 timeout at tmr=%0d", dut.probe_tmr);
        i = 400;
      end
      else tick();
    end
    if (!seen_to) $fatal(1, "323 wait never reached");
    $display("PASS  sim-probe-323");

    do_reset();
    csr_bypass_probe = 0;
    pma_phy_ready = 1;
    csr_lmsm_start = 1;
    probe_wait_cyc = 16'd1;
    tick();
    if (dut.probe_lim !== 16'd1) $fatal(1, "sample 1 failed lim=%0d", dut.probe_lim);
    tick(); // tmr 0 -> 1
    tick(); // tmr==1 timeout
    if (dut.probe_tmr !== 16'd0)
      $fatal(1, "after lim=1 timeout expect retry tmr=0 got %0d", dut.probe_tmr);
    if (dut.probe_try !== 8'd1)
      $fatal(1, "lim=1 retry should bump probe_try got %0d", dut.probe_try);
    $display("PASS  sim-probe-1");

    do_reset();
    csr_bypass_probe = 0;
    pma_phy_ready = 1;
    csr_lmsm_start = 1;
    probe_wait_cyc = 16'd0;
    tick();
    if (dut.probe_lim !== 16'd323)
      $fatal(1, "0 must fold to 323 lim=%0d", dut.probe_lim);
    $display("PASS  sim-probe-0-folds-323");

    do_reset();
    csr_bypass_probe = 0;
    pma_phy_ready = 1;
    csr_lmsm_start = 1;
    probe_wait_cyc = 16'd323;
    tick();
    if (dut.probe_lim !== 16'd323) $fatal(1, "mid-wait start lim");
    tick();
    tick();
    probe_wait_cyc = 16'd1; // rewrite during wait
    for (i = 0; i < 400; i = i + 1) begin
      if (dut.probe_tmr >= 16'd323 && dut.probe_lim === 16'd323) begin
        i = 400;
      end
      else begin
        if (dut.probe_lim !== 16'd323)
          $fatal(1, "rewrite applied mid-wait lim=%0d", dut.probe_lim);
        tick();
      end
    end
    // timeout cycle of first wait: retry samples the rewritten 1
    tick();
    if (dut.probe_lim !== 16'd1)
      $fatal(1, "next wait must sample rewrite lim=%0d", dut.probe_lim);
    $display("PASS  sim-probe-mid-wait-rewrite");

    if (lmsm2pcs_data_rate_support_2[7] !== 1'b0)
      $fatal(1, "Change_Speed bit7 must stay 0");
    $display("PASS  sim-chg-spd-bit7");
    $display("DIRECTED_SIM_PASS");
    $finish;
  end
endmodule
"""


def check_directed_sim() -> None:
    if shutil.which("verilator") is None:
        _fail("directed-sim", "verilator not on PATH")
    with tempfile.TemporaryDirectory(prefix="ub-lmsm-sim-") as td:
        td_path = Path(td)
        tb = td_path / "lmsm_directed.sv"
        tb.write_text(_directed_sv(), encoding="utf-8")
        obj = td_path / "obj"
        cmd = [
            "verilator",
            "--binary",
            "--timing",
            "--public",
            "-Wno-DECLFILENAME",
            "-Wno-UNUSEDSIGNAL",
            "-Wno-TIMESCALEMOD",
            "--top-module",
            "lmsm_directed",
            f"-I{_incdir()}",
            "-Mdir",
            str(obj),
            str(HOOKS_V),
            str(tb),
        ]
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        text = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            _fail("directed-sim", f"verilator --binary failed\\n{text[-1500:]}")
        exe = obj / "Vlmsm_directed"
        if not exe.is_file():
            # Verilator 5.020 names the binary after --top-module
            cands = list(obj.glob("V*"))
            exe = next((p for p in cands if p.is_file() and os.access(p, os.X_OK)), exe)
        run = subprocess.run(
            [str(exe)],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = (run.stdout or "") + (run.stderr or "")
        if run.returncode != 0 or "DIRECTED_SIM_PASS" not in out:
            _fail("directed-sim", out[-2000:])
        cases = [ln[6:] for ln in out.splitlines() if ln.startswith("PASS  sim-")]
        _ok("directed-sim", ", ".join(cases))


def python_counter_model() -> None:
    """Golden of the #41 count rules (entry hold-0, nonnull RX-only, sat)."""
    rx = tx = first = 0
    seen = 0

    def step(in_null, null_blk, nonnull, tx_blk):
        nonlocal rx, tx, first, seen
        count_en = in_null and seen
        if not in_null or not count_en or nonnull:
            rx_n = 0
        elif null_blk:
            rx_n = min(rx + 1, P_NULL_RX_NEED)
        else:
            rx_n = rx
        if not in_null or not count_en:
            first_n = 0
            tx_n = 0
        else:
            first_n = first | null_blk
            gate = first or null_blk
            tx_n = min(tx + 1, P_NULL_TX_NEED) if gate and tx_blk else tx
        fill = rx_n == P_NULL_RX_NEED and tx_n >= P_NULL_TX_NEED
        rx, tx, first = rx_n, tx_n, first_n
        seen = 1 if in_null else 0
        return fill

    # entry pulses ignored
    if step(True, 1, 0, 1):
        _fail("py-null-model", "entry fill")
    if (rx, tx, first) != (0, 0, 0):
        _fail("py-null-model", "entry hold-0")
    # 7 RX + 16 TX: no fill
    for _ in range(7):
        step(True, 1, 0, 1)
    for _ in range(9):
        step(True, 0, 0, 1)
    if rx != 7 or tx < 16 or step(True, 0, 0, 0):
        _fail("py-null-model", f"7 RX fill? rx={rx} tx={tx}")
    if not step(True, 1, 0, 0):
        _fail("py-null-model", "8th RX should fill")
    # reset and 15 vs 16 TX
    rx = tx = first = seen = 0
    step(True, 0, 0, 0)
    for _ in range(8):
        step(True, 1, 0, 1)
    for _ in range(7):
        step(True, 0, 0, 1)
    if tx != 15 or step(True, 0, 0, 0):
        _fail("py-null-model", f"15 TX fill? tx={tx}")
    if not step(True, 0, 0, 1):
        _fail("py-null-model", "16th TX should fill")
    # nonnull clears RX only
    rx = tx = first = seen = 0
    step(True, 0, 0, 0)
    for _ in range(5):
        step(True, 1, 0, 1)
    step(True, 0, 1, 0)
    if (rx, tx, first) != (0, 5, 1):
        _fail("py-null-model", f"nonnull {rx},{tx},{first}")
    # leave clears all
    step(False, 1, 0, 1)
    if (rx, tx, first) != (0, 0, 0):
        _fail("py-null-model", "leave clear")
    _ok("python-null-model", "7/8 RX, 15/16 TX, entry-0, nonnull RX-only, leave-0")


def main() -> int:
    check_source()
    check_netlist_text()
    python_counter_model()
    check_emit_repro()
    check_lint()
    check_logic_depth()
    check_equiv()
    check_directed_sim()
    print()
    print(f"{'check':<32} result")
    print("-" * 60)
    for name, detail in RESULTS:
        print(f"{name:<32} {detail}")
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
