"""ub_cmn_mem_1r1w — 1R1W storage leaf (CODING_STYLE §10).

Described with the pyCircuit ``@module`` API and emitted by pycc. One fixed
netlist per (DEPTH, WIDTH) set; no Verilog ``parameter`` (SPEC §2.2).

Contract (model / formal / Xia / CODING_STYLE §10):
  * Ports: core_clk, we, waddr[AW-1:0], wdata[WIDTH-1:0], re,
    raddr[AW-1:0], rdata[WIDTH-1:0]. AW = $clog2(DEPTH).
    Clock is ``core_clk`` (CODING_STYLE §5). No reset port — the
    business-leaf name is ``rst_pyc``; this primitive does not bring it out.
  * Synchronous 1R1W, single clock. rdata is registered (1-cycle latency).
    Same-address same-cycle read+write returns the OLD data.
  * Array and rdata are NOT reset and are NOT zero-initialised. rdata is
    undefined until a read of an address that has been written. With
    ASSERT_NO_UNINIT_READ=0, a read of an unwritten address is undefined
    (caller gates with an external valid bit). Written-flag tracking lives
    only in assertions / the model, never in this PRODUCT netlist.
  * Out-of-range encodings (non-power-of-2 DEPTH) are not truncated or
    guarded. Storage is 2**AW cells so every AW-bit encoding maps to a
    cell; formal/sim assertions catch OOR.

SPEC §10 lists no ``tb_*`` hooks for this leaf — PRODUCT only.
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

# Tag → DEPTH/WIDTH. Consumed by scripts/emit_rtl.py and by tb/cmn/discover.py
# (pycircuit tag table). Labels follow SPEC §2.2 ``<leaf>_<tag>``.
#
# None listed in MODULE_INVENTORY / SPEC for B-line users. This set is:
#   d5w8  — formal/cmn default (DEPTH=5, non-power-of-2), Xia's BMC case
#   d8w16 — model pytest power-of-2 case
VARIANTS = {
    "d5w8": {"DEPTH": 5, "WIDTH": 8},
    "d8w16": {"DEPTH": 8, "WIDTH": 16},
}

LEAF = "ub_cmn_mem_1r1w"


def clog2(n: int) -> int:
    """Verilog ``$clog2``: clog2(1)=0, clog2(2)=1, clog2(3)=2."""
    if n < 1:
        raise ValueError("DEPTH must be >= 1")
    return (n - 1).bit_length()


@module(name="ub_cmn_mem_1r1w")
def build(
    m: Circuit,
    depth: int = 5,
    width: int = 8,
    test_hooks: int = 0,
) -> None:
    """Elaboration-time DEPTH / WIDTH / TEST_HOOKS.

    ``test_hooks`` is a JIT int. This leaf has no hook ports (SPEC §10);
    both 0 and 1 elaborate the same PRODUCT netlist.
    """
    depth = int(depth)
    width = int(width)
    test_hooks = int(test_hooks)
    if depth < 2:
        raise ValueError("DEPTH must be >= 2")
    if width < 1:
        raise ValueError("WIDTH must be >= 1")
    if test_hooks != 0 and test_hooks != 1:
        raise ValueError("test_hooks must be 0 or 1")

    aw = clog2(depth)
    nloc = 1 << aw

    clk = m.clock("core_clk")
    # pyc_reg / m.out require !pyc.reset. PRODUCT has no reset port
    # (CODING_STYLE §10); emit ties this off so array and rdata stay
    # undefined until written / until a defined read.
    rst = m.reset("rst")
    we = m.input("we", width=1)
    waddr = m.input("waddr", width=aw)
    wdata = m.input("wdata", width=width)
    re = m.input("re", width=1)
    raddr = m.input("raddr", width=aw)

    # Forward range only (JIT rejects reversed range). 2**AW cells: no
    # DEPTH compare in the netlist.
    cells = []
    for i in range(nloc):
        wr_hit = we & (waddr == u(aw, i))
        cell = m.out(
            f"mem_{i}",
            clk=clk,
            rst=rst,
            width=width,
            init=u(width, 0),
            en=wr_hit,
        )
        cell.set(wdata)
        cells.append(cell)

    acc = u(width, 0)
    for i in range(nloc):
        rd_hit = raddr == u(aw, i)
        acc = cells[i].out() if rd_hit else acc

    rdata_q = m.out(
        "rdata_q",
        clk=clk,
        rst=rst,
        width=width,
        init=u(width, 0),
        en=re,
    )
    rdata_q.set(acc)
    m.output("rdata", rdata_q.out())


build.__pycircuit_name__ = "ub_cmn_mem_1r1w"
