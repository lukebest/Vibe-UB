"""ub_mem_ptw — 页表遍历器（UARCH §3/§4/§5.6/§6.2）。

4 KB 粒度，最多 L0–L3 四级。表读走 UARCH 内存读口（地址 48 bit，
回读 512 bit）。读回描述符先寄存，再连同 desc_lvl 交给
ub_mem_ptw_desc_dec（契约：寄存 1 拍）。表描述符进入下一级；
L1 1 GB / L2 2 MB 块或 L3 页合成 4 KB 对齐 PA，只把页地址交给
ub_mem_tlb 的 fill_*。翻译故障与配置非法都不填 TLB。
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from mem.lib.bits import mux
from mem.lib.params import (
    AP_W,
    ATTR_W,
    DESC_ADDR_W,
    DESC_KIND_W,
    DESC_LVL_W,
    ENT_IDX_W,
    IA_W,
    ILL_CAUSE_W,
    ILL_NONE,
    KIND_BLOCK,
    KIND_PAGE,
    KIND_TABLE,
    LVL_L3,
    MATT_BA_W,
    MATTR_W,
    PA_W,
    PAGE_W,
    PFN_W,
    RAW_W,
    RD_DATA_W,
    TOKEN_W,
    UBA_W,
)
from mem.lib.walk import (
    desc_raw64,
    first_walk_addr,
    inst_desc_dec,
    leaf_pfn,
    next_walk_addr,
    req_page,
    sel_attr_byte,
    start_lvl,
)


def _ptw_body(m: Circuit) -> None:
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")

    req_valid = m.input("req_valid", width=1)
    req_ent_idx = m.input("req_ent_idx", width=ENT_IDX_W)
    req_token_id = m.input("req_token_id", width=TOKEN_W)
    req_uba = m.input("req_uba", width=UBA_W)
    ctx_matt_ba = m.input("ctx_matt_ba", width=MATT_BA_W)
    ctx_ia_w = m.input("ctx_ia_w", width=IA_W)
    ctx_mattr0 = m.input("ctx_mattr0", width=MATTR_W)
    ctx_mattr1 = m.input("ctx_mattr1", width=MATTR_W)
    ctx_affd = m.input("ctx_affd", width=1)
    ctx_matt_wd = m.input("ctx_matt_wd", width=1)

    rd_req_ready = m.input("rd_req_ready", width=1)
    rd_rsp_valid = m.input("rd_rsp_valid", width=1)
    rd_rsp_data = m.input("rd_rsp_data", width=RD_DATA_W)
    rd_rsp_err = m.input("rd_rsp_err", width=1)

    fill_ready = m.input("fill_ready", width=1)
    flt_ready = m.input("flt_ready", width=1)

    st_idle = m.out("st_idle", clk=clk, rst=rst, width=1, init=u(1, 1), en=1)
    st_rd = m.out("st_rd", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_dec = m.out("st_dec", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_fill = m.out("st_fill", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_flt = m.out("st_flt", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)

    rd_sent = m.out("rd_sent", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    dec_sent = m.out("dec_sent", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)

    ent_q = m.out("ent_q", clk=clk, rst=rst, width=ENT_IDX_W, init=u(ENT_IDX_W, 0), en=1)
    tok_q = m.out("tok_q", clk=clk, rst=rst, width=TOKEN_W, init=u(TOKEN_W, 0), en=1)
    uba_q = m.out("uba_q", clk=clk, rst=rst, width=UBA_W, init=u(UBA_W, 0), en=1)
    mattr0_q = m.out("mattr0_q", clk=clk, rst=rst, width=MATTR_W, init=u(MATTR_W, 0), en=1)
    mattr1_q = m.out("mattr1_q", clk=clk, rst=rst, width=MATTR_W, init=u(MATTR_W, 0), en=1)
    affd_q = m.out("affd_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    lvl_q = m.out("lvl_q", clk=clk, rst=rst, width=DESC_LVL_W, init=u(DESC_LVL_W, 0), en=1)
    addr_q = m.out("addr_q", clk=clk, rst=rst, width=PA_W, init=u(PA_W, 0), en=1)
    raw_q = m.out("raw_q", clk=clk, rst=rst, width=RAW_W, init=u(RAW_W, 0), en=1)

    pfn_q = m.out("pfn_q", clk=clk, rst=rst, width=PFN_W, init=u(PFN_W, 0), en=1)
    page_q = m.out("page_q", clk=clk, rst=rst, width=PAGE_W, init=u(PAGE_W, 0), en=1)
    attr_q = m.out("attr_q", clk=clk, rst=rst, width=ATTR_W, init=u(ATTR_W, 0), en=1)
    ap_q = m.out("ap_q", clk=clk, rst=rst, width=AP_W, init=u(AP_W, 0), en=1)
    uxn_q = m.out("uxn_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    pxn_q = m.out("pxn_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    af_q = m.out("af_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)

    flt_xlat_q = m.out("flt_xlat_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    flt_ill_q = m.out("flt_ill_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    flt_rd_q = m.out("flt_rd_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    flt_af_q = m.out("flt_af_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    ill_cause_q = m.out(
        "ill_cause_q", clk=clk, rst=rst, width=ILL_CAUSE_W, init=u(ILL_CAUSE_W, 0), en=1
    )

    idle = st_idle.out()
    in_rd = st_rd.out()
    in_dec = st_dec.out()
    in_fill = st_fill.out()
    in_flt = st_flt.out()

    slvl = start_lvl(m, ctx_ia_w)
    saddr = first_walk_addr(m, ctx_matt_ba, req_uba, slvl)

    do_req = idle & req_valid
    to_flt_wd = do_req & ctx_matt_wd
    to_rd_new = do_req & ~ctx_matt_wd

    rd_req_valid = in_rd & ~rd_sent.out()
    rd_accept = rd_req_valid & rd_req_ready
    rd_rsp_ready = in_rd & rd_sent.out()
    rd_take = rd_rsp_ready & rd_rsp_valid
    to_flt_rd = rd_take & rd_rsp_err
    to_dec = rd_take & ~rd_rsp_err

    dec_in_valid = in_dec & ~dec_sent.out()
    dec_out_ready = u(1, 1)
    dec = inst_desc_dec(
        m, clk, rst, dec_in_valid, raw_q.out(), lvl_q.out(), dec_out_ready
    )
    dec_accept = dec_in_valid & dec["in_ready"]
    dec_fire = in_dec & dec["out_valid"]

    kind = dec["desc_kind"]
    is_table = kind == u(DESC_KIND_W, KIND_TABLE)
    is_block = kind == u(DESC_KIND_W, KIND_BLOCK)
    is_page = kind == u(DESC_KIND_W, KIND_PAGE)
    is_leaf = is_block | is_page
    lvl_l3 = lvl_q.out() == u(DESC_LVL_W, LVL_L3)
    nxt_lvl = lvl_q.out() + u(DESC_LVL_W, 1)
    naddr = next_walk_addr(m, dec["desc_addr"], uba_q.out(), nxt_lvl)

    to_flt_ill = dec_fire & dec["desc_illegal"]
    to_flt_xlat = dec_fire & ~dec["desc_illegal"] & ~dec["desc_v"]
    to_next = dec_fire & ~dec["desc_illegal"] & dec["desc_v"] & is_table & ~lvl_l3
    to_flt_bad = dec_fire & ~dec["desc_illegal"] & dec["desc_v"] & is_table & lvl_l3
    to_flt_af = (
        dec_fire
        & ~dec["desc_illegal"]
        & dec["desc_v"]
        & is_leaf
        & ~dec["desc_af"]
        & ~affd_q.out()
    )
    to_fill = (
        dec_fire
        & ~dec["desc_illegal"]
        & dec["desc_v"]
        & is_leaf
        & (dec["desc_af"] | affd_q.out())
    )
    to_idle_fill = in_fill & fill_ready
    to_idle_flt = in_flt & flt_ready

    stay_idle = idle & ~do_req
    stay_rd = in_rd & ~to_dec & ~to_flt_rd
    stay_dec = in_dec & ~dec_fire
    stay_fill = in_fill & ~fill_ready
    stay_flt = in_flt & ~flt_ready

    st_idle.set(stay_idle | to_idle_fill | to_idle_flt)
    st_rd.set(to_rd_new | to_next | stay_rd)
    st_dec.set(to_dec | stay_dec)
    st_fill.set(to_fill | stay_fill)
    st_flt.set(
        to_flt_wd
        | to_flt_rd
        | to_flt_ill
        | to_flt_xlat
        | to_flt_bad
        | to_flt_af
        | stay_flt
    )

    enter_rd = to_rd_new | to_next
    rd_sent.set(
        mux(m, enter_rd | to_idle_fill | to_idle_flt, u(1, 0), mux(m, rd_accept, u(1, 1), rd_sent.out()))
    )
    dec_sent.set(
        mux(m, to_dec | to_idle_fill | to_idle_flt, u(1, 0), mux(m, dec_accept, u(1, 1), dec_sent.out()))
    )

    ent_q.set(req_ent_idx, when=do_req)
    tok_q.set(req_token_id, when=do_req)
    uba_q.set(req_uba, when=do_req)
    mattr0_q.set(ctx_mattr0, when=do_req)
    mattr1_q.set(ctx_mattr1, when=do_req)
    affd_q.set(ctx_affd, when=do_req)

    lvl_q.set(mux(m, to_next, nxt_lvl, slvl), when=do_req | to_next)
    addr_q.set(mux(m, to_next, naddr, saddr), when=do_req | to_next)
    raw_q.set(desc_raw64(m, rd_rsp_data), when=to_dec)

    pfn_now = leaf_pfn(m, dec["desc_addr"], uba_q.out(), kind, lvl_q.out())
    attr_now = sel_attr_byte(m, mattr0_q.out(), mattr1_q.out(), dec["desc_attr_idx"])
    page_now = req_page(m, uba_q.out())
    pfn_q.set(pfn_now, when=to_fill)
    page_q.set(page_now, when=to_fill)
    attr_q.set(attr_now, when=to_fill)
    ap_q.set(dec["desc_ap"], when=to_fill)
    uxn_q.set(dec["desc_uxn"], when=to_fill)
    pxn_q.set(dec["desc_pxn"], when=to_fill)
    af_q.set(dec["desc_af"], when=to_fill)

    enter_flt = (
        to_flt_wd | to_flt_rd | to_flt_ill | to_flt_xlat | to_flt_bad | to_flt_af
    )
    flt_xlat_q.set(to_flt_wd | to_flt_xlat | to_flt_bad, when=enter_flt)
    flt_ill_q.set(to_flt_ill, when=enter_flt)
    flt_rd_q.set(to_flt_rd, when=enter_flt)
    flt_af_q.set(to_flt_af, when=enter_flt)
    ill_cause_q.set(
        mux(m, to_flt_ill, dec["desc_ill_cause"], u(ILL_CAUSE_W, ILL_NONE)),
        when=enter_flt,
    )

    m.output("req_ready", idle)
    m.output("rd_req_valid", rd_req_valid)
    m.output("rd_req_addr", addr_q.out())
    m.output("rd_rsp_ready", rd_rsp_ready)
    m.output("fill_valid", in_fill)
    m.output("fill_ent_idx", ent_q.out())
    m.output("fill_token_id", tok_q.out())
    m.output("fill_page", page_q.out())
    m.output("fill_pfn", pfn_q.out())
    m.output("fill_attr", attr_q.out())
    m.output("fill_ap", ap_q.out())
    m.output("fill_uxn", uxn_q.out())
    m.output("fill_pxn", pxn_q.out())
    m.output("fill_af", af_q.out())
    m.output("flt_valid", in_flt)
    m.output("flt_xlat", flt_xlat_q.out())
    m.output("flt_illegal", flt_ill_q.out())
    m.output("flt_ill_cause", ill_cause_q.out())
    m.output("flt_rd_err", flt_rd_q.out())
    m.output("flt_af", flt_af_q.out())
    m.output("busy", ~idle)


@module(name="ub_mem_ptw")
def build(m: Circuit, test_hooks: int = 0) -> None:
    test_hooks = int(test_hooks)
    if test_hooks != 0:
        if test_hooks != 1:
            raise ValueError("test_hooks must be 0 or 1")
    _ptw_body(m)


build.__pycircuit_name__ = "ub_mem_ptw"

VARIANTS = {
    "": {},
}
LEAF = "ub_mem_ptw"
