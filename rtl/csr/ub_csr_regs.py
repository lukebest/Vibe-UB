"""ub_csr register file — generated from docs/regmap/regmap.yaml.

GENERATED — edit docs/regmap/regmap.yaml

Attribute-driven CSR leaf (SPEC §2.2 / §3.2.3 / §11, CODING_STYLE).
Storage follows pyc_reg semantics: sync, ``rst_pyc`` active-high, ``core_clk``.
``TEST_HOOKS`` is expanded at Python generation time (two netlists).

Behaviors are emitted from YAML attributes, not hand-specialized per register:
W1C sticky + event ports; saturating RO counters + increment ports + CNT_CLR;
WO self-clear; PORT_RST ``pulse_cycles`` → ``port_rst_pulse``; IRQ aggregation;
TEST window gating; unmapped ``csr_err``; full-word writes; 1-cycle read.

Wiring event sources into ``ev_*`` / ``inc_*`` and fanning ``port_rst_pulse``
to PCS/LMSM/DLL/credit is **outside** this module (parent / ub_controller).

Regenerate: ``python3 scripts/gen_regmap.py``
Check:      ``python3 scripts/gen_regmap.py --check``
"""

from __future__ import annotations

from pathlib import Path

BANNER = 'GENERATED — edit docs/regmap/regmap.yaml'

# Serialized map — do not edit; change docs/regmap/regmap.yaml
FIELDS = (
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'PORT_RST', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': 16, 'pulse_output': 'port_rst_pulse', 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LMSM_START', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'RW', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_lmsm_start', 'rsvd': False},
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'IRQ_EN', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'RW', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_irq_en', 'rsvd': False},
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 3, 'width': 29, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LINK_UP', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_link_up', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LINK_READY', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_link_ready', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'DLL_STATUS_UP', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_dll_status_up', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LMSM_ST', 'msb': 7, 'lsb': 3, 'width': 5, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_lmsm_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'DLL_SM_ST', 'msb': 9, 'lsb': 8, 'width': 2, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_dll_sm_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RETRY_REQ_ST', 'msb': 12, 'lsb': 10, 'width': 3, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_retry_req_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RETRY_ACK_ST', 'msb': 14, 'lsb': 13, 'width': 2, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_retry_ack_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 15, 'width': 17, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'FEC_UNCORR', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'W1C', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_fec_uncorr', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CRC_FAIL', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'W1C', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_crc_fail', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RETRY_ERR', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'W1C', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_retry_err', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CRD_PROTO', 'msb': 3, 'lsb': 3, 'width': 1, 'access': 'W1C', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_crd_proto', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'TRAIN_FAIL', 'msb': 4, 'lsb': 4, 'width': 1, 'access': 'W1C', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_train_fail', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'BAD_VL', 'msb': 5, 'lsb': 5, 'width': 1, 'access': 'W1C', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_bad_vl', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CRD_UF', 'msb': 6, 'lsb': 6, 'width': 1, 'access': 'W1C', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_crd_uf', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 7, 'width': 25, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'IRQ_MASK', 'offset': 12, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'MASK', 'msb': 6, 'lsb': 0, 'width': 7, 'access': 'RW', 'reset': 127, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_irq_mask', 'rsvd': False},
    {'reg': 'IRQ_MASK', 'offset': 12, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 7, 'width': 25, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PORT_CNA', 'offset': 16, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CNA', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RW', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_port_cna', 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'PHY_MODE', 'msb': 1, 'lsb': 0, 'width': 2, 'access': 'RO', 'reset': 2, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'DATA_RATE', 'msb': 5, 'lsb': 2, 'width': 4, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_LANES_TX', 'msb': 9, 'lsb': 6, 'width': 4, 'access': 'RO', 'reset': 1, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_LANES_RX', 'msb': 13, 'lsb': 10, 'width': 4, 'access': 'RO', 'reset': 1, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'PMA_W', 'msb': 21, 'lsb': 14, 'width': 8, 'access': 'RO', 'reset': 32, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'ALLOW_ASYM', 'msb': 22, 'lsb': 22, 'width': 1, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 23, 'width': 9, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PARAM_FEC', 'offset': 260, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'FEC_MODE', 'msb': 2, 'lsb': 0, 'width': 3, 'access': 'RO', 'reset': 2, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_FEC', 'offset': 260, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'CODEC_NUM', 'msb': 4, 'lsb': 3, 'width': 2, 'access': 'RO', 'reset': 1, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_FEC', 'offset': 260, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 5, 'width': 27, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_VL', 'msb': 4, 'lsb': 0, 'width': 5, 'access': 'RO', 'reset': 2, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'FLOW_CTRL_SIZE', 'msb': 12, 'lsb': 5, 'width': 8, 'access': 'RO', 'reset': 1, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'ACK_GRAIN', 'msb': 20, 'lsb': 13, 'width': 8, 'access': 'RO', 'reset': 32, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'CREDIT_EXCL', 'msb': 21, 'lsb': 21, 'width': 1, 'access': 'RO', 'reset': 1, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 22, 'width': 10, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PARAM_RETRY', 'offset': 268, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RETRY_BUF_DEPTH', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 256, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_RETRY', 'offset': 268, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_RETRY_TH', 'msb': 23, 'lsb': 16, 'width': 8, 'access': 'RO', 'reset': 15, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_RETRY', 'offset': 268, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_PHY_REINIT_TH', 'msb': 31, 'lsb': 24, 'width': 8, 'access': 'RO', 'reset': 4, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_CRD', 'offset': 272, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'INIT_CRD', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 640, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_CRD', 'offset': 272, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'CRD_BP_TH', 'msb': 31, 'lsb': 16, 'width': 16, 'access': 'RO', 'reset': 1024, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_FEATURE', 'offset': 276, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'FEATURE_ID', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 1, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_FEATURE', 'offset': 276, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RXBUF_VL_SHARE', 'msb': 16, 'lsb': 16, 'width': 1, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_FEATURE', 'offset': 276, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'VL_ENABLE', 'msb': 31, 'lsb': 17, 'width': 15, 'access': 'RO', 'reset': 3, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_VL', 'offset': 280, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'VL_ENABLE', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 3, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_VL', 'offset': 280, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 16, 'width': 16, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'CNT_FEC_UNCORR', 'offset': 512, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_fec_uncorr', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRC_FAIL', 'offset': 516, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crc_fail', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_RETRY_REQ', 'offset': 520, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_retry_req', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_RETRY_TO', 'offset': 524, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_retry_to', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRD_OF', 'offset': 528, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crd_of', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRD_TO', 'offset': 532, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crd_to', 'increment_gate': {'reg': 'CRD_TO_DIS', 'field': 'DIS', 'invert': True}, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_TRAIN_TO', 'offset': 536, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_train_to', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_BAD_VL', 'offset': 540, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_bad_vl', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRD_UF', 'offset': 544, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crd_uf', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'FEC_UNCORR', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_FEC_UNCORR', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRC_FAIL', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRC_FAIL', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'RETRY_REQ', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_RETRY_REQ', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'RETRY_TO', 'msb': 3, 'lsb': 3, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_RETRY_TO', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRD_OF', 'msb': 4, 'lsb': 4, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRD_OF', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRD_TO', 'msb': 5, 'lsb': 5, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRD_TO', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'TRAIN_TO', 'msb': 6, 'lsb': 6, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_TRAIN_TO', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'BAD_VL', 'msb': 7, 'lsb': 7, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_BAD_VL', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRD_UF', 'msb': 8, 'lsb': 8, 'width': 1, 'access': 'WO', 'reset': 0, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRD_UF', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 9, 'width': 23, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'LMSM_TMR_SCALE', 'offset': 768, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'SCALE', 'msb': 7, 'lsb': 0, 'width': 8, 'access': 'RW', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_tmr_scale', 'rsvd': False},
    {'reg': 'LMSM_TMR_SCALE', 'offset': 768, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 8, 'width': 24, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'CRD_TO_DIS', 'offset': 772, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'DIS', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'RW', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_crd_to_dis', 'rsvd': False},
    {'reg': 'CRD_TO_DIS', 'offset': 772, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 1, 'width': 31, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PCS_TX_TEST', 'offset': 776, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'AM_IVL_SCALE', 'msb': 7, 'lsb': 0, 'width': 8, 'access': 'RW', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_am_ivl_scale', 'rsvd': False},
    {'reg': 'PCS_TX_TEST', 'offset': 776, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 8, 'width': 24, 'access': 'RO', 'reset': 0, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'APPD_PORT_BASIC', 'offset': 4096, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_LINK_CAP', 'offset': 4352, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_LINK_LOG', 'offset': 4608, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_LMSM_ST', 'offset': 7680, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_PORT_ERR', 'offset': 7936, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
)

REGS = (
    {'name': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'kind': 'register'},
    {'name': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'kind': 'register'},
    {'name': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'kind': 'register'},
    {'name': 'IRQ_MASK', 'offset': 12, 'window': 'CTRL_STATUS', 'kind': 'register'},
    {'name': 'PORT_CNA', 'offset': 16, 'window': 'CTRL_STATUS', 'kind': 'register'},
    {'name': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'kind': 'register'},
    {'name': 'PARAM_FEC', 'offset': 260, 'window': 'PARAM', 'kind': 'register'},
    {'name': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'kind': 'register'},
    {'name': 'PARAM_RETRY', 'offset': 268, 'window': 'PARAM', 'kind': 'register'},
    {'name': 'PARAM_CRD', 'offset': 272, 'window': 'PARAM', 'kind': 'register'},
    {'name': 'PARAM_INIT_FEATURE', 'offset': 276, 'window': 'PARAM', 'kind': 'register'},
    {'name': 'PARAM_INIT_VL', 'offset': 280, 'window': 'PARAM', 'kind': 'register'},
    {'name': 'CNT_FEC_UNCORR', 'offset': 512, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_CRC_FAIL', 'offset': 516, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_RETRY_REQ', 'offset': 520, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_RETRY_TO', 'offset': 524, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_CRD_OF', 'offset': 528, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_CRD_TO', 'offset': 532, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_TRAIN_TO', 'offset': 536, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_BAD_VL', 'offset': 540, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_CRD_UF', 'offset': 544, 'window': 'ERR', 'kind': 'register'},
    {'name': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'kind': 'register'},
    {'name': 'LMSM_TMR_SCALE', 'offset': 768, 'window': 'TEST', 'kind': 'register'},
    {'name': 'CRD_TO_DIS', 'offset': 772, 'window': 'TEST', 'kind': 'register'},
    {'name': 'PCS_TX_TEST', 'offset': 776, 'window': 'TEST', 'kind': 'register'},
    {'name': 'APPD_PORT_BASIC', 'offset': 4096, 'window': 'APPD_PORT', 'kind': 'window'},
    {'name': 'APPD_LINK_CAP', 'offset': 4352, 'window': 'APPD_PORT', 'kind': 'window'},
    {'name': 'APPD_LINK_LOG', 'offset': 4608, 'window': 'APPD_PORT', 'kind': 'window'},
    {'name': 'APPD_LMSM_ST', 'offset': 7680, 'window': 'APPD_PORT', 'kind': 'window'},
    {'name': 'APPD_PORT_ERR', 'offset': 7936, 'window': 'APPD_PORT', 'kind': 'window'},
)

WINDOWS = (
    {'id': 'CTRL_STATUS', 'start': 0, 'end': 255, 'test_gated': False, 'entire_range_mapped': False},
    {'id': 'PARAM', 'start': 256, 'end': 511, 'test_gated': False, 'entire_range_mapped': False},
    {'id': 'ERR', 'start': 512, 'end': 767, 'test_gated': False, 'entire_range_mapped': False},
    {'id': 'TEST', 'start': 768, 'end': 1023, 'test_gated': True, 'entire_range_mapped': True},
    {'id': 'APPD_PORT', 'start': 4096, 'end': 8191, 'test_gated': False, 'entire_range_mapped': False},
)

IRQ = {'enable': {'reg': 'CTRL', 'field': 'IRQ_EN'}, 'status_reg': 'IRQ_STATUS', 'mask': {'reg': 'IRQ_MASK', 'field': 'MASK'}, 'output': 'irq', 'polarity': 'high', 'reset_masked': True, 'note': 'REGMAP: IRQ_EN=1 and any unmasked IRQ_STATUS bit. MASK bit 1 = block. Reset IRQ_MASK=all-1, IRQ_EN=0. Port `irq` is active-high.'}
RULES = {'full_word_writes_only': True, 'read_latency_cycles': 1, 'write_rvalid_next_cycle': 0, 'write_err_valid_next_cycle': True, 'unmapped_csr_err': True, 'no_read_clear': True, 'no_rw_write_clear': True, 'sticky_access': 'W1C', 'counter_access': 'RO + CNT_CLR', 'reserved_bits': '未实现的保留位读 0、写忽略。'}
PORT_RST_PULSE_CYCLES = 16


HERE = Path(__file__).resolve().parent
PRODUCT_V = HERE / "ub_csr.v"
HOOKS_V = HERE / "hooks" / "ub_csr.v"


def _header(test_hooks: int) -> str:
    return (
        "// Generated by rtl/csr/ub_csr_regs.py from docs/regmap/regmap.yaml.\n"
        f"// {BANNER}\n"
        f"// pyc4.0 leaf ub_csr. TEST_HOOKS={test_hooks} (Python generation-time).\n"
        "// Attribute-driven: W1C / saturating / WO self-clear / pulse_cycles /"
        " TEST gate / csr_err.\n"
        "// SPEC §2.2 / §3.2.3 / §11.\n"
    )


def _wdecl(width: int) -> str:
    return "      " if width == 1 else f"[{width - 1}:0]".rjust(6)


def emit_verilog(test_hooks: bool) -> str:
    """Emit one netlist from FIELDS / REGS / WINDOWS / IRQ attributes."""
    th = 1 if test_hooks else 0
    lines: list[str] = [_header(th)]

    def w(s: str = "") -> None:
        lines.append(s)

    hw = [f for f in FIELDS if f.get("hw_port")]
    ev = [f for f in FIELDS if f.get("event_port")]
    inc = [f for f in FIELDS if f.get("increment_port")]
    cfg = [f for f in FIELDS if f.get("config_output")]
    pulse = [f for f in FIELDS if f.get("pulse_output") and f.get("pulse_cycles")]
    w1c = [f for f in FIELDS if f["access"] == "W1C" and not f["rsvd"]]
    sat = [f for f in FIELDS if f.get("saturating")]
    rw = [f for f in FIELDS if f["access"] == "RW" and not f["rsvd"]]
    clr = [f for f in FIELDS if f.get("clear_target")]
    test_win = next(x for x in WINDOWS if x.get("test_gated"))

    w("module ub_csr (")
    ports = [
        "  input  wire        core_clk",
        "  input  wire        rst_pyc",
        "  input  wire        csr_req",
        "  input  wire        csr_wr",
        "  input  wire [15:0] csr_addr",
        "  input  wire [31:0] csr_wdata",
        "  output wire        csr_ready",
        "  output reg         csr_rvalid",
        "  output reg  [31:0] csr_rdata",
        "  output reg         csr_err",
    ]
    for f in hw:
        ports.append(f"  input  wire {_wdecl(f['width'])} {f['hw_port']}")
    for f in ev:
        ports.append(f"  input  wire        {f['event_port']}")
    for f in inc:
        ports.append(f"  input  wire        {f['increment_port']}")
    for f in pulse:
        ports.append(f"  output wire        {f['pulse_output']}")
    for f in cfg:
        ports.append(f"  output wire {_wdecl(f['width'])} {f['config_output']}")
    ports.append(f"  output wire        {IRQ.get('output', 'irq')}")
    if th:
        ports.append("  input  wire        tb_test_mode")
    w(",\n".join(ports))
    w(");")
    w("")
    w("  assign csr_ready = 1'b1; // full-word, no wait (SPEC §3.2.3)")
    w("  wire addr_aligned = (csr_addr[1:0] == 2'b00);")
    w("  wire req_fire     = csr_req;")
    w("  wire wr_fire      = req_fire & csr_wr;")
    w(
        f"  wire in_test      = (csr_addr[15:0] >= 16'h{test_win['start']:04X})"
        f" && (csr_addr[15:0] <= 16'h{test_win['end']:04X});"
    )
    if th:
        w("  wire test_active  = tb_test_mode;")
    else:
        w("  wire test_active  = 1'b0; // PRODUCT TEST_HOOKS=0")
    w("  wire test_hit     = in_test & addr_aligned;")
    w("")

    seen = set()
    for reg in REGS:
        if reg["name"] in seen:
            continue
        seen.add(reg["name"])
        w(
            f"  wire {_sel(reg['name'])} = addr_aligned"
            f" && (csr_addr[15:0] == 16'h{reg['offset']:04X});"
        )
    fn_sels = " | ".join(
        _sel(r["name"]) for r in REGS if r["window"] not in ("TEST",)
    )
    test_sels = " | ".join(_sel(r["name"]) for r in REGS if r["window"] == "TEST")
    w(f"  wire sel_fn   = {fn_sels};")
    w(f"  wire sel_test = {test_sels};")
    w("  wire wr_ok_fn   = wr_fire & sel_fn;")
    w("  wire wr_ok_test = wr_fire & sel_test & test_active;")
    w("")

    # storage declarations
    for f in rw + w1c + sat:
        w(f"  reg {_wdecl(f['width'])} {_qname(f['reg'], f['field'])};")
    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        w(f"  reg [{cw - 1}:0] cnt_{f['reg'].lower()}_{f['field'].lower()};")
    w("")

    # write enables
    for f in rw + w1c + pulse + clr:
        gate = "wr_ok_test" if f["test"] else "wr_ok_fn"
        w(f"  wire wr_{f['reg'].lower()}_{f['field'].lower()} = {gate} & {_sel(f['reg'])};")
    w("")

    # clear strobes from CNT_CLR
    for f in clr:
        w(
            f"  wire clr_{f['clear_target'].lower()} ="
            f" wr_{f['reg'].lower()}_{f['field'].lower()} & csr_wdata[{f['lsb']}];"
        )
    w("")

    # increment gates (prefer the field's config_output so TEST gating applies)
    for f in sat:
        gate = f.get("increment_gate")
        if gate:
            gfield = next(
                x for x in FIELDS
                if x["reg"] == gate["reg"] and x["field"] == gate["field"]
            )
            gsig = gfield.get("config_output") or _qname(gate["reg"], gate["field"])
            cond = f"~{gsig}" if gate.get("invert") else gsig
            w(f"  wire {f['increment_port']}_qual = {f['increment_port']} & {cond};")
        else:
            w(f"  wire {f['increment_port']}_qual = {f['increment_port']};")
    w("")

    w("  always @(posedge core_clk) begin")
    w("    if (rst_pyc) begin")
    for f in rw + w1c + sat:
        rst = 0 if f["reset"] is None else int(f["reset"])
        w(f"      {_qname(f['reg'], f['field'])} <= {_sv_lit(f['width'], rst)};")
    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        w(f"      cnt_{f['reg'].lower()}_{f['field'].lower()} <= {cw}'d0;")
    w("    end else begin")
    for f in rw:
        q = _qname(f["reg"], f["field"])
        wr = f"wr_{f['reg'].lower()}_{f['field'].lower()}"
        sl = f"csr_wdata[{f['msb']}:{f['lsb']}]" if f["width"] > 1 else f"csr_wdata[{f['lsb']}]"
        w(f"      if ({wr}) {q} <= {sl};")
    for f in w1c:
        q = _qname(f["reg"], f["field"])
        wr = f"wr_{f['reg'].lower()}_{f['field'].lower()}"
        evn = f["event_port"]
        w(f"      {q} <= ({q} | {evn}) & ~({wr} & csr_wdata[{f['lsb']}]);")
    for f in sat:
        q = _qname(f["reg"], f["field"])
        clr_n = f"clr_{f['reg'].lower()}"
        ones = f"{f['width']}'h" + ("f" * ((f["width"] + 3) // 4))
        w(f"      if ({clr_n})")
        w(f"        {q} <= {_sv_lit(f['width'], 0)};")
        w(f"      else if ({f['increment_port']}_qual && {q} != {ones})")
        w(f"        {q} <= {q} + 1'b1;")
    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        cnt = f"cnt_{f['reg'].lower()}_{f['field'].lower()}"
        wr = f"wr_{f['reg'].lower()}_{f['field'].lower()}"
        w(f"      if ({wr} & csr_wdata[{f['lsb']}])")
        w(f"        {cnt} <= {cw}'d{cyc};")
        w(f"      else if ({cnt} != {cw}'d0)")
        w(f"        {cnt} <= {cnt} - 1'b1;")
    w("    end")
    w("  end")
    w("")

    for f in pulse:
        cnt = f"cnt_{f['reg'].lower()}_{f['field'].lower()}"
        cw = max(1, int(f["pulse_cycles"]).bit_length())
        w(f"  assign {f['pulse_output']} = ({cnt} != {cw}'d0);")

    for f in cfg:
        q = _qname(f["reg"], f["field"])
        rst = 0 if f["reset"] is None else int(f["reset"])
        if f["test"]:
            w(
                f"  assign {f['config_output']} = test_active ? {q} :"
                f" {_sv_lit(f['width'], rst)};"
            )
        else:
            w(f"  assign {f['config_output']} = {q};")
    w("")

    # IRQ: enable & OR(status & ~mask). MASK bit 1 = block (REGMAP).
    st_bits = [f for f in w1c if f["reg"] == IRQ.get("status_reg", "IRQ_STATUS")]
    st_bits = sorted(st_bits, key=lambda x: x["lsb"])
    en = IRQ.get("enable") or {"reg": "CTRL", "field": "IRQ_EN"}
    mk = IRQ.get("mask") or {"reg": "IRQ_MASK", "field": "MASK"}
    st_cat = ", ".join(_qname(f["reg"], f["field"]) for f in reversed(st_bits))
    w(f"  wire [{len(st_bits) - 1}:0] irq_sticky = {{{st_cat}}};")
    w(f"  wire [{len(st_bits) - 1}:0] irq_mask_w = {_qname(mk['reg'], mk['field'])};")
    w(f"  assign {IRQ.get('output', 'irq')} = {_qname(en['reg'], en['field'])} & |(irq_sticky & ~irq_mask_w);")
    w("")

    # read data per register
    by_reg: dict[str, list] = {}
    for f in FIELDS:
        by_reg.setdefault(f["reg"], []).append(f)
    for rname, flist in by_reg.items():
        parts = []
        for f in sorted(flist, key=lambda x: -x["lsb"]):
            width = f["width"]
            if f["rsvd"] or f.get("window_kind") or (
                f["access"] == "WO" and f.get("self_clearing")
            ):
                parts.append(f"{width}'h0")
            elif f.get("hw_port"):
                parts.append(f["hw_port"])
            elif f["access"] in ("RW", "W1C") or f.get("saturating"):
                parts.append(_qname(f["reg"], f["field"]))
            elif f["access"] == "RO" and f["reset"] is not None:
                parts.append(_sv_lit(width, int(f["reset"])))
            else:
                parts.append(f"{width}'h0")
        w(f"  wire [31:0] rdata_{rname.lower()} = {{{', '.join(parts)}}};")
    w("")
    w("  reg [31:0] rdata_n;")
    w("  reg        err_n;")
    w("  always @* begin")
    w("    rdata_n = 32'h0;")
    w("    err_n   = 1'b0;")
    w("    if (req_fire) begin")
    w("      if (!addr_aligned) begin")
    w("        err_n = 1'b1;")
    w("      end else if (test_hit) begin")
    w("        err_n = 1'b0; // mapped; PRODUCT / tb_test_mode=0: rdata=0 write-ignore")
    w("        if (test_active) begin")
    for reg in [r for r in REGS if r["window"] == "TEST"]:
        w(f"          if ({_sel(reg['name'])}) rdata_n = rdata_{reg['name'].lower()};")
    w("        end")
    w("      end else begin")
    first = True
    for reg in [r for r in REGS if r["window"] != "TEST"]:
        kw = "if" if first else "else if"
        first = False
        w(f"        {kw} ({_sel(reg['name'])}) rdata_n = rdata_{reg['name'].lower()};")
    w("        else err_n = 1'b1; // unmapped")
    w("      end")
    w("    end")
    w("  end")
    w("")

    w("  always @(posedge core_clk) begin")
    w("    if (rst_pyc) begin")
    w("      csr_rvalid <= 1'b0;")
    w("      csr_rdata  <= 32'h0;")
    w("      csr_err    <= 1'b0;")
    w("    end else begin")
    wrv = RULES.get("write_rvalid_next_cycle", 0)
    if wrv != 0:
        raise ValueError("SPEC §3.2.3 requires write next-cycle csr_rvalid=0")
    w("      csr_rvalid <= req_fire & ~csr_wr; // write cycle: next csr_rvalid=0 (SPEC §3.2.3)")
    w("      csr_rdata  <= rdata_n;")
    w("      csr_err    <= req_fire ? err_n : 1'b0;")
    w("    end")
    w("  end")
    w("")
    w("endmodule")
    w("")
    return "\n".join(lines) + "\n"


def _sv_lit(width: int, value: int) -> str:
    return f"{width}'h{value:x}"


def _sel(name: str) -> str:
    return f"sel_{name.lower()}"


def _qname(reg: str, field: str) -> str:
    return f"q_{reg.lower()}_{field.lower()}"


try:
    from pycircuit import Circuit, compile, module, u  # type: ignore
    HAVE_PYCIRCUIT = True
except ImportError:  # pragma: no cover - frontend optional
    HAVE_PYCIRCUIT = False
    Circuit = None  # type: ignore
    compile = None  # type: ignore
    module = None  # type: ignore
    u = None  # type: ignore


def _csr_circuit(m, test_hooks: int) -> None:
    """Port-accurate pyc4.0 boundary. PRODUCT .v is emit_verilog (no pycc)."""
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")
    req = m.input("csr_req", width=1)
    wr = m.input("csr_wr", width=1)
    m.input("csr_addr", width=16)
    m.input("csr_wdata", width=32)
    seen_in: set[str] = set()
    for f in FIELDS:
        hp = f.get("hw_port")
        if hp and hp not in seen_in:
            seen_in.add(hp)
            m.input(hp, width=int(f["width"]))
        ep = f.get("event_port")
        if ep and ep not in seen_in:
            seen_in.add(ep)
            m.input(ep, width=1)
        ip = f.get("increment_port")
        if ip and ip not in seen_in:
            seen_in.add(ip)
            m.input(ip, width=1)
    if test_hooks:
        m.input("tb_test_mode", width=1)
    ready = m.out("csr_ready_q", clk=clk, rst=rst, width=1, init=u(1, 1))
    ready.set(u(1, 1))
    m.output("csr_ready", ready)
    rvalid = m.out("csr_rvalid_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    rvalid.set(m.and_(req, m.not_(wr)))  # write next-cycle rvalid=0
    m.output("csr_rvalid", rvalid)
    rdata = m.out("csr_rdata_q", clk=clk, rst=rst, width=32, init=u(32, 0))
    rdata.set(u(32, 0))
    m.output("csr_rdata", rdata)
    err = m.out("csr_err_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    err.set(u(1, 0))
    m.output("csr_err", err)
    seen_out: set[str] = set()
    for f in FIELDS:
        po = f.get("pulse_output")
        if po and po not in seen_out:
            seen_out.add(po)
            m.output(po, u(1, 0))
        co = f.get("config_output")
        if co and co not in seen_out:
            seen_out.add(co)
            wdt = int(f["width"])
            rstv = 0 if f["reset"] is None else int(f["reset"])
            q = m.out("elab_" + co, clk=clk, rst=rst, width=wdt, init=u(wdt, rstv))
            q.set(q.out())
            m.output(co, q)
    irq_name = IRQ.get("output", "irq")
    if irq_name not in seen_out:
        m.output(irq_name, u(1, 0))


if HAVE_PYCIRCUIT:
    @module(name="ub_csr")
    def _elab_product(m: Circuit) -> None:
        _csr_circuit(m, 0)

    @module(name="ub_csr")
    def _elab_hooks(m: Circuit) -> None:
        _csr_circuit(m, 1)
else:  # pragma: no cover
    _elab_product = None
    _elab_hooks = None


def elaborate(test_hooks: int = 0) -> dict:
    """Elaborate TEST_HOOKS=0/1 via pycircuit.compile(). PRODUCT .v is emit_verilog."""
    import shutil

    status = {
        "test_hooks": int(test_hooks),
        "pycircuit": HAVE_PYCIRCUIT,
        "elaborated": False,
        "reason": None,
        "verilog_chars": len(emit_verilog(bool(test_hooks))),
        "pycc": shutil.which("pycc") is not None,
        "modules": [],
        "mlir_chars": 0,
    }
    if not HAVE_PYCIRCUIT:
        status["reason"] = "pycircuit not importable"
        return status
    fn = _elab_hooks if test_hooks else _elab_product
    try:
        design = compile(fn)
        status["elaborated"] = True
        status["mlir_chars"] = len(design.emit_mlir())
        status["modules"] = [cm.sym_name for cm in design.modules()]
        status["reason"] = (
            "compile() Design (frontend MLIR). PRODUCT Verilog is emit_verilog; "
            "pycc/LLVM 19 is required to lower Circuit→.v and is not on PATH."
        )
    except Exception as exc:
        status["reason"] = f"compile failed: {type(exc).__name__}: {exc}"
    return status


def generate() -> tuple[Path, Path]:
    product = emit_verilog(False)
    hooks = emit_verilog(True)
    if "`ifdef" in product or "`ifdef" in hooks:
        raise RuntimeError("generated Verilog must not use ifdef TEST_HOOKS")
    if "input  wire        tb_test_mode" in product:
        raise RuntimeError("PRODUCT netlist must not contain tb_test_mode port")
    PRODUCT_V.parent.mkdir(parents=True, exist_ok=True)
    HOOKS_V.parent.mkdir(parents=True, exist_ok=True)
    PRODUCT_V.write_text(product, encoding="utf-8")
    HOOKS_V.write_text(hooks, encoding="utf-8")
    return PRODUCT_V, HOOKS_V


def main() -> int:
    p, h = generate()
    print(f"wrote {p}")
    print(f"wrote {h}")
    print(elaborate(0))
    print(elaborate(1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

