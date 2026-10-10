"""SPEC §2.2 variant naming: <leaf> or <leaf>_<tag>."""

from __future__ import annotations


def variant_name(leaf: str, tag: str) -> str:
    tag = str(tag)
    if tag == "":
        return leaf
    return f"{leaf}_{tag}"
