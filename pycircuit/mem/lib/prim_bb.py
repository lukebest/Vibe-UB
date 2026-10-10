"""Instantiation boundary for ``ub_cmn_mem_1r1w_d64w109``.

This @module exists so pyCircuit can emit a named instance with the PR #21
port list. Its body is a type-check stub (rdata tied to 0) and is stripped
from the PRODUCT / HOOKS netlist by ``pycircuit/emit.py``. The real leaf
comes from design-B PR #21; until that variant is on main, lint/sim uses
``tb/mem/lint_placeholder/ub_cmn_mem_1r1w_d64w109.v``.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from mem.lib.params import SET_W, WORD_W


@module(name="ub_cmn_mem_1r1w_d64w109")
def prim_bb(m: Circuit) -> None:
    m.clock("core_clk")
    m.input("we", width=1)
    m.input("waddr", width=SET_W)
    m.input("wdata", width=WORD_W)
    m.input("re", width=1)
    m.input("raddr", width=SET_W)
    m.output("rdata", u(WORD_W, 0))


prim_bb.__pycircuit_name__ = "ub_cmn_mem_1r1w_d64w109"
