"""ub_dll_bcrc — DLL BCRC generator (SPEC §2.6 + #39 addendum).

Real pyCircuit API. CRC30 as a precomputed GF(2) XOR matrix (1-cycle).
Single-config leaf: untagged name ub_dll_bcrc.
SPEC §10 lists no hooks: HOOKS ports match PRODUCT.

On valid_in && last the CRC register reloads INIT (all-ones) so the
next block without start seeds from INIT. Mid-block valid_in without
start still folds into the current CRC. Next-state muxes match
formal/dll/ref crc_n / word_n / done_n (when=1 assign, not enable-gated).

Register names match formal/dll/ref/ub_dll_bcrc.sv so #16's 4th
equiv method can pair FFs by name after Yosys flatten:

  crc       [29:0] init 30'h3FFF_FFFF
  crc_word  [31:0] init 0           (also the output port)
  done      [0:0]  init 0           (also the output port)

pyCircuit cannot name the pyc_reg instance or its .q port. The
supported hook is Circuit.out(name) / Circuit.alias (emits
`wire <name>; // pyc.name="<name>"` assigned from pyc_reg_N).
Pairing must use that alias, not pyc_reg_N_inst.q.
"""

from __future__ import annotations

from pycircuit import Circuit, module, mux, u

from dll.lib import drive_gen, next_crc_hw
from dll.lib import CRC_W, FLIT_W, INIT, WORD_W

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
    # Names must match the #16 gold regs (not crc_q / word_q / done_q).
    crc = m.out("crc", clk=clk, rst=rst, width=CRC_W, init=u(CRC_W, INIT))
    crc_word = m.out("crc_word", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0))
    done = m.out("done", clk=clk, rst=rst, width=1, init=u(1, 0))
    seed = mux(start, u(CRC_W, INIT), crc.out())
    nxt = next_crc_hw(m, seed, data_in, last)
    drive_gen(crc, crc_word, done, start, valid_in, last, nxt, m)
    m.output("crc_word", crc_word.out())
    m.output("done", done.out())
    return nxt, crc, crc_word, done, start, valid_in, last


@module(name="ub_dll_bcrc")
def build(m: Circuit, test_hooks: int = 0) -> None:
    _ = int(test_hooks)
    _ports(m)


build.__pycircuit_name__ = "ub_dll_bcrc"
