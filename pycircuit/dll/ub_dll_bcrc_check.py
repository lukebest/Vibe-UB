"""ub_dll_bcrc_check — DLL BCRC checker (SPEC §2.6 + #39 addendum).

Same XOR-matrix CRC30 as ub_dll_bcrc (shared _ports). On last:
  compare computed CRC30 to crc_recv[29:0];
  error_flag_rx = crc_recv[30];
  bit31 reserved, consumed without affecting the compare.

Result appears 1 cycle after last (SPEC §7) and holds until the next
last. crc_ok / crc_fail / error_flag_rx are combo `done ? cmp : hold`
like formal/dll/ref/ub_dll_bcrc_check.sv; hold regs are ok_q / fail_q /
eflag_q. recv_q captures crc_recv on valid_in && last. No dummy zero_q.

Circuit.instance(ub_dll_bcrc, name="u_crc") is the API that would
mirror the gold hierarchy, but pycc emits a hashed sibling cell
first (breaks DECLFILENAME / one-top-per-file). Feasible naming is
therefore Circuit.out("crc"|"crc_word"|"done") in this leaf.
Pairing uses those pyc.name aliases (pyCircuit cannot name pyc_reg .q).
"""

from __future__ import annotations

from pycircuit import Circuit, module, mux, u

from dll.lib import bits_or_reduce, drive_gen, next_crc_hw
from dll.lib import CRC_W, FLIT_W, INIT, WORD_W

LEAF = "ub_dll_bcrc_check"
VARIANTS: dict[str, dict] = {
    "": {},
}


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

    crc = m.out("crc", clk=clk, rst=rst, width=CRC_W, init=u(CRC_W, INIT))
    crc_word = m.out("crc_word", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0))
    done = m.out("done", clk=clk, rst=rst, width=1, init=u(1, 0))
    recv_q = m.out("recv_q", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0))
    ok_q = m.out("ok_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    fail_q = m.out("fail_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    eflag_q = m.out("eflag_q", clk=clk, rst=rst, width=1, init=u(1, 0))

    seed = mux(start, u(CRC_W, INIT), crc.out())
    nxt = next_crc_hw(m, seed, data_in, last)
    eat_last = drive_gen(crc, crc_word, done, start, valid_in, last, nxt, m)
    recv_q.set(crc_recv, when=eat_last)

    word = crc_word.out()
    recv = recv_q.out()
    done_q = done.out()
    crc30_diff = word.slice(lsb=0, width=CRC_W) ^ recv.slice(lsb=0, width=CRC_W)
    rsvd = recv.slice(lsb=31, width=1)
    w31 = word.slice(lsb=31, width=1)
    # Reserved crc_recv[31] is ignored (SPEC). Read it against crc_word[31]
    # (hardwired 0) so Verilator -Wall sees the bit, then AND with that
    # registered 0 so the compare is unchanged.
    any_diff = bits_or_reduce(m, crc30_diff) | (rsvd & w31)
    cmp_ok = ~any_diff
    cmp_fail = any_diff
    cmp_ef = recv.slice(lsb=30, width=1)

    ok_q.set(cmp_ok, when=done_q)
    fail_q.set(cmp_fail, when=done_q)
    eflag_q.set(cmp_ef, when=done_q)

    m.output("crc_word", word)
    m.output("done", done_q)
    m.output("crc_ok", mux(done_q, cmp_ok, ok_q.out()))
    m.output("crc_fail", mux(done_q, cmp_fail, fail_q.out()))
    m.output("error_flag_rx", mux(done_q, cmp_ef, eflag_q.out()))


build.__pycircuit_name__ = "ub_dll_bcrc_check"
