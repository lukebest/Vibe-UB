/* GENERATED — edit docs/regmap/regmap.yaml */
#include "ub_regs_access.h"

uint32_t ub_reg_read(const ub_csr_bus_t *bus, uint16_t addr)
{
    return bus->read(bus->ctx, addr);
}

void ub_reg_write(const ub_csr_bus_t *bus, uint16_t addr, uint32_t data)
{
    bus->write(bus->ctx, addr, data);
}

uint32_t ub_ctrl_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CTRL);
}

void ub_ctrl_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_CTRL, data);
}

uint32_t ub_status_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_STATUS);
}

uint32_t ub_irq_status_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_IRQ_STATUS);
}

void ub_irq_status_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_IRQ_STATUS, data);
}

uint32_t ub_irq_mask_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_IRQ_MASK);
}

void ub_irq_mask_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_IRQ_MASK, data);
}

uint32_t ub_port_cna_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PORT_CNA);
}

void ub_port_cna_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_PORT_CNA, data);
}

uint32_t ub_param_phy_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PARAM_PHY);
}

uint32_t ub_param_fec_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PARAM_FEC);
}

uint32_t ub_param_dll_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PARAM_DLL);
}

uint32_t ub_param_retry_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PARAM_RETRY);
}

uint32_t ub_param_crd_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PARAM_CRD);
}

uint32_t ub_param_init_feature_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PARAM_INIT_FEATURE);
}

uint32_t ub_param_init_vl_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PARAM_INIT_VL);
}

uint32_t ub_cnt_fec_uncorr_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_FEC_UNCORR);
}

uint32_t ub_cnt_crc_fail_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_CRC_FAIL);
}

uint32_t ub_cnt_retry_req_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_RETRY_REQ);
}

uint32_t ub_cnt_retry_to_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_RETRY_TO);
}

uint32_t ub_cnt_crd_of_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_CRD_OF);
}

uint32_t ub_cnt_crd_to_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_CRD_TO);
}

uint32_t ub_cnt_train_to_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_TRAIN_TO);
}

uint32_t ub_cnt_bad_vl_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_BAD_VL);
}

uint32_t ub_cnt_crd_uf_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_CRD_UF);
}

uint32_t ub_cnt_clr_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CNT_CLR);
}

void ub_cnt_clr_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_CNT_CLR, data);
}

uint32_t ub_lmsm_tmr_scale_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_LMSM_TMR_SCALE);
}

void ub_lmsm_tmr_scale_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_LMSM_TMR_SCALE, data);
}

uint32_t ub_crd_to_dis_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_CRD_TO_DIS);
}

void ub_crd_to_dis_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_CRD_TO_DIS, data);
}

uint32_t ub_pcs_tx_test_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_PCS_TX_TEST);
}

void ub_pcs_tx_test_write(const ub_csr_bus_t *bus, uint32_t data)
{
    ub_reg_write(bus, (uint16_t)UB_REG_PCS_TX_TEST, data);
}

uint32_t ub_appd_port_basic_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_APPD_PORT_BASIC);
}

uint32_t ub_appd_link_cap_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_APPD_LINK_CAP);
}

uint32_t ub_appd_link_log_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_APPD_LINK_LOG);
}

uint32_t ub_appd_lmsm_st_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_APPD_LMSM_ST);
}

uint32_t ub_appd_port_err_read(const ub_csr_bus_t *bus)
{
    return ub_reg_read(bus, (uint16_t)UB_REG_APPD_PORT_ERR);
}
