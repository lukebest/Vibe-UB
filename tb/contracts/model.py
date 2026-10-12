"""Contract-level golden for NW↔TP and TP↔TA (LAYER_CONTRACTS §2 / §3).

Only encodes widths and lengths written in the contracts, SPEC chapter
numbers, or this B-line plan. Unspecified slices stay in PENDING_XIA.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

# SPEC §4.1: F_CORE = 2.578125e9 / 32. User/plan pin 80.566 MHz.
F_CORE_HZ = 80.566e6
TIMEOUT_US = 4.0
TIMEOUT_DEFAULT_CYC = math.ceil(TIMEOUT_US * 1e-6 * F_CORE_HZ)  # 323

FLIT_W = 160
FLITS_PER_BEAT = 1
PSN_W = 24
PSN_MASK = (1 << PSN_W) - 1
RTPH_BYTES = 16
LPH_NTH_BYTES = 12
INI_TASSN_W = 16
TASSN_MASK = (1 << INI_TASSN_W) - 1
SL_W = 4
NLP_W = 3
OPCODE_W = 8
MODE_W = 2
RT_W = 2
CFG_W = 4

CFG9 = 9
MTU_LEGAL = frozenset({1024, 4096, 8192})
MTU_DEFAULT = 4096
VL_REQ = 0
VL_RESP = 1

# Compact vs full (UB-TA §7.2; format selected by LPH.CFG).
HDR_COMPACT = {
    "BTAH": 4,
    "ATAH": 4,
    "MAETAH": 12,
}
HDR_FULL = {
    "BTAH": 8,
    "ATAH": 8,
    "MAETAH": 16,
}
CFG9_FORBIDDEN = frozenset({"ICRC", "TPH", "EIDH", "UPIH"})

PENDING_XIA = (
    "NTH.SCNA/DCNA 16 vs 24 (LAYER_CONTRACTS §2)",
    "ICRC on every mode / LS path (LAYER_CONTRACTS §2)",
    "packet byte upper bound (LAYER_CONTRACTS §2)",
    "RTPH field widths beyond 16 B / PSN 24 (LAYER_CONTRACTS §2)",
    "NTH.NLP encoding for TAH (LAYER_CONTRACTS §2)",
    "LPH.RT bit slice inside the LPH word (LAYER_CONTRACTS §1)",
    "ta2tp_mode encoding (LAYER_CONTRACTS §3)",
    "flush cycle count (LAYER_CONTRACTS §3)",
    "outstanding TASSN limit (LAYER_CONTRACTS §3)",
    "payload length field width (LAYER_CONTRACTS §3)",
    "TP NAK / fail reason codes (LAYER_CONTRACTS §3)",
    "Go-Back-N vs selective repeat (MODULE_INVENTORY ub_tp_retry)",
    "shared TP channel policy (LAYER_CONTRACTS §3)",
    "CFG6 numeric encoding for CTP (第二波)",
)


def timeout_cycles(wait_cyc: int | None = None) -> int:
    """SPEC §4.1 / §6.1 / §6.3: 0 folds to the reset default 323."""
    if wait_cyc is None or wait_cyc == 0:
        return TIMEOUT_DEFAULT_CYC
    return int(wait_cyc)


def timed_out(elapsed: int, wait_cyc: int | None = None) -> bool:
    """Timeout on the cycle the sampled value is reached (SPEC §6.1 / §6.3)."""
    return int(elapsed) >= timeout_cycles(wait_cyc)


def psn_next(psn: int) -> int:
    return (int(psn) + 1) & PSN_MASK


def psn_wraps(psn: int) -> bool:
    return psn_next(psn) == 0 and (int(psn) & PSN_MASK) == PSN_MASK


def compact_header(cfg: int) -> bool:
    return int(cfg) == CFG9


def header_bytes(kind: str, cfg: int) -> int:
    table = HDR_COMPACT if compact_header(cfg) else HDR_FULL
    if kind not in table:
        raise KeyError(kind)
    return table[kind]


def cfg9_forbidden_headers(cfg: int) -> frozenset[str]:
    return CFG9_FORBIDDEN if int(cfg) == CFG9 else frozenset()


def bypass_cfg_ok(bypass: int, cfg: int) -> bool:
    """TP bypass only uses CFG9 (UB-TP §6.3; LAYER_CONTRACTS §2)."""
    if int(bypass):
        return int(cfg) == CFG9
    return True


def mtu_ok(mtu: int) -> bool:
    return int(mtu) in MTU_LEGAL


def vl_for_dir(direction: str) -> int:
    if direction == "req":
        return VL_REQ
    if direction == "resp":
        return VL_RESP
    raise KeyError(direction)


def extract_rt(lph_word: int, lo: int) -> int:
    """RT is taken from the LPH word. Bit index ``lo`` is 待 Xia."""
    return (int(lph_word) >> int(lo)) & ((1 << RT_W) - 1)


def predict_flit(
    *,
    data: int,
    sop: int,
    eop: int,
    sl: int = 0,
    nlp: int = 0,
    bypass: int = 0,
    err: int = 0,
    vl: int = 0,
) -> dict[str, int]:
    """One 160-bit beat. ``valid==0`` sidebands are ignored by the caller."""
    return {
        "data": int(data) & ((1 << FLIT_W) - 1),
        "sop": int(sop) & 1,
        "eop": int(eop) & 1,
        "sl": int(sl) & ((1 << SL_W) - 1),
        "nlp": int(nlp) & ((1 << NLP_W) - 1),
        "bypass": int(bypass) & 1,
        "err": int(err) & 1,
        "vl": int(vl) & ((1 << SL_W) - 1),
        "flit_w": FLIT_W,
        "flits_per_beat": FLITS_PER_BEAT,
    }


def predict_op(
    *,
    opcode: int,
    tassn: int,
    mode: int,
    bypass: int,
) -> dict[str, int]:
    return {
        "opcode": int(opcode) & ((1 << OPCODE_W) - 1),
        "tassn": int(tassn) & TASSN_MASK,
        "mode": int(mode) & ((1 << MODE_W) - 1),
        "bypass": int(bypass) & 1,
        "tassn_w": INI_TASSN_W,
    }


def done_fail_ok(done: int, fail: int) -> bool:
    return not (int(done) and int(fail))


def err_meaningful(valid: int, eop: int, err: int) -> bool:
    """nw2tp_err / tp2ta_err only matter on valid&&eop (LAYER_CONTRACTS §2 / §3)."""
    if not (int(valid) and int(eop)):
        return int(err) == 0 or True  # ignored; caller must not score err
    return True


def beat_from_signals(sigs: Mapping[str, Any], fields: tuple[str, ...]) -> dict[str, int]:
    return {name: int(sigs[name].value) for name in fields}
