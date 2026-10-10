"""Shims in tb/models/ must re-export the same objects (identity, not copies)."""

from __future__ import annotations


def test_tb_models_reexports_same_classes():
    import model
    import tb.models
    from model.ub_dll_bcrc import UbDllBcrc
    from model.ub_pcs_lane_dist import UbPcsLaneDist
    from model.ub_pcs_scrambler import UbPcsScrambler
    from tb.models.ub_dll_bcrc import UbDllBcrc as ShimBcrc
    from tb.models.ub_pcs_lane_dist import UbPcsLaneDist as ShimDist
    from tb.models.ub_pcs_scrambler import UbPcsScrambler as ShimScr

    assert UbDllBcrc is ShimBcrc is tb.models.UbDllBcrc is model.UbDllBcrc
    assert UbPcsLaneDist is ShimDist is tb.models.UbPcsLaneDist
    assert UbPcsScrambler is ShimScr is tb.models.UbPcsScrambler


def test_package_does_not_ship_regs_py():
    """Another PR generates model/regs.py; this tree must not author it."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert not (root / "regs.py").exists()
