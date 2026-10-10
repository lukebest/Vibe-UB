"""Shim. Canonical: ``model.ub_pcs_lane_dist``."""

from model.ub_pcs_lane_dist import (
    LATENCY_CYCLES,
    LEAF_PORTS,
    PMA_W,
    RS_K,
    RS_N,
    SYMBOL_BITS,
    UbPcsLaneDedist,
    UbPcsLaneDist,
    UbPcsLaneDistConfig,
    pack_pma_word,
    unpack_pma_word,
)

__all__ = [
    "LATENCY_CYCLES",
    "LEAF_PORTS",
    "PMA_W",
    "RS_K",
    "RS_N",
    "SYMBOL_BITS",
    "UbPcsLaneDedist",
    "UbPcsLaneDist",
    "UbPcsLaneDistConfig",
    "pack_pma_word",
    "unpack_pma_word",
]
