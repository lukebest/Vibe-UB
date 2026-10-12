"""ub_tp_bypass — CFG9 TA↔NW bypass leaf (tp_uarch §4.1, wave 1).

Described with the pyCircuit ``@module`` API and emitted by pycc. One
fixed netlist; no Verilog parameter (SPEC §2.2, untagged).

LAYER_CONTRACTS §2 / §3: 160 b, 1 flit/cycle, valid/ready. Bypass
sideband CFG=9 (B.2.6), priority-path DCNA 16 b (§5.2.1). No ICRC
(CFG9). No RTP / CTP / GBN (wave 2).

Ports whose width or encoding the contract marks unknown are omitted
(see docs/uarch/tp_uarch.md Unknown items). SPEC §10 lists no tb_*
hooks — PRODUCT and HOOKS share the port list.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

LEAF = "ub_tp_bypass"
FLIT_W = 160
DCNA_W = 16
SL_W = 4
NLP_W = 3
LBF_W = 8
RT_W = 2
CCI_W = 16

# Untagged single netlist (SPEC §2.2).
VARIANTS: dict[str, dict] = {
    "": {},
}


@module(name="ub_tp_bypass")
def build(m: Circuit, test_hooks: int = 0) -> None:
    """Elaboration-time TEST_HOOKS. SPEC §10: no tb_* ports."""
    test_hooks = int(test_hooks)
    # Flag is 0 or 1 (checked in emit). It does not change the netlist.
    _ = test_hooks

    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")

    ta2tp_data = m.input("ta2tp_data", width=FLIT_W)
    ta2tp_valid = m.input("ta2tp_valid", width=1)
    ta2tp_sop = m.input("ta2tp_sop", width=1)
    ta2tp_eop = m.input("ta2tp_eop", width=1)

    ta2tp_op_valid = m.input("ta2tp_op_valid", width=1)
    ta2tp_bypass = m.input("ta2tp_bypass", width=1)
    ta2tp_dcna = m.input("ta2tp_dcna", width=DCNA_W)

    nw2tp_data = m.input("nw2tp_data", width=FLIT_W)
    nw2tp_valid = m.input("nw2tp_valid", width=1)
    nw2tp_sop = m.input("nw2tp_sop", width=1)
    nw2tp_eop = m.input("nw2tp_eop", width=1)
    nw2tp_err = m.input("nw2tp_err", width=1)
    nw2tp_flush = m.input("nw2tp_flush", width=1)
    nw_link_up = m.input("nw_link_up", width=1)
    tp2nw_ready = m.input("tp2nw_ready", width=1)
    tp2ta_ready = m.input("tp2ta_ready", width=1)

    can_tx_env = nw_link_up & ~nw2tp_flush

    busy_q = m.out(
        "busy_q",
        clk=clk,
        rst=rst,
        width=1,
        init=u(1, 0),
    )
    op_ready = can_tx_env & ~busy_q.out()
    op_hs = ta2tp_op_valid & op_ready
    allow_data = can_tx_env & (busy_q.out() | op_hs)

    # TX valid/ready slice (tp_uarch §4.1 B0). Ready is
    # (dst_ready | ~valid_q) & allow_data — no combo look at this-cycle valid.
    tx_valid_q = m.out("tx_valid_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    tx_vacate = tp2nw_ready | ~tx_valid_q.out()
    ta2tp_ready = tx_vacate & allow_data
    tx_valid_q.set(m.mux(tx_vacate, ta2tp_valid & allow_data, tx_valid_q.out()))
    tx_hs = ta2tp_valid & ta2tp_ready
    tx_data_q = m.out("tx_data_q", clk=clk, rst=rst, width=FLIT_W, init=u(FLIT_W, 0), en=tx_hs)
    tx_data_q.set(ta2tp_data)
    tx_sop_q = m.out("tx_sop_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=tx_hs)
    tx_sop_q.set(ta2tp_sop)
    tx_eop_q = m.out("tx_eop_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=tx_hs)
    tx_eop_q.set(ta2tp_eop)
    data_eop_hs = tx_hs & ta2tp_eop
    busy_q.set(op_hs | (busy_q.out() & ~data_eop_hs))

    dcna_q = m.out(
        "dcna_q",
        clk=clk,
        rst=rst,
        width=DCNA_W,
        init=u(DCNA_W, 0),
        en=op_hs,
    )
    dcna_q.set(ta2tp_dcna)
    bypass_q = m.out(
        "bypass_q",
        clk=clk,
        rst=rst,
        width=1,
        init=u(1, 0),
        en=op_hs,
    )
    bypass_q.set(ta2tp_bypass)

    m.output("ta2tp_ready", ta2tp_ready)
    m.output("ta2tp_op_ready", op_ready)
    m.output("tp2nw_data", tx_data_q.out())
    m.output("tp2nw_valid", tx_valid_q.out())
    m.output("tp2nw_sop", tx_sop_q.out())
    m.output("tp2nw_eop", tx_eop_q.out())
    m.output("tp2nw_bypass", bypass_q.out())
    m.output("tp2nw_dcna", dcna_q.out())
    m.output("tp2nw_sl", u(SL_W, 0))
    m.output("tp2nw_nlp", u(NLP_W, 0))
    m.output("tp2nw_lbf", u(LBF_W, 0))
    m.output("tp2nw_rt", u(RT_W, 0))
    m.output("tp2nw_cci", u(CCI_W, 0))

    # RX slice is ungated (CFG9 bypass; no ICRC).
    rx_valid_q = m.out("rx_valid_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    rx_vacate = tp2ta_ready | ~rx_valid_q.out()
    nw2tp_ready = rx_vacate
    rx_valid_q.set(m.mux(rx_vacate, nw2tp_valid, rx_valid_q.out()))
    rx_hs = nw2tp_valid & nw2tp_ready
    rx_data_q = m.out("rx_data_q", clk=clk, rst=rst, width=FLIT_W, init=u(FLIT_W, 0), en=rx_hs)
    rx_data_q.set(nw2tp_data)
    rx_sop_q = m.out("rx_sop_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=rx_hs)
    rx_sop_q.set(nw2tp_sop)
    rx_eop_q = m.out("rx_eop_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=rx_hs)
    rx_eop_q.set(nw2tp_eop)
    rx_err_q = m.out("rx_err_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=rx_hs)
    rx_err_q.set(nw2tp_err)
    m.output("nw2tp_ready", nw2tp_ready)
    m.output("tp2ta_data", rx_data_q.out())
    m.output("tp2ta_valid", rx_valid_q.out())
    m.output("tp2ta_sop", rx_sop_q.out())
    m.output("tp2ta_eop", rx_eop_q.out())
    m.output("tp2ta_err", rx_err_q.out())


build.__pycircuit_name__ = "ub_tp_bypass"
