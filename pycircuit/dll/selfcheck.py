#!/usr/bin/env python3
"""Generator + SPEC §6.3 / §6.4 transfer self-check (not a verification TB).

Proves emit() runs, PRODUCT and HOOKS have the same ports (Xia: no
tb_test_mode when SPEC §10 lists no hooks), no reserved encodings,
A-13 priorities, and directed WAIT-timer cases (#41 / D20):
  default 323 (no fire at 322, fire at 323),
  value 1, a large value, value 0 treated as 323,
  mid-count rewrite takes effect only on the next wait.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYC = HERE.parent
if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from dll import ub_dll_retry_ack_sm as ack  # noqa: E402
from dll import ub_dll_retry_req_sm as req  # noqa: E402

ST_N, ST_Q, ST_W, ST_R, ST_E = (
    req.ST_NORMAL,
    req.ST_REQ,
    req.ST_WAIT,
    req.ST_RETRAIN,
    req.ST_ERROR,
)
ACK_N, ACK_A = ack.ST_NORMAL, ack.ST_ACK
WAIT_W = req.WAIT_CYC_W
WAIT_DEFAULT = req.RETRY_WAIT_CYC_DEFAULT
TMR_SAT = (1 << WAIT_W) - 1
CNT_SAT = 0xFF


def _map_wait(port: int) -> int:
    """#41 / D20: write 0 is illegal; hardware treats 0 as 323."""
    return WAIT_DEFAULT if port == 0 else port


@dataclass
class ReqS:
    st: int = ST_N
    num_retry: int = 0
    num_phy: int = 0
    tmr: int = 0
    wait_lat: int = WAIT_DEFAULT


def step_req(
    s: ReqS,
    *,
    rst_eff: int = 0,
    blk_crc_err: int = 0,
    fec_uncorr: int = 0,
    phy_retrain: int = 0,
    req_set_done: int = 0,
    ack_set: int = 0,
    phy_retrain_done: int = 0,
    link_up: int = 1,
    retry_wait_cyc: int = WAIT_DEFAULT,
    num_retry_th: int = req.NUM_RETRY_THRESHOLD,
    num_phy_th: int = req.NUM_PHY_REINIT_THRESHOLD,
) -> ReqS:
    """One-cycle model matching ub_dll_retry_req_sm (SPEC §6.3 / A-13)."""
    if rst_eff:
        return ReqS()
    is_n = int(s.st == ST_N)
    is_q = int(s.st == ST_Q)
    is_w = int(s.st == ST_W)
    is_r = int(s.st == ST_R)
    is_e = int(s.st == ST_E)
    illegal = int(not (is_n or is_q or is_w or is_r or is_e))

    tmr_inc = s.tmr if s.tmr == TMR_SAT else s.tmr + 1
    wait_to = int(is_w and (tmr_inc >= s.wait_lat))
    retrain_hold = int(is_r and not link_up)

    start_req = int(
        (is_n and (blk_crc_err or fec_uncorr))
        or (is_w and wait_to)
        or (is_r and phy_retrain_done and not retrain_hold)
    )
    retry_inc = s.num_retry + 1
    retry_hits = int(retry_inc == num_retry_th)
    phy_inc = s.num_phy + 1
    phy_hits = int(phy_inc == num_phy_th)

    prio9 = int(is_w and wait_to)
    prio8 = int(is_n and (blk_crc_err or fec_uncorr))
    prio7 = int(is_q and req_set_done)
    prio6 = int(is_w and ack_set)
    prio5 = int(is_r and phy_retrain_done and not retrain_hold)
    enter_retrain_evt = int((is_n or is_q or is_w) and phy_retrain)
    enter_retrain_th = int(start_req and retry_hits)
    prio4 = int(enter_retrain_evt or enter_retrain_th)
    prio3 = int(prio4 and phy_hits)

    if illegal:
        st_n = ST_N
    elif is_e:
        st_n = ST_E
    elif prio3:
        st_n = ST_E
    elif prio4:
        st_n = ST_R
    elif prio5:
        st_n = ST_Q
    elif prio6:
        st_n = ST_N
    elif prio7:
        st_n = ST_W
    elif prio8:
        st_n = ST_Q
    elif prio9:
        st_n = ST_Q
    else:
        st_n = s.st

    enter_req = int(st_n == ST_Q and s.st != ST_Q)
    enter_retrain = int(st_n == ST_R and s.st != ST_R)
    enter_error = int(st_n == ST_E and s.st != ST_E)
    enter_wait = int(st_n == ST_W and s.st != ST_W)
    in_wait_n = int(st_n == ST_W)

    if enter_retrain:
        num_retry_n = 0
    elif enter_req:
        num_retry_n = retry_inc
    else:
        num_retry_n = s.num_retry
    if num_retry_n > CNT_SAT:
        num_retry_n = CNT_SAT

    if enter_error:
        num_phy_n = 0
    elif enter_retrain:
        num_phy_n = phy_inc
    else:
        num_phy_n = s.num_phy
    if num_phy_n > CNT_SAT:
        num_phy_n = CNT_SAT

    if (not in_wait_n) or enter_wait:
        tmr_n = 0
    else:
        tmr_n = tmr_inc

    if enter_wait:
        wait_lat_n = _map_wait(retry_wait_cyc)
    else:
        wait_lat_n = s.wait_lat

    return ReqS(
        st=st_n,
        num_retry=num_retry_n,
        num_phy=num_phy_n,
        tmr=tmr_n,
        wait_lat=wait_lat_n,
    )


@dataclass
class AckS:
    st: int = ACK_N


def step_ack(
    s: AckS,
    *,
    rst_eff: int = 0,
    req_set: int = 0,
    ack_set_done: int = 0,
) -> AckS:
    """One-cycle model matching ub_dll_retry_ack_sm (SPEC §6.4 / A-13)."""
    if rst_eff:
        return AckS()
    is_n = s.st == ACK_N
    is_a = s.st == ACK_A
    illegal = not (is_n or is_a)
    if illegal:
        st_n = ACK_N
    elif req_set:
        st_n = ACK_A
    elif is_a and ack_set_done:
        st_n = ACK_N
    else:
        st_n = s.st
    return AckS(st=st_n)


def _ports_block(text: str) -> str:
    return text.split("module", 1)[1].split(");", 1)[0]


def _static_common(path: Path, module: str, *, reserved_needles: tuple[str, ...]) -> str:
    text = path.read_text(encoding="utf-8")
    assert "module " in text
    assert "`ifdef" not in text
    assert "$display" not in text
    assert "force " not in text
    assert "negedge rst_n" not in text
    assert "or negedge" not in text
    mod = text.split("module ", 1)[1].split("(", 1)[0].split("#", 1)[0].strip()
    assert path.stem == mod == module, f"DECLFILENAME {path.name} vs {mod}"
    for needle in reserved_needles:
        for line in text.splitlines():
            if "st_n" in line or "st " in line:
                assert needle not in line, line
    return text


def _decl_lines(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.lstrip().startswith(("input", "output", "assign", "wire"))
    ]


def _port_names(text: str) -> list[str]:
    names: list[str] = []
    for line in _ports_block(text).splitlines():
        s = line.strip()
        if s.startswith(("input", "output")):
            names.append(s.rstrip(",").split()[-1])
    return names


def _static_product(path: Path, module: str, *, reserved_needles: tuple[str, ...]) -> str:
    text = _static_common(path, module, reserved_needles=reserved_needles)
    for token in ("tb_test_mode", "tb_inj_", "tb_obs_"):
        assert all(token not in line for line in _decl_lines(text)), token
    return text


def _run_wait(s: ReqS, n: int, wait_port: int) -> ReqS:
    for _ in range(n):
        s = step_req(s, retry_wait_cyc=wait_port)
    return s


def _enter_wait(wait_port: int, num_retry: int = 1) -> ReqS:
    s = ReqS(st=ST_Q, num_retry=num_retry)
    s = step_req(s, req_set_done=1, retry_wait_cyc=wait_port)
    assert s.st == ST_W and s.tmr == 0
    assert s.wait_lat == _map_wait(wait_port)
    return s


def main() -> int:
    req_prod, req_hooks = req.generate()
    ack_prod, ack_hooks = ack.generate()
    req_needles = ("3'd5", "3'd6", "3'd7", "3'b101", "3'b110", "3'b111")
    ack_needles = ("2'd2", "2'd3", "2'b10", "2'b11")

    req_txt = _static_product(req_prod, "ub_dll_retry_req_sm", reserved_needles=req_needles)
    ack_txt = _static_product(ack_prod, "ub_dll_retry_ack_sm", reserved_needles=ack_needles)
    req_hooks_txt = _static_product(
        req_hooks, "ub_dll_retry_req_sm", reserved_needles=req_needles
    )
    ack_hooks_txt = _static_product(
        ack_hooks, "ub_dll_retry_ack_sm", reserved_needles=ack_needles
    )
    assert _port_names(req_txt) == _port_names(req_hooks_txt)
    assert _port_names(ack_txt) == _port_names(ack_hooks_txt)
    assert "tb_test_mode" not in _port_names(req_txt)
    assert "tb_test_mode" not in _port_names(ack_txt)

    req_ports = _ports_block(req_txt)
    for name in (
        "core_clk",
        "rst_pyc",
        "port_rst",
        "ub_dll_blk_crc_err",
        "ub_dll_fec_uncorr",
        "ub_dll_phy_retrain",
        "ub_dll_retry_req_set_done",
        "ub_dll_retry_ack_set",
        "ub_dll_phy_retrain_done",
        "link_up",
        "retry_wait_cyc",
        "retry_req_st",
        "dll_retrain_req",
    ):
        assert name in req_ports, name
    for banned in (
        "device_rst",
        "send_cnt",
        "wr_ptr",
        "rd_ptr",
        "rst_n",
        "lmsm_retrain_ack",
        "start_retry",
        "retry_ack_set_rx",
        "phy_retrain_ok",
        "retry_req_inc",
        "retry_to_inc",
        "retry_err",
        "tb_test_mode",
    ):
        assert banned not in req_ports, banned
    assert "[15:0]" in req_ports or "[15: 0]" in req_ports

    ack_ports = _ports_block(ack_txt)
    for name in (
        "core_clk",
        "rst_pyc",
        "port_rst",
        "ub_dll_retry_req_set",
        "ub_dll_retry_ack_set_done",
        "retry_ack_st",
    ):
        assert name in ack_ports, name
    for banned in (
        "device_rst",
        "wr_ptr",
        "rcv_ptr",
        "rd_ptr",
        "send_cnt",
        "retry_req_set_rx",
        "replay_done",
        "tb_test_mode",
    ):
        assert banned not in ack_ports, banned

    # --- SPEC §6.3 transfers + A-13 ---
    s = step_req(ReqS(), rst_eff=1)
    assert s.st == ST_N and s.num_retry == 0 and s.num_phy == 0

    s = step_req(s, blk_crc_err=1)
    assert s.st == ST_Q and s.num_retry == 1

    s = step_req(s, fec_uncorr=1)
    assert s.st == ST_Q and s.num_retry == 1  # already REQ; no re-entry

    s = step_req(s, req_set_done=1)
    assert s.st == ST_W and s.tmr == 0 and s.wait_lat == WAIT_DEFAULT

    s = step_req(s, ack_set=1)
    assert s.st == ST_N

    s = step_req(ReqS(), fec_uncorr=1)
    assert s.st == ST_Q and s.num_retry == 1

    # 15th REQ entry → RETRAIN, clear NUM_RETRY
    s = step_req(ReqS(st=ST_N, num_retry=14), blk_crc_err=1)
    assert s.st == ST_R and s.num_retry == 0 and s.num_phy == 1

    s = step_req(s, phy_retrain_done=1, link_up=1)
    assert s.st == ST_Q and s.num_retry == 1

    # RETRAIN + link_up==0: stay RETRAIN, ignore phy_retrain_done (A-13 #2)
    s = step_req(ReqS(st=ST_R, num_phy=1), phy_retrain_done=1, link_up=0)
    assert s.st == ST_R

    s = step_req(ReqS(), phy_retrain=1)
    assert s.st == ST_R and s.num_phy == 1

    s = step_req(ReqS(st=ST_Q, num_retry=3), phy_retrain=1)
    assert s.st == ST_R and s.num_retry == 0 and s.num_phy == 1

    s = step_req(ReqS(st=ST_N, num_phy=3), phy_retrain=1)
    assert s.st == ST_E and s.num_phy == 0

    s = step_req(s, blk_crc_err=1, phy_retrain_done=1, ack_set=1)
    assert s.st == ST_E
    s = step_req(s, rst_eff=1)
    assert s.st == ST_N

    # crc vs fec same rank (A-13 #8)
    s = step_req(ReqS(), blk_crc_err=1, fec_uncorr=1)
    assert s.st == ST_Q

    # phy_retrain beats crc (A-13 #4 > #8)
    s = step_req(ReqS(), blk_crc_err=1, phy_retrain=1)
    assert s.st == ST_R

    # ack_set beats wait_to (A-13 #6 > #9)
    s = ReqS(st=ST_W, tmr=WAIT_DEFAULT - 1, wait_lat=WAIT_DEFAULT, num_retry=1)
    s = step_req(s, ack_set=1)
    assert s.st == ST_N

    # reserved encodings never produced
    for st in (ST_N, ST_Q, ST_W, ST_R, ST_E, 5, 6, 7):
        for bits in range(32):
            n = step_req(
                ReqS(st=st, num_retry=1, num_phy=1, tmr=10, wait_lat=20),
                blk_crc_err=bits & 1,
                fec_uncorr=(bits >> 1) & 1,
                phy_retrain=(bits >> 2) & 1,
                req_set_done=(bits >> 3) & 1,
                ack_set=(bits >> 4) & 1,
                phy_retrain_done=(bits >> 5) & 1,
                link_up=(bits >> 6) & 1,
            )
            assert n.st in (ST_N, ST_Q, ST_W, ST_R, ST_E), n.st

    # --- directed WAIT (#41 / D20) ---
    # default 323: no fire at 322, fire at 323
    s = _enter_wait(WAIT_DEFAULT, num_retry=1)
    s = _run_wait(s, 322, WAIT_DEFAULT)
    assert s.st == ST_W and s.tmr == 322, (s.st, s.tmr)
    s = step_req(s, retry_wait_cyc=WAIT_DEFAULT)
    assert s.st == ST_Q and s.num_retry == 2, (s.st, s.num_retry)

    # value 1: fire on the first WAIT cycle
    s = _enter_wait(1, num_retry=1)
    s = step_req(s, retry_wait_cyc=1)
    assert s.st == ST_Q and s.num_retry == 2

    # large value 65535 (#41 / D20 legal max): no fire at 65534, fire at 65535
    large = (1 << WAIT_W) - 1
    s = _enter_wait(large, num_retry=1)
    s = _run_wait(s, large - 1, large)
    assert s.st == ST_W and s.tmr == large - 1
    s = step_req(s, retry_wait_cyc=large)
    assert s.st == ST_Q and s.num_retry == 2

    # value 0 behaves as 323
    s = _enter_wait(0, num_retry=1)
    assert s.wait_lat == WAIT_DEFAULT
    s = _run_wait(s, 322, 0)
    assert s.st == ST_W
    s = step_req(s, retry_wait_cyc=0)
    assert s.st == ST_Q and s.num_retry == 2

    # mid-count rewrite only affects the next wait
    s = _enter_wait(5, num_retry=1)
    s = _run_wait(s, 2, 2)  # rewrite port to 2 while counting to 5
    assert s.st == ST_W and s.wait_lat == 5 and s.tmr == 2
    s = _run_wait(s, 2, 2)
    assert s.st == ST_W and s.tmr == 4
    s = step_req(s, retry_wait_cyc=2)
    assert s.st == ST_Q and s.num_retry == 2
    s = step_req(s, req_set_done=1, retry_wait_cyc=2)
    assert s.st == ST_W and s.wait_lat == 2 and s.tmr == 0
    s = step_req(s, retry_wait_cyc=2)
    assert s.st == ST_W and s.tmr == 1  # value 2: no fire on WAIT cycle 1
    s = step_req(s, retry_wait_cyc=2)
    assert s.st == ST_Q and s.num_retry == 3

    # --- SPEC §6.4 transfers ---
    a = step_ack(AckS(), rst_eff=1)
    assert a.st == ACK_N

    a = step_ack(a, req_set=1)
    assert a.st == ACK_A

    a = step_ack(a, ack_set_done=1)
    assert a.st == ACK_N

    # same-cycle req_set covers ack_set_done → stay ACK
    a = step_ack(AckS(st=ACK_A), req_set=1, ack_set_done=1)
    assert a.st == ACK_A

    a = step_ack(AckS(st=ACK_A), rst_eff=1)
    assert a.st == ACK_N

    for st in (ACK_N, ACK_A, 2, 3):
        for bits in range(8):
            n = step_ack(
                AckS(st=st),
                req_set=bits & 1,
                ack_set_done=(bits >> 1) & 1,
            )
            assert n.st in (ACK_N, ACK_A), n.st

    print(
        "selfcheck ok: PRODUCT + HOOKS "
        f"{req_prod.name} / {ack_prod.name}, DECLFILENAME, "
        "HOOKS ports == PRODUCT (no tb_test_mode; Xia / no §10 hooks), "
        "SPEC §6.3 / §6.4 / A-13, #41/D20 WAIT 16-bit latch + 0→323"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
