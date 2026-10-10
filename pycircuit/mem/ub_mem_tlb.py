"""ub_mem_tlb — 4-way set-associative TLB (UARCH §3/§4/§6/§10).

Default netlist only (TLB_SETS=64, TLB_WAYS=4). SPEC §2.2: module name is
the leaf name; no Verilog parameter.

Storage: four named instances of ``ub_cmn_mem_1r1w_d64w109`` (PR #21 port
list). Valid (256) and tree PLRU (64x3) live in ``rst_pyc`` flops.

Timing (实现 guidance): 4-way hit vector is one-hot AND-OR select; PLRU
and valid write-back are the cycle after compare/select. Fill FSM is
registered one-hot (idle / FILL_CMP / FILL_WB); consumers use the flop
outputs directly (no post-flop decode). Lookup hit and §10 obs stay at
request+1.

Fill reuses a way whose tag (ENT_IDX + TokenID + page) is already valid
in the set. PLRU update is one cycle late — back-to-back hits in the same
set see the old PLRU (accepted).
"""

from __future__ import annotations

from pycircuit import Circuit, module, u

from mem.lib.bits import (
    W,
    and_or_sel,
    any4,
    bit_at,
    bit_write,
    cat_hits,
    ex,
    first_inv_oh,
    inst_ways,
    mux,
    mux_oh,
    oh_to_way,
    pack_data,
    pack_tag,
    pack_word,
    plru_next,
    plru_victim,
    set_index,
    unpack_data,
    unpack_tag,
    unpack_xlat,
    way_oh,
)
from mem.lib.params import (
    AP_W,
    ATTR_W,
    DATA_W,
    ENT_IDX_W,
    PAGE_W,
    PFN_W,
    SET_W,
    TAG_W,
    TLB_SETS,
    TLB_WAYS,
    TOKEN_W,
    WORD_W,
)


def _tlb_body(m: Circuit, *, test_hooks: int) -> None:
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")

    lk_valid = m.input("lk_valid", width=1)
    lk_ent_idx = m.input("lk_ent_idx", width=ENT_IDX_W)
    lk_token_id = m.input("lk_token_id", width=TOKEN_W)
    lk_page = m.input("lk_page", width=PAGE_W)

    fill_valid = m.input("fill_valid", width=1)
    fill_ent_idx = m.input("fill_ent_idx", width=ENT_IDX_W)
    fill_token_id = m.input("fill_token_id", width=TOKEN_W)
    fill_page = m.input("fill_page", width=PAGE_W)
    fill_pfn = m.input("fill_pfn", width=PFN_W)
    fill_attr = m.input("fill_attr", width=ATTR_W)
    fill_ap = m.input("fill_ap", width=AP_W)
    fill_uxn = m.input("fill_uxn", width=1)
    fill_pxn = m.input("fill_pxn", width=1)
    fill_af = m.input("fill_af", width=1)

    inv_all_valid = m.input("inv2tlb_all_valid", width=1)
    scan_valid = m.input("inv2tlb_scan_valid", width=1)
    scan_set = m.input("inv2tlb_scan_set", width=SET_W)
    scan_ent_idx = m.input("inv2tlb_scan_ent_idx", width=ENT_IDX_W)
    scan_token_id = m.input("inv2tlb_scan_token_id", width=TOKEN_W)
    scan_match_ent = m.input("inv2tlb_scan_match_ent", width=1)
    scan_match_tok = m.input("inv2tlb_scan_match_tok", width=1)

    # HOOKS inputs (SPEC §10). Declared only when TEST_HOOKS=1.
    bd_we = []
    bd_addr = []
    bd_wdata = []
    bd_re = []
    bd_vld_we = []
    bd_vld_wd = []
    if test_hooks != 0:
        tb_test_mode = m.input("tb_test_mode", width=1)
        for i in range(4):
            bd_we.append(m.input(f"tb_mem_tlb_w{i}_bd_we", width=1))
            bd_addr.append(m.input(f"tb_mem_tlb_w{i}_bd_addr", width=SET_W))
            bd_wdata.append(m.input(f"tb_mem_tlb_w{i}_bd_wdata", width=WORD_W))
            bd_re.append(m.input(f"tb_mem_tlb_w{i}_bd_re", width=1))
            bd_vld_we.append(m.input(f"tb_mem_tlb_w{i}_bd_vld_we", width=1))
            bd_vld_wd.append(m.input(f"tb_mem_tlb_w{i}_bd_vld_wdata", width=1))
    else:
        # PRODUCT: no hook ports. Typed zeros (not Literal|Literal).
        _z1 = W(m, u(1, 0))
        tb_test_mode = _z1
        for i in range(4):
            bd_we.append(_z1)
            bd_addr.append(u(SET_W, 0))
            bd_wdata.append(u(WORD_W, 0))
            bd_re.append(_z1)
            bd_vld_we.append(_z1)
            bd_vld_wd.append(_z1)

    # One-hot fill FSM, registered from next-state. No post-flop decode.
    st_idle = m.out("st_idle", clk=clk, rst=rst, width=1, init=u(1, 1), en=1)
    st_fill_cmp = m.out("st_fill_cmp", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    st_fill_wb = m.out("st_fill_wb", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    lk_pend = m.out("lk_pend", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    lk_set_q = m.out("lk_set_q", clk=clk, rst=rst, width=SET_W, init=u(SET_W, 0), en=1)
    lk_tag_q = m.out("lk_tag_q", clk=clk, rst=rst, width=TAG_W, init=u(TAG_W, 0), en=1)

    fill_set_q = m.out("fill_set_q", clk=clk, rst=rst, width=SET_W, init=u(SET_W, 0), en=1)
    fill_tag_q = m.out("fill_tag_q", clk=clk, rst=rst, width=TAG_W, init=u(TAG_W, 0), en=1)
    fill_word_q = m.out(
        "fill_word_q", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0), en=1
    )
    pend_v = m.out("pend_v", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    pend_set = m.out("pend_set", clk=clk, rst=rst, width=SET_W, init=u(SET_W, 0), en=1)
    pend_way = m.out("pend_way", clk=clk, rst=rst, width=2, init=u(2, 0), en=1)
    pend_tag = m.out("pend_tag", clk=clk, rst=rst, width=TAG_W, init=u(TAG_W, 0), en=1)

    scan_pend = m.out("scan_pend", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    scan_clr = m.out("scan_clr", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    scan_set_q = m.out("scan_set_q", clk=clk, rst=rst, width=SET_W, init=u(SET_W, 0), en=1)
    scan_set_qq = m.out(
        "scan_set_qq", clk=clk, rst=rst, width=SET_W, init=u(SET_W, 0), en=1
    )
    scan_ent_q = m.out(
        "scan_ent_q", clk=clk, rst=rst, width=ENT_IDX_W, init=u(ENT_IDX_W, 0), en=1
    )
    scan_tok_q = m.out(
        "scan_tok_q", clk=clk, rst=rst, width=TOKEN_W, init=u(TOKEN_W, 0), en=1
    )
    scan_me_q = m.out("scan_me_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    scan_mt_q = m.out("scan_mt_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    scan_hit_q = m.out("scan_hit_q", clk=clk, rst=rst, width=4, init=u(4, 0), en=1)

    plru_we_q = m.out("plru_we_q", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    plru_set_q = m.out("plru_set_q", clk=clk, rst=rst, width=SET_W, init=u(SET_W, 0), en=1)
    plru_way_q = m.out("plru_way_q", clk=clk, rst=rst, width=2, init=u(2, 0), en=1)

    vld0 = m.out("vld_w0", clk=clk, rst=rst, width=TLB_SETS, init=u(TLB_SETS, 0), en=1)
    vld1 = m.out("vld_w1", clk=clk, rst=rst, width=TLB_SETS, init=u(TLB_SETS, 0), en=1)
    vld2 = m.out("vld_w2", clk=clk, rst=rst, width=TLB_SETS, init=u(TLB_SETS, 0), en=1)
    vld3 = m.out("vld_w3", clk=clk, rst=rst, width=TLB_SETS, init=u(TLB_SETS, 0), en=1)
    plru0 = m.out("plru0", clk=clk, rst=rst, width=TLB_SETS, init=u(TLB_SETS, 0), en=1)
    plru1 = m.out("plru1", clk=clk, rst=rst, width=TLB_SETS, init=u(TLB_SETS, 0), en=1)
    plru2 = m.out("plru2", clk=clk, rst=rst, width=TLB_SETS, init=u(TLB_SETS, 0), en=1)

    byp_v0 = m.out("byp_v0", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    byp_v1 = m.out("byp_v1", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    byp_v2 = m.out("byp_v2", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    byp_v3 = m.out("byp_v3", clk=clk, rst=rst, width=1, init=u(1, 0), en=1)
    byp_d0 = m.out("byp_d0", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0), en=1)
    byp_d1 = m.out("byp_d1", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0), en=1)
    byp_d2 = m.out("byp_d2", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0), en=1)
    byp_d3 = m.out("byp_d3", clk=clk, rst=rst, width=WORD_W, init=u(WORD_W, 0), en=1)

    idle = st_idle.out()
    fill_cmp = st_fill_cmp.out()
    fill_wb = st_fill_wb.out()
    fill_busy = fill_cmp | fill_wb
    scan_busy = scan_pend.out() | scan_clr.out()

    if test_hooks != 0:
        bd_steal = tb_test_mode & (
            bd_we[0]
            | bd_we[1]
            | bd_we[2]
            | bd_we[3]
            | bd_re[0]
            | bd_re[1]
            | bd_re[2]
            | bd_re[3]
        )
    else:
        bd_steal = W(m, u(1, 0))
    inv_all_ready = idle & ~lk_pend.out() & ~fill_busy & ~scan_busy & ~bd_steal
    scan_ready = idle & ~inv_all_valid & ~lk_pend.out() & ~fill_busy & ~bd_steal
    fill_ready = (
        idle & ~inv_all_valid & ~scan_valid & ~lk_pend.out() & ~scan_busy & ~bd_steal
    )
    # Lookup may overlap FILL_WB (write + registered read) so the leaf
    # write-then-read bypass is reachable; FILL_CMP owns the read port.
    lk_ready = (
        (idle | fill_wb)
        & ~inv_all_valid
        & ~scan_valid
        & ~fill_valid
        & ~scan_busy
        & ~bd_steal
    )

    do_inv_all = inv_all_valid & inv_all_ready
    do_scan = scan_valid & scan_ready
    do_fill = fill_valid & fill_ready
    do_lk = lk_valid & lk_ready

    lk_set = set_index(m, lk_page, lk_token_id)
    lk_tag = pack_tag(m, lk_ent_idx, lk_token_id, lk_page)
    fill_set = set_index(m, fill_page, fill_token_id)
    fill_tag = pack_tag(m, fill_ent_idx, fill_token_id, fill_page)
    fill_data = pack_data(
        m, fill_pfn, fill_attr, fill_ap, fill_uxn, fill_pxn, fill_af
    )
    fill_word = pack_word(m, fill_tag, fill_data)

    re = do_lk | do_fill | do_scan
    raddr = mux(m, do_scan, scan_set, mux(m, do_fill, fill_set, lk_set))

    cmp_set = mux(
        m,
        lk_pend.out(),
        lk_set_q.out(),
        mux(m, fill_cmp, fill_set_q.out(), scan_set_q.out()),
    )

    vlds = [vld0.out(), vld1.out(), vld2.out(), vld3.out()]
    raw_v = [
        bit_at(m, vlds[0], cmp_set, SET_W),
        bit_at(m, vlds[1], cmp_set, SET_W),
        bit_at(m, vlds[2], cmp_set, SET_W),
        bit_at(m, vlds[3], cmp_set, SET_W),
    ]
    pend_hit_way = way_oh(m, pend_way.out())
    pend_same = pend_v.out() & (pend_set.out() == cmp_set)
    vis_v = []
    for i in range(4):
        vis_v.append(raw_v[i] | (pend_same & pend_hit_way[i]))

    # Primitive write + valid set in FILL_WB (cycle after fill compare).
    we_now = fill_wb
    wr_oh = way_oh(m, pend_way.out())
    func_we = [
        we_now & wr_oh[0],
        we_now & wr_oh[1],
        we_now & wr_oh[2],
        we_now & wr_oh[3],
    ]
    func_waddr = fill_set_q.out()
    func_wdata = fill_word_q.out()
    we_i = []
    waddr_i = []
    wdata_i = []
    re_i = []
    raddr_i = []
    for i in range(4):
        if test_hooks != 0:
            use_bd_w = tb_test_mode & bd_we[i]
            use_bd_r = tb_test_mode & bd_re[i]
            we_i.append(func_we[i] | use_bd_w)
            waddr_i.append(mux(m, use_bd_w, bd_addr[i], func_waddr))
            wdata_i.append(mux(m, use_bd_w, bd_wdata[i], func_wdata))
            re_i.append(re | use_bd_r)
            raddr_i.append(mux(m, use_bd_r, bd_addr[i], raddr))
        else:
            we_i.append(func_we[i])
            waddr_i.append(func_waddr)
            wdata_i.append(func_wdata)
            re_i.append(re)
            raddr_i.append(raddr)

    rdatas = inst_ways(m, clk, we_i, waddr_i, wdata_i, re_i, raddr_i)

    byp_fire = [
        we_i[0] & re_i[0] & (waddr_i[0] == raddr_i[0]),
        we_i[1] & re_i[1] & (waddr_i[1] == raddr_i[1]),
        we_i[2] & re_i[2] & (waddr_i[2] == raddr_i[2]),
        we_i[3] & re_i[3] & (waddr_i[3] == raddr_i[3]),
    ]
    byp_v0.set(byp_fire[0])
    byp_v1.set(byp_fire[1])
    byp_v2.set(byp_fire[2])
    byp_v3.set(byp_fire[3])
    byp_d0.set(wdata_i[0])
    byp_d1.set(wdata_i[1])
    byp_d2.set(wdata_i[2])
    byp_d3.set(wdata_i[3])

    r_use = [
        mux(m, byp_v0.out(), byp_d0.out(), rdatas[0]),
        mux(m, byp_v1.out(), byp_d1.out(), rdatas[1]),
        mux(m, byp_v2.out(), byp_d2.out(), rdatas[2]),
        mux(m, byp_v3.out(), byp_d3.out(), rdatas[3]),
    ]
    tags = [
        unpack_tag(m, r_use[0]),
        unpack_tag(m, r_use[1]),
        unpack_tag(m, r_use[2]),
        unpack_tag(m, r_use[3]),
    ]
    datas = [
        unpack_data(m, r_use[0]),
        unpack_data(m, r_use[1]),
        unpack_data(m, r_use[2]),
        unpack_data(m, r_use[3]),
    ]
    vis_tag = []
    for i in range(4):
        vis_tag.append(mux(m, pend_same & pend_hit_way[i], pend_tag.out(), tags[i]))

    lk_hits = []
    for i in range(4):
        lk_hits.append(vis_v[i] & (vis_tag[i] == lk_tag_q.out()))

    fill_hits = []
    for i in range(4):
        fill_hits.append(vis_v[i] & (vis_tag[i] == fill_tag_q.out()))

    any_fill_hit = any4(m, fill_hits)
    inv_oh = first_inv_oh(m, vis_v)
    any_inv = any4(m, inv_oh)
    b0s = bit_at(m, plru0.out(), fill_set_q.out(), SET_W)
    b1s = bit_at(m, plru1.out(), fill_set_q.out(), SET_W)
    b2s = bit_at(m, plru2.out(), fill_set_q.out(), SET_W)
    vic = plru_victim(m, b0s, b1s, b2s)
    vic_oh = way_oh(m, vic)
    fill_oh = mux_oh(
        m, any_fill_hit, fill_hits, mux_oh(m, any_inv, inv_oh, vic_oh)
    )
    fill_way = oh_to_way(m, fill_oh)

    sel_data = and_or_sel(m, lk_hits, datas, DATA_W)
    xlat = unpack_xlat(m, sel_data)
    lk_hit = any4(m, lk_hits)

    # Scan match: way valid and (optional) ENT_IDX / TokenID compare.
    scan_hits = []
    for i in range(4):
        ent_i = ex(m, vis_tag[i], PAGE_W + TOKEN_W, ENT_IDX_W)
        tok_i = ex(m, vis_tag[i], PAGE_W, TOKEN_W)
        ent_ok = ~scan_me_q.out() | (ent_i == scan_ent_q.out())
        tok_ok = ~scan_mt_q.out() | (tok_i == scan_tok_q.out())
        scan_hits.append(vis_v[i] & ent_ok & tok_ok)

    # Next-state one-hot (same cycle map as the old encoded st).
    nxt_fill_cmp = do_fill
    nxt_fill_wb = ~do_fill & fill_cmp
    nxt_idle = ~do_fill & ~fill_cmp
    st_idle.set(nxt_idle)
    st_fill_cmp.set(nxt_fill_cmp)
    st_fill_wb.set(nxt_fill_wb)

    lk_pend.set(do_lk)
    lk_set_q.set(lk_set, when=do_lk)
    lk_tag_q.set(lk_tag, when=do_lk)

    fill_set_q.set(fill_set, when=do_fill)
    fill_tag_q.set(fill_tag, when=do_fill)
    fill_word_q.set(fill_word, when=do_fill)

    pend_v.set(fill_cmp)
    pend_set.set(fill_set_q.out(), when=fill_cmp)
    pend_way.set(fill_way, when=fill_cmp)
    pend_tag.set(fill_tag_q.out(), when=fill_cmp)

    scan_pend.set(do_scan)
    scan_clr.set(scan_pend.out())
    scan_set_q.set(scan_set, when=do_scan)
    scan_set_qq.set(scan_set_q.out(), when=scan_pend.out())
    scan_ent_q.set(scan_ent_idx, when=do_scan)
    scan_tok_q.set(scan_token_id, when=do_scan)
    scan_me_q.set(scan_match_ent, when=do_scan)
    scan_mt_q.set(scan_match_tok, when=do_scan)
    scan_hit_q.set(cat_hits(m, scan_hits), when=scan_pend.out())

    # Valid write-back: inv_all this cycle; fill set in FILL_WB; scan clear
    # the cycle after compare (scan_clr).
    clr_oh = [
        ex(m, scan_hit_q.out(), 0, 1),
        ex(m, scan_hit_q.out(), 1, 1),
        ex(m, scan_hit_q.out(), 2, 1),
        ex(m, scan_hit_q.out(), 3, 1),
    ]
    wr_v = [vld0, vld1, vld2, vld3]
    for i in range(4):
        set_bit = fill_wb & wr_oh[i]
        clr_bit = scan_clr.out() & clr_oh[i]
        if test_hooks != 0:
            bd_v = tb_test_mode & bd_vld_we[i]
            v_idx = mux(
                m,
                bd_v,
                bd_addr[i],
                mux(m, fill_wb, fill_set_q.out(), scan_set_qq.out()),
            )
            v_we = set_bit | clr_bit | bd_v
            v_bit = mux(m, bd_v, bd_vld_wd[i], set_bit)
        else:
            v_idx = mux(m, fill_wb, fill_set_q.out(), scan_set_qq.out())
            v_we = set_bit | clr_bit
            v_bit = set_bit
        nxt = bit_write(m, wr_v[i].out(), v_idx, v_we, v_bit, SET_W)
        wr_v[i].set(mux(m, do_inv_all, u(TLB_SETS, 0), nxt))

    # PLRU update the cycle after lookup hit or in FILL_WB.
    lk_way = oh_to_way(m, lk_hits)
    plru_we_q.set(lk_pend.out() & lk_hit)
    plru_set_q.set(lk_set_q.out(), when=lk_pend.out() & lk_hit)
    plru_way_q.set(lk_way, when=lk_pend.out() & lk_hit)

    plru_upd = plru_we_q.out() | fill_wb
    plru_upd_set = mux(m, fill_wb, fill_set_q.out(), plru_set_q.out())
    plru_upd_way = mux(m, fill_wb, pend_way.out(), plru_way_q.out())
    cb0 = bit_at(m, plru0.out(), plru_upd_set, SET_W)
    cb1 = bit_at(m, plru1.out(), plru_upd_set, SET_W)
    cb2 = bit_at(m, plru2.out(), plru_upd_set, SET_W)
    nb0, nb1, nb2 = plru_next(m, cb0, cb1, cb2, plru_upd_way)
    plru0.set(bit_write(m, plru0.out(), plru_upd_set, plru_upd, nb0, SET_W))
    plru1.set(bit_write(m, plru1.out(), plru_upd_set, plru_upd, nb1, SET_W))
    plru2.set(bit_write(m, plru2.out(), plru_upd_set, plru_upd, nb2, SET_W))

    m.output("lk_ready", lk_ready)
    m.output("lk_rsp_valid", lk_pend.out())
    m.output("lk_hit", lk_hit & lk_pend.out())
    m.output("xlat_pfn", mux(m, lk_pend.out() & lk_hit, xlat[0], u(PFN_W, 0)))
    m.output("xlat_attr", mux(m, lk_pend.out() & lk_hit, xlat[1], u(ATTR_W, 0)))
    m.output("xlat_ap", mux(m, lk_pend.out() & lk_hit, xlat[2], u(AP_W, 0)))
    m.output("xlat_uxn", mux(m, lk_pend.out() & lk_hit, xlat[3], u(1, 0)))
    m.output("xlat_pxn", mux(m, lk_pend.out() & lk_hit, xlat[4], u(1, 0)))
    m.output("xlat_af", mux(m, lk_pend.out() & lk_hit, xlat[5], u(1, 0)))
    m.output("fill_ready", fill_ready)
    m.output("inv2tlb_all_ready", inv_all_ready)
    m.output("inv2tlb_scan_ready", scan_ready)
    m.output("tlb2inv_scan_done", scan_clr.out())
    m.output("busy", fill_busy | scan_busy | lk_pend.out() | inv_all_valid)

    if test_hooks != 0:
        # Observation: HOOKS-only, not gated by tb_test_mode, no keep (SPEC §10).
        # Same cycle = lookup request + 1 (tag-compare). hit is before AND-OR select.
        lk_vld_vec = [
            bit_at(m, vlds[0], lk_set_q.out(), SET_W),
            bit_at(m, vlds[1], lk_set_q.out(), SET_W),
            bit_at(m, vlds[2], lk_set_q.out(), SET_W),
            bit_at(m, vlds[3], lk_set_q.out(), SET_W),
        ]
        m.output("tb_mem_tlb_obs_lkup_v", lk_pend.out())
        m.output("tb_mem_tlb_obs_hit", cat_hits(m, lk_hits))
        m.output("tb_mem_tlb_obs_vld", cat_hits(m, lk_vld_vec))
        m.output("tb_mem_tlb_obs_tag_w0", tags[0])
        m.output("tb_mem_tlb_obs_tag_w1", tags[1])
        m.output("tb_mem_tlb_obs_tag_w2", tags[2])
        m.output("tb_mem_tlb_obs_tag_w3", tags[3])

        # Backdoor readout: tb_test_mode=0 holds 0 (SPEC §10).
        bd_re_q = []
        bd_rd_q = []
        for i in range(4):
            rq = m.out(
                f"bd_re_q_{i}", clk=clk, rst=rst, width=1, init=u(1, 0), en=1
            )
            dq = m.out(
                f"bd_rd_q_{i}",
                clk=clk,
                rst=rst,
                width=WORD_W,
                init=u(WORD_W, 0),
                en=1,
            )
            rq.set(tb_test_mode & bd_re[i])
            dq.set(
                mux(
                    m,
                    tb_test_mode,
                    mux(m, rq.out(), r_use[i], dq.out()),
                    u(WORD_W, 0),
                )
            )
            bd_re_q.append(rq)
            bd_rd_q.append(dq)
            m.output(f"tb_mem_tlb_w{i}_bd_rdata", dq.out())


@module(name="ub_mem_tlb")
def build(
    m: Circuit,
    tlb_sets: int = 64,
    tlb_ways: int = 4,
    test_hooks: int = 0,
) -> None:
    tlb_sets = int(tlb_sets)
    tlb_ways = int(tlb_ways)
    test_hooks = int(test_hooks)
    if tlb_sets != TLB_SETS:
        raise ValueError("this netlist is the default TLB_SETS=64 set")
    if tlb_ways != TLB_WAYS:
        raise ValueError("this netlist is the default TLB_WAYS=4 set")
    if test_hooks != 0:
        if test_hooks != 1:
            raise ValueError("test_hooks must be 0 or 1")
    _tlb_body(m, test_hooks=test_hooks)


build.__pycircuit_name__ = "ub_mem_tlb"

VARIANTS = {
    "": {"TLB_SETS": 64, "TLB_WAYS": 4},
}
LEAF = "ub_mem_tlb"
