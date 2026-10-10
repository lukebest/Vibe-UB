"""GF(2) CRC30 map for ub_dll_bcrc (SPEC §2.6).

Plain Python — not a @module body. Used at elaboration to build the
XOR masks, and by selfcheck against the bit-serial golden / TB model.
"""

from __future__ import annotations

POLY = 0x15A94AD5
CRC_W = 30
MASK = (1 << CRC_W) - 1
INIT = MASK
FLIT_W = 160
FLIT_BYTES = FLIT_W // 8
BCRC_BYTES = 4
WORD_W = 32


def crc_step(c: int, b: int, poly: int = POLY, crc_w: int = CRC_W) -> int:
    fb = ((c >> (crc_w - 1)) & 1) ^ (b & 1)
    shl = (c << 1) & ((1 << crc_w) - 1)
    return shl ^ (poly if fb else 0)


def consume_bit_indices(nbyte: int) -> list[int]:
    """Byte 0 upward, MSB-first inside each byte → data_in bit indices."""
    idxs: list[int] = []
    for by in range(nbyte):
        for bi in range(7, -1, -1):
            idxs.append(by * 8 + bi)
    return idxs


def crc_bytes(c: int, data: bytes, poly: int = POLY) -> int:
    t = c
    for byte in data:
        for bi in range(7, -1, -1):
            t = crc_step(t, (byte >> bi) & 1, poly)
    return t


def flit_bytes(flit: int, flit_w: int = FLIT_W) -> bytes:
    nbytes = flit_w // 8
    return bytes((flit >> (8 * i)) & 0xFF for i in range(nbytes))


def crc_flit(c: int, flit: int, *, last: bool = False) -> int:
    raw = flit_bytes(flit)
    body = raw[:-BCRC_BYTES] if last else raw
    return crc_bytes(c, body)


def build_masks(
    n_data_bits: int,
    *,
    poly: int = POLY,
    crc_w: int = CRC_W,
    consume: list[int] | None = None,
) -> tuple[list[int], list[int]]:
    """Return (state_mask[k], data_mask[k]) for next CRC bit k.

    state_mask[k] bit i = crc_q[i] feeds next[k]
    data_mask[k] bit j = data_in[j] feeds next[k]
    Linear through the origin (crc_step(0,0)=0).
    """
    if consume is None:
        consume = list(range(n_data_bits))
    state_mask = [0] * crc_w
    data_mask = [0] * crc_w
    zeros = [0] * n_data_bits

    def run(state: int, bits: list[int]) -> int:
        t = state
        for b in bits:
            t = crc_step(t, b, poly, crc_w)
        return t

    for i in range(crc_w):
        c = run(1 << i, zeros)
        for k in range(crc_w):
            if (c >> k) & 1:
                state_mask[k] |= 1 << i

    for pos, din_bit in enumerate(consume):
        bits = [0] * n_data_bits
        bits[pos] = 1
        c = run(0, bits)
        for k in range(crc_w):
            if (c >> k) & 1:
                data_mask[k] |= 1 << din_bit
    return state_mask, data_mask


def apply_masks(
    state: int,
    data: int,
    state_mask: list[int],
    data_mask: list[int],
    *,
    crc_w: int = CRC_W,
) -> int:
    out = 0
    for k in range(crc_w):
        acc = 0
        sm = state_mask[k]
        dm = data_mask[k]
        for i in range(crc_w):
            if (sm >> i) & 1:
                acc ^= (state >> i) & 1
        bit = 0
        tmp = dm
        while tmp:
            if tmp & 1:
                acc ^= (data >> bit) & 1
            tmp >>= 1
            bit += 1
        if acc:
            out |= 1 << k
    return out


def masks_full() -> tuple[list[int], list[int]]:
    return build_masks(FLIT_W, consume=consume_bit_indices(FLIT_BYTES))


def masks_last() -> tuple[list[int], list[int]]:
    n = (FLIT_BYTES - BCRC_BYTES) * 8
    return build_masks(n, consume=consume_bit_indices(FLIT_BYTES - BCRC_BYTES))


def next_crc(state: int, data: int, *, last: bool) -> int:
    sm, dm = masks_last() if last else masks_full()
    return apply_masks(state, data, sm, dm)
