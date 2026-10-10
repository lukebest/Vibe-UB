"""Shim. Canonical golden package is top-level ``model/`` (architecture).

Behaviour is unchanged: every name is re-exported from ``model``.
"""

from model import (
    PENDING,
    PendingParams,
    SymbolKind,
    UbDllBcrc,
    UbDllBcrcCheck,
    UbDllBcrcConfig,
    UbPcsDescrambler,
    UbPcsLaneDedist,
    UbPcsLaneDist,
    UbPcsLaneDistConfig,
    UbPcsScrambler,
    UbPcsScramblerConfig,
    pack_bcrc_word,
)

__all__ = [
    "PENDING",
    "PendingParams",
    "SymbolKind",
    "UbDllBcrc",
    "UbDllBcrcCheck",
    "UbDllBcrcConfig",
    "UbPcsDescrambler",
    "UbPcsLaneDedist",
    "UbPcsLaneDist",
    "UbPcsLaneDistConfig",
    "UbPcsScrambler",
    "UbPcsScramblerConfig",
    "pack_bcrc_word",
]
