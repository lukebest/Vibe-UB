"""Plain helpers for C-line leaves (loops / concat live here, not in @module).

``m.extract`` / ``m.mux`` return raw ``Signal`` objects; operator overloads
live on ``Wire``. Helpers therefore wrap every slice / mux as a Wire.
"""

from __future__ import annotations

from pycircuit import Circuit, u
from pycircuit.hw import Wire

from mem.lib.params import (
    AP_W,
    ATTR_W,
    DATA_W,
    ENT_IDX_W,
    PAGE_W,
    PFN_W,
    SET_W,
    TAG_W,
    TOKEN_W,
    WORD_W,
)
from mem.lib.prim_bb import prim_bb


def W(m: Circuit, v):
    return Wire.as_wire(v, m=m)


def mux(m: Circuit, sel, a, b):
    return W(m, sel).select(a, b)


def ex(m: Circuit, v, lsb: int, width: int):
    return W(m, v).slice(lsb=lsb, width=width)


def pack_tag(m: Circuit, ent, tok, page):
    return m.cat(ent, tok, page)


def pack_data(m: Circuit, pfn, attr, ap, uxn, pxn, af):
    return m.cat(pfn, attr, ap, uxn, pxn, af)


def pack_word(m: Circuit, tag, data):
    return m.cat(tag, data)


def unpack_tag(m: Circuit, word):
    return ex(m, word, DATA_W, TAG_W)


def unpack_data(m: Circuit, word):
    return ex(m, word, 0, DATA_W)


def unpack_xlat(m: Circuit, data):
    af = ex(m, data, 0, 1)
    pxn = ex(m, data, 1, 1)
    uxn = ex(m, data, 2, 1)
    ap = ex(m, data, 3, AP_W)
    attr = ex(m, data, 3 + AP_W, ATTR_W)
    pfn = ex(m, data, 3 + AP_W + ATTR_W, PFN_W)
    return pfn, attr, ap, uxn, pxn, af


def unpack_tag_fields(m: Circuit, tag):
    page = ex(m, tag, 0, PAGE_W)
    tok = ex(m, tag, PAGE_W, TOKEN_W)
    ent = ex(m, tag, PAGE_W + TOKEN_W, ENT_IDX_W)
    return ent, tok, page


def set_index(m: Circuit, page, token_id):
    return ex(m, page, 0, SET_W) ^ ex(m, token_id, 0, SET_W)


def bit_at(m: Circuit, word, idx, aw: int):
    nloc = 1 << aw
    cur = []
    for i in range(nloc):
        cur.append(ex(m, word, i, 1))
    for b in range(aw):
        bit = ex(m, idx, b, 1)
        nxt = []
        half = nloc >> (b + 1)
        for j in range(half):
            nxt.append(mux(m, bit, cur[2 * j + 1], cur[2 * j]))
        cur = nxt
    return cur[0]


def _cat_tree_lsb(m: Circuit, bits):
    """Balanced concat; ``bits[0]`` is LSB. Avoids a 64-deep concat chain."""
    cur = list(bits)
    while len(cur) > 1:
        nxt = []
        n = len(cur)
        pairs = n // 2
        for j in range(pairs):
            nxt.append(m.cat(cur[2 * j + 1], cur[2 * j]))
        if (n % 2) == 1:
            nxt.append(cur[n - 1])
        cur = nxt
    return cur[0]


def bit_write(m: Circuit, word, idx, we, wbit, aw: int):
    """Write one bit of a packed word. Per-bit mux + concat tree."""
    nloc = 1 << aw
    we_w = W(m, we)
    idx_w = W(m, idx)
    bits = []
    for i in range(nloc):
        old = ex(m, word, i, 1)
        hit = we_w & (idx_w == u(aw, i))
        bits.append(mux(m, hit, wbit, old))
    return _cat_tree_lsb(m, bits)


def and_or_sel(m: Circuit, hits, vals, width: int):
    acc = W(m, u(width, 0))
    for i in range(4):
        acc = acc | mux(m, hits[i], vals[i], u(width, 0))
    return acc


def cat_hits(m: Circuit, hits):
    return m.cat(W(m, hits[3]), W(m, hits[2]), W(m, hits[1]), W(m, hits[0]))


def any4(m: Circuit, hits):
    return W(m, hits[0]) | W(m, hits[1]) | W(m, hits[2]) | W(m, hits[3])


def first_inv_oh(m: Circuit, vis_valid):
    n0 = ~W(m, vis_valid[0])
    n1 = ~W(m, vis_valid[1])
    n2 = ~W(m, vis_valid[2])
    n3 = ~W(m, vis_valid[3])
    return [
        n0,
        n1 & ~n0,
        n2 & ~n0 & ~n1,
        n3 & ~n0 & ~n1 & ~n2,
    ]


def way_oh(m: Circuit, way):
    w = W(m, way)
    return [
        w == u(2, 0),
        w == u(2, 1),
        w == u(2, 2),
        w == u(2, 3),
    ]


def oh_to_way(m: Circuit, oh):
    b0 = W(m, oh[1]) | W(m, oh[3])
    b1 = W(m, oh[2]) | W(m, oh[3])
    return m.cat(b1, b0)


def mux_oh(m: Circuit, sel, a, b):
    return [mux(m, sel, a[i], b[i]) for i in range(4)]


def plru_victim(m: Circuit, b0, b1, b2):
    left = ~W(m, b0)
    lo = mux(m, b1, u(2, 1), u(2, 0))
    hi = mux(m, b2, u(2, 3), u(2, 2))
    return mux(m, left, lo, hi)


def plru_next(m: Circuit, b0, b1, b2, way):
    w = W(m, way)
    is0 = w == u(2, 0)
    is1 = w == u(2, 1)
    is2 = w == u(2, 2)
    is3 = w == u(2, 3)
    nb0 = mux(m, is0 | is1, u(1, 1), u(1, 0))
    nb1 = mux(m, is0, u(1, 1), mux(m, is1, u(1, 0), b1))
    nb2 = mux(m, is2, u(1, 1), mux(m, is3, u(1, 0), b2))
    return nb0, nb1, nb2


def inst_ways(m: Circuit, clk, we, waddr, wdata, re, raddr):
    """Four named primitives. Each way has its own we/waddr/wdata/re/raddr."""
    rdatas = []
    for i in range(4):
        rd = m.instance(
            prim_bb,
            name="mem_tlb_w" + str(i),
            module_name="ub_cmn_mem_1r1w_d64w109",
            core_clk=clk,
            we=we[i],
            waddr=waddr[i],
            wdata=wdata[i],
            re=re[i],
            raddr=raddr[i],
        )
        rdatas.append(W(m, rd))
    return rdatas


def word_eq_tag(m: Circuit, word, tag):
    return unpack_tag(m, word) == W(m, tag)
