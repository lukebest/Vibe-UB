"""Hardware XOR-matrix helpers for ub_dll_bcrc (plain Python, not @module)."""

from __future__ import annotations

from pycircuit import Circuit, mux, u

from dll.bcrc_matrix import (
    BCRC_BYTES,
    CRC_W,
    FLIT_W,
    INIT,
    WORD_W,
    masks_full,
    masks_last,
)


def xor_reduce(m: Circuit, bits):
    if not bits:
        return m.const(0, width=1)
    cur = list(bits)
    while len(cur) > 1:
        nxt = []
        i = 0
        n = len(cur)
        while i < n:
            if i + 1 < n:
                nxt.append(cur[i] ^ cur[i + 1])
            else:
                nxt.append(cur[i])
            i = i + 2
        cur = nxt
    return cur[0]


def _pack_lsb(m: Circuit, bits):
    pieces = []
    i = len(bits) - 1
    while i >= 0:
        pieces.append(bits[i])
        i = i - 1
    return m.cat(*pieces)


def apply_masks_hw(m: Circuit, state, data, state_mask, data_mask, *, crc_w: int = CRC_W):
    out_bits = []
    sw = int(state.width)
    dw = int(data.width)
    for k in range(crc_w):
        terms = []
        sm = state_mask[k]
        dm = data_mask[k]
        for i in range(sw):
            if (sm >> i) & 1:
                terms.append(state.slice(lsb=i, width=1))
        for j in range(dw):
            if (dm >> j) & 1:
                terms.append(data.slice(lsb=j, width=1))
        out_bits.append(xor_reduce(m, terms))
    return _pack_lsb(m, out_bits)


def next_crc_hw(m: Circuit, crc_q, data_in, last):
    sm_f, dm_f = masks_full()
    sm_l, dm_l = masks_last()
    full = apply_masks_hw(m, crc_q, data_in, sm_f, dm_f)
    last_w = FLIT_W - 8 * BCRC_BYTES
    last_data = data_in.slice(lsb=0, width=last_w)
    last_crc = apply_masks_hw(m, crc_q, last_data, sm_l, dm_l)
    return mux(last, last_crc, full)


def pack_tx_word(m: Circuit, crc):
    return m.cat(u(1, 0), u(1, 0), crc)


def bits_or_reduce(m: Circuit, word):
    bits = [word.slice(lsb=i, width=1) for i in range(int(word.width))]
    cur = list(bits)
    while len(cur) > 1:
        nxt = []
        i = 0
        n = len(cur)
        while i < n:
            if i + 1 < n:
                nxt.append(cur[i] | cur[i + 1])
            else:
                nxt.append(cur[i])
            i = i + 2
        cur = nxt
    return cur[0]


def drive_gen(crc_q, word_q, done_q, start, valid_in, last, nxt, m: Circuit):
    init = u(CRC_W, INIT)
    crc_q.set(mux(start, init, nxt), when=(start | valid_in))
    eat_last = (~start) & valid_in & last
    word_q.set(pack_tx_word(m, nxt), when=eat_last)
    done_q.set(eat_last)
    return eat_last
