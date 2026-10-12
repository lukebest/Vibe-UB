"""Wire helpers. Loops / mux trees live here, not in @module."""

from __future__ import annotations

from pycircuit import Circuit
from pycircuit.hw import Wire


def W(m: Circuit, v):
    return Wire.as_wire(v, m=m)


def mux(m: Circuit, sel, a, b):
    return W(m, sel).select(a, b)


def ex(m: Circuit, v, lsb: int, width: int):
    return W(m, v).slice(lsb=lsb, width=width)

