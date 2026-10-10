# Changelog

## Unreleased

### Added

- M1 RTL leaf batch 1 (pyCircuit): whitelist `ub_rst_sync`; generated `ub_pyc_rst_adapt`, `ub_pcs_scrambler` / `ub_pcs_descrambler`, `ub_pcs_lane_dist` / `ub_pcs_lane_dedist`, `ub_dll_bcrc` / `ub_dll_bcrc_check`. PRODUCT at `rtl/<block>/<module>.v` and HOOKS at `rtl/<block>/hooks/<module>.v` (SPEC §2.2 / CODING_STYLE §5 / §11). SPEC §10 lists no hook ports on these leaves (HOOKS ≡ PRODUCT). Whitelist `ub_rst_sync.sv` has no hooks copy.
- `TOOLCHAIN.lock` + `tb/` uvm-python 骨架、golden-model 接口、双网表自检入口（叠在 M1 SPEC 上；不改 `rtl/` / SPEC 类文档）。
- TB 模型按 CODING_STYLE §5 命名：`ub_dll_bcrc` 已按 SPEC §2.6 写全；`ub_pcs_scrambler` 已按已定项实现，抽头与 `AMCTL.LID`→种子为必填参数（SPEC §13，无默认）；`ub_pcs_lane_dist` 已实现。无 LMB/LTB golden。
- `tb/vibe_uvm/ub_csr_map.py` + harness：`CNT_CLR` `0x0224` bit0–8（含 `CNT_CRD_UF`）；`APPD_LMSM_ST` `0x1E00`；`APPD_PORT_ERR` `0x1F00`；TEST 窗按 SPEC §3.2.3 / §10 / §11、REGMAP §2.4。`CTRL.LMSM_START`、`RETRY_*_ST` 与 `NUM_LANES_*` 合法编码及保留值 TB assert。
- `docs/SPEC.md`：M1 功能规格（范围、模块划分、接口、时钟复位、状态机、异常、参数、测试钩子、两套 `TEST_HOOKS` 网表）。
- `docs/REGMAP.md`：M1 寄存器表（CTRL/STATUS/PARAM/ERR/TEST + App. D 端口子集镜像）。
- `docs/CODING_STYLE.md`：pyc4.0 生成、同步复位、白名单单元、禁止 force/deposit、lint/waiver、两套网表门禁。
- `docs/TEAM.md`：角色表、所有权、角色接口、工具守门与豁免、人工评审重点（D17）。
- `docs/PROCESS.md`：每模块节拍、工具流水线、REGMAP 单一来源、规则库每周版本、每周复盘指标、PHY 先行、过渡安排（D17）。
- `docs/rules/`：architect / design / verification / backend 规则库骨架（v0.1）。
- `docs/DECISIONS.md` D17：团队分工与流程（Luke Liu via Firstmate，2026-10-10 16:48 Asia/Shanghai）。
- `docs/DECISIONS.md` D18：全层级范围，作为完整 UB 控制器（Luke Liu via Firstmate，2026-10-10 17:04 Asia/Shanghai）；D18 取代 D2 的分阶段范围。
- `docs/DECISIONS.md` D19：三线并行与新增角色（Luke Liu via Firstmate，2026-10-10 17:22 Asia/Shanghai）。

### Changed

- `docs/SPEC.md` §2.2：pycc 按参数集展开固定网表（`<leaf>_<tag>` 命名；占位变体 `_placeholder`）。
- 架构关闭若干待定项：M1 单时钟 80.57 MHz、`rst_n` 封装、CSR 整字/1 拍/未映射 `csr_err`、非法 VL 丢包、信用下溢计数+irq（TB assert）、`irq` 高有效默认全屏蔽、预编码默认关、信用钩子仅 VL0、`tb_obs_lmsm_st` 仅顶层编码。
- LTB/CLTB 字段口（SPEC §3.3.4）；去掉 `pma_rx_ready` / `pcs2dll_ready`（RX valid-only）；计数 RO + `CNT_CLR`；`PORT_RST` 16 拍脉冲及复位范围；`tb_inj_crd_cells` 每拍 mux；TEST 窗 `tb_test_mode=0` 时已映射且 `csr_err=0`；`ub_rst_sync` 2 级；`CRD_UF` 具名 waiver。
- App. D 镜像迁址：`APPD_LMSM_ST` `0x2400`→`0x1E00`；`APPD_PORT_ERR` `0x2500`→`0x1F00`。
- 关闭 Q4 剩余项：TX Lane_ID 由 PCS 按 `lmsm2pcs_lane_id_mode` / `lmsm2pcs_lane_id_base` / `lmsm2pcs_lane_id_map` 逐 lane 填写后再算 CRC；LMB 字段在每帧 LMB 起始锁存，无多拍 valid 稳定要求。
- `lmsm2pcs_lane_id_mode` 编码 3 为保留：LMSM 不驱动（TB assert）；PCS 与 2（NULL）同分支解码，无需 waiver。
- 关闭加扰/BCRC/`ERROR_FLAG`：种子源为 `AMCTL.LID`（叶子口 `amctl_lid[3:0]`）；PRBS23 状态 23 bit、每 lane 32-bit 通路（抽头与 LID→种子映射仍待定）；BCRC CRC30 `30'h15A94AD5`、初值全 1、余数不取反、每字节 MSB 先、`{rsvd, ERROR_FLAG, CRC30}`；TX `ERROR_FLAG` 恒 0（无 ECC、无 `nw_tx_err`），RX 用 `nw_rx_err`；PMA 字符号 0 在 LSB。
- 模块名对齐 CODING_STYLE §5：`pcs_fec_enc`→`ub_pcs_fec_enc`，`pcs_fec_dec`→`ub_pcs_fec_dec`，`pcs_scrambler`→`ub_pcs_scrambler`，`pcs_descrambler`→`ub_pcs_descrambler`，`pcs_lane_dist`→`ub_pcs_lane_dist`，`pcs_lane_dedist`→`ub_pcs_lane_dedist`，`pcs_amctl_tx`→`ub_pcs_amctl_tx`，`pcs_amctl_rx`→`ub_pcs_amctl_rx`，`pcs_deskew`→`ub_pcs_deskew`，`segmenter`→`ub_dll_segmenter`，`reassembler`→`ub_dll_reassembler`，BCRC TX/RX→`ub_dll_bcrc` / `ub_dll_bcrc_check`，credit/VL/retry→`ub_dll_credit` / `ub_dll_vl` / `ub_dll_retry`。
- `LMSM_CTRL.START` 更名为 `CTRL.LMSM_START`（REGMAP `0x0000` bit1）。关闭 `STATUS.RETRY_REQ_ST` / `RETRY_ACK_ST` 与 `PARAM_PHY.NUM_LANES_{TX,RX}` 编码（二进制 1/2/4/8）；保留值 RTL 不产出、TB assert。
- `docs/TEAM.md`、`docs/PROCESS.md`：按 D18 写全层级范围；PROCESS §6 为「全层级推进」。
- `docs/TEAM.md`、`docs/PROCESS.md`：按 D19 写入三条轨道、轨道所有权，以及「设计-B」/「验证-B」、「设计-C」/「验证-C」新角色。
