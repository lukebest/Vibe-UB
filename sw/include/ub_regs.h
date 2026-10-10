/* GENERATED — edit docs/regmap/regmap.yaml */
#ifndef UB_REGS_H
#define UB_REGS_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define UB_CSR_WORD_BITS          32u
#define UB_CSR_ADDR_BITS          16u
#define UB_CSR_ALIGN_BYTES        4u
#define UB_CSR_READ_LATENCY       1u
#define UB_CSR_PORT_RST_CYCLES    16u

#define UB_WIN_CTRL_STATUS_START  0x0000u
#define UB_WIN_CTRL_STATUS_END    0x00ffu
#define UB_WIN_PARAM_START  0x0100u
#define UB_WIN_PARAM_END    0x01ffu
#define UB_WIN_ERR_START  0x0200u
#define UB_WIN_ERR_END    0x02ffu
#define UB_WIN_TEST_START  0x0300u
#define UB_WIN_TEST_END    0x03ffu
#define UB_WIN_APPD_PORT_START  0x1000u
#define UB_WIN_APPD_PORT_END    0x1fffu

#define UB_REG_CTRL  0x0000u
#define UB_CTRL_PORT_RST_SHIFT  0u
#define UB_CTRL_PORT_RST_WIDTH  1u
#define UB_CTRL_PORT_RST_MASK   0x00000001u
#define UB_CTRL_PORT_RST_RESET  0x0u
#define UB_CTRL_LMSM_START_SHIFT  1u
#define UB_CTRL_LMSM_START_WIDTH  1u
#define UB_CTRL_LMSM_START_MASK   0x00000002u
#define UB_CTRL_LMSM_START_RESET  0x0u
#define UB_CTRL_IRQ_EN_SHIFT  2u
#define UB_CTRL_IRQ_EN_WIDTH  1u
#define UB_CTRL_IRQ_EN_MASK   0x00000004u
#define UB_CTRL_IRQ_EN_RESET  0x0u
#define UB_CTRL_RSVD_SHIFT  3u
#define UB_CTRL_RSVD_WIDTH  29u
#define UB_CTRL_RSVD_MASK   0xfffffff8u
#define UB_CTRL_RSVD_RESET  0x0u

#define UB_REG_STATUS  0x0004u
#define UB_STATUS_LINK_UP_SHIFT  0u
#define UB_STATUS_LINK_UP_WIDTH  1u
#define UB_STATUS_LINK_UP_MASK   0x00000001u
#define UB_STATUS_LINK_UP_RESET  0x0u
#define UB_STATUS_LINK_READY_SHIFT  1u
#define UB_STATUS_LINK_READY_WIDTH  1u
#define UB_STATUS_LINK_READY_MASK   0x00000002u
#define UB_STATUS_LINK_READY_RESET  0x0u
#define UB_STATUS_DLL_STATUS_UP_SHIFT  2u
#define UB_STATUS_DLL_STATUS_UP_WIDTH  1u
#define UB_STATUS_DLL_STATUS_UP_MASK   0x00000004u
#define UB_STATUS_DLL_STATUS_UP_RESET  0x0u
#define UB_STATUS_LMSM_ST_SHIFT  3u
#define UB_STATUS_LMSM_ST_WIDTH  5u
#define UB_STATUS_LMSM_ST_MASK   0x000000f8u
#define UB_STATUS_LMSM_ST_RESET  0x0u
#define UB_STATUS_DLL_SM_ST_SHIFT  8u
#define UB_STATUS_DLL_SM_ST_WIDTH  2u
#define UB_STATUS_DLL_SM_ST_MASK   0x00000300u
#define UB_STATUS_DLL_SM_ST_RESET  0x0u
#define UB_STATUS_RETRY_REQ_ST_SHIFT  10u
#define UB_STATUS_RETRY_REQ_ST_WIDTH  3u
#define UB_STATUS_RETRY_REQ_ST_MASK   0x00001c00u
#define UB_STATUS_RETRY_REQ_ST_RESET  0x0u
#define UB_STATUS_RETRY_REQ_ST_NORMAL  0u
#define UB_STATUS_RETRY_REQ_ST_REQ  1u
#define UB_STATUS_RETRY_REQ_ST_WAIT  2u
#define UB_STATUS_RETRY_REQ_ST_RETRAIN  3u
#define UB_STATUS_RETRY_REQ_ST_ERROR  4u
#define UB_STATUS_RETRY_REQ_ST_RSVD5  5u
#define UB_STATUS_RETRY_REQ_ST_RSVD6  6u
#define UB_STATUS_RETRY_REQ_ST_RSVD7  7u
#define UB_STATUS_RETRY_ACK_ST_SHIFT  13u
#define UB_STATUS_RETRY_ACK_ST_WIDTH  2u
#define UB_STATUS_RETRY_ACK_ST_MASK   0x00006000u
#define UB_STATUS_RETRY_ACK_ST_RESET  0x0u
#define UB_STATUS_RETRY_ACK_ST_NORMAL  0u
#define UB_STATUS_RETRY_ACK_ST_ACK  1u
#define UB_STATUS_RETRY_ACK_ST_RSVD2  2u
#define UB_STATUS_RETRY_ACK_ST_RSVD3  3u
#define UB_STATUS_RSVD_SHIFT  15u
#define UB_STATUS_RSVD_WIDTH  17u
#define UB_STATUS_RSVD_MASK   0xffff8000u
#define UB_STATUS_RSVD_RESET  0x0u

#define UB_REG_IRQ_STATUS  0x0008u
#define UB_IRQ_STATUS_FEC_UNCORR_SHIFT  0u
#define UB_IRQ_STATUS_FEC_UNCORR_WIDTH  1u
#define UB_IRQ_STATUS_FEC_UNCORR_MASK   0x00000001u
#define UB_IRQ_STATUS_FEC_UNCORR_RESET  0x0u
#define UB_IRQ_STATUS_CRC_FAIL_SHIFT  1u
#define UB_IRQ_STATUS_CRC_FAIL_WIDTH  1u
#define UB_IRQ_STATUS_CRC_FAIL_MASK   0x00000002u
#define UB_IRQ_STATUS_CRC_FAIL_RESET  0x0u
#define UB_IRQ_STATUS_RETRY_ERR_SHIFT  2u
#define UB_IRQ_STATUS_RETRY_ERR_WIDTH  1u
#define UB_IRQ_STATUS_RETRY_ERR_MASK   0x00000004u
#define UB_IRQ_STATUS_RETRY_ERR_RESET  0x0u
#define UB_IRQ_STATUS_CRD_PROTO_SHIFT  3u
#define UB_IRQ_STATUS_CRD_PROTO_WIDTH  1u
#define UB_IRQ_STATUS_CRD_PROTO_MASK   0x00000008u
#define UB_IRQ_STATUS_CRD_PROTO_RESET  0x0u
#define UB_IRQ_STATUS_TRAIN_FAIL_SHIFT  4u
#define UB_IRQ_STATUS_TRAIN_FAIL_WIDTH  1u
#define UB_IRQ_STATUS_TRAIN_FAIL_MASK   0x00000010u
#define UB_IRQ_STATUS_TRAIN_FAIL_RESET  0x0u
#define UB_IRQ_STATUS_BAD_VL_SHIFT  5u
#define UB_IRQ_STATUS_BAD_VL_WIDTH  1u
#define UB_IRQ_STATUS_BAD_VL_MASK   0x00000020u
#define UB_IRQ_STATUS_BAD_VL_RESET  0x0u
#define UB_IRQ_STATUS_CRD_UF_SHIFT  6u
#define UB_IRQ_STATUS_CRD_UF_WIDTH  1u
#define UB_IRQ_STATUS_CRD_UF_MASK   0x00000040u
#define UB_IRQ_STATUS_CRD_UF_RESET  0x0u
#define UB_IRQ_STATUS_RSVD_SHIFT  7u
#define UB_IRQ_STATUS_RSVD_WIDTH  25u
#define UB_IRQ_STATUS_RSVD_MASK   0xffffff80u
#define UB_IRQ_STATUS_RSVD_RESET  0x0u

#define UB_REG_IRQ_MASK  0x000cu
#define UB_IRQ_MASK_MASK_SHIFT  0u
#define UB_IRQ_MASK_MASK_WIDTH  7u
#define UB_IRQ_MASK_MASK_MASK   0x0000007fu
#define UB_IRQ_MASK_MASK_RESET  0x7fu
#define UB_IRQ_MASK_RSVD_SHIFT  7u
#define UB_IRQ_MASK_RSVD_WIDTH  25u
#define UB_IRQ_MASK_RSVD_MASK   0xffffff80u
#define UB_IRQ_MASK_RSVD_RESET  0x0u

#define UB_REG_PORT_CNA  0x0010u
#define UB_PORT_CNA_CNA_SHIFT  0u
#define UB_PORT_CNA_CNA_WIDTH  32u
#define UB_PORT_CNA_CNA_MASK   0xffffffffu
#define UB_PORT_CNA_CNA_RESET  0x0u

#define UB_REG_PARAM_PHY  0x0100u
#define UB_PARAM_PHY_PHY_MODE_SHIFT  0u
#define UB_PARAM_PHY_PHY_MODE_WIDTH  2u
#define UB_PARAM_PHY_PHY_MODE_MASK   0x00000003u
#define UB_PARAM_PHY_PHY_MODE_RESET  0x2u
#define UB_PARAM_PHY_PHY_MODE_MODE_1  1u
#define UB_PARAM_PHY_PHY_MODE_MODE_2  2u
#define UB_PARAM_PHY_DATA_RATE_SHIFT  2u
#define UB_PARAM_PHY_DATA_RATE_WIDTH  4u
#define UB_PARAM_PHY_DATA_RATE_MASK   0x0000003cu
#define UB_PARAM_PHY_DATA_RATE_RESET  0x0u
#define UB_PARAM_PHY_NUM_LANES_TX_SHIFT  6u
#define UB_PARAM_PHY_NUM_LANES_TX_WIDTH  4u
#define UB_PARAM_PHY_NUM_LANES_TX_MASK   0x000003c0u
#define UB_PARAM_PHY_NUM_LANES_RX_SHIFT  10u
#define UB_PARAM_PHY_NUM_LANES_RX_WIDTH  4u
#define UB_PARAM_PHY_NUM_LANES_RX_MASK   0x00003c00u
#define UB_PARAM_PHY_PMA_W_SHIFT  14u
#define UB_PARAM_PHY_PMA_W_WIDTH  8u
#define UB_PARAM_PHY_PMA_W_MASK   0x003fc000u
#define UB_PARAM_PHY_PMA_W_RESET  0x20u
#define UB_PARAM_PHY_ALLOW_ASYM_SHIFT  22u
#define UB_PARAM_PHY_ALLOW_ASYM_WIDTH  1u
#define UB_PARAM_PHY_ALLOW_ASYM_MASK   0x00400000u
#define UB_PARAM_PHY_ALLOW_ASYM_RESET  0x0u
#define UB_PARAM_PHY_RSVD_SHIFT  23u
#define UB_PARAM_PHY_RSVD_WIDTH  9u
#define UB_PARAM_PHY_RSVD_MASK   0xff800000u
#define UB_PARAM_PHY_RSVD_RESET  0x0u

#define UB_REG_PARAM_FEC  0x0104u
#define UB_PARAM_FEC_FEC_MODE_SHIFT  0u
#define UB_PARAM_FEC_FEC_MODE_WIDTH  3u
#define UB_PARAM_FEC_FEC_MODE_MASK   0x00000007u
#define UB_PARAM_FEC_FEC_MODE_RESET  0x2u
#define UB_PARAM_FEC_CODEC_NUM_SHIFT  3u
#define UB_PARAM_FEC_CODEC_NUM_WIDTH  2u
#define UB_PARAM_FEC_CODEC_NUM_MASK   0x00000018u
#define UB_PARAM_FEC_CODEC_NUM_RESET  0x1u
#define UB_PARAM_FEC_RSVD_SHIFT  5u
#define UB_PARAM_FEC_RSVD_WIDTH  27u
#define UB_PARAM_FEC_RSVD_MASK   0xffffffe0u
#define UB_PARAM_FEC_RSVD_RESET  0x0u

#define UB_REG_PARAM_DLL  0x0108u
#define UB_PARAM_DLL_NUM_VL_SHIFT  0u
#define UB_PARAM_DLL_NUM_VL_WIDTH  5u
#define UB_PARAM_DLL_NUM_VL_MASK   0x0000001fu
#define UB_PARAM_DLL_FLOW_CTRL_SIZE_SHIFT  5u
#define UB_PARAM_DLL_FLOW_CTRL_SIZE_WIDTH  8u
#define UB_PARAM_DLL_FLOW_CTRL_SIZE_MASK   0x00001fe0u
#define UB_PARAM_DLL_FLOW_CTRL_SIZE_RESET  0x1u
#define UB_PARAM_DLL_ACK_GRAIN_SHIFT  13u
#define UB_PARAM_DLL_ACK_GRAIN_WIDTH  8u
#define UB_PARAM_DLL_ACK_GRAIN_MASK   0x001fe000u
#define UB_PARAM_DLL_ACK_GRAIN_RESET  0x20u
#define UB_PARAM_DLL_CREDIT_EXCL_SHIFT  21u
#define UB_PARAM_DLL_CREDIT_EXCL_WIDTH  1u
#define UB_PARAM_DLL_CREDIT_EXCL_MASK   0x00200000u
#define UB_PARAM_DLL_CREDIT_EXCL_RESET  0x1u
#define UB_PARAM_DLL_RSVD_SHIFT  22u
#define UB_PARAM_DLL_RSVD_WIDTH  10u
#define UB_PARAM_DLL_RSVD_MASK   0xffc00000u
#define UB_PARAM_DLL_RSVD_RESET  0x0u

#define UB_REG_PARAM_RETRY  0x010cu
#define UB_PARAM_RETRY_RETRY_BUF_DEPTH_SHIFT  0u
#define UB_PARAM_RETRY_RETRY_BUF_DEPTH_WIDTH  16u
#define UB_PARAM_RETRY_RETRY_BUF_DEPTH_MASK   0x0000ffffu
#define UB_PARAM_RETRY_RETRY_BUF_DEPTH_RESET  0x100u
#define UB_PARAM_RETRY_NUM_RETRY_TH_SHIFT  16u
#define UB_PARAM_RETRY_NUM_RETRY_TH_WIDTH  8u
#define UB_PARAM_RETRY_NUM_RETRY_TH_MASK   0x00ff0000u
#define UB_PARAM_RETRY_NUM_RETRY_TH_RESET  0xfu
#define UB_PARAM_RETRY_NUM_PHY_REINIT_TH_SHIFT  24u
#define UB_PARAM_RETRY_NUM_PHY_REINIT_TH_WIDTH  8u
#define UB_PARAM_RETRY_NUM_PHY_REINIT_TH_MASK   0xff000000u
#define UB_PARAM_RETRY_NUM_PHY_REINIT_TH_RESET  0x4u

#define UB_REG_PARAM_CRD  0x0110u
#define UB_PARAM_CRD_INIT_CRD_SHIFT  0u
#define UB_PARAM_CRD_INIT_CRD_WIDTH  16u
#define UB_PARAM_CRD_INIT_CRD_MASK   0x0000ffffu
#define UB_PARAM_CRD_INIT_CRD_RESET  0x280u
#define UB_PARAM_CRD_CRD_BP_TH_SHIFT  16u
#define UB_PARAM_CRD_CRD_BP_TH_WIDTH  16u
#define UB_PARAM_CRD_CRD_BP_TH_MASK   0xffff0000u
#define UB_PARAM_CRD_CRD_BP_TH_RESET  0x400u

#define UB_REG_PARAM_INIT_FEATURE  0x0114u
#define UB_PARAM_INIT_FEATURE_FEATURE_ID_SHIFT  0u
#define UB_PARAM_INIT_FEATURE_FEATURE_ID_WIDTH  16u
#define UB_PARAM_INIT_FEATURE_FEATURE_ID_MASK   0x0000ffffu
#define UB_PARAM_INIT_FEATURE_FEATURE_ID_RESET  0x1u
#define UB_PARAM_INIT_FEATURE_RXBUF_VL_SHARE_SHIFT  16u
#define UB_PARAM_INIT_FEATURE_RXBUF_VL_SHARE_WIDTH  1u
#define UB_PARAM_INIT_FEATURE_RXBUF_VL_SHARE_MASK   0x00010000u
#define UB_PARAM_INIT_FEATURE_RXBUF_VL_SHARE_RESET  0x0u
#define UB_PARAM_INIT_FEATURE_VL_ENABLE_SHIFT  17u
#define UB_PARAM_INIT_FEATURE_VL_ENABLE_WIDTH  15u
#define UB_PARAM_INIT_FEATURE_VL_ENABLE_MASK   0xfffe0000u
#define UB_PARAM_INIT_FEATURE_VL_ENABLE_RESET  0x3u

#define UB_REG_PARAM_INIT_VL  0x0118u
#define UB_PARAM_INIT_VL_VL_ENABLE_SHIFT  0u
#define UB_PARAM_INIT_VL_VL_ENABLE_WIDTH  16u
#define UB_PARAM_INIT_VL_VL_ENABLE_MASK   0x0000ffffu
#define UB_PARAM_INIT_VL_VL_ENABLE_RESET  0x3u
#define UB_PARAM_INIT_VL_RSVD_SHIFT  16u
#define UB_PARAM_INIT_VL_RSVD_WIDTH  16u
#define UB_PARAM_INIT_VL_RSVD_MASK   0xffff0000u
#define UB_PARAM_INIT_VL_RSVD_RESET  0x0u

#define UB_REG_PARAM_VARIANT  0x011cu
#define UB_PARAM_VARIANT_NUM_VL_SHIFT  0u
#define UB_PARAM_VARIANT_NUM_VL_WIDTH  4u
#define UB_PARAM_VARIANT_NUM_VL_MASK   0x0000000fu
#define UB_PARAM_VARIANT_SCR_PLACEHOLDER_SHIFT  4u
#define UB_PARAM_VARIANT_SCR_PLACEHOLDER_WIDTH  1u
#define UB_PARAM_VARIANT_SCR_PLACEHOLDER_MASK   0x00000010u
#define UB_PARAM_VARIANT_RSVD_SHIFT  5u
#define UB_PARAM_VARIANT_RSVD_WIDTH  27u
#define UB_PARAM_VARIANT_RSVD_MASK   0xffffffe0u
#define UB_PARAM_VARIANT_RSVD_RESET  0x0u

#define UB_REG_CNT_FEC_UNCORR  0x0200u
#define UB_CNT_FEC_UNCORR_COUNT_SHIFT  0u
#define UB_CNT_FEC_UNCORR_COUNT_WIDTH  32u
#define UB_CNT_FEC_UNCORR_COUNT_MASK   0xffffffffu
#define UB_CNT_FEC_UNCORR_COUNT_RESET  0x0u

#define UB_REG_CNT_CRC_FAIL  0x0204u
#define UB_CNT_CRC_FAIL_COUNT_SHIFT  0u
#define UB_CNT_CRC_FAIL_COUNT_WIDTH  32u
#define UB_CNT_CRC_FAIL_COUNT_MASK   0xffffffffu
#define UB_CNT_CRC_FAIL_COUNT_RESET  0x0u

#define UB_REG_CNT_RETRY_REQ  0x0208u
#define UB_CNT_RETRY_REQ_COUNT_SHIFT  0u
#define UB_CNT_RETRY_REQ_COUNT_WIDTH  32u
#define UB_CNT_RETRY_REQ_COUNT_MASK   0xffffffffu
#define UB_CNT_RETRY_REQ_COUNT_RESET  0x0u

#define UB_REG_CNT_RETRY_TO  0x020cu
#define UB_CNT_RETRY_TO_COUNT_SHIFT  0u
#define UB_CNT_RETRY_TO_COUNT_WIDTH  32u
#define UB_CNT_RETRY_TO_COUNT_MASK   0xffffffffu
#define UB_CNT_RETRY_TO_COUNT_RESET  0x0u

#define UB_REG_CNT_CRD_OF  0x0210u
#define UB_CNT_CRD_OF_COUNT_SHIFT  0u
#define UB_CNT_CRD_OF_COUNT_WIDTH  32u
#define UB_CNT_CRD_OF_COUNT_MASK   0xffffffffu
#define UB_CNT_CRD_OF_COUNT_RESET  0x0u

#define UB_REG_CNT_CRD_TO  0x0214u
#define UB_CNT_CRD_TO_COUNT_SHIFT  0u
#define UB_CNT_CRD_TO_COUNT_WIDTH  32u
#define UB_CNT_CRD_TO_COUNT_MASK   0xffffffffu
#define UB_CNT_CRD_TO_COUNT_RESET  0x0u

#define UB_REG_CNT_TRAIN_TO  0x0218u
#define UB_CNT_TRAIN_TO_COUNT_SHIFT  0u
#define UB_CNT_TRAIN_TO_COUNT_WIDTH  32u
#define UB_CNT_TRAIN_TO_COUNT_MASK   0xffffffffu
#define UB_CNT_TRAIN_TO_COUNT_RESET  0x0u

#define UB_REG_CNT_BAD_VL  0x021cu
#define UB_CNT_BAD_VL_COUNT_SHIFT  0u
#define UB_CNT_BAD_VL_COUNT_WIDTH  32u
#define UB_CNT_BAD_VL_COUNT_MASK   0xffffffffu
#define UB_CNT_BAD_VL_COUNT_RESET  0x0u

#define UB_REG_CNT_CRD_UF  0x0220u
#define UB_CNT_CRD_UF_COUNT_SHIFT  0u
#define UB_CNT_CRD_UF_COUNT_WIDTH  32u
#define UB_CNT_CRD_UF_COUNT_MASK   0xffffffffu
#define UB_CNT_CRD_UF_COUNT_RESET  0x0u

#define UB_REG_CNT_CLR  0x0224u
#define UB_CNT_CLR_FEC_UNCORR_SHIFT  0u
#define UB_CNT_CLR_FEC_UNCORR_WIDTH  1u
#define UB_CNT_CLR_FEC_UNCORR_MASK   0x00000001u
#define UB_CNT_CLR_FEC_UNCORR_RESET  0x0u
#define UB_CNT_CLR_CRC_FAIL_SHIFT  1u
#define UB_CNT_CLR_CRC_FAIL_WIDTH  1u
#define UB_CNT_CLR_CRC_FAIL_MASK   0x00000002u
#define UB_CNT_CLR_CRC_FAIL_RESET  0x0u
#define UB_CNT_CLR_RETRY_REQ_SHIFT  2u
#define UB_CNT_CLR_RETRY_REQ_WIDTH  1u
#define UB_CNT_CLR_RETRY_REQ_MASK   0x00000004u
#define UB_CNT_CLR_RETRY_REQ_RESET  0x0u
#define UB_CNT_CLR_RETRY_TO_SHIFT  3u
#define UB_CNT_CLR_RETRY_TO_WIDTH  1u
#define UB_CNT_CLR_RETRY_TO_MASK   0x00000008u
#define UB_CNT_CLR_RETRY_TO_RESET  0x0u
#define UB_CNT_CLR_CRD_OF_SHIFT  4u
#define UB_CNT_CLR_CRD_OF_WIDTH  1u
#define UB_CNT_CLR_CRD_OF_MASK   0x00000010u
#define UB_CNT_CLR_CRD_OF_RESET  0x0u
#define UB_CNT_CLR_CRD_TO_SHIFT  5u
#define UB_CNT_CLR_CRD_TO_WIDTH  1u
#define UB_CNT_CLR_CRD_TO_MASK   0x00000020u
#define UB_CNT_CLR_CRD_TO_RESET  0x0u
#define UB_CNT_CLR_TRAIN_TO_SHIFT  6u
#define UB_CNT_CLR_TRAIN_TO_WIDTH  1u
#define UB_CNT_CLR_TRAIN_TO_MASK   0x00000040u
#define UB_CNT_CLR_TRAIN_TO_RESET  0x0u
#define UB_CNT_CLR_BAD_VL_SHIFT  7u
#define UB_CNT_CLR_BAD_VL_WIDTH  1u
#define UB_CNT_CLR_BAD_VL_MASK   0x00000080u
#define UB_CNT_CLR_BAD_VL_RESET  0x0u
#define UB_CNT_CLR_CRD_UF_SHIFT  8u
#define UB_CNT_CLR_CRD_UF_WIDTH  1u
#define UB_CNT_CLR_CRD_UF_MASK   0x00000100u
#define UB_CNT_CLR_CRD_UF_RESET  0x0u
#define UB_CNT_CLR_RSVD_SHIFT  9u
#define UB_CNT_CLR_RSVD_WIDTH  23u
#define UB_CNT_CLR_RSVD_MASK   0xfffffe00u
#define UB_CNT_CLR_RSVD_RESET  0x0u

#define UB_REG_LMSM_TMR_SCALE  0x0300u
#define UB_LMSM_TMR_SCALE_SCALE_SHIFT  0u
#define UB_LMSM_TMR_SCALE_SCALE_WIDTH  8u
#define UB_LMSM_TMR_SCALE_SCALE_MASK   0x000000ffu
#define UB_LMSM_TMR_SCALE_SCALE_RESET  0x0u
#define UB_LMSM_TMR_SCALE_RSVD_SHIFT  8u
#define UB_LMSM_TMR_SCALE_RSVD_WIDTH  24u
#define UB_LMSM_TMR_SCALE_RSVD_MASK   0xffffff00u
#define UB_LMSM_TMR_SCALE_RSVD_RESET  0x0u

#define UB_REG_CRD_TO_DIS  0x0304u
#define UB_CRD_TO_DIS_DIS_SHIFT  0u
#define UB_CRD_TO_DIS_DIS_WIDTH  1u
#define UB_CRD_TO_DIS_DIS_MASK   0x00000001u
#define UB_CRD_TO_DIS_DIS_RESET  0x0u
#define UB_CRD_TO_DIS_RSVD_SHIFT  1u
#define UB_CRD_TO_DIS_RSVD_WIDTH  31u
#define UB_CRD_TO_DIS_RSVD_MASK   0xfffffffeu
#define UB_CRD_TO_DIS_RSVD_RESET  0x0u

#define UB_REG_PCS_TX_TEST  0x0308u
#define UB_PCS_TX_TEST_AM_IVL_SCALE_SHIFT  0u
#define UB_PCS_TX_TEST_AM_IVL_SCALE_WIDTH  8u
#define UB_PCS_TX_TEST_AM_IVL_SCALE_MASK   0x000000ffu
#define UB_PCS_TX_TEST_AM_IVL_SCALE_RESET  0x0u
#define UB_PCS_TX_TEST_RSVD_SHIFT  8u
#define UB_PCS_TX_TEST_RSVD_WIDTH  24u
#define UB_PCS_TX_TEST_RSVD_MASK   0xffffff00u
#define UB_PCS_TX_TEST_RSVD_RESET  0x0u

#define UB_REG_APPD_PORT_BASIC  0x1000u
#define UB_APPD_PORT_BASIC_WINDOW_SHIFT  0u
#define UB_APPD_PORT_BASIC_WINDOW_WIDTH  32u
#define UB_APPD_PORT_BASIC_WINDOW_MASK   0xffffffffu

#define UB_REG_APPD_LINK_CAP  0x1100u
#define UB_APPD_LINK_CAP_WINDOW_SHIFT  0u
#define UB_APPD_LINK_CAP_WINDOW_WIDTH  32u
#define UB_APPD_LINK_CAP_WINDOW_MASK   0xffffffffu

#define UB_REG_APPD_LINK_LOG  0x1200u
#define UB_APPD_LINK_LOG_WINDOW_SHIFT  0u
#define UB_APPD_LINK_LOG_WINDOW_WIDTH  32u
#define UB_APPD_LINK_LOG_WINDOW_MASK   0xffffffffu

#define UB_REG_APPD_LMSM_ST  0x1e00u
#define UB_APPD_LMSM_ST_WINDOW_SHIFT  0u
#define UB_APPD_LMSM_ST_WINDOW_WIDTH  32u
#define UB_APPD_LMSM_ST_WINDOW_MASK   0xffffffffu

#define UB_REG_APPD_PORT_ERR  0x1f00u
#define UB_APPD_PORT_ERR_WINDOW_SHIFT  0u
#define UB_APPD_PORT_ERR_WINDOW_WIDTH  32u
#define UB_APPD_PORT_ERR_WINDOW_MASK   0xffffffffu

#define UB_CSR_DEFAULT_VARIANT  "product_x4_vl2"
#define UB_CSR_VARIANT_PRODUCT_X4_VL2  0u
#define UB_CSR_MODULE_PRODUCT_X4_VL2  "ub_csr_product_x4_vl2"
#define UB_VARIANT_PRODUCT_X4_VL2_NUM_LANES  4u
#define UB_VARIANT_PRODUCT_X4_VL2_NUM_VL  2u
#define UB_VARIANT_PRODUCT_X4_VL2_SCR_PLACEHOLDER  1u
#define UB_VARIANT_PRODUCT_X4_VL2_PARAM_VARIANT_RESET  0x12u
#define UB_CSR_VARIANT_PRODUCT_X8_VL2  1u
#define UB_CSR_MODULE_PRODUCT_X8_VL2  "ub_csr_product_x8_vl2"
#define UB_VARIANT_PRODUCT_X8_VL2_NUM_LANES  8u
#define UB_VARIANT_PRODUCT_X8_VL2_NUM_VL  2u
#define UB_VARIANT_PRODUCT_X8_VL2_SCR_PLACEHOLDER  1u
#define UB_VARIANT_PRODUCT_X8_VL2_PARAM_VARIANT_RESET  0x12u

typedef struct {
    const char *tag;
    uint32_t num_lanes;
    uint32_t num_vl;
    uint32_t scr_placeholder;
    uint32_t param_variant_reset;
} ub_csr_variant_t;

static const ub_csr_variant_t UB_CSR_VARIANTS[] = {
    {"product_x4_vl2", 4u, 2u, 1u, 0x12u},
    {"product_x8_vl2", 8u, 2u, 1u, 0x12u},
};
#define UB_CSR_VARIANT_COUNT  2u

static inline uint32_t ub_fld_get(uint32_t word, uint32_t mask, unsigned shift)
{
    return (word & mask) >> shift;
}

static inline uint32_t ub_fld_insert(uint32_t word, uint32_t mask, unsigned shift, uint32_t value)
{
    return (word & ~mask) | ((value << shift) & mask);
}

static inline uint32_t ub_ctrl_port_rst_get(uint32_t word)
{
    return ub_fld_get(word, UB_CTRL_PORT_RST_MASK, UB_CTRL_PORT_RST_SHIFT);
}

static inline uint32_t ub_ctrl_port_rst_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CTRL_PORT_RST_MASK, UB_CTRL_PORT_RST_SHIFT, value);
}

static inline uint32_t ub_ctrl_lmsm_start_get(uint32_t word)
{
    return ub_fld_get(word, UB_CTRL_LMSM_START_MASK, UB_CTRL_LMSM_START_SHIFT);
}

static inline uint32_t ub_ctrl_lmsm_start_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CTRL_LMSM_START_MASK, UB_CTRL_LMSM_START_SHIFT, value);
}

static inline uint32_t ub_ctrl_irq_en_get(uint32_t word)
{
    return ub_fld_get(word, UB_CTRL_IRQ_EN_MASK, UB_CTRL_IRQ_EN_SHIFT);
}

static inline uint32_t ub_ctrl_irq_en_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CTRL_IRQ_EN_MASK, UB_CTRL_IRQ_EN_SHIFT, value);
}

static inline uint32_t ub_status_link_up_get(uint32_t word)
{
    return ub_fld_get(word, UB_STATUS_LINK_UP_MASK, UB_STATUS_LINK_UP_SHIFT);
}

static inline uint32_t ub_status_link_ready_get(uint32_t word)
{
    return ub_fld_get(word, UB_STATUS_LINK_READY_MASK, UB_STATUS_LINK_READY_SHIFT);
}

static inline uint32_t ub_status_dll_status_up_get(uint32_t word)
{
    return ub_fld_get(word, UB_STATUS_DLL_STATUS_UP_MASK, UB_STATUS_DLL_STATUS_UP_SHIFT);
}

static inline uint32_t ub_status_lmsm_st_get(uint32_t word)
{
    return ub_fld_get(word, UB_STATUS_LMSM_ST_MASK, UB_STATUS_LMSM_ST_SHIFT);
}

static inline uint32_t ub_status_dll_sm_st_get(uint32_t word)
{
    return ub_fld_get(word, UB_STATUS_DLL_SM_ST_MASK, UB_STATUS_DLL_SM_ST_SHIFT);
}

static inline uint32_t ub_status_retry_req_st_get(uint32_t word)
{
    return ub_fld_get(word, UB_STATUS_RETRY_REQ_ST_MASK, UB_STATUS_RETRY_REQ_ST_SHIFT);
}

static inline uint32_t ub_status_retry_ack_st_get(uint32_t word)
{
    return ub_fld_get(word, UB_STATUS_RETRY_ACK_ST_MASK, UB_STATUS_RETRY_ACK_ST_SHIFT);
}

static inline uint32_t ub_irq_status_fec_uncorr_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_STATUS_FEC_UNCORR_MASK, UB_IRQ_STATUS_FEC_UNCORR_SHIFT);
}

static inline uint32_t ub_irq_status_fec_uncorr_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_STATUS_FEC_UNCORR_MASK, UB_IRQ_STATUS_FEC_UNCORR_SHIFT, value);
}

static inline uint32_t ub_irq_status_crc_fail_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_STATUS_CRC_FAIL_MASK, UB_IRQ_STATUS_CRC_FAIL_SHIFT);
}

static inline uint32_t ub_irq_status_crc_fail_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_STATUS_CRC_FAIL_MASK, UB_IRQ_STATUS_CRC_FAIL_SHIFT, value);
}

static inline uint32_t ub_irq_status_retry_err_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_STATUS_RETRY_ERR_MASK, UB_IRQ_STATUS_RETRY_ERR_SHIFT);
}

static inline uint32_t ub_irq_status_retry_err_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_STATUS_RETRY_ERR_MASK, UB_IRQ_STATUS_RETRY_ERR_SHIFT, value);
}

static inline uint32_t ub_irq_status_crd_proto_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_STATUS_CRD_PROTO_MASK, UB_IRQ_STATUS_CRD_PROTO_SHIFT);
}

static inline uint32_t ub_irq_status_crd_proto_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_STATUS_CRD_PROTO_MASK, UB_IRQ_STATUS_CRD_PROTO_SHIFT, value);
}

static inline uint32_t ub_irq_status_train_fail_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_STATUS_TRAIN_FAIL_MASK, UB_IRQ_STATUS_TRAIN_FAIL_SHIFT);
}

static inline uint32_t ub_irq_status_train_fail_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_STATUS_TRAIN_FAIL_MASK, UB_IRQ_STATUS_TRAIN_FAIL_SHIFT, value);
}

static inline uint32_t ub_irq_status_bad_vl_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_STATUS_BAD_VL_MASK, UB_IRQ_STATUS_BAD_VL_SHIFT);
}

static inline uint32_t ub_irq_status_bad_vl_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_STATUS_BAD_VL_MASK, UB_IRQ_STATUS_BAD_VL_SHIFT, value);
}

static inline uint32_t ub_irq_status_crd_uf_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_STATUS_CRD_UF_MASK, UB_IRQ_STATUS_CRD_UF_SHIFT);
}

static inline uint32_t ub_irq_status_crd_uf_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_STATUS_CRD_UF_MASK, UB_IRQ_STATUS_CRD_UF_SHIFT, value);
}

static inline uint32_t ub_irq_mask_mask_get(uint32_t word)
{
    return ub_fld_get(word, UB_IRQ_MASK_MASK_MASK, UB_IRQ_MASK_MASK_SHIFT);
}

static inline uint32_t ub_irq_mask_mask_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_IRQ_MASK_MASK_MASK, UB_IRQ_MASK_MASK_SHIFT, value);
}

static inline uint32_t ub_port_cna_cna_get(uint32_t word)
{
    return ub_fld_get(word, UB_PORT_CNA_CNA_MASK, UB_PORT_CNA_CNA_SHIFT);
}

static inline uint32_t ub_port_cna_cna_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_PORT_CNA_CNA_MASK, UB_PORT_CNA_CNA_SHIFT, value);
}

static inline uint32_t ub_param_phy_phy_mode_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_PHY_PHY_MODE_MASK, UB_PARAM_PHY_PHY_MODE_SHIFT);
}

static inline uint32_t ub_param_phy_data_rate_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_PHY_DATA_RATE_MASK, UB_PARAM_PHY_DATA_RATE_SHIFT);
}

static inline uint32_t ub_param_phy_num_lanes_tx_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_PHY_NUM_LANES_TX_MASK, UB_PARAM_PHY_NUM_LANES_TX_SHIFT);
}

static inline uint32_t ub_param_phy_num_lanes_rx_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_PHY_NUM_LANES_RX_MASK, UB_PARAM_PHY_NUM_LANES_RX_SHIFT);
}

static inline uint32_t ub_param_phy_pma_w_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_PHY_PMA_W_MASK, UB_PARAM_PHY_PMA_W_SHIFT);
}

static inline uint32_t ub_param_phy_allow_asym_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_PHY_ALLOW_ASYM_MASK, UB_PARAM_PHY_ALLOW_ASYM_SHIFT);
}

static inline uint32_t ub_param_fec_fec_mode_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_FEC_FEC_MODE_MASK, UB_PARAM_FEC_FEC_MODE_SHIFT);
}

static inline uint32_t ub_param_fec_codec_num_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_FEC_CODEC_NUM_MASK, UB_PARAM_FEC_CODEC_NUM_SHIFT);
}

static inline uint32_t ub_param_dll_num_vl_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_DLL_NUM_VL_MASK, UB_PARAM_DLL_NUM_VL_SHIFT);
}

static inline uint32_t ub_param_dll_flow_ctrl_size_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_DLL_FLOW_CTRL_SIZE_MASK, UB_PARAM_DLL_FLOW_CTRL_SIZE_SHIFT);
}

static inline uint32_t ub_param_dll_ack_grain_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_DLL_ACK_GRAIN_MASK, UB_PARAM_DLL_ACK_GRAIN_SHIFT);
}

static inline uint32_t ub_param_dll_credit_excl_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_DLL_CREDIT_EXCL_MASK, UB_PARAM_DLL_CREDIT_EXCL_SHIFT);
}

static inline uint32_t ub_param_retry_retry_buf_depth_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_RETRY_RETRY_BUF_DEPTH_MASK, UB_PARAM_RETRY_RETRY_BUF_DEPTH_SHIFT);
}

static inline uint32_t ub_param_retry_num_retry_th_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_RETRY_NUM_RETRY_TH_MASK, UB_PARAM_RETRY_NUM_RETRY_TH_SHIFT);
}

static inline uint32_t ub_param_retry_num_phy_reinit_th_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_RETRY_NUM_PHY_REINIT_TH_MASK, UB_PARAM_RETRY_NUM_PHY_REINIT_TH_SHIFT);
}

static inline uint32_t ub_param_crd_init_crd_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_CRD_INIT_CRD_MASK, UB_PARAM_CRD_INIT_CRD_SHIFT);
}

static inline uint32_t ub_param_crd_crd_bp_th_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_CRD_CRD_BP_TH_MASK, UB_PARAM_CRD_CRD_BP_TH_SHIFT);
}

static inline uint32_t ub_param_init_feature_feature_id_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_INIT_FEATURE_FEATURE_ID_MASK, UB_PARAM_INIT_FEATURE_FEATURE_ID_SHIFT);
}

static inline uint32_t ub_param_init_feature_rxbuf_vl_share_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_INIT_FEATURE_RXBUF_VL_SHARE_MASK, UB_PARAM_INIT_FEATURE_RXBUF_VL_SHARE_SHIFT);
}

static inline uint32_t ub_param_init_feature_vl_enable_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_INIT_FEATURE_VL_ENABLE_MASK, UB_PARAM_INIT_FEATURE_VL_ENABLE_SHIFT);
}

static inline uint32_t ub_param_init_vl_vl_enable_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_INIT_VL_VL_ENABLE_MASK, UB_PARAM_INIT_VL_VL_ENABLE_SHIFT);
}

static inline uint32_t ub_param_variant_num_vl_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_VARIANT_NUM_VL_MASK, UB_PARAM_VARIANT_NUM_VL_SHIFT);
}

static inline uint32_t ub_param_variant_scr_placeholder_get(uint32_t word)
{
    return ub_fld_get(word, UB_PARAM_VARIANT_SCR_PLACEHOLDER_MASK, UB_PARAM_VARIANT_SCR_PLACEHOLDER_SHIFT);
}

static inline uint32_t ub_cnt_fec_uncorr_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_FEC_UNCORR_COUNT_MASK, UB_CNT_FEC_UNCORR_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_crc_fail_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CRC_FAIL_COUNT_MASK, UB_CNT_CRC_FAIL_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_retry_req_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_RETRY_REQ_COUNT_MASK, UB_CNT_RETRY_REQ_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_retry_to_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_RETRY_TO_COUNT_MASK, UB_CNT_RETRY_TO_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_crd_of_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CRD_OF_COUNT_MASK, UB_CNT_CRD_OF_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_crd_to_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CRD_TO_COUNT_MASK, UB_CNT_CRD_TO_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_train_to_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_TRAIN_TO_COUNT_MASK, UB_CNT_TRAIN_TO_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_bad_vl_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_BAD_VL_COUNT_MASK, UB_CNT_BAD_VL_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_crd_uf_count_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CRD_UF_COUNT_MASK, UB_CNT_CRD_UF_COUNT_SHIFT);
}

static inline uint32_t ub_cnt_clr_fec_uncorr_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_FEC_UNCORR_MASK, UB_CNT_CLR_FEC_UNCORR_SHIFT);
}

static inline uint32_t ub_cnt_clr_fec_uncorr_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_FEC_UNCORR_MASK, UB_CNT_CLR_FEC_UNCORR_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_crc_fail_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_CRC_FAIL_MASK, UB_CNT_CLR_CRC_FAIL_SHIFT);
}

static inline uint32_t ub_cnt_clr_crc_fail_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_CRC_FAIL_MASK, UB_CNT_CLR_CRC_FAIL_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_retry_req_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_RETRY_REQ_MASK, UB_CNT_CLR_RETRY_REQ_SHIFT);
}

static inline uint32_t ub_cnt_clr_retry_req_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_RETRY_REQ_MASK, UB_CNT_CLR_RETRY_REQ_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_retry_to_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_RETRY_TO_MASK, UB_CNT_CLR_RETRY_TO_SHIFT);
}

static inline uint32_t ub_cnt_clr_retry_to_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_RETRY_TO_MASK, UB_CNT_CLR_RETRY_TO_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_crd_of_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_CRD_OF_MASK, UB_CNT_CLR_CRD_OF_SHIFT);
}

static inline uint32_t ub_cnt_clr_crd_of_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_CRD_OF_MASK, UB_CNT_CLR_CRD_OF_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_crd_to_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_CRD_TO_MASK, UB_CNT_CLR_CRD_TO_SHIFT);
}

static inline uint32_t ub_cnt_clr_crd_to_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_CRD_TO_MASK, UB_CNT_CLR_CRD_TO_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_train_to_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_TRAIN_TO_MASK, UB_CNT_CLR_TRAIN_TO_SHIFT);
}

static inline uint32_t ub_cnt_clr_train_to_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_TRAIN_TO_MASK, UB_CNT_CLR_TRAIN_TO_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_bad_vl_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_BAD_VL_MASK, UB_CNT_CLR_BAD_VL_SHIFT);
}

static inline uint32_t ub_cnt_clr_bad_vl_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_BAD_VL_MASK, UB_CNT_CLR_BAD_VL_SHIFT, value);
}

static inline uint32_t ub_cnt_clr_crd_uf_get(uint32_t word)
{
    return ub_fld_get(word, UB_CNT_CLR_CRD_UF_MASK, UB_CNT_CLR_CRD_UF_SHIFT);
}

static inline uint32_t ub_cnt_clr_crd_uf_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CNT_CLR_CRD_UF_MASK, UB_CNT_CLR_CRD_UF_SHIFT, value);
}

static inline uint32_t ub_lmsm_tmr_scale_scale_get(uint32_t word)
{
    return ub_fld_get(word, UB_LMSM_TMR_SCALE_SCALE_MASK, UB_LMSM_TMR_SCALE_SCALE_SHIFT);
}

static inline uint32_t ub_lmsm_tmr_scale_scale_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_LMSM_TMR_SCALE_SCALE_MASK, UB_LMSM_TMR_SCALE_SCALE_SHIFT, value);
}

static inline uint32_t ub_crd_to_dis_dis_get(uint32_t word)
{
    return ub_fld_get(word, UB_CRD_TO_DIS_DIS_MASK, UB_CRD_TO_DIS_DIS_SHIFT);
}

static inline uint32_t ub_crd_to_dis_dis_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_CRD_TO_DIS_DIS_MASK, UB_CRD_TO_DIS_DIS_SHIFT, value);
}

static inline uint32_t ub_pcs_tx_test_am_ivl_scale_get(uint32_t word)
{
    return ub_fld_get(word, UB_PCS_TX_TEST_AM_IVL_SCALE_MASK, UB_PCS_TX_TEST_AM_IVL_SCALE_SHIFT);
}

static inline uint32_t ub_pcs_tx_test_am_ivl_scale_insert(uint32_t word, uint32_t value)
{
    return ub_fld_insert(word, UB_PCS_TX_TEST_AM_IVL_SCALE_MASK, UB_PCS_TX_TEST_AM_IVL_SCALE_SHIFT, value);
}

#ifdef __cplusplus
}
#endif

#endif /* UB_REGS_H */
