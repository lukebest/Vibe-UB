"""ub_dll_bcrc_check — DLL BCRC checker (SPEC §2.6).

Same XOR-matrix CRC30 as ub_dll_bcrc. On last:
  compare computed CRC30 to crc_recv[29:0];
  error_flag_rx = crc_recv[30];
  bit31 reserved, consumed without affecting the compare.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from dll.bcrc_hw import bits_or_reduce, consume_rsvd, drive_gen, next_crc_hw
from dll.bcrc_matrix import CRC_W, FLIT_W, INIT, WORD_W

LEAF = "ub_dll_bcrc_check"
VARIANTS: dict[str, dict] = {
    "": {},
}


def _check_update(m: Circuit, nxt, crc_recv, eat_last, ok_q, fail_q, eflag_q):
    recv_crc = crc_recv.slice(lsb=0, width=CRC_W)
    recv_flag = crc_recv.slice(lsb=30, width=1)
    recv_rsvd = crc_recv.slice(lsb=31, width=1)
    any_diff = bits_or_reduce(m, nxt ^ recv_crc)
    match = ~any_diff
    ok_q.set(consume_rsvd(match, recv_rsvd), when=eat_last)
    fail_q.set(any_diff, when=eat_last)
    eflag_q.set(recv_flag, when=eat_last)


@module(name="ub_dll_bcrc_check")
def build(m: Circuit, test_hooks: int = 0) -> None:
    _ = int(test_hooks)
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")
    start = m.input("start", width=1)
    valid_in = m.input("valid_in", width=1)
    data_in = m.input("data_in", width=FLIT_W)
    last = m.input("last", width=1)
    crc_recv = m.input("crc_recv", width=WORD_W)
    crc_q = m.out("crc_q", clk=clk, rst=rst, width=CRC_W, init=u(CRC_W, INIT))
    word_q = m.out("word_q", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0))
    done_q = m.out("done_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    ok_q = m.out("ok_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    fail_q = m.out("fail_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    eflag_q = m.out("eflag_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    nxt = next_crc_hw(m, crc_q.out(), data_in, last)
    eat_last = drive_gen(crc_q, word_q, done_q, start, valid_in, last, nxt, m)
    _check_update(m, nxt, crc_recv, eat_last, ok_q, fail_q, eflag_q)
    m.output("crc_word", word_q.out())
    m.output("done", done_q.out())
    m.output("crc_ok", ok_q.out())
    m.output("crc_fail", fail_q.out())
    m.output("error_flag_rx", eflag_q.out())


build.__pycircuit_name__ = "ub_dll_bcrc_check"
