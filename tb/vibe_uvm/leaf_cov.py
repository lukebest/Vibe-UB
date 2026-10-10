"""CoverPoint / CoverCross for leaf batch 1 (D8). Names map to VERIF_PLAN TPs."""

from __future__ import annotations

from cocotb_coverage.coverage import CoverCross, CoverPoint


@CoverPoint("tp.rst_sync.phase", xf=lambda phase, kind, hooks: phase,
            bins=["after_posedge", "after_negedge", "mid_high", "mid_low"])
@CoverPoint("tp.rst_sync.kind", xf=lambda phase, kind, hooks: kind,
            bins=["async_assert", "sync_deassert_2", "glitch", "short_pulse",
                  "clk_stop_rst", "clk_stop_rel"])
@CoverPoint("tp.rst_sync.hooks", xf=lambda phase, kind, hooks: hooks, bins=[0, 1])
@CoverCross("tp.rst_sync.phase_x_kind",
            items=["tp.rst_sync.phase", "tp.rst_sync.kind"])
def sample_rst_sync(phase: str, kind: str, hooks: int) -> None:
    """TP-UNIT-RST-001 / TP-UNIT-CDC-001."""


@CoverPoint("tp.rst_adapt.polarity", xf=lambda pol, kind, hooks: pol, bins=[0, 1])
@CoverPoint("tp.rst_adapt.kind", xf=lambda pol, kind, hooks: kind,
            bins=["invert", "wire", "combo_0", "not_registered"])
@CoverPoint("tp.rst_adapt.hooks", xf=lambda pol, kind, hooks: hooks, bins=[0, 1])
@CoverCross("tp.rst_adapt.pol_x_kind",
            items=["tp.rst_adapt.polarity", "tp.rst_adapt.kind"])
def sample_rst_adapt(pol: int, kind: str, hooks: int) -> None:
    """TP-UNIT-RST-002."""


@CoverPoint("tp.lane.num", xf=lambda n, kind, hooks: n, bins=[1, 2, 4, 8])
@CoverPoint("tp.lane.kind", xf=lambda n, kind, hooks: kind,
            bins=["first_wire", "window", "zero", "one", "walk", "rand",
                  "loopback", "valid_rst", "lat0", "inc", "onehot"])
@CoverPoint("tp.lane.hooks", xf=lambda n, kind, hooks: hooks, bins=[0, 1])
@CoverCross("tp.lane.num_x_kind", items=["tp.lane.num", "tp.lane.kind"])
def sample_lane(n: int, kind: str, hooks: int) -> None:
    """TP-UNIT-PCS-006 / 007 / 008."""


@CoverPoint("tp.bcrc.kind", xf=lambda kind, n_flit, hooks: kind,
            bins=["dir0", "dir1", "dir_inc", "onehot", "rand", "two_flit",
                  "tx_flag0", "rst_quiet", "start_reinit"])
@CoverPoint("tp.bcrc.n_flit", xf=lambda kind, n_flit, hooks: n_flit, bins=[1, 2, 3])
@CoverPoint("tp.bcrc.hooks", xf=lambda kind, n_flit, hooks: hooks, bins=[0, 1])
@CoverCross("tp.bcrc.kind_x_nflit", items=["tp.bcrc.kind", "tp.bcrc.n_flit"])
def sample_bcrc(kind: str, n_flit: int, hooks: int) -> None:
    """TP-UNIT-DLL-001."""


@CoverPoint("tp.bcrc_chk.kind", xf=lambda kind, hooks: kind,
            bins=["good", "flag_flip", "rsvd_flip", "bit_flip",
                  "rand", "rst_quiet", "lat1"])
@CoverPoint("tp.bcrc_chk.hooks", xf=lambda kind, hooks: hooks, bins=[0, 1])
@CoverCross("tp.bcrc_chk.kind_x_hooks",
            items=["tp.bcrc_chk.kind", "tp.bcrc_chk.hooks"])
def sample_bcrc_check(kind: str, hooks: int) -> None:
    """TP-UNIT-DLL-002."""
