"""Per-lane AMCTL RX helpers (loops live here, not in @module)."""

from __future__ import annotations

from pycircuit import Circuit, u

from pcs.lib.bits import W, ex, mux
from pcs.lib import params as P


def _cw_dec_build():
    from pcs.stub.ub_pcs_amctl_cw_dec import build as cw_dec_build

    return cw_dec_build


def lane_word(m: Circuit, pma_rx_data, lane: int):
    return ex(m, pma_rx_data, lane * P.PMA_W, P.PMA_W)


def lane_cfg(m: Circuit, pma_rx_width, lane: int):
    """Lane i is configured when i < pma_rx_width (binary 1/2/4/8)."""
    return W(m, pma_rx_width) > u(4, lane)


def inst_cw_dec(m: Circuit, clk, rst, word, word_vld, lane: int):
    outs = m.instance(
        _cw_dec_build(),
        name="u_cw_dec_" + str(lane),
        module_name="ub_pcs_amctl_cw_dec",
        core_clk=clk,
        rst_pyc=rst,
        word=word,
        word_vld=word_vld,
    )
    return {k: W(m, outs[k]) for k in (
        "end_hit",
        "amctl_vld",
        "end_ok",
        "lid",
        "lid_ok",
        "ctrl_type",
        "ctrl_type_ok",
        "ctrl_detail",
        "ctrl_detail_ok",
    )}


def adopt(dec):
    """amctl_vld && ctrl_ok && lid_ok. Else 'not AMCTL' (inventory robustness).

    end_ok is also required: END-valid is the public identification
    ('AMCTL Identification Mechanism'). Still ignored when amctl_vld=0.
    """
    ctrl_ok = dec["ctrl_type_ok"] & dec["ctrl_detail_ok"]
    return dec["amctl_vld"] & ctrl_ok & dec["lid_ok"] & dec["end_ok"]


def is_sdf(m: Circuit, dec):
    typ = dec["ctrl_type"]
    det = dec["ctrl_detail"]
    lw = typ == u(P.CTRL_TYPE_W, P.CTRL_LW_SWITCH)
    x1 = det == u(P.CTRL_DETAIL_W, P.DET_X1)
    x2 = det == u(P.CTRL_DETAIL_W, P.DET_X2)
    x4 = det == u(P.CTRL_DETAIL_W, P.DET_X4)
    x8 = det == u(P.CTRL_DETAIL_W, P.DET_X8)
    return lw & (x1 | x2 | x4 | x8)


def and_cfg(m: Circuit, flags, pma_rx_width, n: int):
    """AND of flags on configured lanes. Vacuous 1 when width==0 (illegal)."""
    acc = u(1, 1)
    for i in range(n):
        cfg = lane_cfg(m, pma_rx_width, i)
        acc = acc & mux(m, cfg, flags[i], u(1, 1))
    return acc


def lids_match(m: Circuit, lids, haves, pma_rx_width, n: int):
    """All configured lanes have a stored LID and they are equal."""
    have_all = and_cfg(m, haves, pma_rx_width, n)
    ref = lids[0]
    eq = u(1, 1)
    for i in range(n):
        cfg = lane_cfg(m, pma_rx_width, i)
        same = W(m, lids[i]) == W(m, ref)
        eq = eq & mux(m, cfg, same, u(1, 1))
    return have_all & eq, ref
