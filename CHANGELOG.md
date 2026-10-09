# Changelog

## Unreleased

### Added

- M1 RTL leaf batch 1 (pyCircuit, stacked on the architecture SPEC): whitelist `ub_rst_sync`; generated `ub_pyc_rst_adapt`, `ub_pcs_scrambler` / `ub_pcs_descrambler`, `ub_pcs_lane_dist` / `ub_pcs_lane_dedist`, `ub_dll_bcrc` / `ub_dll_bcrc_check`. PRODUCT only (`TEST_HOOKS=0`; SPEC §10 lists no hooks on these leaves).
- `docs/SPEC.md`：M1 功能规格（范围、模块划分、接口、时钟复位、状态机、异常、参数、测试钩子、两套 `TEST_HOOKS` 网表）。
- `docs/REGMAP.md`：M1 寄存器表（CTRL/STATUS/PARAM/ERR/TEST + App. D 端口子集镜像）。
- `docs/CODING_STYLE.md`：pyc4.0 生成、同步复位、白名单单元、禁止 force/deposit、lint/waiver、两套网表门禁。

### Changed

- 架构关闭若干待定项：M1 单时钟 80.57 MHz、`rst_n` 封装、CSR 整字/1 拍/未映射 `csr_err`、非法 VL 丢包、信用下溢计数+irq（TB assert）、`irq` 高有效默认全屏蔽、预编码默认关、信用钩子仅 VL0、`tb_obs_lmsm_st` 仅顶层编码。
- LTB/CLTB 字段口（SPEC §3.3.4）；去掉 `pma_rx_ready` / `pcs2dll_ready`（RX valid-only）；计数 RO + `CNT_CLR`；`PORT_RST` 16 拍脉冲及复位范围；`tb_inj_crd_cells` 每拍 mux；TEST 窗 `tb_test_mode=0` 时已映射且 `csr_err=0`；`ub_rst_sync` 2 级；`CRD_UF` 具名 waiver。
- App. D 镜像迁址：`APPD_LMSM_ST` `0x2400`→`0x1E00`；`APPD_PORT_ERR` `0x2500`→`0x1F00`。
- 关闭 Q4 剩余项：TX Lane_ID 由 PCS 按 `lmsm2pcs_lane_id_mode` / `lmsm2pcs_lane_id_base` / `lmsm2pcs_lane_id_map` 逐 lane 填写后再算 CRC；LMB 字段在每帧 LMB 起始锁存，无多拍 valid 稳定要求。
