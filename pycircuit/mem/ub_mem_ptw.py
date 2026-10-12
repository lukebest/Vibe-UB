"""ub_mem_ptw — 页表遍历器（UARCH §3/§4/§5.6/§6.2）。

4 KB 粒度，最多 L0–L3 四级。表读走 ub_mem_tbl_rd / mem2host_rd_*
（地址 48 bit、长度、tag；回读 512 bit、tag、错误）。
SPEC §14 Q-C07 (D20)：首轮单未决，mem2host_rd_len 为 8 bit 字节数（合法
RD_LEN_8B / RD_LEN_32B / RD_LEN_64B），本叶驱动 RD_LEN_8B；tag 恒
RD_TAG_ZERO，口宽一次拉齐。表读请求口 mem2host_rd_valid / addr / len / tag
一律出寄存器（Xia 准：valid/ready 握手；valid 为高期间请求保持）。
addr 接 addr_q Q（pending 期间 addr_q 不写）；valid 在请求成交当拍置位，
下一沿送出。len / tag 为寄存器常量，无输入时序路径。
从 512 bit 回读按地址低位取出 8 B 描述符。读回描述符先寄存，再连同
desc_lvl 交给 ub_mem_ptw_desc_dec（契约：寄存 1 拍）。表描述符进入
下一级；L1 1 GB / L2 2 MB 块或 L3 页合成 4 KB 对齐 PA，只把页地址
交给 ub_mem_tlb 的 fill_*。
SPEC §14 Q-A08 (D20)：ctx_matt_wd=1 时不发表读、不报翻译故障、不填
TLB，只记一条翻译事件。
SPEC §14 Q-A18 (D20)：HAF 按 0；AF=0 且 ctx_affd=0 报 AF 故障；
AF=0 且 ctx_affd=1 正常填充。S2_AFFD 等 Stage 2。
翻译故障与配置非法都不填 TLB。
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from mem.lib.bits import ex, mux
from mem.lib.params import (
    AP_W,
    ATTR_W,
    DESC_KIND_W,
    DESC_LVL_W,
    ENT_IDX_W,
    EVT_CODE_W,
    EVT_MATT_WD_MISS,
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
    PAGE_LSB,
    PAGE_W,
    PFN_W,
    RAW_W,
    RD_DATA_W,
    RD_LEN_8B,
    RD_LEN_W,
    RD_TAG_W,
    RD_TAG_ZERO,
    TOKEN_W,
    UBA_W,
)
from mem.lib.walk import (
    desc_raw64,
    first_walk_addr,
    inst_desc_dec,
    leaf_pfn,
    next_walk_addr,
    sel_attr_byte,
    start_lvl,
)


def _ptw_body(m: Circuit, test_hooks: int = 0) -> None:
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

    rd_ready = m.input("mem2host_rd_ready", width=1)
    rd_rsp_valid = m.input("mem2host_rd_rsp_valid", width=1)
    rd_rsp_data = m.input("mem2host_rd_rsp_data", width=RD_DATA_W)
    rd_rsp_tag = m.input("mem2host_rd_rsp_tag", width=RD_TAG_W)
    rd_rsp_err = m.input("mem2host_rd_rsp_err", width=1)

    fill_ready = m.input("fill_ready", width=1)
    flt_ready = m.input("flt_ready", width=1)
    evt_ready = m.input("evt_ready", width=1)

    st_idle = m.out("st_idle", clk=clk, rst=rst, width=1, init=u(1, 1), en=1)
    st_rd = m.out("st_rd", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_dec = m.out("st_dec", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_fill = m.out("st_fill", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_flt = m.out("st_flt", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_evt = m.out("st_evt", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)

    rd_sent = m.out("rd_sent", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    dec_sent = m.out("dec_sent", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    # 表读请求口：valid 出寄存器；addr 直出 addr_q Q。
    rd_valid_q = m.out("rd_valid_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    rd_len_q = m.out(
        "rd_len_q", clk=clk, rst=rst, width=RD_LEN_W, init=u(RD_LEN_W, RD_LEN_8B), en=1
    )
    rd_tag_q = m.out(
        "rd_tag_q", clk=clk, rst=rst, width=RD_TAG_W, init=u(RD_TAG_W, RD_TAG_ZERO), en=1
    )

    ent_q = m.out("ent_q", clk=clk, rst=rst, width=ENT_IDX_W, init=u(ENT_IDX_W, 0), en=1)
    tok_q = m.out("tok_q", clk=clk, rst=rst, width=TOKEN_W, init=u(TOKEN_W, 0), en=1)
    # 只存页号 [47:12]（36 bit）；低 12 / 高 16 不进寄存器。
    uba_q = m.out("uba_q", clk=clk, rst=rst, width=PAGE_W, init=u(PAGE_W, 0), en=1)
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
    evt_code_q = m.out(
        "evt_code_q", clk=clk, rst=rst, width=EVT_CODE_W, init=u(EVT_CODE_W, 0), en=1
    )

    idle = st_idle.out()
    in_rd = st_rd.out()
    in_dec = st_dec.out()
    in_fill = st_fill.out()
    in_flt = st_flt.out()
    in_evt = st_evt.out()

    slvl = start_lvl(m, ctx_ia_w)
    saddr = first_walk_addr(m, ctx_matt_ba, req_uba, slvl)

    do_req = idle & req_valid
    # SPEC §14 Q-A08 (D20)：MATT_WD=1 只走事件口。
    to_evt_wd = do_req & ctx_matt_wd
    to_rd_new = do_req & ~ctx_matt_wd

    rd_req_valid = rd_valid_q.out()
    rd_accept = rd_req_valid & rd_ready
    rd_rsp_ready = in_rd & rd_sent.out()
    tag_live = rd_rsp_tag == rd_rsp_tag
    rd_take = rd_rsp_ready & rd_rsp_valid & tag_live
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
    kind_ok = is_table | is_leaf
    lvl_l3 = lvl_q.out() == u(DESC_LVL_W, LVL_L3)
    nxt_lvl = lvl_q.out() + u(DESC_LVL_W, 1)
    uba_page = uba_q.out()
    uba_ext = m.cat(uba_page, u(PAGE_LSB, 0))
    naddr = next_walk_addr(m, dec["desc_addr"], uba_ext, nxt_lvl)

    to_flt_ill = dec_fire & dec["desc_illegal"]
    # SPEC §14：desc_v=1 且 kind 不是 table/block/page 走翻译故障（与 !desc_v 同 flt_xlat）。
    to_flt_xlat = (
        dec_fire & ~dec["desc_illegal"] & (~dec["desc_v"] | ~kind_ok)
    )
    to_next = dec_fire & ~dec["desc_illegal"] & dec["desc_v"] & is_table & ~lvl_l3
    enter_rd = to_rd_new | to_next
    to_flt_bad = dec_fire & ~dec["desc_illegal"] & dec["desc_v"] & is_table & lvl_l3
    # SPEC §14 Q-A18 (D20)：AF × AFFD；HAF 按 0。
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
    to_idle_evt = in_evt & evt_ready

    stay_idle = idle & ~do_req
    stay_rd = in_rd & ~to_dec & ~to_flt_rd
    stay_dec = in_dec & ~dec_fire
    stay_fill = in_fill & ~fill_ready
    stay_flt = in_flt & ~flt_ready
    stay_evt = in_evt & ~evt_ready

    nxt_idle = stay_idle | to_idle_fill | to_idle_flt | to_idle_evt
    nxt_rd = to_rd_new | to_next | stay_rd
    nxt_dec = to_dec | stay_dec
    nxt_fill = to_fill | stay_fill
    nxt_flt = to_flt_rd | to_flt_ill | to_flt_xlat | to_flt_bad | to_flt_af | stay_flt
    nxt_evt = to_evt_wd | stay_evt
    any_nxt = nxt_idle | nxt_rd | nxt_dec | nxt_fill | nxt_flt | nxt_evt
    st_idle.set(nxt_idle | ~any_nxt)
    st_rd.set(nxt_rd)
    st_dec.set(nxt_dec)
    st_fill.set(nxt_fill)
    st_flt.set(nxt_flt)
    st_evt.set(nxt_evt)

    done_walk = to_idle_fill | to_idle_flt | to_idle_evt
    rd_sent.set(
        mux(m, enter_rd | done_walk, u(1, 0), mux(m, rd_accept, u(1, 1), rd_sent.out()))
    )
    # AP_TBLRD_REQ_HOLD：valid && !ready 时 valid/addr/len/tag 保持。
    # enter_rd 当拍置 valid D，下一沿送出（req 成交 → 第一次 valid 为 1 拍）。
    rd_valid_q.set(
        mux(
            m,
            rd_accept | done_walk,
            u(1, 0),
            mux(m, enter_rd, u(1, 1), rd_valid_q.out()),
        )
    )
    rd_len_q.set(u(RD_LEN_W, RD_LEN_8B))
    rd_tag_q.set(u(RD_TAG_W, RD_TAG_ZERO))
    dec_sent.set(
        mux(m, to_dec | done_walk, u(1, 0), mux(m, dec_accept, u(1, 1), dec_sent.out()))
    )

    ent_q.set(req_ent_idx, when=do_req)
    tok_q.set(req_token_id, when=do_req)
    uba_q.set(ex(m, req_uba, PAGE_LSB, PAGE_W), when=do_req)
    mattr0_q.set(ctx_mattr0, when=do_req)
    mattr1_q.set(ctx_mattr1, when=do_req)
    affd_q.set(ctx_affd, when=do_req)

    lvl_q.set(mux(m, to_next, nxt_lvl, slvl), when=do_req | to_next)
    addr_q.set(mux(m, to_next, naddr, saddr), when=do_req | to_next)
    raw_q.set(desc_raw64(m, rd_rsp_data, addr_q.out()), when=to_dec)

    pfn_now = leaf_pfn(m, dec["desc_addr"], uba_ext, kind, lvl_q.out())
    attr_now = sel_attr_byte(m, mattr0_q.out(), mattr1_q.out(), dec["desc_attr_idx"])
    page_now = uba_page
    pfn_q.set(pfn_now, when=to_fill)
    page_q.set(page_now, when=to_fill)
    attr_q.set(attr_now, when=to_fill)
    ap_q.set(dec["desc_ap"], when=to_fill)
    uxn_q.set(dec["desc_uxn"], when=to_fill)
    pxn_q.set(dec["desc_pxn"], when=to_fill)
    af_q.set(dec["desc_af"], when=to_fill)

    enter_flt = to_flt_rd | to_flt_ill | to_flt_xlat | to_flt_bad | to_flt_af
    flt_xlat_q.set(to_flt_xlat | to_flt_bad, when=enter_flt)
    flt_ill_q.set(to_flt_ill, when=enter_flt)
    flt_rd_q.set(to_flt_rd, when=enter_flt)
    flt_af_q.set(to_flt_af, when=enter_flt)
    ill_cause_q.set(
        mux(m, to_flt_ill, dec["desc_ill_cause"], u(ILL_CAUSE_W, ILL_NONE)),
        when=enter_flt,
    )
    evt_code_q.set(u(EVT_CODE_W, EVT_MATT_WD_MISS), when=to_evt_wd)

    m.output("req_ready", idle)
    # SPEC §14 Q-C07 (D20)：请求口出寄存器；长度恒 8 B，tag 恒 0。
    m.output("mem2host_rd_valid", rd_valid_q.out())
    m.output("mem2host_rd_addr", addr_q.out())
    m.output("mem2host_rd_len", rd_len_q.out())
    m.output("mem2host_rd_tag", rd_tag_q.out())
    m.output("mem2host_rd_rsp_ready", rd_rsp_ready)
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
    m.output("evt_valid", in_evt)
    m.output("evt_code", evt_code_q.out())
    m.output("busy", ~idle)

    if test_hooks != 0:
        # HOOKS 只读观察，不受 tb_test_mode 门控（SPEC §10）。
        m.output(
            "tb_mem_ptw_obs_st",
            m.cat(
                st_evt.out(),
                st_flt.out(),
                st_fill.out(),
                st_dec.out(),
                st_rd.out(),
                st_idle.out(),
            ),
        )
        m.output("tb_mem_ptw_obs_rd_pend", rd_valid_q.out())


@module(name="ub_mem_ptw")
def build(m: Circuit, test_hooks: int = 0) -> None:
    test_hooks = int(test_hooks)
    if test_hooks != 0:
        if test_hooks != 1:
            raise ValueError("test_hooks must be 0 or 1")
    _ptw_body(m, test_hooks=test_hooks)


build.__pycircuit_name__ = "ub_mem_ptw"

VARIANTS = {
    "": {},
}
LEAF = "ub_mem_ptw"
