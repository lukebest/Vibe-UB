"""CSR offsets for the TB (REGMAP §2). Whole-word, 1-cycle read (SPEC §3.2.3).

TEST window: SPEC §3.2.3 / §10 / §11 and REGMAP §2.4.
Quiet (tb_test_mode=0 or PRODUCT): mapped, read 0, write ignore, csr_err=0.
"""

from __future__ import annotations

# CTRL / STATUS
CTRL = 0x0000
STATUS = 0x0004
IRQ_STATUS = 0x0008
IRQ_MASK = 0x000C
PORT_CNA = 0x0010

CTRL_PORT_RST = 0
CTRL_LMSM_START = 1  # REGMAP 0x0000 bit1; was LMSM_CTRL.START
CTRL_IRQ_EN = 2

# STATUS encodings closed on PR #4 4ed4eae. Reserved values: RTL never
# produces them; TB asserts (REGMAP §2 preamble, SPEC §6.3 / §6.4).
STATUS_LMSM_ST = (7, 3)
STATUS_DLL_SM_ST = (9, 8)
STATUS_RETRY_REQ_ST = (12, 10)
STATUS_RETRY_ACK_ST = (14, 13)

RETRY_REQ_ST = {
    "NORMAL": 0,
    "REQ": 1,
    "WAIT": 2,
    "RETRAIN": 3,
    "ERROR": 4,
}
RETRY_REQ_ST_RESERVED = frozenset({5, 6, 7})

RETRY_ACK_ST = {
    "NORMAL": 0,
    "ACK": 1,
}
RETRY_ACK_ST_RESERVED = frozenset({2, 3})

PARAM_PHY = 0x0100
# PARAM_PHY.NUM_LANES_{TX,RX}: binary lane count. Legal 1/2/4/8 only.
NUM_LANES_LEGAL = frozenset({1, 2, 4, 8})

# ERR counters (RO, saturate) + CNT_CLR (WO, self-clear)
CNT_FEC_UNCORR = 0x0200
CNT_CRC_FAIL = 0x0204
CNT_RETRY_REQ = 0x0208
CNT_RETRY_TO = 0x020C
CNT_CRD_OF = 0x0210
CNT_CRD_TO = 0x0214
CNT_TRAIN_TO = 0x0218
CNT_BAD_VL = 0x021C
CNT_CRD_UF = 0x0220
CNT_CLR = 0x0224

# CNT_CLR bit0–8 cover every counter, including CNT_CRD_UF (REGMAP §2.3).
CNT_CLR_BITS = {
    "FEC_UNCORR": 0,
    "CRC_FAIL": 1,
    "RETRY_REQ": 2,
    "RETRY_TO": 3,
    "CRD_OF": 4,
    "CRD_TO": 5,
    "TRAIN_TO": 6,
    "BAD_VL": 7,
    "CRD_UF": 8,
}
CNT_CLR_ALL = (1 << 9) - 1  # bits 0–8
CNT_ADDR = {
    "FEC_UNCORR": CNT_FEC_UNCORR,
    "CRC_FAIL": CNT_CRC_FAIL,
    "RETRY_REQ": CNT_RETRY_REQ,
    "RETRY_TO": CNT_RETRY_TO,
    "CRD_OF": CNT_CRD_OF,
    "CRD_TO": CNT_CRD_TO,
    "TRAIN_TO": CNT_TRAIN_TO,
    "BAD_VL": CNT_BAD_VL,
    "CRD_UF": CNT_CRD_UF,
}

# TEST window 0x0300–0x03FF
TEST_BASE = 0x0300
TEST_END = 0x03FF
LMSM_TMR_SCALE = 0x0300
CRD_TO_DIS = 0x0304
PCS_TX_TEST = 0x0308

# App. D mirrors (M1 window addresses after the 0x2400/0x2500 move)
APPD_PORT_BASIC = 0x1000
APPD_LINK_CAP = 0x1100
APPD_LINK_LOG = 0x1200
APPD_LMSM_ST = 0x1E00
APPD_PORT_ERR = 0x1F00


def _field(word: int, hi: int, lo: int) -> int:
    return (word >> lo) & ((1 << (hi - lo + 1)) - 1)


def assert_retry_req_st(value: int) -> int:
    if value in RETRY_REQ_ST_RESERVED:
        raise AssertionError(f"STATUS.RETRY_REQ_ST reserved encoding {value} (REGMAP §2.1)")
    return value


def assert_retry_ack_st(value: int) -> int:
    if value in RETRY_ACK_ST_RESERVED:
        raise AssertionError(f"STATUS.RETRY_ACK_ST reserved encoding {value} (REGMAP §2.1)")
    return value


def assert_num_lanes(value: int, name: str = "NUM_LANES") -> int:
    if value not in NUM_LANES_LEGAL:
        raise AssertionError(f"{name} reserved encoding {value}; legal {sorted(NUM_LANES_LEGAL)}")
    return value


def retry_req_st(status: int) -> int:
    return assert_retry_req_st(_field(status, *STATUS_RETRY_REQ_ST))


def retry_ack_st(status: int) -> int:
    return assert_retry_ack_st(_field(status, *STATUS_RETRY_ACK_ST))


def is_aligned(addr: int) -> bool:
    return (addr & 0x3) == 0


def in_test_window(addr: int) -> bool:
    return TEST_BASE <= addr <= TEST_END


def in_cnt_window(addr: int) -> bool:
    return addr in CNT_ADDR.values() or addr == CNT_CLR
