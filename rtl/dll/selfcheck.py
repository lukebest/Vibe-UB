#!/usr/bin/env python3
"""Generator + SPEC §6.3 / §6.4 transfer self-check (not a verification TB).

Proves emit() runs, PRODUCT has no hooks / no reserved encodings, and a
cycle-accurate Python model of the two SMs walks every SPEC transfer.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ub_dll_retry_ack_sm as ack
import ub_dll_retry_req_sm as req

ST_N, ST_Q, ST_W, ST_R, ST_E = (
    req.ST_NORMAL,
    req.ST_REQ,
    req.ST_WAIT,
    req.ST_RETRAIN,
    req.ST_ERROR,
)
ACK_N, ACK_A = ack.ST_NORMAL, ack.ST_ACK
SUB_SET, SUB_REPLAY = ack.SUB_SET, ack.SUB_REPLAY


@dataclass
class ReqS:
    st: int = ST_N
    num_retry: int = 0
    num_phy: int = 0
    tmr: int = 0
    retry_req_inc: int = 0
    retry_to_inc: int = 0


def step_req(
    s: ReqS,
    *,
    rst_eff: int = 0,
    start_retry: int = 0,
    lmsm_retrain_ack: int = 0,
    retry_req_set_done: int = 0,
    retry_ack_set_rx: int = 0,
    phy_retrain_ok: int = 0,
    num_retry_th: int = req.NUM_RETRY_THRESHOLD,
    num_phy_th: int = req.NUM_PHY_REINIT_THRESHOLD,
    wait_cyc: int = req.RETRY_WAIT_CYC,
    cnt_sat: int = 0xFF,
    tmr_sat: int = 0xFFFFFFFF,
) -> ReqS:
    """One-cycle model matching ub_dll_retry_req_sm.v (SPEC §6.3)."""
    if rst_eff:
        return ReqS()
    st_n = s.st
    num_retry_n = s.num_retry
    num_phy_n = s.num_phy
    tmr_n = s.tmr
    try_enter_req = 0
    enter_retrain = 0
    wait_timeout = 0
    num_retry_inc = s.num_retry if s.num_retry == cnt_sat else s.num_retry + 1
    num_phy_inc = s.num_phy if s.num_phy == cnt_sat else s.num_phy + 1
    retry_hits_th = int(num_retry_inc == num_retry_th)
    phy_hits_th = int(num_phy_inc == num_phy_th)
    tmr_inc = s.tmr if s.tmr == tmr_sat else s.tmr + 1
    tmr_to = int(s.tmr >= wait_cyc)

    if s.st == ST_N:
        tmr_n = 0
        if lmsm_retrain_ack:
            enter_retrain = 1
        elif start_retry:
            try_enter_req = 1
    elif s.st == ST_Q:
        tmr_n = 0
        if lmsm_retrain_ack:
            enter_retrain = 1
            num_retry_n = 0
        elif retry_req_set_done:
            st_n = ST_W
            tmr_n = 0
    elif s.st == ST_W:
        tmr_n = tmr_inc
        if lmsm_retrain_ack:
            enter_retrain = 1
        elif retry_ack_set_rx:
            st_n = ST_N
        elif tmr_to:
            wait_timeout = 1
            try_enter_req = 1
    elif s.st == ST_R:
        tmr_n = 0
        if phy_retrain_ok and not lmsm_retrain_ack:
            try_enter_req = 1
    elif s.st == ST_E:
        tmr_n = 0
        st_n = ST_E
    else:
        st_n = ST_N
        num_retry_n = 0
        num_phy_n = 0
        tmr_n = 0

    if try_enter_req:
        if retry_hits_th:
            num_retry_n = 0
            enter_retrain = 1
        else:
            st_n = ST_Q
            num_retry_n = num_retry_inc

    if enter_retrain:
        if phy_hits_th:
            st_n = ST_E
            num_phy_n = 0
        else:
            st_n = ST_R
            num_phy_n = num_phy_inc

    enter_req = int(st_n == ST_Q and s.st != ST_Q)
    return ReqS(
        st=st_n,
        num_retry=num_retry_n,
        num_phy=num_phy_n,
        tmr=tmr_n,
        retry_req_inc=enter_req,
        retry_to_inc=wait_timeout,
    )


@dataclass
class AckS:
    st: int = ACK_N
    sub: int = SUB_SET


def step_ack(
    s: AckS,
    *,
    rst_eff: int = 0,
    retry_req_set_rx: int = 0,
    retry_ack_set_done: int = 0,
    replay_done: int = 0,
) -> AckS:
    """One-cycle model matching ub_dll_retry_ack_sm.v (SPEC §6.4)."""
    if rst_eff:
        return AckS()
    st_n = s.st
    sub_n = s.sub
    if s.st == ACK_N:
        sub_n = SUB_SET
        if retry_req_set_rx:
            st_n = ACK_A
    elif s.st == ACK_A:
        if s.sub == SUB_REPLAY and retry_req_set_rx:
            sub_n = SUB_SET
        elif s.sub == SUB_SET and retry_ack_set_done and replay_done:
            st_n = ACK_N
            sub_n = SUB_SET
        elif s.sub == SUB_SET and retry_ack_set_done:
            sub_n = SUB_REPLAY
        elif s.sub == SUB_REPLAY and replay_done:
            st_n = ACK_N
            sub_n = SUB_SET
    else:
        st_n = ACK_N
        sub_n = SUB_SET
    return AckS(st=st_n, sub=sub_n)


def _ports_block(text: str) -> str:
    return text.split("module", 1)[1].split(");", 1)[0]


def _static_leaf(path: Path, module: str, *, reserved_needles: tuple[str, ...]) -> str:
    text = path.read_text(encoding="utf-8")
    assert "module " in text
    assert "`ifdef" not in text
    assert "$display" not in text
    assert "force " not in text
    assert "negedge rst_n" not in text
    assert "or negedge" not in text
    mod = text.split("module ", 1)[1].split("(", 1)[0].split("#", 1)[0].strip()
    assert path.stem == mod == module, f"DECLFILENAME {path.name} vs {mod}"
    for token in ("tb_test_mode", "tb_inj_", "tb_obs_"):
        assert token not in text
    for needle in reserved_needles:
        for line in text.splitlines():
            if "st_n" in line:
                assert needle not in line, line
    return text


def main() -> int:
    req_v = req.generate()
    ack_v = ack.generate()
    req_txt = _static_leaf(
        req_v,
        "ub_dll_retry_req_sm",
        reserved_needles=("3'd5", "3'd6", "3'd7", "3'b101", "3'b110", "3'b111"),
    )
    ack_txt = _static_leaf(
        ack_v,
        "ub_dll_retry_ack_sm",
        reserved_needles=("2'd2", "2'd3", "2'b10", "2'b11"),
    )

    hooks = HERE / "hooks"
    assert not hooks.exists(), "SPEC §10 lists no hooks; do not emit hooks/"

    req_ports = _ports_block(req_txt)
    for name in (
        "core_clk",
        "rst_pyc",
        "port_rst",
        "lmsm_retrain_ack",
        "dll_retrain_req",
        "start_retry",
        "retry_req_set_done",
        "retry_ack_set_rx",
        "phy_retrain_ok",
        "retry_req_st",
        "retry_req_inc",
        "retry_to_inc",
        "retry_err",
    ):
        assert name in req_ports, name
    # Do not silently grow Switch-only pins (D9 names that SPEC does not give).
    for banned in ("device_rst", "send_cnt", "wr_ptr", "rd_ptr", "rst_n"):
        assert banned not in req_ports, banned

    ack_ports = _ports_block(ack_txt)
    for name in (
        "core_clk",
        "rst_pyc",
        "port_rst",
        "retry_req_set_rx",
        "retry_ack_set_done",
        "replay_done",
        "retry_ack_st",
    ):
        assert name in ack_ports, name
    for banned in ("device_rst", "wr_ptr", "rcv_ptr", "rd_ptr", "send_cnt"):
        assert banned not in ack_ports, banned

    # --- SPEC §6.3 transfers ---
    s = ReqS()
    s = step_req(s, rst_eff=1)
    assert s.st == ST_N and s.num_retry == 0 and s.num_phy == 0

    s = step_req(s, start_retry=1)
    assert s.st == ST_Q and s.num_retry == 1 and s.retry_req_inc == 1

    s = step_req(s, retry_req_set_done=1)
    assert s.st == ST_W

    s = step_req(s, retry_ack_set_rx=1)
    assert s.st == ST_N

    # WAIT timeout → REQ (SPEC §6.3). Use wait_cyc=1 so tmr>=1 after one WAIT beat.
    s = step_req(ReqS(st=ST_W, tmr=0, num_retry=1), wait_cyc=1)
    # first WAIT cycle increments tmr; tmr_to uses *current* tmr (0) so not yet
    s = step_req(s, wait_cyc=1)
    assert s.st == ST_Q and s.num_retry == 2 and s.retry_to_inc == 1

    # 15th REQ entry (NUM_RETRY_THRESHOLD=15) → RETRAIN, clear NUM_RETRY
    s = ReqS(st=ST_N, num_retry=14)
    s = step_req(s, start_retry=1)
    assert s.st == ST_R and s.num_retry == 0 and s.num_phy == 1

    # RETRAIN success → REQ
    s = step_req(s, phy_retrain_ok=1)
    assert s.st == ST_Q and s.num_retry == 1

    # PHY retrain from NORMAL → RETRAIN
    s = step_req(ReqS(), lmsm_retrain_ack=1)
    assert s.st == ST_R and s.num_phy == 1

    # PHY retrain from REQ clears NUM_RETRY
    s = step_req(ReqS(st=ST_Q, num_retry=3), lmsm_retrain_ack=1)
    assert s.st == ST_R and s.num_retry == 0 and s.num_phy == 1

    # 4th RETRAIN entry → ERROR, clear NUM_PHY_REINIT
    s = ReqS(st=ST_N, num_phy=3)
    s = step_req(s, lmsm_retrain_ack=1)
    assert s.st == ST_E and s.num_phy == 0

    # ERROR holds until PORT_RST
    s = step_req(s, start_retry=1, phy_retrain_ok=1, retry_ack_set_rx=1)
    assert s.st == ST_E
    s = step_req(s, rst_eff=1)
    assert s.st == ST_N and s.num_retry == 0 and s.num_phy == 0

    # Reserved encodings never produced
    for st in (ST_N, ST_Q, ST_W, ST_R, ST_E):
        for bits in range(32):
            kwargs = dict(
                start_retry=bits & 1,
                lmsm_retrain_ack=(bits >> 1) & 1,
                retry_req_set_done=(bits >> 2) & 1,
                retry_ack_set_rx=(bits >> 3) & 1,
                phy_retrain_ok=(bits >> 4) & 1,
            )
            n = step_req(ReqS(st=st, num_retry=1, num_phy=1, tmr=10), **kwargs)
            assert n.st in (ST_N, ST_Q, ST_W, ST_R, ST_E), n.st

    # --- SPEC §6.4 transfers ---
    a = AckS()
    a = step_ack(a, rst_eff=1)
    assert a.st == ACK_N and a.sub == SUB_SET

    a = step_ack(a, retry_req_set_rx=1)
    assert a.st == ACK_A and a.sub == SUB_SET

    a = step_ack(a, retry_ack_set_done=1)
    assert a.st == ACK_A and a.sub == SUB_REPLAY

    a = step_ack(a, replay_done=1)
    assert a.st == ACK_N

    # both dones in one cycle (empty replay)
    a = step_ack(AckS(st=ACK_A, sub=SUB_SET), retry_ack_set_done=1, replay_done=1)
    assert a.st == ACK_N

    # new Retry_Req_Set during replay → stay ACK, restart set
    a = step_ack(AckS(st=ACK_A, sub=SUB_REPLAY), retry_req_set_rx=1)
    assert a.st == ACK_A and a.sub == SUB_SET

    # Retry_Req_Set during set-send does not invent a restart (SPEC names replay)
    a = step_ack(AckS(st=ACK_A, sub=SUB_SET), retry_req_set_rx=1)
    assert a.st == ACK_A and a.sub == SUB_SET

    a = step_ack(AckS(st=ACK_A, sub=SUB_SET), rst_eff=1)
    assert a.st == ACK_N

    for st, sub in ((ACK_N, SUB_SET), (ACK_A, SUB_SET), (ACK_A, SUB_REPLAY), (2, 0), (3, 1)):
        for bits in range(8):
            n = step_ack(
                AckS(st=st, sub=sub),
                retry_req_set_rx=bits & 1,
                retry_ack_set_done=(bits >> 1) & 1,
                replay_done=(bits >> 2) & 1,
            )
            assert n.st in (ACK_N, ACK_A), n.st

    print(
        "selfcheck ok: PRODUCT "
        f"{req_v.name} + {ack_v.name}, DECLFILENAME, no hooks, "
        "SPEC §6.3 / §6.4 transfers, reserved encodings never produced"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
