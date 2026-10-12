"""ub_mem_ptw_desc_dec — 公开占位桩。

contract_sha256: HANDWRITTEN

端口与 docs/arch/mem/contracts/ub_mem_ptw_desc_dec.md YAML 头一致。
寄存 1 拍，握手按契约兑现。输出固定为翻译故障束：
desc_v=0、desc_kind=KIND_INVALID、desc_illegal=0、desc_ill_cause=ILL_NONE，
其余字段为 0。不查看 raw 的内容。
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from mem.lib.params import (
    AP_W,
    ATTR_IDX_W,
    DESC_ADDR_W,
    DESC_KIND_W,
    DESC_LVL_W,
    ILL_CAUSE_W,
    ILL_NONE,
    KIND_INVALID,
    RAW_W,
)


@module(name="ub_mem_ptw_desc_dec")
def build(m: Circuit, test_hooks: int = 0) -> None:
    test_hooks = int(test_hooks)
    if test_hooks != 0:
        if test_hooks != 1:
            raise ValueError("test_hooks must be 0 or 1")

    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")

    in_valid = m.input("in_valid", width=1)
    raw = m.input("raw", width=RAW_W)
    desc_lvl = m.input("desc_lvl", width=DESC_LVL_W)
    out_ready = m.input("out_ready", width=1)

    rst_gone = m.out("rst_gone", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    pending = m.out("pending", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)

    rst_gone.set(u(1, 1))
    # 端口保持活性，不解读 raw。
    live = (raw == raw) & (desc_lvl == desc_lvl)
    in_ready = rst_gone.out() & (~pending.out() | out_ready) & live
    accept = in_valid & in_ready
    pending.set(accept | (pending.out() & ~out_ready))

    m.output("in_ready", in_ready)
    m.output("out_valid", pending.out())
    m.output("desc_v", u(1, 0))
    m.output("desc_kind", u(DESC_KIND_W, KIND_INVALID))
    m.output("desc_addr", u(DESC_ADDR_W, 0))
    m.output("desc_attr_idx", u(ATTR_IDX_W, 0))
    m.output("desc_ap", u(AP_W, 0))
    m.output("desc_uxn", u(1, 0))
    m.output("desc_pxn", u(1, 0))
    m.output("desc_af", u(1, 0))
    m.output("desc_illegal", u(1, 0))
    m.output("desc_ill_cause", u(ILL_CAUSE_W, ILL_NONE))


build.__pycircuit_name__ = "ub_mem_ptw_desc_dec"

VARIANTS = {
    "": {},
}
LEAF = "ub_mem_ptw_desc_dec"
