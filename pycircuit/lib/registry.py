"""Leaf emit registry. Later layers (lmsm, dll, csr) call ``register()``.

Each emit callable must accept ``test_hooks: bool`` (SPEC §11):
  test_hooks=False → PRODUCT (TEST_HOOKS=0)
  test_hooks=True  → HOOKS   (TEST_HOOKS=1)

SPEC §10 lists which ``tb_*`` ports a leaf may add. Do not invent ports.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

EmitFn = Callable[..., str]


@dataclass(frozen=True)
class Leaf:
    layer: str
    name: str
    emit: EmitFn


_LEAVES: list[Leaf] = []


def register(layer: str, name: str, emit: EmitFn) -> Leaf:
    """Register or replace a generated leaf. Safe to call more than once."""
    leaf = Leaf(layer, name, emit)
    for i, existing in enumerate(_LEAVES):
        if existing.layer == layer and existing.name == name:
            _LEAVES[i] = leaf
            return leaf
    _LEAVES.append(leaf)
    return leaf


def registered() -> tuple[Leaf, ...]:
    return tuple(_LEAVES)


def clear() -> None:
    """Test helper. Not used by emit."""
    _LEAVES.clear()
