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
CTRL_LMSM_START = 1
CTRL_IRQ_EN = 2

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


def is_aligned(addr: int) -> bool:
    return (addr & 0x3) == 0


def in_test_window(addr: int) -> bool:
    return TEST_BASE <= addr <= TEST_END


def in_cnt_window(addr: int) -> bool:
    return addr in CNT_ADDR.values() or addr == CNT_CLR
