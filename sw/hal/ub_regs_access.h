/* GENERATED — edit docs/regmap/regmap.yaml */
#ifndef UB_REGS_ACCESS_H
#define UB_REGS_ACCESS_H

#include "ub_regs.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef uint32_t (*ub_csr_read_fn)(void *ctx, uint16_t addr);
typedef void (*ub_csr_write_fn)(void *ctx, uint16_t addr, uint32_t data);

typedef struct ub_csr_bus {
    ub_csr_read_fn read;
    ub_csr_write_fn write;
    void *ctx;
} ub_csr_bus_t;

uint32_t ub_reg_read(const ub_csr_bus_t *bus, uint16_t addr);
void ub_reg_write(const ub_csr_bus_t *bus, uint16_t addr, uint32_t data);

/* Full-word only (SPEC §3.2.3). Unaligned addresses are the bus's csr_err path. */

uint32_t ub_ctrl_read(const ub_csr_bus_t *bus);
void ub_ctrl_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_status_read(const ub_csr_bus_t *bus);
uint32_t ub_irq_status_read(const ub_csr_bus_t *bus);
void ub_irq_status_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_irq_mask_read(const ub_csr_bus_t *bus);
void ub_irq_mask_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_port_cna_read(const ub_csr_bus_t *bus);
void ub_port_cna_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_param_phy_read(const ub_csr_bus_t *bus);
uint32_t ub_param_fec_read(const ub_csr_bus_t *bus);
uint32_t ub_param_dll_read(const ub_csr_bus_t *bus);
uint32_t ub_param_retry_read(const ub_csr_bus_t *bus);
uint32_t ub_param_crd_read(const ub_csr_bus_t *bus);
uint32_t ub_param_init_feature_read(const ub_csr_bus_t *bus);
uint32_t ub_param_init_vl_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_fec_uncorr_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_crc_fail_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_retry_req_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_retry_to_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_crd_of_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_crd_to_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_train_to_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_bad_vl_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_crd_uf_read(const ub_csr_bus_t *bus);
uint32_t ub_cnt_clr_read(const ub_csr_bus_t *bus);
void ub_cnt_clr_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_lmsm_tmr_scale_read(const ub_csr_bus_t *bus);
void ub_lmsm_tmr_scale_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_crd_to_dis_read(const ub_csr_bus_t *bus);
void ub_crd_to_dis_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_pcs_tx_test_read(const ub_csr_bus_t *bus);
void ub_pcs_tx_test_write(const ub_csr_bus_t *bus, uint32_t data);
uint32_t ub_appd_port_basic_read(const ub_csr_bus_t *bus);
uint32_t ub_appd_link_cap_read(const ub_csr_bus_t *bus);
uint32_t ub_appd_link_log_read(const ub_csr_bus_t *bus);
uint32_t ub_appd_lmsm_st_read(const ub_csr_bus_t *bus);
uint32_t ub_appd_port_err_read(const ub_csr_bus_t *bus);

#ifdef __cplusplus
}
#endif

#endif /* UB_REGS_ACCESS_H */
