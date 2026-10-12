"""ub_dll_retry_req_sm — DLL RETRY_REQ_SM (real pyc4.0 leaf).

SPEC main 62d9ce63 (#41 / D20) §6.3 / §13 A-12 A-13 / §4.1.
Event names, pulse vs level, and fixed priority are from that merge.
SPEC §10 lists no hooks: HOOKS ports match PRODUCT.

RETRY_WAIT_CYC (SPEC §6.3 / §13 A-10 / D20):
  16-bit input, units core_clk cycles, reset / default 323,
  legal range 1-65535. Write 0 is illegal: hardware treats 0 as 323.
  Counter and comparator are 16 bits.
  Sample the port on the cycle WAIT starts; the current wait runs to
  that sampled value; a rewrite takes effect from the next wait.
"""

from __future__ import annotations

from pathlib import Path

from pycircuit import Circuit, module, mux, u

# Closed by SPEC main 62d9ce63 (#41 / D20).
NUM_RETRY_THRESHOLD = 15  # SPEC §9 / §6.3 / §13 A-12
NUM_PHY_REINIT_THRESHOLD = 4  # SPEC §9 / §6.3 / §13 A-12
# CSR reset / default (SPEC §4.1 / §6.3 / A-10). Also the 0-write substitute.
RETRY_WAIT_CYC_DEFAULT = 323
# SPEC §6.3 / A-10: port, counter, and comparator width.
WAIT_CYC_W = 16

CNT_W = 8  # holds closed thresholds 15 / 4 (A-12); not a CSR field width

ST_NORMAL = 0
ST_REQ = 1
ST_WAIT = 2
ST_RETRAIN = 3
ST_ERROR = 4

LEAF = "ub_dll_retry_req_sm"
VARIANTS: dict[str, dict] = {
    "": {},
}

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCT_V = REPO / "rtl" / "dll" / "ub_dll_retry_req_sm.v"
HOOKS_V = REPO / "rtl" / "dll" / "hooks" / "ub_dll_retry_req_sm.v"


def _build_body(m: Circuit) -> None:
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")
    port_rst = m.input("port_rst", width=1)

    # SPEC §6.3 / A-13 event ports (pulse vs level as closed).
    blk_crc_err = m.input("ub_dll_blk_crc_err", width=1)
    fec_uncorr = m.input("ub_dll_fec_uncorr", width=1)
    phy_retrain = m.input("ub_dll_phy_retrain", width=1)
    req_set_done = m.input("ub_dll_retry_req_set_done", width=1)
    ack_set = m.input("ub_dll_retry_ack_set", width=1)
    phy_retrain_done = m.input("ub_dll_phy_retrain_done", width=1)
    link_up = m.input("link_up", width=1)
    retry_wait_cyc = m.input("retry_wait_cyc", width=WAIT_CYC_W)

    st = m.out("st", clk=clk, rst=rst, width=3, init=u(3, ST_NORMAL))
    num_retry = m.out("num_retry", clk=clk, rst=rst, width=CNT_W, init=u(CNT_W, 0))
    num_phy = m.out("num_phy", clk=clk, rst=rst, width=CNT_W, init=u(CNT_W, 0))
    tmr = m.out("tmr", clk=clk, rst=rst, width=WAIT_CYC_W, init=u(WAIT_CYC_W, 0))
    # Latched on WAIT entry (SPEC §6.3). Reset value matches CSR default.
    wait_lat = m.out(
        "wait_lat",
        clk=clk,
        rst=rst,
        width=WAIT_CYC_W,
        init=u(WAIT_CYC_W, RETRY_WAIT_CYC_DEFAULT),
    )

    is_n = st == ST_NORMAL
    is_q = st == ST_REQ
    is_w = st == ST_WAIT
    is_r = st == ST_RETRAIN
    is_e = st == ST_ERROR
    illegal = ~(is_n | is_q | is_w | is_r | is_e)

    # Write 0 is illegal config: hardware treats 0 as 323 (SPEC §6.3 / A-10).
    wait_cyc_eff = mux(
        retry_wait_cyc == 0,
        u(WAIT_CYC_W, RETRY_WAIT_CYC_DEFAULT),
        retry_wait_cyc,
    )

    ones = u(WAIT_CYC_W, (1 << WAIT_CYC_W) - 1)
    tmr_inc = mux(tmr == ones, tmr.out(), tmr.out() + 1)
    # Compare against the value sampled when this wait started.
    wait_to = is_w & (tmr_inc >= wait_lat)

    # Priority 2: RETRAIN and link_up==0 is parent DLL_Disabled. This leaf
    # stays RETRAIN and does not take phy_retrain_done (A-13 item 2 before 5).
    retrain_hold = is_r & ~link_up

    start_req = (is_n & (blk_crc_err | fec_uncorr)) | (is_w & wait_to) | (
        is_r & phy_retrain_done & ~retrain_hold
    )
    retry_inc = num_retry.out() + 1
    retry_hits = retry_inc == NUM_RETRY_THRESHOLD
    phy_inc = num_phy.out() + 1
    phy_hits = phy_inc == NUM_PHY_REINIT_THRESHOLD

    # A-13: only the highest legal item. 1=reset (rst_pyc / port_rst).
    prio9 = is_w & wait_to
    prio8 = is_n & (blk_crc_err | fec_uncorr)
    prio7 = is_q & req_set_done
    prio6 = is_w & ack_set
    prio5 = is_r & phy_retrain_done & ~retrain_hold
    enter_retrain_evt = (is_n | is_q | is_w) & phy_retrain
    enter_retrain_th = start_req & retry_hits
    prio4 = enter_retrain_evt | enter_retrain_th
    prio3 = prio4 & phy_hits

    st_n = mux(
        port_rst | illegal,
        u(3, ST_NORMAL),
        mux(
            is_e,
            u(3, ST_ERROR),
            mux(
                prio3,
                u(3, ST_ERROR),
                mux(
                    prio4,
                    u(3, ST_RETRAIN),
                    mux(
                        prio5,
                        u(3, ST_REQ),
                        mux(
                            prio6,
                            u(3, ST_NORMAL),
                            mux(
                                prio7,
                                u(3, ST_WAIT),
                                mux(
                                    prio8,
                                    u(3, ST_REQ),
                                    mux(prio9, u(3, ST_REQ), st.out()),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    enter_req = (st_n == ST_REQ) & (st != ST_REQ)
    enter_retrain = (st_n == ST_RETRAIN) & (st != ST_RETRAIN)
    enter_error = (st_n == ST_ERROR) & (st != ST_ERROR)
    enter_wait = (st_n == ST_WAIT) & (st != ST_WAIT)
    in_wait_n = st_n == ST_WAIT

    num_retry_n = mux(
        port_rst | enter_retrain,
        u(CNT_W, 0),
        mux(enter_req, retry_inc, num_retry.out()),
    )
    num_phy_n = mux(
        port_rst | enter_error,
        u(CNT_W, 0),
        mux(enter_retrain, phy_inc, num_phy.out()),
    )
    # Clear on WAIT entry so the first cycle in WAIT has tmr==0.
    tmr_n = mux(port_rst | ~in_wait_n | enter_wait, u(WAIT_CYC_W, 0), tmr_inc)
    wait_lat_n = mux(
        port_rst,
        u(WAIT_CYC_W, RETRY_WAIT_CYC_DEFAULT),
        mux(enter_wait, wait_cyc_eff, wait_lat.out()),
    )

    st.set(st_n)
    num_retry.set(num_retry_n)
    num_phy.set(num_phy_n)
    tmr.set(tmr_n)
    wait_lat.set(wait_lat_n)

    m.output("retry_req_st", st.out())
    m.output("dll_retrain_req", is_r)


@module(name="ub_dll_retry_req_sm")
def build(m: Circuit, test_hooks: int = 0) -> None:
    _ = int(test_hooks)
    _build_body(m)


build.__pycircuit_name__ = "ub_dll_retry_req_sm"


def generate() -> tuple[Path, Path]:
    from lib.pycc_emit import compile_to_verilog

    product = compile_to_verilog(
        build,
        name=LEAF,
        params={},
        test_hooks=False,
    )
    hooks = compile_to_verilog(
        build,
        name=LEAF,
        params={},
        test_hooks=True,
    )
    PRODUCT_V.parent.mkdir(parents=True, exist_ok=True)
    HOOKS_V.parent.mkdir(parents=True, exist_ok=True)
    PRODUCT_V.write_text(product, encoding="utf-8")
    HOOKS_V.write_text(hooks, encoding="utf-8")
    return PRODUCT_V, HOOKS_V


if __name__ == "__main__":
    p, h = generate()
    print(f"wrote {p}")
    print(f"wrote {h}")
