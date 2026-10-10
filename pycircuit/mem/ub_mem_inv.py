"""ub_mem_inv — invalidation engine (UARCH §7).

Internal valid/ready only. No TA / FUN ports (LAYER_CONTRACTS freeze).

Commands:
  * INV_ALL  — one-cycle valid clear on the TLB (and future caches).
  * INV_COND — scan TLB sets; ENT_IDX / TokenID match enables.
  * SYNC     — wait until previous commands done and miss_pend=0, then
               pulse done (event write-back is ub_mem_evtq, not this leaf).

CTX / PLB ports are not present yet; those caches are not in this batch.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from mem.bits import ex, mux
from mem.params import (
    CMD_INV_ALL,
    CMD_INV_COND,
    CMD_OP_W,
    CMD_SYNC,
    ENT_IDX_W,
    INV_ST_ALL,
    INV_ST_DONE,
    INV_ST_IDLE,
    INV_ST_SCAN,
    INV_ST_SYNC,
    SET_W,
    TOKEN_W,
)


def _eq(st, val: int):
    return st == u(3, val)


def _inv_body(m: Circuit) -> None:
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")

    cmd_valid = m.input("cmd_valid", width=1)
    cmd_op = m.input("cmd_op", width=CMD_OP_W)
    cmd_ent_idx = m.input("cmd_ent_idx", width=ENT_IDX_W)
    cmd_token_id = m.input("cmd_token_id", width=TOKEN_W)
    cmd_match_ent = m.input("cmd_match_ent", width=1)
    cmd_match_tok = m.input("cmd_match_tok", width=1)
    done_ready = m.input("done_ready", width=1)
    miss_pend = m.input("miss_pend", width=1)

    tlb_all_ready = m.input("inv2tlb_all_ready", width=1)
    tlb_scan_ready = m.input("inv2tlb_scan_ready", width=1)
    tlb_scan_done = m.input("tlb2inv_scan_done", width=1)

    st = m.out("st", clk=clk, rst=rst, width=3, init=u(3, INV_ST_IDLE), en=1)
    issued = m.out("issued", clk=clk, rst=rst, width=7, init=u(7, 0), en=1)
    dones = m.out("dones", clk=clk, rst=rst, width=7, init=u(7, 0), en=1)
    ent_q = m.out("ent_q", clk=clk, rst=rst, width=ENT_IDX_W, init=u(ENT_IDX_W, 0), en=1)
    tok_q = m.out("tok_q", clk=clk, rst=rst, width=TOKEN_W, init=u(TOKEN_W, 0), en=1)
    me_q = m.out("me_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    mt_q = m.out("mt_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)

    idle = _eq(st.out(), INV_ST_IDLE)
    in_all = _eq(st.out(), INV_ST_ALL)
    in_scan = _eq(st.out(), INV_ST_SCAN)
    in_sync = _eq(st.out(), INV_ST_SYNC)
    in_done = _eq(st.out(), INV_ST_DONE)

    accept = idle & cmd_valid
    is_all = cmd_op == u(CMD_OP_W, CMD_INV_ALL)
    is_cond = cmd_op == u(CMD_OP_W, CMD_INV_COND)
    is_sync = cmd_op == u(CMD_OP_W, CMD_SYNC)

    st_next = mux(
        m,
        accept & is_all,
        u(3, INV_ST_ALL),
        mux(
            m,
            accept & is_cond,
            u(3, INV_ST_SCAN),
            mux(
                m,
                accept & is_sync,
                u(3, INV_ST_SYNC),
                mux(
                    m,
                    in_all & tlb_all_ready,
                    u(3, INV_ST_DONE),
                    mux(
                        m,
                        in_scan & (dones.out() == u(7, 64)),
                        u(3, INV_ST_DONE),
                        mux(
                            m,
                            in_sync & ~miss_pend,
                            u(3, INV_ST_DONE),
                            mux(m, in_done & done_ready, u(3, INV_ST_IDLE), st.out()),
                        ),
                    ),
                ),
            ),
        ),
    )
    st.set(st_next)

    ent_q.set(cmd_ent_idx, when=accept)
    tok_q.set(cmd_token_id, when=accept)
    me_q.set(cmd_match_ent, when=accept)
    mt_q.set(cmd_match_tok, when=accept)

    issue_go = in_scan & (issued.out() != u(7, 64)) & tlb_scan_ready
    issued.set(
        mux(
            m,
            accept & is_cond,
            u(7, 0),
            mux(m, issue_go, issued.out() + u(7, 1), issued.out()),
        )
    )
    dones.set(
        mux(
            m,
            accept & is_cond,
            u(7, 0),
            mux(m, in_scan & tlb_scan_done, dones.out() + u(7, 1), dones.out()),
        )
    )

    m.output("cmd_ready", idle)
    m.output("done_valid", in_done)
    m.output("inv2tlb_all_valid", in_all)
    m.output("inv2tlb_scan_valid", in_scan & (issued.out() != u(7, 64)))
    m.output("inv2tlb_scan_set", ex(m, issued.out(), 0, SET_W))
    m.output("inv2tlb_scan_ent_idx", ent_q.out())
    m.output("inv2tlb_scan_token_id", tok_q.out())
    m.output("inv2tlb_scan_match_ent", me_q.out())
    m.output("inv2tlb_scan_match_tok", mt_q.out())
    m.output("busy", ~idle)


@module(name="ub_mem_inv")
def build(m: Circuit, test_hooks: int = 0) -> None:
    test_hooks = int(test_hooks)
    if test_hooks != 0:
        if test_hooks != 1:
            raise ValueError("test_hooks must be 0 or 1")
    # SPEC §10 on main lists no hooks for this leaf.
    _inv_body(m)


build.__pycircuit_name__ = "ub_mem_inv"

VARIANTS = {
    "": {},
}
LEAF = "ub_mem_inv"
