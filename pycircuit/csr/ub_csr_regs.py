"""ub_csr register file — generated from docs/regmap/regmap.yaml.

GENERATED — edit docs/regmap/regmap.yaml

Attribute-driven CSR leaf (SPEC §2.2 / §3.2.3 / §11, CODING_STYLE, D5).
Describes the circuit with the pyc4.0 modeling API
(``from pycircuit import Circuit, compile, module, u``; lukebest/pyCircuit @43cc5918)
and lowers Verilog through ``pycc --emit=verilog`` (LLVM 19). Not string-templated.

Storage follows pyc_reg semantics: sync, ``rst_pyc`` active-high, ``core_clk``.
``TEST_HOOKS`` is expanded at Python generation time (PRODUCT + HOOKS).
SPEC §2.2: one fixed netlist per ``variants:`` tag, module ``ub_csr_<tag>``.
Reset values marked ``reset_from: variant`` are baked from that table
(not handwritten). ``_placeholder`` scrambler leaves are lint/TB only.

Behaviors are built from YAML attributes, not hand-specialized per register:
W1C sticky + event ports; saturating RO counters + increment ports + CNT_CLR;
WO self-clear; PORT_RST ``pulse_cycles`` → ``port_rst_pulse``; IRQ aggregation;
TEST window gating; unmapped ``csr_err``; full-word writes; 1-cycle read.

Wiring event sources into ``ev_*`` / ``inc_*`` and fanning ``port_rst_pulse``
to PCS/LMSM/DLL/credit is **outside** this module (parent / ub_controller).

Regenerate: ``python3 scripts/gen_regmap.py`` then ``python3 scripts/emit_rtl.py``
Check:      ``python3 scripts/gen_regmap.py --check`` (YAML artifacts + pycc
``.v`` byte-equality when pycc is on PATH).

Committed Verilog: ``rtl/csr/ub_csr_<tag>.v`` and ``rtl/csr/hooks/ub_csr_<tag>.v``.
Do not hand-write ``.v``.
"""

from __future__ import annotations

from pathlib import Path

BANNER = 'GENERATED — edit docs/regmap/regmap.yaml'

# Serialized map — do not edit; change docs/regmap/regmap.yaml
FIELDS = (
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'PORT_RST', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': 16, 'pulse_output': 'port_rst_pulse', 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LMSM_START', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'RW', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_lmsm_start', 'rsvd': False},
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'IRQ_EN', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'RW', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_irq_en', 'rsvd': False},
    {'reg': 'CTRL', 'offset': 0, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 3, 'width': 29, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LINK_UP', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_link_up', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LINK_READY', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_link_ready', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'DLL_STATUS_UP', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_dll_status_up', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'LMSM_ST', 'msb': 7, 'lsb': 3, 'width': 5, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_lmsm_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'DLL_SM_ST', 'msb': 9, 'lsb': 8, 'width': 2, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_dll_sm_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RETRY_REQ_ST', 'msb': 12, 'lsb': 10, 'width': 3, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_retry_req_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RETRY_ACK_ST', 'msb': 14, 'lsb': 13, 'width': 2, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': 'hw', 'hw_port': 'hw_retry_ack_st', 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'STATUS', 'offset': 4, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 15, 'width': 17, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'FEC_UNCORR', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'W1C', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_fec_uncorr', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CRC_FAIL', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'W1C', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_crc_fail', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RETRY_ERR', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'W1C', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_retry_err', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CRD_PROTO', 'msb': 3, 'lsb': 3, 'width': 1, 'access': 'W1C', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_crd_proto', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'TRAIN_FAIL', 'msb': 4, 'lsb': 4, 'width': 1, 'access': 'W1C', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_train_fail', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'BAD_VL', 'msb': 5, 'lsb': 5, 'width': 1, 'access': 'W1C', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_bad_vl', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CRD_UF', 'msb': 6, 'lsb': 6, 'width': 1, 'access': 'W1C', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': 'ev_crd_uf', 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'IRQ_STATUS', 'offset': 8, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 7, 'width': 25, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'IRQ_MASK', 'offset': 12, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'MASK', 'msb': 6, 'lsb': 0, 'width': 7, 'access': 'RW', 'reset': 127, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_irq_mask', 'rsvd': False},
    {'reg': 'IRQ_MASK', 'offset': 12, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 7, 'width': 25, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PORT_CNA', 'offset': 16, 'window': 'CTRL_STATUS', 'test': False, 'window_kind': False, 'field': 'CNA', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RW', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_port_cna', 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'PHY_MODE', 'msb': 1, 'lsb': 0, 'width': 2, 'access': 'RO', 'reset': 2, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'DATA_RATE', 'msb': 5, 'lsb': 2, 'width': 4, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_LANES_TX', 'msb': 9, 'lsb': 6, 'width': 4, 'access': 'RO', 'reset': None, 'reset_from': 'variant', 'reset_key': 'NUM_LANES', 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_LANES_RX', 'msb': 13, 'lsb': 10, 'width': 4, 'access': 'RO', 'reset': None, 'reset_from': 'variant', 'reset_key': 'NUM_LANES', 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'PMA_W', 'msb': 21, 'lsb': 14, 'width': 8, 'access': 'RO', 'reset': 32, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'ALLOW_ASYM', 'msb': 22, 'lsb': 22, 'width': 1, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_PHY', 'offset': 256, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 23, 'width': 9, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PARAM_FEC', 'offset': 260, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'FEC_MODE', 'msb': 2, 'lsb': 0, 'width': 3, 'access': 'RO', 'reset': 2, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_FEC', 'offset': 260, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'CODEC_NUM', 'msb': 4, 'lsb': 3, 'width': 2, 'access': 'RO', 'reset': 1, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_FEC', 'offset': 260, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 5, 'width': 27, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_VL', 'msb': 4, 'lsb': 0, 'width': 5, 'access': 'RO', 'reset': None, 'reset_from': 'variant', 'reset_key': 'NUM_VL', 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'FLOW_CTRL_SIZE', 'msb': 12, 'lsb': 5, 'width': 8, 'access': 'RO', 'reset': 1, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'ACK_GRAIN', 'msb': 20, 'lsb': 13, 'width': 8, 'access': 'RO', 'reset': 32, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'CREDIT_EXCL', 'msb': 21, 'lsb': 21, 'width': 1, 'access': 'RO', 'reset': 1, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_DLL', 'offset': 264, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 22, 'width': 10, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PARAM_RETRY', 'offset': 268, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RETRY_BUF_DEPTH', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 256, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_RETRY', 'offset': 268, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_RETRY_TH', 'msb': 23, 'lsb': 16, 'width': 8, 'access': 'RO', 'reset': 15, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_RETRY', 'offset': 268, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_PHY_REINIT_TH', 'msb': 31, 'lsb': 24, 'width': 8, 'access': 'RO', 'reset': 4, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_CRD', 'offset': 272, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'INIT_CRD', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 640, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_CRD', 'offset': 272, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'CRD_BP_TH', 'msb': 31, 'lsb': 16, 'width': 16, 'access': 'RO', 'reset': 1024, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_FEATURE', 'offset': 276, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'FEATURE_ID', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 1, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_FEATURE', 'offset': 276, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RXBUF_VL_SHARE', 'msb': 16, 'lsb': 16, 'width': 1, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_FEATURE', 'offset': 276, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'VL_ENABLE', 'msb': 31, 'lsb': 17, 'width': 15, 'access': 'RO', 'reset': 3, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_VL', 'offset': 280, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'VL_ENABLE', 'msb': 15, 'lsb': 0, 'width': 16, 'access': 'RO', 'reset': 3, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_INIT_VL', 'offset': 280, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 16, 'width': 16, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PARAM_VARIANT', 'offset': 284, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'NUM_VL', 'msb': 3, 'lsb': 0, 'width': 4, 'access': 'RO', 'reset': None, 'reset_from': 'variant', 'reset_key': 'NUM_VL', 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_VARIANT', 'offset': 284, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'SCR_PLACEHOLDER', 'msb': 4, 'lsb': 4, 'width': 1, 'access': 'RO', 'reset': None, 'reset_from': 'variant', 'reset_key': 'SCR_PLACEHOLDER', 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'PARAM_VARIANT', 'offset': 284, 'window': 'PARAM', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 5, 'width': 27, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'CNT_FEC_UNCORR', 'offset': 512, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_fec_uncorr', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRC_FAIL', 'offset': 516, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crc_fail', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_RETRY_REQ', 'offset': 520, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_retry_req', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_RETRY_TO', 'offset': 524, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_retry_to', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRD_OF', 'offset': 528, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crd_of', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRD_TO', 'offset': 532, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crd_to', 'increment_gate': {'reg': 'CRD_TO_DIS', 'field': 'DIS', 'invert': True}, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_TRAIN_TO', 'offset': 536, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_train_to', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_BAD_VL', 'offset': 540, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_bad_vl', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CRD_UF', 'offset': 544, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'COUNT', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': True, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': 'inc_crd_uf', 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'FEC_UNCORR', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_FEC_UNCORR', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRC_FAIL', 'msb': 1, 'lsb': 1, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRC_FAIL', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'RETRY_REQ', 'msb': 2, 'lsb': 2, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_RETRY_REQ', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'RETRY_TO', 'msb': 3, 'lsb': 3, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_RETRY_TO', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRD_OF', 'msb': 4, 'lsb': 4, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRD_OF', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRD_TO', 'msb': 5, 'lsb': 5, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRD_TO', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'TRAIN_TO', 'msb': 6, 'lsb': 6, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_TRAIN_TO', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'BAD_VL', 'msb': 7, 'lsb': 7, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_BAD_VL', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'CRD_UF', 'msb': 8, 'lsb': 8, 'width': 1, 'access': 'WO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': True, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': 'CNT_CRD_UF', 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'CNT_CLR', 'offset': 548, 'window': 'ERR', 'test': False, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 9, 'width': 23, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'LMSM_TMR_SCALE', 'offset': 768, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'SCALE', 'msb': 7, 'lsb': 0, 'width': 8, 'access': 'RW', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_tmr_scale', 'rsvd': False},
    {'reg': 'LMSM_TMR_SCALE', 'offset': 768, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 8, 'width': 24, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'CRD_TO_DIS', 'offset': 772, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'DIS', 'msb': 0, 'lsb': 0, 'width': 1, 'access': 'RW', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_crd_to_dis', 'rsvd': False},
    {'reg': 'CRD_TO_DIS', 'offset': 772, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 1, 'width': 31, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'PCS_TX_TEST', 'offset': 776, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'AM_IVL_SCALE', 'msb': 7, 'lsb': 0, 'width': 8, 'access': 'RW', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': 'csr_am_ivl_scale', 'rsvd': False},
    {'reg': 'PCS_TX_TEST', 'offset': 776, 'window': 'TEST', 'test': True, 'window_kind': False, 'field': 'RSVD', 'msb': 31, 'lsb': 8, 'width': 24, 'access': 'RO', 'reset': 0, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': True},
    {'reg': 'APPD_PORT_BASIC', 'offset': 4096, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_LINK_CAP', 'offset': 4352, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_LINK_LOG', 'offset': 4608, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_LMSM_ST', 'offset': 7680, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
    {'reg': 'APPD_PORT_ERR', 'offset': 7936, 'window': 'APPD_PORT', 'test': False, 'window_kind': True, 'field': 'WINDOW', 'msb': 31, 'lsb': 0, 'width': 32, 'access': 'MIX', 'reset': None, 'reset_from': None, 'reset_key': None, 'self_clearing': False, 'saturating': False, 'pulse_cycles': None, 'pulse_output': None, 'clear_target': None, 'source': None, 'hw_port': None, 'event_port': None, 'increment_port': None, 'increment_gate': None, 'config_output': None, 'rsvd': False},
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
    {'name': 'PARAM_VARIANT', 'offset': 284, 'window': 'PARAM', 'kind': 'register'},
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

DEFAULT_VARIANT = 'product_x4_vl2'
VARIANTS = {'product_x4_vl2': {'NUM_LANES': 4, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 0}, 'product_x8_vl2': {'NUM_LANES': 8, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 0}, 'x4_vl2_placeholder': {'NUM_LANES': 4, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 1}, 'x8_vl2_placeholder': {'NUM_LANES': 8, 'NUM_VL': 2, 'SCR_PLACEHOLDER': 1}}
CSR_MODULE = {'product_x4_vl2': 'ub_csr_product_x4_vl2', 'product_x8_vl2': 'ub_csr_product_x8_vl2', 'x4_vl2_placeholder': 'ub_csr_x4_vl2_placeholder', 'x8_vl2_placeholder': 'ub_csr_x8_vl2_placeholder'}


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def product_v(tag: str | None = None):
    return REPO / "rtl" / "csr" / f"ub_csr_{tag or DEFAULT_VARIANT}.v"


def hooks_v(tag: str | None = None):
    return REPO / "rtl" / "csr" / "hooks" / f"ub_csr_{tag or DEFAULT_VARIANT}.v"


PRODUCT_V = product_v()
HOOKS_V = hooks_v()


import os
import shutil
import subprocess
import tempfile

try:
    from pycircuit import Circuit, compile, module, u  # type: ignore
    HAVE_PYCIRCUIT = True
except ImportError:  # pragma: no cover - frontend optional
    HAVE_PYCIRCUIT = False
    Circuit = None  # type: ignore
    compile = None  # type: ignore
    module = None  # type: ignore
    u = None  # type: ignore

PYCIRCUIT_COMMIT = "43cc5918e3d09ecc0c814cabef6c1384cb9980ae"
PYCC_EMIT = ["--emit=verilog"]

_ACTIVE_VARIANT = DEFAULT_VARIANT


def csr_module_name(tag: str) -> str:
    if tag not in CSR_MODULE:
        raise KeyError(f"unknown CSR variant {tag!r}")
    return CSR_MODULE[tag]


def variant_reset_word(tag: str) -> int:
    params = VARIANTS[tag]
    return (int(params["NUM_VL"]) & 0xF) | ((int(params["SCR_PLACEHOLDER"]) & 1) << 4)


def _resolve_reset(f, params=None):
    params = params or VARIANTS[_ACTIVE_VARIANT]
    if f.get("reset_from") == "variant":
        key = f.get("reset_key") or f["field"]
        return int(params[key])
    rst = f.get("reset")
    return None if rst is None else int(rst)


def _resolved_fields(tag=None):
    name = tag or _ACTIVE_VARIANT
    if name not in VARIANTS:
        raise KeyError(f"unknown CSR variant {name!r}")
    params = VARIANTS[name]
    out = []
    for f in FIELDS:
        g = dict(f)
        if g.get("reset_from") == "variant":
            g["reset"] = _resolve_reset(g, params)
        out.append(g)
    return out


def _qname(reg: str, field: str) -> str:
    return f"q_{reg.lower()}_{field.lower()}"


def _or_tree(m, wires, *, width: int):
    """Balanced OR reduction so pycc combinational depth stays under the limit."""
    if not wires:
        return m.const(0, width=width)
    cur = list(wires)
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur), 2):
            if i + 1 < len(cur):
                nxt.append(cur[i] | cur[i + 1])
            else:
                nxt.append(cur[i])
        cur = nxt
    return cur[0]


def _or_bits(m, wires):
    return _or_tree(m, wires, width=1)


def _find_pycc() -> str | None:
    env = os.environ.get("PYCC")
    if env and Path(env).is_file():
        return env
    return shutil.which("pycc")


def _llvm_version() -> str | None:
    for name in ("llvm-config-19", "llvm-config"):
        exe = shutil.which(name)
        if not exe:
            continue
        try:
            return subprocess.check_output([exe, "--version"], text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            continue
    return None


def _verilog_banner(test_hooks: int, variant: str) -> str:
    mod = csr_module_name(variant)
    return (
        "// Generated by pycircuit/csr/ub_csr_regs.py via pycircuit.compile() + pycc --emit=verilog\n"
        f"// {BANNER}\n"
        f"// pyc4.0 leaf {mod}. TEST_HOOKS={test_hooks} variant={variant}.\n"
        f"// lukebest/pyCircuit @{PYCIRCUIT_COMMIT}; backend pycc / LLVM 19.\n"
        "// Attribute-driven Circuit API: W1C / saturating / WO pulse / TEST gate / csr_err.\n"
        "// SPEC §2.2 / §3.2.3 / §11. Not string-templated Verilog.\n"
    )


def _pycc_verilog(mlir: str) -> str:
    """Lower frontend MLIR through pycc to synthesizable Verilog."""
    pycc = _find_pycc()
    if not pycc:
        raise RuntimeError(
            "pycc not on PATH. D5 Verilog is compile()+pycc --emit=verilog (LLVM 19). "
            "Frontend: pip install git+https://github.com/lukebest/pyCircuit@43cc5918 . "
            "Backend: clone that pin, LLVM 19 + cmake/ninja, flows/scripts/pyc build "
            "(CC=gcc CXX=g++), then PATH+=<install>/bin."
        )
    with tempfile.TemporaryDirectory(prefix="ub-csr-pycc-") as td:
        td_p = Path(td)
        pyc = td_p / "ub_csr.pyc"
        out = td_p / "ub_csr.v"
        pyc.write_text(mlir, encoding="utf-8")
        cmd = [pycc, str(pyc), *PYCC_EMIT, "--logic-depth=64", "-o", str(out)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not out.is_file():
            err = (proc.stderr or proc.stdout or "").strip()
            raise RuntimeError(f"pycc --emit=verilog failed ({proc.returncode}): {err}")
        return _keep_used_primitive_includes(out.read_text(encoding="utf-8"))


def _keep_used_primitive_includes(verilog: str) -> str:
    """Drop pycc's unused `include of fifo/mem/cdc primitives (this leaf is pyc_reg only)."""
    used = set()
    for name in (
        "pyc_reg",
        "pyc_add",
        "pyc_and",
        "pyc_or",
        "pyc_not",
        "pyc_xor",
        "pyc_mux",
        "pyc_fifo",
        "pyc_byte_mem",
        "pyc_sync_mem",
        "pyc_sync_mem_dp",
        "pyc_async_fifo",
        "pyc_cdc_sync",
    ):
        if f"{name} #" in verilog or f"{name} " in verilog.replace(f'`include "{name}.v"', ""):
            used.add(name)
    kept: list[str] = []
    for line in verilog.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("`include"):
            keep = any(f'"{name}.v"' in stripped for name in used)
            if not keep:
                continue
        kept.append(line)
    return "".join(kept)


def _cfg_wire(m, f, qs, test_active):
    """Live config (TEST-gated fields hold reset when test_active=0)."""
    q = qs[_qname(f["reg"], f["field"])]
    width = int(f["width"])
    rstv = 0 if f["reset"] is None else int(f["reset"])
    if f["test"]:
        return test_active.select(q, m.const(rstv, width=width))
    return q


def _csr_circuit(m, test_hooks: int, variant: str | None = None) -> None:
    """Full ub_csr on the pyc4.0 Circuit API (addr/W1C/sat/pulse/IRQ/rvalid)."""
    FIELDS = _resolved_fields(variant)
    if RULES.get("write_rvalid_next_cycle", 0) != 0:
        raise ValueError("SPEC §3.2.3 requires write next-cycle csr_rvalid=0")

    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")
    req = m.input("csr_req", width=1)
    wr = m.input("csr_wr", width=1)
    addr = m.input("csr_addr", width=16)
    wdata = m.input("csr_wdata", width=32)

    pins: dict[str, object] = {}
    seen_in: set[str] = set()
    for f in FIELDS:
        hp = f.get("hw_port")
        if hp and hp not in seen_in:
            seen_in.add(hp)
            pins[hp] = m.input(hp, width=int(f["width"]))
        ep = f.get("event_port")
        if ep and ep not in seen_in:
            seen_in.add(ep)
            pins[ep] = m.input(ep, width=1)
        ip = f.get("increment_port")
        if ip and ip not in seen_in:
            seen_in.add(ip)
            pins[ip] = m.input(ip, width=1)

    if test_hooks:
        test_active = m.input("tb_test_mode", width=1)
    else:
        test_active = m.const(0, width=1)

    cfg = [f for f in FIELDS if f.get("config_output")]
    pulse = [f for f in FIELDS if f.get("pulse_output") and f.get("pulse_cycles")]
    w1c = [f for f in FIELDS if f["access"] == "W1C" and not f["rsvd"]]
    sat = [f for f in FIELDS if f.get("saturating")]
    rw = [f for f in FIELDS if f["access"] == "RW" and not f["rsvd"]]
    clr = [f for f in FIELDS if f.get("clear_target")]
    test_win = next(x for x in WINDOWS if x.get("test_gated"))

    addr_aligned = addr.slice(lsb=0, width=2) == m.const(0, width=2)
    wr_fire = req & wr
    in_test = addr.uge(m.const(int(test_win["start"]), width=16)) & addr.ule(
        m.const(int(test_win["end"]), width=16)
    )
    test_hit = in_test & addr_aligned

    sels: dict[str, object] = {}
    for reg in REGS:
        sels[reg["name"]] = addr_aligned & (
            addr == m.const(int(reg["offset"]), width=16)
        )
    sel_fn = _or_bits(m, [sels[r["name"]] for r in REGS if r["window"] != "TEST"])
    sel_test = _or_bits(m, [sels[r["name"]] for r in REGS if r["window"] == "TEST"])
    wr_ok_fn = wr_fire & sel_fn
    wr_ok_test = wr_fire & sel_test & test_active

    qs: dict[str, object] = {}
    for f in rw + w1c + sat:
        key = _qname(f["reg"], f["field"])
        width = int(f["width"])
        rstv = 0 if f["reset"] is None else int(f["reset"])
        qs[key] = m.out(key, clk=clk, rst=rst, width=width, init=u(width, rstv))

    cnts: dict[str, object] = {}
    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        ckey = f"cnt_{f['reg'].lower()}_{f['field'].lower()}"
        cnts[ckey] = m.out(ckey, clk=clk, rst=rst, width=cw, init=u(cw, 0))

    wr_en: dict[str, object] = {}
    for f in rw + w1c + pulse + clr:
        key = f"{f['reg'].lower()}_{f['field'].lower()}"
        gate = wr_ok_test if f["test"] else wr_ok_fn
        wr_en[key] = gate & sels[f["reg"]]

    clrs: dict[str, object] = {}
    for f in clr:
        key = f"{f['reg'].lower()}_{f['field'].lower()}"
        clrs[f["clear_target"]] = wr_en[key] & wdata[int(f["lsb"])]

    cfg_w: dict[str, object] = {}
    for f in cfg:
        cfg_w[f["config_output"]] = _cfg_wire(m, f, qs, test_active)

    for f in rw:
        key = _qname(f["reg"], f["field"])
        sl = wdata.slice(lsb=int(f["lsb"]), width=int(f["width"]))
        qs[key].set(sl, when=wr_en[f"{f['reg'].lower()}_{f['field'].lower()}"])

    for f in w1c:
        key = _qname(f["reg"], f["field"])
        evn = pins[f["event_port"]]
        wrb = wr_en[f"{f['reg'].lower()}_{f['field'].lower()}"] & wdata[int(f["lsb"])]
        qs[key].set((qs[key] | evn) & ~wrb)

    for f in sat:
        key = _qname(f["reg"], f["field"])
        width = int(f["width"])
        q = qs[key]
        ones = m.const((1 << width) - 1, width=width)
        zero = m.const(0, width=width)
        one = m.const(1, width=width)
        inc = pins[f["increment_port"]]
        gate = f.get("increment_gate")
        if gate:
            gfield = next(
                x
                for x in FIELDS
                if x["reg"] == gate["reg"] and x["field"] == gate["field"]
            )
            gsig = cfg_w.get(gfield.get("config_output") or "")
            if gsig is None:
                gsig = qs[_qname(gate["reg"], gate["field"])]
            cond = ~gsig if gate.get("invert") else gsig
            inc = inc & cond
        clr_n = clrs[f["reg"]]
        do_inc = inc & (q != ones)
        q.set(clr_n.select(zero, do_inc.select(q.out() + one, q)))

    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        ckey = f"cnt_{f['reg'].lower()}_{f['field'].lower()}"
        cnt = cnts[ckey]
        load = wr_en[f"{f['reg'].lower()}_{f['field'].lower()}"] & wdata[int(f["lsb"])]
        cnt.set(
            load.select(
                m.const(cyc, width=cw),
                (cnt != 0).select(cnt.out() - m.const(1, width=cw), cnt),
            )
        )

    m.output("csr_ready", m.const(1, width=1))

    for f in pulse:
        ckey = f"cnt_{f['reg'].lower()}_{f['field'].lower()}"
        m.output(f["pulse_output"], cnts[ckey] != 0)

    for f in cfg:
        m.output(f["config_output"], cfg_w[f["config_output"]])

    st_bits = [f for f in w1c if f["reg"] == IRQ.get("status_reg", "IRQ_STATUS")]
    st_bits = sorted(st_bits, key=lambda x: x["lsb"])
    en = IRQ.get("enable") or {"reg": "CTRL", "field": "IRQ_EN"}
    mk = IRQ.get("mask") or {"reg": "IRQ_MASK", "field": "MASK"}
    irq_sticky = m.cat(*[qs[_qname(f["reg"], f["field"])] for f in reversed(st_bits)])
    irq_mask_w = qs[_qname(mk["reg"], mk["field"])]
    irq_en = qs[_qname(en["reg"], en["field"])]
    pending = irq_sticky & ~irq_mask_w
    m.output(IRQ.get("output", "irq"), irq_en & (pending != 0))

    by_reg: dict[str, list] = {}
    for f in FIELDS:
        by_reg.setdefault(f["reg"], []).append(f)
    rdatas: dict[str, object] = {}
    for rname, flist in by_reg.items():
        parts = []
        for f in sorted(flist, key=lambda x: -x["lsb"]):
            width = int(f["width"])
            if f["rsvd"] or f.get("window_kind") or (
                f["access"] == "WO" and f.get("self_clearing")
            ):
                parts.append(m.const(0, width=width))
            elif f.get("hw_port"):
                parts.append(pins[f["hw_port"]])
            elif f["access"] in ("RW", "W1C") or f.get("saturating"):
                parts.append(qs[_qname(f["reg"], f["field"])])
            elif f["access"] == "RO" and f["reset"] is not None:
                parts.append(m.const(int(f["reset"]), width=width))
            else:
                parts.append(m.const(0, width=width))
        rdatas[rname] = m.cat(*parts)

    gated_rdata = []
    for reg in REGS:
        hit = sels[reg["name"]]
        if reg["window"] == "TEST":
            hit = hit & test_active
        gated_rdata.append(hit.select(rdatas[reg["name"]], m.const(0, width=32)))
    rdata_n = _or_tree(m, gated_rdata, width=32)

    err_n = (~addr_aligned) | ((~sel_fn) & (~test_hit))

    rvalid = m.out("csr_rvalid_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    rvalid.set(req & ~wr)
    m.output("csr_rvalid", rvalid)

    rdata_q = m.out("csr_rdata_q", clk=clk, rst=rst, width=32, init=u(32, 0))
    rdata_q.set(rdata_n)
    m.output("csr_rdata", rdata_q)

    err_q = m.out("csr_err_q", clk=clk, rst=rst, width=1, init=u(1, 0))
    err_q.set(req.select(err_n, m.const(0, width=1)))
    m.output("csr_err", err_q)


if HAVE_PYCIRCUIT:
    @module(name="ub_csr")
    def _elab_product(m: Circuit) -> None:
        _csr_circuit(m, 0, _ACTIVE_VARIANT)

    @module(name="ub_csr")
    def _elab_hooks(m: Circuit) -> None:
        _csr_circuit(m, 1, _ACTIVE_VARIANT)
else:  # pragma: no cover
    _elab_product = None
    _elab_hooks = None


def _compile_design(test_hooks: int, variant: str | None = None):
    global _ACTIVE_VARIANT
    if not HAVE_PYCIRCUIT:
        raise RuntimeError("pycircuit not importable")
    tag = variant or DEFAULT_VARIANT
    if tag not in VARIANTS:
        raise KeyError(f"unknown CSR variant {tag!r}")
    _ACTIVE_VARIANT = tag
    fn = _elab_hooks if test_hooks else _elab_product
    return compile(fn, name=f"ub_csr_{tag}")


def emit_verilog(test_hooks: bool, variant: str | None = None) -> str:
    """Lower one TEST_HOOKS × variants: tag netlist: compile() → pycc --emit=verilog."""
    th = 1 if test_hooks else 0
    tag = variant or DEFAULT_VARIANT
    design = _compile_design(th, tag)
    body = _pycc_verilog(design.emit_mlir())
    text = _verilog_banner(th, tag) + body
    if "`ifdef" in text:
        raise RuntimeError("generated Verilog must not use ifdef TEST_HOOKS")
    if not test_hooks and "tb_test_mode" in text:
        raise RuntimeError("PRODUCT netlist must not contain tb_test_mode port")
    return text


def elaborate(test_hooks: int = 0, variant: str | None = None) -> dict:
    """Elaborate TEST_HOOKS=0/1 for one variants: tag via pycircuit.compile()."""
    tag = variant or DEFAULT_VARIANT
    mod = f"ub_csr_{tag}"
    status = {
        "test_hooks": int(test_hooks),
        "variant": tag,
        "module": mod,
        "pycircuit": HAVE_PYCIRCUIT,
        "elaborated": False,
        "reason": None,
        "pycc": _find_pycc(),
        "llvm": _llvm_version(),
        "modules": [],
        "arg_names": [],
        "result_names": [],
        "mlir_chars": 0,
        "verilog_via": None,
        "verilog_chars": 0,
        "entry": "_elab_hooks" if test_hooks else "_elab_product",
        "pycc_invoke": f"pycc <{mod}.pyc> --emit=verilog --logic-depth=64 -o <{mod}.v>",
        "commit": PYCIRCUIT_COMMIT,
    }
    if not HAVE_PYCIRCUIT:
        status["reason"] = "pycircuit not importable"
        return status
    try:
        design = _compile_design(int(test_hooks), tag)
        status["elaborated"] = True
        status["mlir_chars"] = len(design.emit_mlir())
        mods = list(design.modules())
        status["modules"] = [cm.sym_name for cm in mods]
        if mods:
            status["arg_names"] = list(mods[0].arg_names)
            status["result_names"] = list(mods[0].result_names)
        status["reason"] = (
            "compile() Design (frontend MLIR, lukebest/pyCircuit @"
            f"{PYCIRCUIT_COMMIT}). Verilog via pycc --emit=verilog / LLVM 19."
        )
        if status["pycc"]:
            try:
                v = emit_verilog(bool(test_hooks), variant=tag)
                status["verilog_via"] = "pycc"
                status["verilog_chars"] = len(v)
            except Exception as exc:  # pragma: no cover
                status["verilog_via"] = f"pycc failed: {type(exc).__name__}: {exc}"
        else:
            status["verilog_via"] = "pycc not on PATH"
    except Exception as exc:
        status["reason"] = f"compile failed: {type(exc).__name__}: {exc}"
    return status


def _write_verilog(path: Path, text: str) -> None:
    if not text.endswith("\n"):
        text += "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def generate():
    written = []
    for tag in VARIANTS:
        dest_p = product_v(tag)
        dest_h = hooks_v(tag)
        _write_verilog(dest_p, emit_verilog(False, variant=tag))
        _write_verilog(dest_h, emit_verilog(True, variant=tag))
        written.extend((dest_p, dest_h))
    return written


def main() -> int:
    for path in generate():
        print(f"wrote {path}")
    for tag in VARIANTS:
        print(elaborate(0, variant=tag))
        print(elaborate(1, variant=tag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

