"""ub_pcs_nullblk_det — observe aligned flits, pulse LMSM (SPEC §3.3.4 / §6.1).

Bypass sample only. Does not sit in the data path.
Null test: block-type == Null Block code and CLENGTH == 5'b00000
(MODULE_INVENTORY, Xia 2026-10-12; UB-DL §4.3.3.2). Bit indexes are
parameters (未知 in the public tree).
SPEC §10 lists no hook ports: HOOKS ports match PRODUCT.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from pcs.lib.bits import W, ex, mux
from pcs.lib import params as P

LEAF = "ub_pcs_nullblk_det"
VARIANTS: dict[str, dict] = {
    "": {},
}


def _is_null(m: Circuit, flit):
    blk = ex(m, flit, P.BLK_TYPE_LSB, P.BLK_TYPE_W)
    clen = ex(m, flit, P.CLENGTH_LSB, P.CLENGTH_W)
    return (blk == u(P.BLK_TYPE_W, P.NULL_BLK_CODE)) & (
        clen == u(P.CLENGTH_W, P.CLENGTH_NULL)
    )


def _body(m: Circuit) -> None:
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")

    pcs2dll_data = m.input("pcs2dll_data", width=P.FLIT_W)
    pcs2dll_valid = m.input("pcs2dll_valid", width=1)
    dll2pcs_data = m.input("dll2pcs_data", width=P.FLIT_W)
    dll2pcs_valid = m.input("dll2pcs_valid", width=1)
    dll2pcs_ready = m.input("dll2pcs_ready", width=1)
    pcs_deskew_ok = m.input("pcs_deskew_ok", width=1)
    pcs_rx_sdf_seen = m.input("pcs_rx_sdf_seen", width=1)
    # MODULE_INVENTORY: 只读作对照. SDF set/clear is in ub_pcs_amctl_rx.
    # Pending lint waiver: waivers/pending/lint_pcs_amctl.yml
    m.input("lmsm2pcs_nb_phase", width=1)

    gate = W(m, pcs_deskew_ok) & W(m, pcs_rx_sdf_seen)
    rx_null = W(m, pcs2dll_valid) & _is_null(m, pcs2dll_data)
    rx_non = W(m, pcs2dll_valid) & ~_is_null(m, pcs2dll_data)
    # Gate before the output flop. A beat already in the flop still pulses
    # after the gate drops.
    rx_null_d = rx_null & gate
    rx_non_d = rx_non & gate
    tx_acc = W(m, dll2pcs_valid) & W(m, dll2pcs_ready)
    tx_null_d = tx_acc & _is_null(m, dll2pcs_data)

    null_q = m.out("pcs2lmsm_null_blk", clk=clk, rst=rst, width=1, init=u(1, 0))
    non_q = m.out("pcs2lmsm_rx_nonnull_blk", clk=clk, rst=rst, width=1, init=u(1, 0))
    tx_q = m.out("pcs2lmsm_tx_null_blk", clk=clk, rst=rst, width=1, init=u(1, 0))
    null_q.set(rx_null_d)
    non_q.set(rx_non_d)
    tx_q.set(tx_null_d)

    # Mutex: a Null flit cannot also be non-Null. Force the pair exclusive
    # even if both Ds were 1 (they are complements under the same valid).
    m.output("pcs2lmsm_null_blk", null_q.out())
    m.output("pcs2lmsm_rx_nonnull_blk", mux(m, null_q.out(), u(1, 0), non_q.out()))
    m.output("pcs2lmsm_tx_null_blk", tx_q.out())


@module(name="ub_pcs_nullblk_det")
def build(m: Circuit, test_hooks: int = 0) -> None:
    _ = int(test_hooks)
    _body(m)


build.__pycircuit_name__ = "ub_pcs_nullblk_det"
