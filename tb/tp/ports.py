"""ub_tp_bypass port contract (LAYER_CONTRACTS §2 / §3; wave-1 CFG9).

Unknown-width / unknown-encoding ports are omitted (tp_uarch Unknown items).
Clock is ``core_clk``. Business reset is ``rst_pyc``. SPEC §10 lists no
``tb_*`` hooks.
"""

from __future__ import annotations

from pathlib import Path

from tb.cmn.ports import parse_module_port_widths, parse_module_ports

LEAF = "ub_tp_bypass"
CLK_PORT = "core_clk"
RST_PORT = "rst_pyc"

# name -> (dir, width)
PORTS: dict[str, tuple[str, int]] = {
    "core_clk": ("input", 1),
    "rst_pyc": ("input", 1),
    "ta2tp_data": ("input", 160),
    "ta2tp_valid": ("input", 1),
    "ta2tp_ready": ("output", 1),
    "ta2tp_sop": ("input", 1),
    "ta2tp_eop": ("input", 1),
    "ta2tp_op_valid": ("input", 1),
    "ta2tp_op_ready": ("output", 1),
    "ta2tp_bypass": ("input", 1),
    "ta2tp_dcna": ("input", 16),
    "tp2nw_data": ("output", 160),
    "tp2nw_valid": ("output", 1),
    "tp2nw_ready": ("input", 1),
    "tp2nw_sop": ("output", 1),
    "tp2nw_eop": ("output", 1),
    "tp2nw_bypass": ("output", 1),
    "tp2nw_dcna": ("output", 16),
    "tp2nw_sl": ("output", 4),
    "tp2nw_nlp": ("output", 3),
    "tp2nw_lbf": ("output", 8),
    "tp2nw_rt": ("output", 2),
    "tp2nw_cci": ("output", 16),
    "nw2tp_data": ("input", 160),
    "nw2tp_valid": ("input", 1),
    "nw2tp_ready": ("output", 1),
    "nw2tp_sop": ("input", 1),
    "nw2tp_eop": ("input", 1),
    "nw2tp_err": ("input", 1),
    "nw2tp_flush": ("input", 1),
    "nw_link_up": ("input", 1),
    "tp2ta_data": ("output", 160),
    "tp2ta_valid": ("output", 1),
    "tp2ta_ready": ("input", 1),
    "tp2ta_sop": ("output", 1),
    "tp2ta_eop": ("output", 1),
    "tp2ta_err": ("output", 1),
}

UNKNOWN_OMITTED: tuple[str, ...] = (
    "ta2tp_op_len",
    "ta2tp_mode",
    "ta2tp_cmp_rspst",
    "ta2tp_cmp_rspinfo",
    "tp2nw_dcna24",
    "nw2tp_icrc_err",
)

REPO = Path(__file__).resolve().parents[2]
PRODUCT = REPO / "rtl" / "tp" / f"{LEAF}.v"
HOOKS = REPO / "rtl" / "tp" / "hooks" / f"{LEAF}.v"


def check_ports(text: str, module: str = LEAF) -> None:
    names = parse_module_ports(text, module)
    widths = parse_module_port_widths(text, module)
    have = set(names)
    want = set(PORTS)
    if have != want:
        raise AssertionError(
            f"{module} ports {sorted(have)} != {sorted(want)}; "
            f"missing={sorted(want - have)} extra={sorted(have - want)}"
        )
    for name in UNKNOWN_OMITTED:
        if name in have:
            raise AssertionError(f"{module} must omit unknown port {name}")
    for name, (_d, width) in PORTS.items():
        got = widths.get(name)
        if got != width:
            raise AssertionError(f"{module}.{name} width {got} != {width}")
    if any(n.startswith("tb_") for n in names):
        raise AssertionError(f"{module} has tb_* ports; SPEC §10 lists none")


__all__ = [
    "CLK_PORT",
    "HOOKS",
    "LEAF",
    "PORTS",
    "PRODUCT",
    "RST_PORT",
    "UNKNOWN_OMITTED",
    "check_ports",
]
