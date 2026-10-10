"""ub_cmn_mem_1r1w — 1R1W storage leaf (CODING_STYLE §10).

Described with the pyCircuit ``@module`` API and emitted by pycc. One fixed
netlist per (DEPTH, WIDTH, WMASK_W) set; no Verilog ``parameter`` (SPEC §2.2).

Contract (model / formal / Xia / CODING_STYLE §10):
  * Ports: core_clk, we, waddr[AW-1:0], wdata[WIDTH-1:0], re,
    raddr[AW-1:0], rdata[WIDTH-1:0]. AW = $clog2(DEPTH).
    Clock is ``core_clk`` (CODING_STYLE §5). No reset port — the
    business-leaf name is ``rst_pyc``; this primitive does not bring it out.
  * ``WMASK_W`` is bits per write segment (default ``WIDTH``: whole-word).
    ``WIDTH`` must be a multiple of ``WMASK_W``. N = WIDTH/WMASK_W.
    Only when N > 1 the leaf has ``wmask[N-1:0]``: bit i writes segment i
    (bits ``[i*WMASK_W +: WMASK_W]``); other segments keep their old value.
    Default config (N=1) keeps the port list unchanged.
  * Synchronous 1R1W, single clock. rdata is registered (1-cycle latency).
    Same-address same-cycle read+write returns the OLD data, per segment.
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

# Tag → DEPTH/WIDTH/WMASK_W. Consumed by scripts/emit_rtl.py and by
# tb/cmn/discover.py (pycircuit tag table). Labels follow SPEC §2.2
# ``<leaf>_<tag>``. N>1 tags include the mask width (``m<WMASK_W>``).
#
# None listed in MODULE_INVENTORY / SPEC for B-line users. This set is:
#   d5w8         — formal/cmn default (DEPTH=5, non-power-of-2), Xia BMC
#   d8w16        — model pytest power-of-2, whole-word (N=1)
#   d64w64m16    — required small masked case (N=4, 4096 array bits)
#   d512w512m64  — C-line style (N=8); gate treats as black box
VARIANTS = {
    "d5w8": {"DEPTH": 5, "WIDTH": 8, "WMASK_W": 8},
    "d8w16": {"DEPTH": 8, "WIDTH": 16, "WMASK_W": 16},
    "d64w64m16": {"DEPTH": 64, "WIDTH": 64, "WMASK_W": 16},
    "d512w512m64": {"DEPTH": 512, "WIDTH": 512, "WMASK_W": 64},
}

LEAF = "ub_cmn_mem_1r1w"


def clog2(n: int) -> int:
    """Verilog ``$clog2``: clog2(1)=0, clog2(2)=1, clog2(3)=2."""
    if n < 1:
        raise ValueError("DEPTH must be >= 1")
    return (n - 1).bit_length()


def variant_tag(depth: int, width: int, wmask_w: int) -> str:
    """SPEC §2.2 tag. Mask suffix only when N = WIDTH/WMASK_W > 1."""
    if width % wmask_w != 0:
        raise ValueError(f"WIDTH={width} is not a multiple of WMASK_W={wmask_w}")
    nseg = width // wmask_w
    if nseg == 1:
        return f"d{depth}w{width}"
    return f"d{depth}w{width}m{wmask_w}"


@module(name="ub_cmn_mem_1r1w")
def build(
    m: Circuit,
    depth: int = 5,
    width: int = 8,
    wmask_w: int = 0,
    test_hooks: int = 0,
) -> None:
    """Elaboration-time DEPTH / WIDTH / WMASK_W / TEST_HOOKS.

    ``wmask_w==0`` means ``WMASK_W=WIDTH`` (whole-word, no ``wmask`` port).
    ``test_hooks`` is a JIT int. This leaf has no hook ports (SPEC §10);
    both 0 and 1 elaborate the same PRODUCT netlist.
    """
    depth = int(depth)
    width = int(width)
    wmask_w = int(wmask_w)
    test_hooks = int(test_hooks)
    if depth < 2:
        raise ValueError("DEPTH must be >= 2")
    if width < 1:
        raise ValueError("WIDTH must be >= 1")
    if wmask_w == 0:
        wmask_w = width
    if wmask_w < 1:
        raise ValueError("WMASK_W must be >= 1")
    if width % wmask_w != 0:
        raise ValueError(f"WIDTH={width} must be a multiple of WMASK_W={wmask_w}")
    if test_hooks != 0 and test_hooks != 1:
        raise ValueError("test_hooks must be 0 or 1")

    aw = clog2(depth)
    nloc = 1 << aw
    nseg = width // wmask_w

    clk = m.clock("core_clk")
    # pyc_reg / m.out require !pyc.reset. PRODUCT has no reset port
    # (CODING_STYLE §10); emit ties this off so array and rdata stay
    # undefined until written / until a defined read.
    rst = m.reset("rst")
    we = m.input("we", width=1)
    waddr = m.input("waddr", width=aw)
    wdata = m.input("wdata", width=width)
    wmask = m.input("wmask", width=nseg) if nseg > 1 else None
    re = m.input("re", width=1)
    raddr = m.input("raddr", width=aw)

    # Forward range only (JIT rejects reversed range). 2**AW cells: no
    # DEPTH compare in the netlist. Avoid m.cat(*list): concat two at a time.
    cells = []
    for i in range(nloc):
        wr_hit = we & (waddr == u(aw, i))
        if nseg == 1:
            cell = m.out(
                f"mem_{i}",
                clk=clk,
                rst=rst,
                width=width,
                init=u(width, 0),
                en=wr_hit,
            )
            cell.set(wdata)
            cells.append(cell.out())
        else:
            word = None
            for s in range(nseg):
                en = wr_hit & m.extract(wmask, lsb=s, width=1)
                seg = m.out(
                    f"mem_{i}_{s}",
                    clk=clk,
                    rst=rst,
                    width=wmask_w,
                    init=u(wmask_w, 0),
                    en=en,
                )
                seg.set(m.extract(wdata, lsb=s * wmask_w, width=wmask_w))
                if s == 0:
                    word = seg.out()
                else:
                    word = m.concat(seg.out(), word)
            cells.append(word)

    # Balanced mux tree (raddr LSB first). A linear fold is O(2**AW)
    # deep and exceeds pycc's combinational-depth limit at C-line sizes.
    cur = cells
    for b in range(aw):
        bit = m.extract(raddr, lsb=b, width=1)
        nxt = []
        half = nloc >> (b + 1)
        for j in range(half):
            lo = cur[2 * j]
            hi = cur[2 * j + 1]
            nxt.append(m.mux(bit, hi, lo))
        cur = nxt
    acc = cur[0]

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
