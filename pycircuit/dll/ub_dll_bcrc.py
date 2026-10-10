"""ub_dll_bcrc — DLL BCRC generator (SPEC §2.6).

Real pyCircuit API. CRC30 as a precomputed GF(2) XOR matrix (1-cycle).
Single-config leaf: untagged name ub_dll_bcrc.
SPEC §10 lists no hooks: HOOKS ports match PRODUCT.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from dll.bcrc_hw import drive_gen, next_crc_hw
from dll.bcrc_matrix import CRC_W, FLIT_W, INIT, WORD_W

LEAF = "ub_dll_bcrc"
VARIANTS: dict[str, dict] = {
    "": {},
}


def _ports(m: Circuit):
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")
    start = m.input("start", width=1)
    valid_in = m.input("valid_in", width=1)
    data_in = m.input("data_in", width=FLIT_W)
    last = m.input("last", width=1)
    crc_q = m.out("crc_q", clk=clk, rst=rst, width=CRC_W, init=u(CRC_W, INIT))
    word_q = m.out("word_q", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0))
    done_q = m.out("done_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    nxt = next_crc_hw(m, crc_q.out(), data_in, last)
    drive_gen(crc_q, word_q, done_q, start, valid_in, last, nxt, m)
    m.output("crc_word", word_q.out())
    m.output("done", done_q.out())
    return nxt, crc_q, word_q, done_q, start, valid_in, last


@module(name="ub_dll_bcrc")
def build(m: Circuit, test_hooks: int = 0) -> None:
    _ = int(test_hooks)
    _ports(m)


build.__pycircuit_name__ = "ub_dll_bcrc"
