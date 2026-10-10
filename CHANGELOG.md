# Changelog

## Unreleased

### Added

- `docs/SPEC.md`：M1 功能规格（范围、模块划分、接口、时钟复位、状态机、异常、参数、测试钩子、两套 `TEST_HOOKS` 网表）。
- `docs/REGMAP.md`：M1 寄存器表（CTRL/STATUS/PARAM/ERR/TEST + App. D 端口子集镜像）。
- `docs/CODING_STYLE.md`：pyc4.0 生成、同步复位、白名单单元、禁止 force/deposit、lint/waiver、两套网表门禁。

### Changed

- 架构关闭若干待定项：M1 单时钟 80.57 MHz、`rst_n` 封装、CSR 整字/1 拍/未映射 `csr_err`、非法 VL 丢包、信用下溢计数+irq（TB assert）、`irq` 高有效默认全屏蔽、预编码默认关、信用钩子仅 VL0、`tb_obs_lmsm_st` 仅顶层编码。
- LTB/CLTB 字段口（SPEC §3.3.4）；去掉 `pma_rx_ready` / `pcs2dll_ready`（RX valid-only）；计数 RO + `CNT_CLR`；`PORT_RST` 16 拍脉冲及复位范围；`tb_inj_crd_cells` 每拍 mux；TEST 窗 `tb_test_mode=0` 时已映射且 `csr_err=0`；`ub_rst_sync` 2 级；`CRD_UF` 具名 waiver。
- App. D 镜像迁址：`APPD_LMSM_ST` `0x2400`→`0x1E00`；`APPD_PORT_ERR` `0x2500`→`0x1F00`。
- 关闭 Q4 剩余项：TX Lane_ID 由 PCS 按 `lmsm2pcs_lane_id_mode` / `lmsm2pcs_lane_id_base` / `lmsm2pcs_lane_id_map` 逐 lane 填写后再算 CRC；LMB 字段在每帧 LMB 起始锁存，无多拍 valid 稳定要求。
- `lmsm2pcs_lane_id_mode` 编码 3 为保留：LMSM 不驱动（TB assert）；PCS 与 2（NULL）同分支解码，无需 waiver。
- 关闭加扰/BCRC/`ERROR_FLAG`：种子源为 `AMCTL.LID`（叶子口 `amctl_lid[3:0]`）；PRBS23 状态 23 bit、每 lane 32-bit 通路（抽头与 LID→种子映射仍待定）；BCRC CRC30 `30'h15A94AD5`、初值全 1、余数不取反、每字节 MSB 先、`{rsvd, ERROR_FLAG, CRC30}`；TX `ERROR_FLAG` 恒 0（无 ECC、无 `nw_tx_err`），RX 用 `nw_rx_err`；PMA 字符号 0 在 LSB。
- 模块名对齐 CODING_STYLE §5：`pcs_fec_enc`→`ub_pcs_fec_enc`，`pcs_fec_dec`→`ub_pcs_fec_dec`，`pcs_scrambler`→`ub_pcs_scrambler`，`pcs_descrambler`→`ub_pcs_descrambler`，`pcs_lane_dist`→`ub_pcs_lane_dist`，`pcs_lane_dedist`→`ub_pcs_lane_dedist`，`pcs_amctl_tx`→`ub_pcs_amctl_tx`，`pcs_amctl_rx`→`ub_pcs_amctl_rx`，`pcs_deskew`→`ub_pcs_deskew`，`segmenter`→`ub_dll_segmenter`，`reassembler`→`ub_dll_reassembler`，BCRC TX/RX→`ub_dll_bcrc` / `ub_dll_bcrc_check`，credit/VL/retry→`ub_dll_credit` / `ub_dll_vl` / `ub_dll_retry`。
- `LMSM_CTRL.START` 更名为 `CTRL.LMSM_START`（REGMAP `0x0000` bit1）。关闭 `STATUS.RETRY_REQ_ST` / `RETRY_ACK_ST` 与 `PARAM_PHY.NUM_LANES_{TX,RX}` 编码（二进制 1/2/4/8）；保留值 RTL 不产出、TB assert。
- §13 冻结推进：关闭 RETRY_REQ_SM / RETRY_ACK_SM 转移（UB-DL §4.7.3.3–§4.7.3.5）、`MAX_DP_FLITS=512`（§4.3.2.1）、AMCTL 与 `pma_*_data` 同流（UB-PHY §3.2.4/§3.2.5）、bypass 时 `fec_ok=1`/`fec_uncorr=0`（§4.7.1）、PCS 忽略 `dll2pcs_sop/eop`（§3.2.2.1）、DR0 下 RXEQ 48 ms / Equalization 按该节超时且 DR1+ FFE 不做（§3.4.2.9、§3.4.3.3）。其余未裁定项改列为决策表（已查节号、建议、影响、可否非目标）。`tb_obs_dll_sm_st` 编码已在 §10.3 关闭。waiver 节改为 §13.1。
- §13 续：写入规范已裁定项——LTB Type 字节（§3.4.1.1）、Lane_ID/Link_ID 空值 `8'hFF`、`data_rate_support_2[7]`=Change_Speed、`LinkUp`/`LinkReady` 赋值点、LMSM 官方超时、`Send_NullBlock` 8/16 Null Block、`core_clk` 须在同步释放期间跑、`APPD_LMSM_ST` 为 D.6.21 切片窗（叶子只出顶层 `lmsm_st[4:0]`）。工艺节点标「未知，待 Luke；影响库/SDC/面积；非规范」。决策表新增：`LFSR_INIT`、Retrain 期间 `LinkUp`、Null Block 计数口、`cfg_*` CSR 来源、`Change_Speed` 空闲停留。不改已定端口/寄存器（`amctl_lid` 8=NULL、`lane_id_mode` 2=NULL、`tb_obs_lmsm_st` 仅顶层、`APPD_LMSM_ST` 仍 `0x1E00`、§10.2 观察口）。
