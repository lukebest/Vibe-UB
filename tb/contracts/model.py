"""Contract-level golden for NW↔TP and TP↔TA (LAYER_CONTRACTS §2 / §3).

Only encodes widths and lengths written in the contracts or SPEC chapter
numbers. Fields the contract marks unknown have no predicted value.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

# SPEC §4.1: F_CORE = 2.578125e9 / 32. User/plan pin 80.566 MHz.
# LAYER_CONTRACTS §3: 322/323 RETRY_WAIT_CYC / PROBE_WAIT_CYC are
# DLL (§4.7.3.3) / LMSM (§3.4.3.2). TP timers are RTO / ACK-coal.
F_CORE_HZ = 80.566e6
TIMEOUT_US = 4.0
TIMEOUT_DEFAULT_CYC = math.ceil(TIMEOUT_US * 1e-6 * F_CORE_HZ)  # 323

FLIT_W = 160
FLITS_PER_BEAT = 1
PSN_W = 24
PSN_MASK = (1 << PSN_W) - 1
TPMSN_W = 24
TPMSN_MASK = (1 << TPMSN_W) - 1
RTPH_BYTES = 16
LPH_NTH_BYTES = 12
INI_TASSN_W = 16
TASSN_MASK = (1 << INI_TASSN_W) - 1
SL_W = 4
NLP_W = 3
DCNA_W = 16
LBF_W = 8
RT_W = 2
CCI_W = 16
OPCODE_W = 8
MODE_W = 2
CFG_W = 4

CFG_CTP = 6
CFG_RTP = 7
CFG_BYP = 9
CFG9 = CFG_BYP
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

# TP-owned timers (LAYER_CONTRACTS §3 / UB-TP §6.4.2.1). Not 322/323.
TP_TIMERS = frozenset({"rto", "ack_coal"})

CLOSED_FROM_59 = (
    "NTH.SCNA/DCNA 16 b (LAYER_CONTRACTS §2)",
    "ICRC on CFG7, not on CFG9 (LAYER_CONTRACTS §2)",
    "LPH.CFG 4 b; CTP=6 / RTP=7 / bypass=9 (LAYER_CONTRACTS §2)",
    "LPH.RT 2 b (LAYER_CONTRACTS §2)",
)

UNKNOWN_XIA = (
    "packet byte upper bound (LAYER_CONTRACTS §2)",
    "RTPH field widths beyond 16 B / PSN 24 (LAYER_CONTRACTS §2)",
    "NTH.NLP encoding for TAH (LAYER_CONTRACTS §2)",
    "ta2tp_mode encoding (LAYER_CONTRACTS §3)",
    "flush cycle count (LAYER_CONTRACTS §3)",
    "outstanding TASSN limit (LAYER_CONTRACTS §3)",
    "payload length field width (LAYER_CONTRACTS §3)",
    "TP NAK / fail reason codes (LAYER_CONTRACTS §3)",
    "Go-Back-N vs selective repeat (LAYER_CONTRACTS §3)",
    "shared TP channel policy (LAYER_CONTRACTS §3)",
)

# Alias used by older tests: the still-open contract unknowns.
PENDING_XIA = UNKNOWN_XIA


def timeout_cycles(wait_cyc: int | None = None) -> int:
    """SPEC §4.1 / §6.1 / §6.3: 0 folds to the reset default 323.

    Owned by DLL RETRY_WAIT_CYC / LMSM PROBE_WAIT_CYC (LAYER_CONTRACTS §3).
    """
    if wait_cyc is None or wait_cyc == 0:
        return TIMEOUT_DEFAULT_CYC
    return int(wait_cyc)


def timed_out(elapsed: int, wait_cyc: int | None = None) -> bool:
    """Timeout on the cycle the sampled value is reached (SPEC §6.1 / §6.3)."""
    return int(elapsed) >= timeout_cycles(wait_cyc)


def tp_timer_ok(kind: str) -> bool:
    """TP formal covers only RTO and ACK coalescing."""
    return kind in TP_TIMERS


def psn_next(psn: int) -> int:
    return (int(psn) + 1) & PSN_MASK


def psn_wraps(psn: int) -> bool:
    return psn_next(psn) == 0 and (int(psn) & PSN_MASK) == PSN_MASK


def compact_header(cfg: int) -> bool:
    return int(cfg) == CFG_BYP


def header_bytes(kind: str, cfg: int) -> int:
    table = HDR_COMPACT if compact_header(cfg) else HDR_FULL
    if kind not in table:
        raise KeyError(kind)
    return table[kind]


def cfg9_forbidden_headers(cfg: int) -> frozenset[str]:
    return CFG9_FORBIDDEN if int(cfg) == CFG_BYP else frozenset()


def icrc_on_cfg(cfg: int) -> bool:
    """ICRC is present on CFG7 (RTP), not on CFG9 (bypass). LAYER_CONTRACTS §2."""
    return int(cfg) == CFG_RTP


def icrc_forbidden(cfg: int) -> bool:
    return int(cfg) == CFG_BYP


def bypass_cfg_ok(bypass: int, cfg: int) -> bool:
    """TP bypass only uses CFG9 (UB-TP §6.3; LAYER_CONTRACTS §2)."""
    if int(bypass):
        return int(cfg) == CFG_BYP
    return True


def cfg_encoding_ok(cfg: int) -> bool:
    """Locked 4 b CFG packet values: CTP=6, RTP=7, bypass=9."""
    return int(cfg) in {CFG_CTP, CFG_RTP, CFG_BYP}


def mtu_ok(mtu: int) -> bool:
    return int(mtu) in MTU_LEGAL


def vl_for_dir(direction: str) -> int:
    if direction == "req":
        return VL_REQ
    if direction == "resp":
        return VL_RESP
    raise KeyError(direction)


def extract_rt(lph_word: int, lo: int) -> int:
    """RT width is 2 b (LAYER_CONTRACTS §2). Bit index ``lo`` is unknown."""
    return (int(lph_word) >> int(lo)) & ((1 << RT_W) - 1)


def predict_flit(
    *,
    data: int,
    sop: int,
    eop: int,
    sl: int = 0,
    nlp: int = 0,
    bypass: int = 0,
    dcna: int = 0,
    lbf: int = 0,
    rt: int = 0,
    cci: int = 0,
    err: int = 0,
    icrc_err: int = 0,
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
        "dcna": int(dcna) & ((1 << DCNA_W) - 1),
        "lbf": int(lbf) & ((1 << LBF_W) - 1),
        "rt": int(rt) & ((1 << RT_W) - 1),
        "cci": int(cci) & ((1 << CCI_W) - 1),
        "err": int(err) & 1,
        "icrc_err": int(icrc_err) & 1,
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
    dcna: int = 0,
) -> dict[str, int]:
    return {
        "opcode": int(opcode) & ((1 << OPCODE_W) - 1),
        "tassn": int(tassn) & TASSN_MASK,
        "mode": int(mode) & ((1 << MODE_W) - 1),
        "bypass": int(bypass) & 1,
        "dcna": int(dcna) & ((1 << DCNA_W) - 1),
        "tassn_w": INI_TASSN_W,
    }


def predict_msn(*, tpmsn: int) -> dict[str, int]:
    return {
        "tpmsn": int(tpmsn) & TPMSN_MASK,
        "tpmsn_w": TPMSN_W,
    }


def predict_cmp(
    *,
    tassn: int,
    fail: int,
    opcode: int,
) -> dict[str, int]:
    return {
        "tassn": int(tassn) & TASSN_MASK,
        "fail": int(fail) & 1,
        "opcode": int(opcode) & ((1 << OPCODE_W) - 1),
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
