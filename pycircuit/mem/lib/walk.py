"""Helpers for ub_mem_ptw (loops / mux trees live here, not in @module)."""

from __future__ import annotations

from pycircuit import Circuit, u

from mem.lib.bits import W, ex, mux
from mem.lib.params import (
    ATTR_W,
    DESC_KIND_W,
    DESC_LVL_W,
    DESC_OFF_W,
    DESC_SLOT_LSB,
    DESC_SLOT_W,
    KIND_BLOCK,
    L1_BLK_PAGE_W,
    L2_BLK_PAGE_W,
    LVL_L0,
    LVL_L1,
    LVL_L2,
    LVL_L3,
    MATT_BA_PAD_W,
    PA_W,
    PAGE_LSB,
    PAGE_W,
    PFN_W,
    RAW_W,
    VA_IDX_W,
    VA_L0_LSB,
    VA_L1_LSB,
    VA_L2_LSB,
    VA_L3_LSB,
)
from mem.stub.ub_mem_ptw_desc_dec import build as desc_dec_build


def mux4(m: Circuit, sel, v0, v1, v2, v3):
    s = W(m, sel)
    w = v0.width
    return mux(
        m,
        s == u(DESC_LVL_W, LVL_L0),
        v0,
        mux(
            m,
            s == u(DESC_LVL_W, LVL_L1),
            v1,
            mux(m, s == u(DESC_LVL_W, LVL_L2), v2, v3),
        ),
    )


def mux8(m: Circuit, sel, v0, v1, v2, v3, v4, v5, v6, v7):
    lo_sel = ex(m, sel, 0, 2)
    hi = ex(m, sel, 2, 1)
    lo = mux4(m, lo_sel, v0, v1, v2, v3)
    hi_v = mux4(m, lo_sel, v4, v5, v6, v7)
    return mux(m, hi, hi_v, lo)


def start_lvl(m: Circuit, ia_w):
    """起始级由输入有效位数推出：覆盖 L0 / L1 / L2 下标则从该级起走。"""
    w = W(m, ia_w)
    return mux(
        m,
        w > u(w.width, VA_L0_LSB),
        u(DESC_LVL_W, LVL_L0),
        mux(
            m,
            w > u(w.width, VA_L1_LSB),
            u(DESC_LVL_W, LVL_L1),
            mux(
                m,
                w > u(w.width, VA_L2_LSB),
                u(DESC_LVL_W, LVL_L2),
                u(DESC_LVL_W, LVL_L3),
            ),
        ),
    )


def va_index(m: Circuit, uba, lvl):
    i0 = ex(m, uba, VA_L0_LSB, VA_IDX_W)
    i1 = ex(m, uba, VA_L1_LSB, VA_IDX_W)
    i2 = ex(m, uba, VA_L2_LSB, VA_IDX_W)
    i3 = ex(m, uba, VA_L3_LSB, VA_IDX_W)
    return mux4(m, lvl, i0, i1, i2, i3)


def first_walk_addr(m: Circuit, matt_ba, uba, lvl):
    idx = va_index(m, uba, lvl)
    base = m.cat(matt_ba, u(MATT_BA_PAD_W, 0))
    off = m.cat(u(PA_W - VA_IDX_W - DESC_OFF_W, 0), idx, u(DESC_OFF_W, 0))
    return W(m, base) + W(m, off)


def next_walk_addr(m: Circuit, desc_addr, uba, nxt_lvl):
    idx = va_index(m, uba, nxt_lvl)
    return m.cat(desc_addr, idx, u(DESC_OFF_W, 0))


def leaf_pfn(m: Circuit, desc_addr, uba, kind, lvl):
    """4 KB 对齐 PA 页号：块基址加上请求地址的块内页偏移。"""
    l1 = m.cat(
        ex(m, desc_addr, L1_BLK_PAGE_W, PFN_W - L1_BLK_PAGE_W),
        ex(m, uba, PAGE_LSB, L1_BLK_PAGE_W),
    )
    l2 = m.cat(
        ex(m, desc_addr, L2_BLK_PAGE_W, PFN_W - L2_BLK_PAGE_W),
        ex(m, uba, PAGE_LSB, L2_BLK_PAGE_W),
    )
    is_l1 = (W(m, kind) == u(DESC_KIND_W, KIND_BLOCK)) & (
        W(m, lvl) == u(DESC_LVL_W, LVL_L1)
    )
    is_l2 = (W(m, kind) == u(DESC_KIND_W, KIND_BLOCK)) & (
        W(m, lvl) == u(DESC_LVL_W, LVL_L2)
    )
    return mux(m, is_l1, l1, mux(m, is_l2, l2, desc_addr))


def req_page(m: Circuit, uba):
    return ex(m, uba, PAGE_LSB, PAGE_W)


def desc_raw64(m: Circuit, rd_data, addr):
    """从 512 bit 回读里按地址低位取出本次 8 B 描述符。"""
    sel = ex(m, addr, DESC_SLOT_LSB, DESC_SLOT_W)
    return mux8(
        m,
        sel,
        ex(m, rd_data, 0 * RAW_W, RAW_W),
        ex(m, rd_data, 1 * RAW_W, RAW_W),
        ex(m, rd_data, 2 * RAW_W, RAW_W),
        ex(m, rd_data, 3 * RAW_W, RAW_W),
        ex(m, rd_data, 4 * RAW_W, RAW_W),
        ex(m, rd_data, 5 * RAW_W, RAW_W),
        ex(m, rd_data, 6 * RAW_W, RAW_W),
        ex(m, rd_data, 7 * RAW_W, RAW_W),
    )


def _byte(m: Circuit, word, lsb: int):
    return ex(m, word, lsb, ATTR_W)


def sel_attr_byte(m: Circuit, mattr0, mattr1, idx):
    """从 ctx_mattr0/1 按 desc_attr_idx 取出 8 bit 属性字节。"""
    b0 = _byte(m, mattr0, 0)
    b1 = _byte(m, mattr0, 8)
    b2 = _byte(m, mattr0, 16)
    b3 = _byte(m, mattr0, 24)
    b4 = _byte(m, mattr1, 0)
    b5 = _byte(m, mattr1, 8)
    b6 = _byte(m, mattr1, 16)
    b7 = _byte(m, mattr1, 24)
    s0 = ex(m, idx, 0, 1)
    s1 = ex(m, idx, 1, 1)
    s2 = ex(m, idx, 2, 1)
    t0 = mux(m, s0, b1, b0)
    t1 = mux(m, s0, b3, b2)
    t2 = mux(m, s0, b5, b4)
    t3 = mux(m, s0, b7, b6)
    u0 = mux(m, s1, t1, t0)
    u1 = mux(m, s1, t3, t2)
    return mux(m, s2, u1, u0)


def inst_desc_dec(m: Circuit, clk, rst, in_valid, raw, desc_lvl, out_ready):
    outs = m.instance(
        desc_dec_build,
        name="u_desc_dec",
        module_name="ub_mem_ptw_desc_dec",
        core_clk=clk,
        rst_pyc=rst,
        in_valid=in_valid,
        raw=raw,
        desc_lvl=desc_lvl,
        out_ready=out_ready,
    )
    return {
        "in_ready": W(m, outs["in_ready"]),
        "out_valid": W(m, outs["out_valid"]),
        "desc_v": W(m, outs["desc_v"]),
        "desc_kind": W(m, outs["desc_kind"]),
        "desc_addr": W(m, outs["desc_addr"]),
        "desc_attr_idx": W(m, outs["desc_attr_idx"]),
        "desc_ap": W(m, outs["desc_ap"]),
        "desc_uxn": W(m, outs["desc_uxn"]),
        "desc_pxn": W(m, outs["desc_pxn"]),
        "desc_af": W(m, outs["desc_af"]),
        "desc_illegal": W(m, outs["desc_illegal"]),
        "desc_ill_cause": W(m, outs["desc_ill_cause"]),
    }
