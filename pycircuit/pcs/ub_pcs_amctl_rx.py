"""ub_pcs_amctl_rx — per-lane AMCTL lock, SDF, LID (SPEC §2.4 / §3.2.4.4).

Instantiates NUM_LANES_RX copies of ub_pcs_amctl_cw_dec (S-01(b) public stub).
Lanes >= pma_rx_width are ignored. Qualified cw_dec fields are taken only
when amctl_vld=1; amctl_vld=1 && (!ctrl_ok || !lid_ok) is not AMCTL.
end_hit is used for lock even when amctl_vld=0.
Formal treats cw_dec outputs as free; this parent stays in a legal state.
SPEC §10 lists no hook ports on this leaf: HOOKS ports match PRODUCT.
tb_inj_am_lock is an LMSM/controller hook (hooks_ports.yml), not this leaf.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from pcs.lib.amctl import (
    adopt,
    and_cfg,
    inst_cw_dec,
    is_sdf,
    lane_cfg,
    lane_word,
    lids_match,
)
from pcs.lib.bits import mux
from pcs.lib import params as P

LEAF = "ub_pcs_amctl_rx"
VARIANTS: dict[str, dict] = {
    "": {},
}


def _body(m: Circuit, num_lanes: int) -> None:
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")

    pma_rx_data = m.input("pma_rx_data", width=num_lanes * P.PMA_W)
    pma_rx_valid = m.input("pma_rx_valid", width=1)
    # Listed port. Lock does not consume deskew (deskew is a sibling leaf).
    # Pending lint waiver: waivers/pending/lint_pcs_amctl.yml
    m.input("pcs_deskew_ok", width=1)
    nb_phase = m.input("lmsm2pcs_nb_phase", width=1)
    pma_rx_width = m.input("pma_rx_width", width=4)

    locked = []
    sdf_f = []
    last_lid = []
    have_last = []
    cur_lid = []
    have_cur = []

    for i in range(num_lanes):
        word = lane_word(m, pma_rx_data, i)
        dec = inst_cw_dec(m, clk, rst, word, pma_rx_valid, i)
        cfg = lane_cfg(m, pma_rx_width, i)
        take = adopt(dec)
        # end_hit is not gated by amctl_vld (inventory robustness).
        lock_set = cfg & pma_rx_valid & dec["end_hit"]
        lq = m.out(
            "locked_l" + str(i), clk=clk, rst=rst, width=1, init=u(1, 0)
        )
        lq.set(lq.out() | lock_set)
        locked.append(lq.out())

        sdf_set = take & is_sdf(m, dec) & nb_phase & cfg
        sq = m.out("sdf_l" + str(i), clk=clk, rst=rst, width=1, init=u(1, 0))
        # Next-state (D) is the '旗' at t+1; AND of Ds is registered to
        # pcs_rx_sdf_seen so it rises at t+2.
        sdf_d = mux(m, nb_phase, sq.out() | sdf_set, u(1, 0))
        sq.set(sdf_d)
        sdf_f.append(sdf_d)

        ll = m.out(
            "last_lid_l" + str(i),
            clk=clk,
            rst=rst,
            width=P.LID_W,
            init=u(P.LID_W, P.LID_NULL),
        )
        hl = m.out("have_last_l" + str(i), clk=clk, rst=rst, width=1, init=u(1, 0))
        cl = m.out(
            "cur_lid_l" + str(i),
            clk=clk,
            rst=rst,
            width=P.LID_W,
            init=u(P.LID_W, P.LID_NULL),
        )
        hc = m.out("have_cur_l" + str(i), clk=clk, rst=rst, width=1, init=u(1, 0))
        match = hl.out() & (dec["lid"] == ll.out())
        ll.set(mux(m, take & cfg, dec["lid"], ll.out()))
        hl.set(hl.out() | (take & cfg))
        cl.set(mux(m, take & cfg & match, dec["lid"], cl.out()))
        hc.set(hc.out() | (take & cfg & match))
        last_lid.append(ll.out())
        have_last.append(hl.out())
        cur_lid.append(cl.out())
        have_cur.append(hc.out())

    sdf_all = and_cfg(m, sdf_f, pma_rx_width, num_lanes)
    # Extra flop: last configured AMCTL last-word at t → cw_dec at t+1 →
    # pcs_rx_sdf_seen from t+2. Clear on nb_phase==0.
    sdf_seen_q = m.out("pcs_rx_sdf_seen", clk=clk, rst=rst, width=1, init=u(1, 0))
    sdf_seen_q.set(mux(m, nb_phase, sdf_all, u(1, 0)))

    locked_all = and_cfg(m, locked, pma_rx_width, num_lanes)
    am_lock_q = m.out("pcs_am_locked", clk=clk, rst=rst, width=1, init=u(1, 0))
    am_lock_q.set(locked_all)

    agree, ref_lid = lids_match(m, cur_lid, have_cur, pma_rx_width, num_lanes)
    lid_q = m.out(
        "pcs_rx_lid", clk=clk, rst=rst, width=P.LID_W, init=u(P.LID_W, P.LID_NULL)
    )
    lid_q.set(mux(m, agree, ref_lid, u(P.LID_W, P.LID_NULL)))
    agree_d = m.out("lid_agree_d", clk=clk, rst=rst, width=1, init=u(1, 0))
    agree_d.set(agree)
    # 1-cycle pulse when all configured lanes have a matching stored LID.
    lid_vld_q = m.out("pcs_rx_lid_vld", clk=clk, rst=rst, width=1, init=u(1, 0))
    lid_vld_q.set(agree & ~agree_d.out())

    m.output("pcs_rx_sdf_seen", sdf_seen_q.out())
    m.output("pcs_am_locked", am_lock_q.out())
    m.output("pcs_rx_lid", lid_q.out())
    m.output("pcs_rx_lid_vld", lid_vld_q.out())
    _ = last_lid


@module(name="ub_pcs_amctl_rx")
def build(
    m: Circuit,
    num_lanes: int = P.NUM_LANES_RX,
    test_hooks: int = 0,
) -> None:
    _ = int(test_hooks)
    _body(m, int(num_lanes))


build.__pycircuit_name__ = "ub_pcs_amctl_rx"
