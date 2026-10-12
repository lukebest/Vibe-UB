"""ub_lmsm — UB link-management state machine (real pyc4.0 @module).

Business registers are ``pyc_reg`` (sync, active-high ``rst_pyc``,
``core_clk`` only). ``TEST_HOOKS`` is a Python-time compile parameter
(SPEC §11); generated Verilog has no ifdef.

SPEC: §2.5 / §3.2.5 / §3.3.3 / §3.3.4 / §4.2 / §6.1 / §9 / §10.
Null-block handshake and ``PROBE_WAIT_CYC``: PR #41 @ 9a85b136 (D20).
Earlier PR #9 closures kept: CTRL.LMSM_START, lane_id_mode never 3,
LTB type bytes, Change_Speed bit7=0, LinkReady = Active.
Architectural ``link_up`` is Null|Active|Retrain (SPEC §6.1 / A-22);
``tb_obs_link_up`` stays Null|Active (§10.2).

Does not compute LMB CRC (PCS). Does not generate the 16-cycle PORT_RST
pulse (ub_csr); ``port_rst`` is a sync clear to Link_Idle.
"""

from __future__ import annotations

from pycircuit import Circuit, module, mux, u

LEAF = "ub_lmsm"
VARIANTS: dict[str, dict] = {"": {}}

# ---------------------------------------------------------------------------
# Parameters (SPEC §9 / §6.1). Identifiers match the spec table.
# ---------------------------------------------------------------------------

NUM_LANES_TX = 1
NUM_LANES_RX = 1

F_CORE_HZ = 2_578_125_000 / 32


def _cycles(seconds: float) -> int:
    return int(round(seconds * F_CORE_HZ))


TMR_W = 32
PROBE_W = 16
RX_CNT_W = 4
TX_CNT_W = 5

# Official timeouts: cycles = round(duration × F_CORE) (SPEC §6.1).
P_TMR_RXEQ = _cycles(0.048)
P_TMR_DISC_ACTIVE = _cycles(0.024)
P_TMR_DISC_ACTIVE_RTR_CFG = _cycles(10e-6)
P_TMR_DISC_CONFIRM = _cycles(0.048)
P_TMR_CFG = _cycles(0.002)
P_TMR_NULL = _cycles(0.002)
P_TMR_RETRAIN_ACTIVE = _cycles(0.024)
P_TMR_RETRAIN_CONFIRM = _cycles(0.048)
P_TMR_CHG_SPD = _cycles(0.048)
P_TMR_EQ_PASSIVE = _cycles(0.032)
P_TMR_EQ_ACTIVE = _cycles(0.024)

P_NULL_RX_NEED = 8
P_NULL_TX_NEED = 16
P_MAX_RETRAIN = 4
P_PROBE_MAX_RETRY = 8
P_PROBE_WAIT_CYC = 323

P_LTB_TYPE_DLTB_ACTIVE = 0xA0
P_LTB_TYPE_DLTB_CONFIRM = 0xA1
P_LTB_TYPE_RXEQ = 0xE0
P_LTB_TYPE_CLTB_ACTIVE = 0xB0
P_LTB_TYPE_CLTB_CHECK = 0xB1
P_LTB_TYPE_CLTB_CONFIRM = 0xB2
P_LTB_TYPE_RLTB_ACTIVE = 0xC0
P_LTB_TYPE_RLTB_CONFIRM = 0xC1
P_LTB_TYPE_RLTB_LP1 = 0xC2
P_LTB_TYPE_RLTB_EQ_INIT = 0xC3
P_LTB_TYPE_ELTB = 0xD0

P_LANE_ID_NULL = 0xFF
P_LINK_ID_NULL = 0xFF
P_CHG_SPD_BIT = 7

ST_LINK_IDLE = 0
ST_PROBE = 1
ST_RXEQ_OPTIMIZE = 2
ST_DISCOVERY = 3
ST_CONFIG = 4
ST_SEND_NULLBLOCK = 5
ST_LINK_ACTIVE = 6
ST_RETRAIN = 7
ST_CHANGE_SPEED = 8
ST_EQUALIZATION = 9

SUB_0 = 0
SUB_1 = 1
SUB_2 = 2

PAT_IDLE = 0
PAT_EEIB = 1
PAT_LTB = 2
PAT_DLL = 3

LANE_ID_PHYS = 0
LANE_ID_ASCEND = 1
LANE_ID_NULL = 2


def _red_or(word):
    bits = [word.slice(lsb=i, width=1) for i in range(int(word.width))]
    acc = bits[0]
    for bit in bits[1:]:
        acc = acc | bit
    return acc


def _red_and(word):
    bits = [word.slice(lsb=i, width=1) for i in range(int(word.width))]
    acc = bits[0]
    for bit in bits[1:]:
        acc = acc & bit
    return acc


def _red_xor(words):
    acc = words[0]
    for word in words[1:]:
        acc = acc ^ word
    return acc


def _sat_add(cur, step):
    summed = cur + step
    return mux(_red_and(cur), cur, summed)


def _auto_ascend(base, ntx: int):
    if ntx == 1:
        return base
    pieces = [base + u(8, i) for i in range(ntx - 1, -1, -1)]
    return pieces[0].m.cat(*pieces)


def _null_map(m: Circuit, ntx: int):
    if ntx == 1:
        return u(8, P_LANE_ID_NULL)
    pieces = [u(8, P_LANE_ID_NULL) for _ in range(ntx)]
    return m.cat(*pieces)


def _ports(m: Circuit, *, test_hooks: int, ntx: int, nrx: int, probe_wait_def: int):
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")
    port_rst = m.input("port_rst", width=1)

    csr_lmsm_start = m.input("csr_lmsm_start", width=1)
    csr_bypass_probe = m.input("csr_bypass_probe", width=1)
    cfg_fixed_rate_rxeq = m.input("cfg_fixed_rate_rxeq", width=1)
    cfg_req_change_speed = m.input("cfg_req_change_speed", width=1)
    cfg_req_equalization = m.input("cfg_req_equalization", width=1)
    cfg_null_need_rediscovery = m.input("cfg_null_need_rediscovery", width=1)
    cfg_lane_reverse_tx = m.input("cfg_lane_reverse_tx", width=1)
    cfg_lane_reverse_rx = m.input("cfg_lane_reverse_rx", width=1)
    cfg_polarity_inv = m.input("cfg_polarity_inv", width=nrx)
    cfg_link_id = m.input("cfg_link_id", width=8)
    cfg_tlw = m.input("cfg_tlw", width=6)
    cfg_rlw = m.input("cfg_rlw", width=6)
    cfg_data_rate_support_1 = m.input("cfg_data_rate_support_1", width=8)
    cfg_data_rate_support_2 = m.input("cfg_data_rate_support_2", width=8)
    cfg_fec_mode_support = m.input("cfg_fec_mode_support", width=8)
    cfg_port_type = m.input("cfg_port_type", width=1)
    cfg_portnego_random_value = m.input("cfg_portnego_random_value", width=7)
    cfg_fec_interleave_support = m.input("cfg_fec_interleave_support", width=4)
    cfg_rx_lane0_id = m.input("cfg_rx_lane0_id", width=3)
    cfg_max_link_width = m.input("cfg_max_link_width", width=3)
    cfg_eq_mode = m.input("cfg_eq_mode", width=2)
    cfg_fec_mode_ctrl = m.input("cfg_fec_mode_ctrl", width=3)
    cfg_fec_interleave_ctrl = m.input("cfg_fec_interleave_ctrl", width=1)
    cfg_eq_ctrl1 = m.input("cfg_eq_ctrl1", width=6)
    cfg_eq_ctrl2 = m.input("cfg_eq_ctrl2", width=8)
    cfg_eq_ctrl3 = m.input("cfg_eq_ctrl3", width=8)
    cfg_eq_ctrl4 = m.input("cfg_eq_ctrl4", width=8)
    cfg_fec_crc_mode_reject = m.input("cfg_fec_crc_mode_reject", width=1)
    cfg_pre_fec_ber_meas_st = m.input("cfg_pre_fec_ber_meas_st", width=2)
    cfg_fec_interleave_enable = m.input("cfg_fec_interleave_enable", width=1)
    cfg_fec_interleave_ctrl_reject = m.input("cfg_fec_interleave_ctrl_reject", width=1)
    cfg_request_equalization = m.input("cfg_request_equalization", width=1)
    cfg_crc_mode_ctrl = m.input("cfg_crc_mode_ctrl", width=3)
    cfg_local_tx_preset = m.input("cfg_local_tx_preset", width=4)
    cfg_first_pre_cursor = m.input("cfg_first_pre_cursor", width=6)
    cfg_eq_reject = m.input("cfg_eq_reject", width=1)
    cfg_current_eq_phase = m.input("cfg_current_eq_phase", width=2)
    cfg_preset_mode_en = m.input("cfg_preset_mode_en", width=1)
    cfg_tx_preset = m.input("cfg_tx_preset", width=4)
    cfg_lane_id_base = m.input("cfg_lane_id_base", width=8)
    map_w = 8 * ntx
    cfg_lane_id_map = m.input("cfg_lane_id_map", width=map_w)
    csr_tmr_scale = m.input("csr_tmr_scale", width=8)
    probe_wait_cyc = m.input("probe_wait_cyc", width=PROBE_W)

    pma_term_detect = m.input("pma_term_detect", width=ntx)
    pma_rx_eidle_exit = m.input("pma_rx_eidle_exit", width=nrx)
    pma_phy_ready = m.input("pma_phy_ready", width=1)
    dll_retrain_req = m.input("dll_retrain_req", width=1)

    pcs2lmsm_ltb_valid = m.input("pcs2lmsm_ltb_valid", width=1)
    pcs2lmsm_ltb_type = m.input("pcs2lmsm_ltb_type", width=8)
    pcs2lmsm_link_id = m.input("pcs2lmsm_link_id", width=8)
    pcs2lmsm_lane_id = m.input("pcs2lmsm_lane_id", width=8)
    pcs2lmsm_tlw = m.input("pcs2lmsm_tlw", width=6)
    pcs2lmsm_rlw = m.input("pcs2lmsm_rlw", width=6)
    pcs2lmsm_data_rate_support_1 = m.input("pcs2lmsm_data_rate_support_1", width=8)
    pcs2lmsm_data_rate_support_2 = m.input("pcs2lmsm_data_rate_support_2", width=8)
    pcs2lmsm_fec_mode_support = m.input("pcs2lmsm_fec_mode_support", width=8)
    pcs2lmsm_port_type = m.input("pcs2lmsm_port_type", width=1)
    pcs2lmsm_portnego_random_value = m.input("pcs2lmsm_portnego_random_value", width=7)
    pcs2lmsm_fec_interleave_support = m.input("pcs2lmsm_fec_interleave_support", width=4)
    pcs2lmsm_rx_lane0_id = m.input("pcs2lmsm_rx_lane0_id", width=3)
    pcs2lmsm_max_link_width = m.input("pcs2lmsm_max_link_width", width=3)
    pcs2lmsm_eq_mode = m.input("pcs2lmsm_eq_mode", width=2)
    pcs2lmsm_fec_mode_ctrl = m.input("pcs2lmsm_fec_mode_ctrl", width=3)
    pcs2lmsm_fec_interleave_ctrl = m.input("pcs2lmsm_fec_interleave_ctrl", width=1)
    pcs2lmsm_eq_ctrl1 = m.input("pcs2lmsm_eq_ctrl1", width=6)
    pcs2lmsm_eq_ctrl2 = m.input("pcs2lmsm_eq_ctrl2", width=8)
    pcs2lmsm_eq_ctrl3 = m.input("pcs2lmsm_eq_ctrl3", width=8)
    pcs2lmsm_eq_ctrl4 = m.input("pcs2lmsm_eq_ctrl4", width=8)
    pcs2lmsm_fec_crc_mode_reject = m.input("pcs2lmsm_fec_crc_mode_reject", width=1)
    pcs2lmsm_pre_fec_ber_meas_st = m.input("pcs2lmsm_pre_fec_ber_meas_st", width=2)
    pcs2lmsm_fec_interleave_enable = m.input("pcs2lmsm_fec_interleave_enable", width=1)
    pcs2lmsm_fec_interleave_ctrl_reject = m.input("pcs2lmsm_fec_interleave_ctrl_reject", width=1)
    pcs2lmsm_request_equalization = m.input("pcs2lmsm_request_equalization", width=1)
    pcs2lmsm_crc_mode_ctrl = m.input("pcs2lmsm_crc_mode_ctrl", width=3)
    pcs2lmsm_local_tx_preset = m.input("pcs2lmsm_local_tx_preset", width=4)
    pcs2lmsm_first_pre_cursor = m.input("pcs2lmsm_first_pre_cursor", width=6)
    pcs2lmsm_eq_reject = m.input("pcs2lmsm_eq_reject", width=1)
    pcs2lmsm_current_eq_phase = m.input("pcs2lmsm_current_eq_phase", width=2)
    pcs2lmsm_preset_mode_en = m.input("pcs2lmsm_preset_mode_en", width=1)
    pcs2lmsm_tx_preset = m.input("pcs2lmsm_tx_preset", width=4)
    pcs_am_locked = m.input("pcs_am_locked", width=nrx)
    pcs_lid_bad = m.input("pcs_lid_bad", width=1)
    pcs_deskew_ok = m.input("pcs_deskew_ok", width=1)
    pcs2lmsm_null_blk = m.input("pcs2lmsm_null_blk", width=1)
    pcs2lmsm_rx_nonnull_blk = m.input("pcs2lmsm_rx_nonnull_blk", width=1)
    pcs2lmsm_tx_null_blk = m.input("pcs2lmsm_tx_null_blk", width=1)

    # Simulation-only; no synthesis effect (pyc.assert).
    m.assert_(~(pcs2lmsm_null_blk & pcs2lmsm_rx_nonnull_blk))

    tb_test_mode = None
    if test_hooks:
        tb_test_mode = m.input("tb_test_mode", width=1)
        tb_inj_am_lock = m.input("tb_inj_am_lock", width=nrx)
        tb_inj_lid_bad = m.input("tb_inj_lid_bad", width=1)
        hook_en = tb_test_mode
        am_locked_u = mux(hook_en, tb_inj_am_lock, pcs_am_locked)
        lid_bad_u = mux(hook_en, tb_inj_lid_bad, pcs_lid_bad)
        tmr_step = mux(hook_en & (csr_tmr_scale != 0), csr_tmr_scale, m.const(1, width=8))
    else:
        am_locked_u = pcs_am_locked
        lid_bad_u = pcs_lid_bad
        tmr_step = m.const(1, width=8)

    am_all = _red_and(am_locked_u)
    term_any = _red_or(pma_term_detect)
    eidle_any = _red_or(pma_rx_eidle_exit)

    st = m.out("st", clk=clk, rst=rst, width=5, init=u(5, ST_LINK_IDLE))
    sub = m.out("sub", clk=clk, rst=rst, width=2, init=u(2, SUB_0))
    tmr = m.out("tmr", clk=clk, rst=rst, width=TMR_W, init=u(TMR_W, 0))
    probe_try = m.out("probe_try", clk=clk, rst=rst, width=8, init=u(8, 0))
    retrain_left = m.out(
        "retrain_left", clk=clk, rst=rst, width=8, init=u(8, P_MAX_RETRAIN)
    )
    saw_rx_ltb = m.out("saw_rx_ltb", clk=clk, rst=rst, width=1, init=u(1, 0))
    disc_short = m.out("disc_short", clk=clk, rst=rst, width=1, init=u(1, 0))
    train_fail_q = m.out("train_fail_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    train_to_q = m.out("train_to_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    rx_type_q = m.out("rx_type_q", clk=clk, rst=rst, width=8, init=u(8, 0))
    rx_link_q = m.out("rx_link_q", clk=clk, rst=rst, width=8, init=u(8, 0))
    rx_lane_q = m.out("rx_lane_q", clk=clk, rst=rst, width=8, init=u(8, 0))
    rx_tlw_q = m.out("rx_tlw_q", clk=clk, rst=rst, width=6, init=u(6, 0))
    rx_rlw_q = m.out("rx_rlw_q", clk=clk, rst=rst, width=6, init=u(6, 0))
    rx_fec_ctrl_q = m.out("rx_fec_ctrl_q", clk=clk, rst=rst, width=3, init=u(3, 0))
    rx_req_eq_q = m.out("rx_req_eq_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    rx_drs2_q = m.out("rx_drs2_q", clk=clk, rst=rst, width=8, init=u(8, 0))
    null_seen = m.out("null_seen", clk=clk, rst=rst, width=1, init=u(1, 0))
    rx_cnt = m.out("rx_cnt", clk=clk, rst=rst, width=RX_CNT_W, init=u(RX_CNT_W, 0))
    tx_cnt = m.out("tx_cnt", clk=clk, rst=rst, width=TX_CNT_W, init=u(TX_CNT_W, 0))
    first_rx = m.out("first_rx", clk=clk, rst=rst, width=1, init=u(1, 0))
    probe_tmr = m.out("probe_tmr", clk=clk, rst=rst, width=PROBE_W, init=u(PROBE_W, 0))
    probe_lim = m.out(
        "probe_lim", clk=clk, rst=rst, width=PROBE_W, init=u(PROBE_W, probe_wait_def)
    )

    unused_aux = _red_xor(
        [
            _red_or(pcs2lmsm_data_rate_support_1),
            _red_or(pcs2lmsm_fec_mode_support),
            pcs2lmsm_port_type,
            _red_or(pcs2lmsm_portnego_random_value),
            _red_or(pcs2lmsm_fec_interleave_support),
            _red_or(pcs2lmsm_rx_lane0_id),
            _red_or(pcs2lmsm_max_link_width),
            _red_or(pcs2lmsm_eq_mode),
            pcs2lmsm_fec_interleave_ctrl,
            _red_or(pcs2lmsm_eq_ctrl1),
            _red_or(pcs2lmsm_eq_ctrl2),
            _red_or(pcs2lmsm_eq_ctrl3),
            _red_or(pcs2lmsm_eq_ctrl4),
            pcs2lmsm_fec_crc_mode_reject,
            _red_or(pcs2lmsm_pre_fec_ber_meas_st),
            pcs2lmsm_fec_interleave_enable,
            pcs2lmsm_fec_interleave_ctrl_reject,
            _red_or(pcs2lmsm_crc_mode_ctrl),
            _red_or(pcs2lmsm_local_tx_preset),
            _red_or(pcs2lmsm_first_pre_cursor),
            pcs2lmsm_eq_reject,
            _red_or(pcs2lmsm_current_eq_phase),
            pcs2lmsm_preset_mode_en,
            _red_or(pcs2lmsm_tx_preset),
            eidle_any,
            _red_or(csr_tmr_scale),
        ]
    )

    st_q = st.out()
    sub_q = sub.out()
    tmr_q = tmr.out()
    probe_try_q = probe_try.out()
    retrain_left_q = retrain_left.out()
    saw_q = saw_rx_ltb.out()
    disc_short_q = disc_short.out()
    rx_type = rx_type_q.out()
    rx_req_eq = rx_req_eq_q.out()
    rx_drs2 = rx_drs2_q.out()
    null_seen_q = null_seen.out()
    rx_cnt_q = rx_cnt.out()
    tx_cnt_q = tx_cnt.out()
    first_rx_q = first_rx.out()
    probe_tmr_q = probe_tmr.out()
    probe_lim_q = probe_lim.out()

    # Keep RX-aux / eidle / PRODUCT csr_tmr_scale / shadow-Q in the cone
    # (BCRC crc_recv[31] pattern): AND with a live flop bit that is
    # architecturally 0 (retrain_left max is 4). pycc cannot DCE
    # `x & reg`. The AND is only in a synth-off assert.
    keep0 = retrain_left_q.slice(lsb=7, width=1)
    unused_hold = _red_xor(
        [
            _red_or(rx_link_q.out()),
            _red_or(rx_lane_q.out()),
            _red_or(rx_tlw_q.out()),
            _red_or(rx_rlw_q.out()),
            _red_or(rx_fec_ctrl_q.out()),
            rx_link_q.out() == P_LINK_ID_NULL,
        ]
    )
    # Keep RX-aux in the emit cone via a synth-off assert (BCRC keep
    # pattern). Do not OR into term_u — that poisoned PRODUCT≡HOOKS.
    m.assert_(~((unused_aux ^ unused_hold) & keep0))
    term_u = term_any

    in_idle = st_q == ST_LINK_IDLE
    in_probe = st_q == ST_PROBE
    in_rxeq = st_q == ST_RXEQ_OPTIMIZE
    in_disc = st_q == ST_DISCOVERY
    in_cfg = st_q == ST_CONFIG
    in_null = st_q == ST_SEND_NULLBLOCK
    in_active = st_q == ST_LINK_ACTIVE
    in_retrain = st_q == ST_RETRAIN
    in_chg = st_q == ST_CHANGE_SPEED
    in_eq = st_q == ST_EQUALIZATION
    sub0 = sub_q == SUB_0
    sub1 = sub_q == SUB_1

    legal_st = (
        in_idle
        | in_probe
        | in_rxeq
        | in_disc
        | in_cfg
        | in_null
        | in_active
        | in_retrain
        | in_chg
        | in_eq
    )

    tmr_lim = u(TMR_W, (1 << TMR_W) - 1)
    tmr_lim = mux(in_rxeq, u(TMR_W, P_TMR_RXEQ), tmr_lim)
    tmr_lim = mux(
        in_disc & sub0 & disc_short_q, u(TMR_W, P_TMR_DISC_ACTIVE_RTR_CFG), tmr_lim
    )
    tmr_lim = mux(
        in_disc & sub0 & ~disc_short_q, u(TMR_W, P_TMR_DISC_ACTIVE), tmr_lim
    )
    tmr_lim = mux(in_disc & ~sub0, u(TMR_W, P_TMR_DISC_CONFIRM), tmr_lim)
    tmr_lim = mux(in_cfg, u(TMR_W, P_TMR_CFG), tmr_lim)
    tmr_lim = mux(in_null, u(TMR_W, P_TMR_NULL), tmr_lim)
    tmr_lim = mux(in_retrain & sub0, u(TMR_W, P_TMR_RETRAIN_ACTIVE), tmr_lim)
    tmr_lim = mux(in_retrain & ~sub0, u(TMR_W, P_TMR_RETRAIN_CONFIRM), tmr_lim)
    tmr_lim = mux(in_chg, u(TMR_W, P_TMR_CHG_SPD), tmr_lim)
    tmr_lim = mux(in_eq & sub0, u(TMR_W, P_TMR_EQ_PASSIVE), tmr_lim)
    tmr_lim = mux(in_eq & ~sub0, u(TMR_W, P_TMR_EQ_ACTIVE), tmr_lim)

    tmr_to_main = tmr_q >= tmr_lim
    tmr_to_probe = probe_tmr_q >= probe_lim_q
    tmr_to = mux(in_probe, tmr_to_probe, tmr_to_main)

    rx_type_dltb = (rx_type == P_LTB_TYPE_DLTB_ACTIVE) | (
        rx_type == P_LTB_TYPE_DLTB_CONFIRM
    )
    rx_type_cltb = (
        (rx_type == P_LTB_TYPE_CLTB_ACTIVE)
        | (rx_type == P_LTB_TYPE_CLTB_CHECK)
        | (rx_type == P_LTB_TYPE_CLTB_CONFIRM)
    )
    rx_type_rltb = (
        (rx_type == P_LTB_TYPE_RLTB_ACTIVE)
        | (rx_type == P_LTB_TYPE_RLTB_CONFIRM)
        | (rx_type == P_LTB_TYPE_RLTB_LP1)
        | (rx_type == P_LTB_TYPE_RLTB_EQ_INIT)
    )
    disc_ok = am_all & ~lid_bad_u & pcs_deskew_ok & saw_q & rx_type_dltb
    cfg_ok = am_all & ~lid_bad_u & saw_q & rx_type_cltb
    rtr_ok = am_all & ~lid_bad_u & mux(saw_q, rx_type_rltb, u(1, 1))
    rx_chg_spd = rx_drs2.slice(lsb=P_CHG_SPD_BIT, width=1) | cfg_req_change_speed
    rx_want_eq = rx_req_eq | cfg_req_equalization | cfg_request_equalization

    # Null-block counts: first in-state cycle holds 0; pulses that cycle
    # do not count. Condition uses next-count so same-cycle fill is seen.
    count_en = in_null & null_seen_q
    rx_inc = mux(rx_cnt_q == P_NULL_RX_NEED, rx_cnt_q, rx_cnt_q + 1)
    rx_n = mux(
        ~in_null | ~count_en | pcs2lmsm_rx_nonnull_blk,
        u(RX_CNT_W, 0),
        mux(pcs2lmsm_null_blk, rx_inc, rx_cnt_q),
    )
    first_rx_n = mux(~in_null | ~count_en, u(1, 0), first_rx_q | pcs2lmsm_null_blk)
    tx_gate = count_en & (first_rx_q | pcs2lmsm_null_blk)
    tx_inc = mux(tx_cnt_q == P_NULL_TX_NEED, tx_cnt_q, tx_cnt_q + 1)
    tx_n = mux(
        ~in_null | ~count_en,
        u(TX_CNT_W, 0),
        mux(tx_gate & pcs2lmsm_tx_null_blk, tx_inc, tx_cnt_q),
    )
    null_fill = (rx_n == P_NULL_RX_NEED) & (tx_n >= P_NULL_TX_NEED)

    # ---- next-state (SPEC §6.1). Discovery / 2 ms timeout beat fill. ----
    idle_go = csr_lmsm_start & pma_phy_ready
    idle_st = mux(
        ~idle_go,
        u(5, ST_LINK_IDLE),
        mux(
            ~csr_bypass_probe,
            u(5, ST_PROBE),
            mux(cfg_fixed_rate_rxeq, u(5, ST_RXEQ_OPTIMIZE), u(5, ST_DISCOVERY)),
        ),
    )

    probe_wait = in_probe & sub0
    probe_max = probe_try_q >= P_PROBE_MAX_RETRY
    wait_retry = probe_wait & tmr_to & ~term_u & ~probe_max
    wait_fail = probe_wait & tmr_to & ~term_u & probe_max
    wait_confirm = probe_wait & term_u
    probe_st = mux(wait_fail, u(5, ST_LINK_IDLE), u(5, ST_PROBE))
    probe_st = mux(in_probe & ~sub0 & tmr_to, u(5, ST_DISCOVERY), probe_st)
    probe_sub = mux(wait_confirm, u(2, SUB_1), u(2, SUB_0))
    probe_fail = wait_fail
    probe_totime = wait_fail

    rxeq_st = mux(tmr_to, u(5, ST_DISCOVERY), u(5, ST_RXEQ_OPTIMIZE))

    disc_fail = lid_bad_u | (sub0 & ~am_all & tmr_to) | (~sub0 & ~disc_ok & tmr_to)
    disc_to_cfg = ~lid_bad_u & ~sub0 & disc_ok
    disc_st = mux(disc_fail, u(5, ST_LINK_IDLE), mux(disc_to_cfg, u(5, ST_CONFIG), u(5, ST_DISCOVERY)))
    disc_sub = mux(sub0 & am_all & ~lid_bad_u, u(2, SUB_1), u(2, SUB_0))
    disc_fail_p = disc_fail
    disc_to_p = lid_bad_u.eq(0) & (
        (sub0 & ~am_all & tmr_to) | (~sub0 & ~disc_ok & tmr_to)
    )
    # lid_bad is fail but not a timeout pulse
    disc_to_p = (sub0 & ~am_all & tmr_to) | (~sub0 & ~disc_ok & tmr_to)

    cfg_fail = lid_bad_u | (sub0 & ~am_all & tmr_to) | ((sub_q == SUB_2) & ~cfg_ok & tmr_to)
    cfg_to_null = ~lid_bad_u & (sub_q == SUB_2) & cfg_ok
    cfg_st = mux(cfg_fail, u(5, ST_LINK_IDLE), mux(cfg_to_null, u(5, ST_SEND_NULLBLOCK), u(5, ST_CONFIG)))
    cfg_sub = mux(sub0 & am_all & ~lid_bad_u, u(2, SUB_1), sub_q)
    cfg_sub = mux((sub_q == SUB_1) & (tmr_to | cfg_ok), u(2, SUB_2), cfg_sub)
    cfg_sub = mux(cfg_fail | cfg_to_null, u(2, SUB_0), cfg_sub)
    cfg_to_p = (sub0 & ~am_all & tmr_to) | ((sub_q == SUB_2) & ~cfg_ok & tmr_to)

    null_to_disc = cfg_null_need_rediscovery
    null_to_rtr = ~null_to_disc & tmr_to & (retrain_left_q != 0)
    null_to_idle = ~null_to_disc & tmr_to & (retrain_left_q == 0)
    null_to_act = ~null_to_disc & ~tmr_to & null_fill
    null_st = mux(
        null_to_disc,
        u(5, ST_DISCOVERY),
        mux(
            null_to_rtr,
            u(5, ST_RETRAIN),
            mux(null_to_idle, u(5, ST_LINK_IDLE), mux(null_to_act, u(5, ST_LINK_ACTIVE), u(5, ST_SEND_NULLBLOCK))),
        ),
    )

    act_st = mux(dll_retrain_req | lid_bad_u, u(5, ST_RETRAIN), u(5, ST_LINK_ACTIVE))

    rtr_fail = (sub0 & ~am_all & tmr_to) | (~sub0 & tmr_to & ~rtr_ok)
    rtr_advance = ~sub0 & (rtr_ok | tmr_to) & ~rtr_fail
    rtr_st = mux(rtr_fail, u(5, ST_LINK_IDLE), u(5, ST_RETRAIN))
    rtr_st = mux(
        rtr_advance,
        mux(
            rx_chg_spd,
            u(5, ST_CHANGE_SPEED),
            mux(
                rx_want_eq,
                u(5, ST_EQUALIZATION),
                mux(cfg_null_need_rediscovery, u(5, ST_DISCOVERY), u(5, ST_SEND_NULLBLOCK)),
            ),
        ),
        rtr_st,
    )
    rtr_sub = mux(sub0 & am_all, u(2, SUB_1), u(2, SUB_0))
    rtr_sub = mux(rtr_fail | rtr_advance, u(2, SUB_0), rtr_sub)

    chg_st = mux(tmr_to, u(5, ST_LINK_IDLE), u(5, ST_CHANGE_SPEED))
    eq_st = mux(sub0, u(5, ST_EQUALIZATION), mux(tmr_to, u(5, ST_RETRAIN), u(5, ST_EQUALIZATION)))
    eq_sub = mux(sub0 & tmr_to, u(2, SUB_1), mux(sub0, u(2, SUB_0), u(2, SUB_0)))

    st_n = u(5, ST_LINK_IDLE)
    st_n = mux(in_eq, eq_st, st_n)
    st_n = mux(in_chg, chg_st, st_n)
    st_n = mux(in_retrain, rtr_st, st_n)
    st_n = mux(in_active, act_st, st_n)
    st_n = mux(in_null, null_st, st_n)
    st_n = mux(in_cfg, cfg_st, st_n)
    st_n = mux(in_disc, disc_st, st_n)
    st_n = mux(in_rxeq, rxeq_st, st_n)
    st_n = mux(in_probe, probe_st, st_n)
    st_n = mux(in_idle, idle_st, st_n)
    st_n = mux(legal_st, st_n, u(5, ST_LINK_IDLE))

    sub_n = u(2, SUB_0)
    sub_n = mux(in_eq, eq_sub, sub_n)
    sub_n = mux(in_retrain, rtr_sub, sub_n)
    sub_n = mux(in_cfg, cfg_sub, sub_n)
    sub_n = mux(in_disc, disc_sub, sub_n)
    sub_n = mux(in_probe, probe_sub, sub_n)
    sub_n = mux(legal_st, sub_n, u(2, SUB_0))

    to_idle_fail = mux(in_probe, probe_fail, u(1, 0))
    to_idle_fail = mux(in_disc, disc_fail_p, to_idle_fail)
    to_idle_fail = mux(in_cfg, cfg_fail, to_idle_fail)
    to_idle_fail = mux(in_null, null_to_idle, to_idle_fail)
    to_idle_fail = mux(in_retrain, rtr_fail, to_idle_fail)
    to_idle_fail = mux(in_chg, tmr_to, to_idle_fail)

    to_idle_timeout = mux(in_probe, probe_totime, u(1, 0))
    to_idle_timeout = mux(in_disc, disc_to_p, to_idle_timeout)
    to_idle_timeout = mux(in_cfg, cfg_to_p, to_idle_timeout)
    to_idle_timeout = mux(in_null, null_to_idle, to_idle_timeout)
    to_idle_timeout = mux(in_retrain, rtr_fail, to_idle_timeout)
    to_idle_timeout = mux(in_chg, tmr_to, to_idle_timeout)

    st_enter = (st_n != st_q) | (sub_n != sub_q)
    enter_probe_from_idle = (st_n == ST_PROBE) & in_idle
    entering_probe_wait = (st_n == ST_PROBE) & (sub_n == SUB_0) & ~(in_probe & sub0)
    entering_confirm = wait_confirm
    probe_wait_start = entering_probe_wait | wait_retry | entering_confirm

    folded_wait = mux(probe_wait_cyc == 0, u(PROBE_W, probe_wait_def), probe_wait_cyc)
    step16 = tmr_step.zext(width=PROBE_W)
    step32 = tmr_step.zext(width=TMR_W)
    tmr_inc = _sat_add(tmr_q, step32)
    probe_inc = _sat_add(probe_tmr_q, step16)

    st.set(mux(port_rst, u(5, ST_LINK_IDLE), st_n))
    sub.set(mux(port_rst, u(2, SUB_0), sub_n))
    tmr.set(mux(port_rst | st_enter, u(TMR_W, 0), tmr_inc))
    probe_try_n = mux(enter_probe_from_idle, u(8, 0), probe_try_q)
    probe_try_n = mux(
        wait_retry,
        mux(probe_try_q == 0xFF, probe_try_q, probe_try_q + 1),
        probe_try_n,
    )
    probe_try.set(mux(port_rst, u(8, 0), probe_try_n))
    retrain_n = mux(st_n == ST_LINK_IDLE, u(8, P_MAX_RETRAIN), retrain_left_q)
    retrain_n = mux(
        st_enter & (st_n == ST_RETRAIN) & in_active & (retrain_left_q != 0),
        retrain_left_q - 1,
        retrain_n,
    )
    retrain_left.set(mux(port_rst, u(8, P_MAX_RETRAIN), retrain_n))
    saw_n = mux(st_enter, u(1, 0), saw_q)
    saw_n = mux(pcs2lmsm_ltb_valid, u(1, 1), saw_n)
    saw_rx_ltb.set(mux(port_rst, u(1, 0), saw_n))
    disc_n = mux(
        st_enter & (st_n == ST_DISCOVERY),
        in_retrain | in_cfg,
        disc_short_q,
    )
    disc_short.set(mux(port_rst, u(1, 0), disc_n))
    train_fail_q.set(mux(port_rst, u(1, 0), to_idle_fail))
    train_to_q.set(mux(port_rst, u(1, 0), to_idle_timeout))
    rx_type_q.set(mux(port_rst, u(8, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_ltb_type, rx_type)))
    rx_link_q.set(mux(port_rst, u(8, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_link_id, rx_link_q.out())))
    rx_lane_q.set(mux(port_rst, u(8, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_lane_id, rx_lane_q.out())))
    rx_tlw_q.set(mux(port_rst, u(6, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_tlw, rx_tlw_q.out())))
    rx_rlw_q.set(mux(port_rst, u(6, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_rlw, rx_rlw_q.out())))
    rx_fec_ctrl_q.set(
        mux(port_rst, u(3, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_fec_mode_ctrl, rx_fec_ctrl_q.out()))
    )
    rx_req_eq_q.set(
        mux(port_rst, u(1, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_request_equalization, rx_req_eq))
    )
    rx_drs2_q.set(
        mux(port_rst, u(8, 0), mux(pcs2lmsm_ltb_valid, pcs2lmsm_data_rate_support_2, rx_drs2))
    )
    null_seen.set(mux(port_rst | ~in_null, u(1, 0), u(1, 1)))
    # Clear on the leave edge (st_n != Null). Fill still uses rx_n/tx_n.
    leave_null = st_n != ST_SEND_NULLBLOCK
    rx_cnt.set(mux(port_rst | leave_null, u(RX_CNT_W, 0), rx_n))
    tx_cnt.set(mux(port_rst | leave_null, u(TX_CNT_W, 0), tx_n))
    first_rx.set(mux(port_rst | leave_null, u(1, 0), first_rx_n))
    probe_lim.set(
        mux(
            port_rst,
            u(PROBE_W, probe_wait_def),
            mux(probe_wait_start, folded_wait, probe_lim_q),
        )
    )
    probe_tmr.set(
        mux(port_rst | ~in_probe | probe_wait_start, u(PROBE_W, 0), probe_inc)
    )

    # A-22: LinkUp stays 1 in Retrain and clears on Idle. Obs port is
    # still Null|Active (SPEC §10.2). Change_Speed / Equalization are
    # not written; not guessed.
    link_up = in_null | in_active | in_retrain
    obs_link_up = in_null | in_active
    link_ready = in_active
    lmsm_retrain_ack = in_retrain

    pma_tx_w = 1 if ntx not in (2, 4, 8) else ntx
    pma_rx_w = 1 if nrx not in (2, 4, 8) else nrx

    use_rxeq = in_rxeq
    use_dltb = in_disc
    use_cltb = in_cfg
    use_rltb = in_retrain | in_chg
    use_eltb = in_eq
    use_dltb_cltb = use_dltb | use_cltb
    use_dltb_rltb = use_dltb | use_rltb
    use_cltb_rltb = use_cltb | use_rltb
    use_rltb_eltb = use_rltb | use_eltb

    pattern = mux(in_idle, u(2, PAT_IDLE), u(2, PAT_LTB))
    pattern = mux(in_probe, u(2, PAT_EEIB), pattern)
    pattern = mux(in_null | in_active, u(2, PAT_DLL), pattern)

    sel_phys = in_disc
    sel_ascend = in_cfg | in_active
    lane_mode = mux(sel_phys, u(2, LANE_ID_PHYS), mux(sel_ascend, u(2, LANE_ID_ASCEND), u(2, LANE_ID_NULL)))

    auto_ascend = _auto_ascend(cfg_lane_id_base, ntx)
    null_map = _null_map(m, ntx)
    map_is_zero = cfg_lane_id_map == 0
    lane_map = mux(sel_ascend, mux(map_is_zero, auto_ascend, cfg_lane_id_map), null_map)

    ltb_type = u(8, 0)
    ltb_type = mux(use_eltb, u(8, P_LTB_TYPE_ELTB), ltb_type)
    ltb_type = mux(
        use_rltb,
        mux(sub0, u(8, P_LTB_TYPE_RLTB_ACTIVE), u(8, P_LTB_TYPE_RLTB_CONFIRM)),
        ltb_type,
    )
    ltb_type = mux(
        use_cltb,
        mux(
            sub0,
            u(8, P_LTB_TYPE_CLTB_ACTIVE),
            mux(sub1, u(8, P_LTB_TYPE_CLTB_CHECK), u(8, P_LTB_TYPE_CLTB_CONFIRM)),
        ),
        ltb_type,
    )
    ltb_type = mux(
        use_dltb,
        mux(sub0, u(8, P_LTB_TYPE_DLTB_ACTIVE), u(8, P_LTB_TYPE_DLTB_CONFIRM)),
        ltb_type,
    )
    ltb_type = mux(use_rxeq, u(8, P_LTB_TYPE_RXEQ), ltb_type)

    m.output("pma_data_rate_sel", u(4, 0))
    m.output("pma_tx_width", u(4, pma_tx_w))
    m.output("pma_rx_width", u(4, pma_rx_w))
    m.output("pma_lane_reverse_tx", cfg_lane_reverse_tx)
    m.output("pma_lane_reverse_rx", cfg_lane_reverse_rx)
    m.output("pma_polarity_inv", cfg_polarity_inv)
    m.output("pma_probe_pulse_en", in_probe & sub0)
    m.output("link_up", link_up)
    m.output("link_ready", link_ready)
    m.output("lmsm_retrain_ack", lmsm_retrain_ack)
    m.output("lmsm2pcs_pattern", pattern)
    m.output("lmsm2pcs_ltb_valid", use_rxeq | use_dltb | use_cltb | use_rltb | use_eltb)
    m.output("lmsm2pcs_lane_id_mode", lane_mode)
    m.output("lmsm2pcs_lane_id_base", cfg_lane_id_base)
    m.output("lmsm2pcs_lane_id_map", lane_map)
    m.output("lmsm2pcs_ltb_type", ltb_type)
    m.output("lmsm2pcs_link_id", mux(use_dltb_cltb, cfg_link_id, u(8, 0)))
    m.output("lmsm2pcs_tlw", mux(use_dltb_cltb, cfg_tlw, u(6, 0)))
    m.output("lmsm2pcs_rlw", mux(use_dltb_cltb, cfg_rlw, u(6, 0)))
    m.output("lmsm2pcs_data_rate_support_1", mux(use_dltb_rltb, cfg_data_rate_support_1, u(8, 0)))
    m.output(
        "lmsm2pcs_data_rate_support_2",
        mux(use_dltb_rltb, cfg_data_rate_support_2 & u(8, 0x7F), u(8, 0)),
    )
    m.output("lmsm2pcs_fec_mode_support", mux(use_dltb, cfg_fec_mode_support, u(8, 0)))
    m.output("lmsm2pcs_port_type", mux(use_dltb, cfg_port_type, u(1, 0)))
    m.output(
        "lmsm2pcs_portnego_random_value",
        mux(use_dltb, cfg_portnego_random_value, u(7, 0)),
    )
    m.output(
        "lmsm2pcs_fec_interleave_support",
        mux(use_dltb, cfg_fec_interleave_support, u(4, 0)),
    )
    m.output("lmsm2pcs_rx_lane0_id", mux(use_dltb, cfg_rx_lane0_id, u(3, 0)))
    m.output("lmsm2pcs_max_link_width", mux(use_dltb, cfg_max_link_width, u(3, 0)))
    m.output("lmsm2pcs_eq_mode", mux(use_cltb, cfg_eq_mode, u(2, 0)))
    m.output("lmsm2pcs_fec_mode_ctrl", mux(use_cltb_rltb, cfg_fec_mode_ctrl, u(3, 0)))
    m.output("lmsm2pcs_fec_interleave_ctrl", mux(use_cltb, cfg_fec_interleave_ctrl, u(1, 0)))
    m.output("lmsm2pcs_eq_ctrl1", mux(use_rltb_eltb, cfg_eq_ctrl1, u(6, 0)))
    m.output("lmsm2pcs_eq_ctrl2", mux(use_rltb_eltb, cfg_eq_ctrl2, u(8, 0)))
    m.output("lmsm2pcs_eq_ctrl3", mux(use_rltb_eltb, cfg_eq_ctrl3, u(8, 0)))
    m.output("lmsm2pcs_eq_ctrl4", mux(use_eltb, cfg_eq_ctrl4, u(8, 0)))
    m.output(
        "lmsm2pcs_fec_crc_mode_reject",
        mux(use_rltb, cfg_fec_crc_mode_reject, u(1, 0)),
    )
    m.output(
        "lmsm2pcs_pre_fec_ber_meas_st",
        mux(use_rltb, cfg_pre_fec_ber_meas_st, u(2, 0)),
    )
    m.output(
        "lmsm2pcs_fec_interleave_enable",
        mux(use_rltb, cfg_fec_interleave_enable, u(1, 0)),
    )
    m.output(
        "lmsm2pcs_fec_interleave_ctrl_reject",
        mux(use_rltb, cfg_fec_interleave_ctrl_reject, u(1, 0)),
    )
    m.output(
        "lmsm2pcs_request_equalization",
        mux(use_rltb, cfg_request_equalization, u(1, 0)),
    )
    m.output("lmsm2pcs_crc_mode_ctrl", mux(use_rltb, cfg_crc_mode_ctrl, u(3, 0)))
    m.output("lmsm2pcs_local_tx_preset", mux(use_rltb, cfg_local_tx_preset, u(4, 0)))
    m.output("lmsm2pcs_first_pre_cursor", mux(use_rltb_eltb, cfg_first_pre_cursor, u(6, 0)))
    m.output("lmsm2pcs_eq_reject", mux(use_eltb, cfg_eq_reject, u(1, 0)))
    m.output("lmsm2pcs_current_eq_phase", mux(use_eltb, cfg_current_eq_phase, u(2, 0)))
    m.output("lmsm2pcs_preset_mode_en", mux(use_eltb, cfg_preset_mode_en, u(1, 0)))
    m.output("lmsm2pcs_tx_preset", mux(use_eltb, cfg_tx_preset, u(4, 0)))
    m.output("lmsm_st", st_q)
    m.output("train_fail", train_fail_q.out())
    m.output("train_to_inc", train_to_q.out())

    if test_hooks:
        hook_en = tb_test_mode
        m.output("tb_obs_link_ready", mux(hook_en, link_ready, u(1, 0)))
        m.output("tb_obs_link_up", mux(hook_en, obs_link_up, u(1, 0)))
        m.output("tb_obs_lmsm_st", mux(hook_en, st_q, u(5, 0)))


@module(name="ub_lmsm")
def build(
    m: Circuit,
    test_hooks: int = 0,
    NUM_LANES_TX: int = NUM_LANES_TX,
    NUM_LANES_RX: int = NUM_LANES_RX,
    PROBE_WAIT_CYC: int = P_PROBE_WAIT_CYC,
) -> None:
    _ports(
        m,
        test_hooks=int(test_hooks),
        ntx=int(NUM_LANES_TX),
        nrx=int(NUM_LANES_RX),
        probe_wait_def=int(PROBE_WAIT_CYC),
    )


build.__pycircuit_name__ = "ub_lmsm"
