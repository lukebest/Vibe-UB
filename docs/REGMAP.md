<!-- GENERATED — edit docs/regmap/regmap.yaml -->
# Vibe-UB M1 寄存器表

| 项 | 值 |
| --- | --- |
| 配套规格 | [SPEC.md](SPEC.md) |
| 规范基线 | UB Base Spec Rev 2.0，附录 D **子集**（见 [SPEC_INDEX.md](SPEC_INDEX.md)） |
| 总线 | [SPEC.md](SPEC.md) §3.2.3：32-bit 整字，无 `csr_wstrb`；16-bit 字节地址，4 字节对齐；读固定 1 拍；写响应下一拍 `csr_rvalid=0` 且 `csr_err` 有效；未映射读 0/`csr_err=1`，写忽略/`csr_err=1` |
| 字节序 | 小端；位 0 为 LSB |

职责与流程见 [TEAM.md](TEAM.md)、[PROCESS.md](PROCESS.md)。

**引用约定：** 不抄录规范字段说明、表或复位表。App. D / Init Block 只给 **节号**。 实现对照官方规范展开位域。本表足够生成头文件与 Python 寄存器模型。

**机器可读列：** `offset_hex,reg_name,field_name,hi,lo,access,reset_hex,description,spec_ref`

- `offset_hex`：相对 M1 CSR 窗口的字节偏移。
- `access`：`RW` / `RO` / `W1C` / `WO`。禁止读清；禁止 RW 写清。粘滞=W1C；计数=RO + `CNT_CLR`。
- `reset_hex`：字段复位。`NA` = 本仓库不抄规范复位，实现时对照 `spec_ref`。
- `spec_ref`：规范节号，或 `proj`（项目本地）。
- 测试寄存器仅当 `tb_test_mode=1` 且 `TEST_HOOKS=1` 时功能生效。 `tb_test_mode=0` 或 PRODUCT：该窗读 0、写忽略、`csr_err=0`（已映射）。 见 SPEC §3.2.3、§11。

---

## 1. 窗口划分

| 窗口 | 字节范围 | 内容 |
| --- | --- | --- |
| CTRL/STATUS | `0x0000`–`0x00FF` | 端口复位、启动训练、链路/DLL 状态、irq |
| PARAM | `0x0100`–`0x01FF` | M1 / spec-max 参数读回 |
| ERR | `0x0200`–`0x02FF` | 错误计数 RO（饱和）+ `CNT_CLR`（WO） |
| TEST | `0x0300`–`0x03FF` | 测试控制：代替 deposit 的缩放/关闭位 |
| APPD_PORT | `0x1000`–`0x1FFF` | App. D 端口子集镜像。相对偏移与规范 PORT0（基址 `0x0002_0000`）对齐，便于日后并入完整配置空间 |

不实现：CFG0_BASIC 设备级、CFG1_*、CFG0_ROUTE_TABLE、热插拔 / 眼图 / QDLWS / 多 DATA_RATE 切片（M1 固定 Data Rate 0）。

---

## 2. 字段表

未实现的保留位读 0、写忽略。多值字段的保留编码（如 `RETRY_REQ_ST` 5–7、 `RETRY_ACK_ST` 2–3、`NUM_LANES_*` 除 1/2/4/8 外）由 RTL **永不产出**；TB assert。

### 2.1 CTRL / STATUS（`0x0000`）

| offset_hex | reg_name | field_name | hi | lo | access | reset_hex | description | spec_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0x0000 | CTRL | PORT_RST | 0 | 0 | WO | 0x0 | 写 1 自清。产生 16 拍 `core_clk` 脉冲，复位 PCS/LMSM/DLL（含 retry）与信用计数。 **不**复位 CSR 配置、计数、IRQ、TEST | proj; SPEC §3.2.3 |
| 0x0000 | CTRL | LMSM_START | 1 | 1 | RW | 0x0 | 软件启动 LMSM 离开 Link_Idle（实现「上层指示」） | proj; UB-PHY §3.4.3.1 |
| 0x0000 | CTRL | IRQ_EN | 2 | 2 | RW | 0x0 | 顶层 `irq` 总使能 | proj |
| 0x0000 | CTRL | RSVD | 31 | 3 | RO | 0x0 | 保留 | proj |
| 0x0004 | STATUS | LINK_UP | 0 | 0 | RO | 0x0 | 与顶层 `link_up` 同 | proj; UB-PHY §3.4.3 |
| 0x0004 | STATUS | LINK_READY | 1 | 1 | RO | 0x0 | 与顶层 `link_ready` 同 | proj; UB-PHY §3.4.3.7 |
| 0x0004 | STATUS | DLL_STATUS_UP | 2 | 2 | RO | 0x0 | 可发 DLLDP | proj; UB-DL §4.2 |
| 0x0004 | STATUS | LMSM_ST | 7 | 3 | RO | 0x0 | 同 `tb_obs_lmsm_st` 编码，见 SPEC §10.3 | proj; UB-PHY §3.4.3 |
| 0x0004 | STATUS | DLL_SM_ST | 9 | 8 | RO | 0x0 | 同 `tb_obs_dll_sm_st` 编码，见 SPEC §10.3 | proj; UB-DL §4.2 |
| 0x0004 | STATUS | RETRY_REQ_ST | 12 | 10 | RO | 0x0 | 0=`NORMAL`，1=`REQ`，2=`WAIT`，3=`RETRAIN`，4=`ERROR`，5–7 保留。RTL 永不产出保留值；TB assert | proj; UB-DL §4.7.3.3 |
| 0x0004 | STATUS | RETRY_ACK_ST | 14 | 13 | RO | 0x0 | 0=`NORMAL`，1=`ACK`，2–3 保留。RTL 永不产出保留值；TB assert | proj; UB-DL §4.7.3.4 |
| 0x0004 | STATUS | RSVD | 31 | 15 | RO | 0x0 | 保留 | proj |
| 0x0008 | IRQ_STATUS | FEC_UNCORR | 0 | 0 | W1C | 0x0 | FEC 不可纠正曾发生 | proj; UB-PHY §3.2.3.5 |
| 0x0008 | IRQ_STATUS | CRC_FAIL | 1 | 1 | W1C | 0x0 | BCRC 失败曾发生 | proj; UB-DL §4.7.2 |
| 0x0008 | IRQ_STATUS | RETRY_ERR | 2 | 2 | W1C | 0x0 | 重传进 ERROR 或超过阈值 | proj; UB-DL §4.8.2 |
| 0x0008 | IRQ_STATUS | CRD_PROTO | 3 | 3 | W1C | 0x0 | 信用协议类错误（溢出/归还超时） | proj; UB-DL §4.8.1 |
| 0x0008 | IRQ_STATUS | TRAIN_FAIL | 4 | 4 | W1C | 0x0 | LMSM 回到 Link_Idle 且训练未成功 | proj; UB-PHY §3.4.3 |
| 0x0008 | IRQ_STATUS | BAD_VL | 5 | 5 | W1C | 0x0 | 未使能 VL 的包曾被丢弃（粘滞） | proj; SPEC §7 |
| 0x0008 | IRQ_STATUS | CRD_UF | 6 | 6 | W1C | 0x0 | 信用下溢（计数减过 0）曾发生（粘滞）。RTL irq 源，不是 RTL assert | proj; SPEC §7 |
| 0x0008 | IRQ_STATUS | RSVD | 31 | 7 | RO | 0x0 | 保留 | proj |
| 0x000C | IRQ_MASK | MASK | 6 | 0 | RW | 0x7F | 对应 IRQ_STATUS[6:0]，1=屏蔽。复位 **全部屏蔽** | proj |
| 0x000C | IRQ_MASK | RSVD | 31 | 7 | RO | 0x0 | 保留 | proj |
| 0x0010 | PORT_CNA | CNA | 31 | 0 | RW | 0x0 | 本地 CNA。软件读/写；**无** `tb_*` 钩子 | proj; App. D.5.5 |

`irq`：高有效电平。`IRQ_EN=1` 且任一未屏蔽 `IRQ_STATUS` 位置位则为 1。 复位后 `IRQ_MASK` 全 1、`IRQ_EN=0`，全部源屏蔽。

### 2.2 PARAM 读回（`0x0100`）

只读，反映编译/协商后的生效值。复位列为 M1 已确认默认（船长确认）， 协商完成后 STATUS 类镜像以 App. D 节为准。

| offset_hex | reg_name | field_name | hi | lo | access | reset_hex | description | spec_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0x0100 | PARAM_PHY | PHY_MODE | 1 | 0 | RO | 0x2 | 1=Mode-1，2=Mode-2。M1=2 | proj; UB-PHY §3.1.2 |
| 0x0100 | PARAM_PHY | DATA_RATE | 5 | 2 | RO | 0x0 | Data Rate 编号。M1=0（2.578125G NRZ） | proj; UB-PHY §3.1.2 |
| 0x0100 | PARAM_PHY | NUM_LANES_TX | 9 | 6 | RO | 0x1 | 二进制 TX lane 数。合法 1/2/4/8，其余保留。RTL 永不产出保留值；TB assert。复位 1 | proj; UB-PHY §3.1.1 |
| 0x0100 | PARAM_PHY | NUM_LANES_RX | 13 | 10 | RO | 0x1 | 二进制 RX lane 数。合法 1/2/4/8，其余保留。RTL 永不产出保留值；TB assert。复位 1；默认等于 TX | proj |
| 0x0100 | PARAM_PHY | PMA_W | 21 | 14 | RO | 0x20 | PMA–PCS 每 lane 位宽，M1=32 | proj |
| 0x0100 | PARAM_PHY | ALLOW_ASYM | 22 | 22 | RO | 0x0 | 1=允许非对称。M1=0 | proj |
| 0x0100 | PARAM_PHY | RSVD | 31 | 23 | RO | 0x0 | 保留 | proj |
| 0x0104 | PARAM_FEC | FEC_MODE | 2 | 0 | RO | 0x2 | 与 LTB `fec_mode_ctrl` 同编码（§3.4.1.1）。复位 T=4 | proj; UB-PHY §3.2.2.1、§3.4.1.1 |
| 0x0104 | PARAM_FEC | CODEC_NUM | 4 | 3 | RO | 0x1 | FEC 交织路数。默认建议 1，**待定** | proj; UB-PHY §3.2.2.3 |
| 0x0104 | PARAM_FEC | RSVD | 31 | 5 | RO | 0x0 | 保留 | proj |
| 0x0108 | PARAM_DLL | NUM_VL | 4 | 0 | RO | 0x2 | 使能 VL 数。M1=2 | proj; UB-DL §4.5.1 |
| 0x0108 | PARAM_DLL | FLOW_CTRL_SIZE | 12 | 5 | RO | 0x1 | cell 对应 flit 数。M1=1 | proj; UB-DL §4.3.3.9 |
| 0x0108 | PARAM_DLL | ACK_GRAIN | 20 | 13 | RO | 0x20 | credit/ACK 粒度（flit 或 cell，见协商）。M1=32 | proj; UB-DL §4.3.3.9、§4.6 |
| 0x0108 | PARAM_DLL | CREDIT_EXCL | 21 | 21 | RO | 0x1 | 1=独占模式 | proj; UB-DL §4.6.1.2 |
| 0x0108 | PARAM_DLL | RSVD | 31 | 22 | RO | 0x0 | 保留 | proj |
| 0x010C | PARAM_RETRY | RETRY_BUF_DEPTH | 15 | 0 | RO | 0x0100 | 重传缓冲深度（flit）。M1=256 | proj; UB-DL §4.7.3.2、§4.3.3.9 |
| 0x010C | PARAM_RETRY | NUM_RETRY_TH | 23 | 16 | RO | 0x0F | **草案** 15 | proj; UB-DL §4.7.3.3 |
| 0x010C | PARAM_RETRY | NUM_PHY_REINIT_TH | 31 | 24 | RO | 0x04 | **草案** 4 | proj; UB-DL §4.7.3.3 |
| 0x0110 | PARAM_CRD | INIT_CRD | 15 | 0 | RO | 0x0280 | 每 VL 初始信用（cell）。M1=640 | proj; UB-DL §4.6.1 |
| 0x0110 | PARAM_CRD | CRD_BP_TH | 31 | 16 | RO | 0x0400 | `CRD_BP_THRESHOLD`，**草案** 1024 | proj; SPEC §10 |
| 0x0114 | PARAM_INIT_FEATURE | FEATURE_ID | 15 | 0 | RO | 0x1 | Init Block 协议版本标识读回 | UB-DL §4.3.3.9 |
| 0x0114 | PARAM_INIT_FEATURE | RXBUF_VL_SHARE | 16 | 16 | RO | 0x0 | 本端是否支持 VL 共享缓冲。M1 独占=0 | UB-DL §4.3.3.9 |
| 0x0114 | PARAM_INIT_FEATURE | VL_ENABLE | 31 | 17 | RO | 0x3 | bit0→VL0。M1 低 2 bit=1。宽度不足 16 VL 时高位置 0，完整 16 bit 见 0x0118 | UB-DL §4.3.3.9、§4.5 |
| 0x0118 | PARAM_INIT_VL | VL_ENABLE | 15 | 0 | RO | 0x0003 | 16-bit VL 使能，M1=VL0+VL1 | UB-DL §4.3.3.9 |
| 0x0118 | PARAM_INIT_VL | RSVD | 31 | 16 | RO | 0x0 | 保留 | proj |

Init Block 其余字段（`DATA_ACK_GRAIN_SIZE`、`CTRL_ACK_GRAIN_SIZE`、 `DATA_CREDIT_GRAIN_SIZE`、`CTRL_CREDIT_GRAIN_SIZE`、`PACKET_MIN_INTERVAL`） 的位打包 **不在本仓库展开**，实现按 UB-DL §4.3.3.9；协商后的只读镜像落在 App. D.6.2.3 窗口（§2.5）。

### 2.3 ERR 计数（`0x0200`）

计数器 **RO**，饱和到全 1。**无读清、无 RW 写清**。写 `CNT_CLR` 对应位 1 清零该计数；`CNT_CLR` 为 WO，写后读为 0（自清）。`PORT_RST` **不**清这些计数。

| offset_hex | reg_name | field_name | hi | lo | access | reset_hex | description | spec_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0x0200 | CNT_FEC_UNCORR | COUNT | 31 | 0 | RO | 0x0 | FEC 不可纠正次数 | proj; UB-PHY §3.2.3.5 |
| 0x0204 | CNT_CRC_FAIL | COUNT | 31 | 0 | RO | 0x0 | BCRC 失败次数 | proj; UB-DL §4.7.2 |
| 0x0208 | CNT_RETRY_REQ | COUNT | 31 | 0 | RO | 0x0 | 进入 RETRY_REQ_SM.REQ 次数 | proj; UB-DL §4.7.3.3 |
| 0x020C | CNT_RETRY_TO | COUNT | 31 | 0 | RO | 0x0 | Retry ACK 超时次数 | proj; UB-DL §4.8.2 |
| 0x0210 | CNT_CRD_OF | COUNT | 31 | 0 | RO | 0x0 | 信用/RX 缓冲溢出次数 | proj; UB-DL §4.8.1 |
| 0x0214 | CNT_CRD_TO | COUNT | 31 | 0 | RO | 0x0 | 信用归还超时次数。`CRD_TO_DIS=1` 时不递增 | proj; UB-DL §4.8.1 |
| 0x0218 | CNT_TRAIN_TO | COUNT | 31 | 0 | RO | 0x0 | LMSM 训练超时回到 Idle 次数 | proj; UB-PHY §3.4.3 |
| 0x021C | CNT_BAD_VL | COUNT | 31 | 0 | RO | 0x0 | 未使能 VL 丢包次数 | proj; SPEC §7 |
| 0x0220 | CNT_CRD_UF | COUNT | 31 | 0 | RO | 0x0 | 信用下溢次数。正确设计不可达，见 SPEC §13.1 waiver | proj; SPEC §7 |
| 0x0224 | CNT_CLR | FEC_UNCORR | 0 | 0 | WO | 0x0 | 写 1 清 `CNT_FEC_UNCORR`，自清 | proj |
| 0x0224 | CNT_CLR | CRC_FAIL | 1 | 1 | WO | 0x0 | 写 1 清 `CNT_CRC_FAIL` | proj |
| 0x0224 | CNT_CLR | RETRY_REQ | 2 | 2 | WO | 0x0 | 写 1 清 `CNT_RETRY_REQ` | proj |
| 0x0224 | CNT_CLR | RETRY_TO | 3 | 3 | WO | 0x0 | 写 1 清 `CNT_RETRY_TO` | proj |
| 0x0224 | CNT_CLR | CRD_OF | 4 | 4 | WO | 0x0 | 写 1 清 `CNT_CRD_OF` | proj |
| 0x0224 | CNT_CLR | CRD_TO | 5 | 5 | WO | 0x0 | 写 1 清 `CNT_CRD_TO` | proj |
| 0x0224 | CNT_CLR | TRAIN_TO | 6 | 6 | WO | 0x0 | 写 1 清 `CNT_TRAIN_TO` | proj |
| 0x0224 | CNT_CLR | BAD_VL | 7 | 7 | WO | 0x0 | 写 1 清 `CNT_BAD_VL` | proj |
| 0x0224 | CNT_CLR | CRD_UF | 8 | 8 | WO | 0x0 | 写 1 清 `CNT_CRD_UF` | proj |
| 0x0224 | CNT_CLR | RSVD | 31 | 9 | RO | 0x0 | 保留（WO 寄存器的保留位写忽略） | proj |

App. D PORT_CAP2 的 flit/LTB 错误计数切片（D.6.3）为规范镜像，不在本窗口重复抄字段。

### 2.4 TEST（`0x0300`）— 代替内部 deposit

功能生效：`TEST_HOOKS=1` **且** `tb_test_mode=1`。

`tb_test_mode=0` 以及 PRODUCT（`TEST_HOOKS=0`）：本窗地址 **已映射**。读回 0，写忽略，**`csr_err=0`**。

PRODUCT 与 HOOKS（`tb_test_mode=0`）对 eqy 等价（SPEC §11 (d)）。`PORT_RST` 不复位本窗。

复位 = 不介入。

| offset_hex | reg_name | field_name | hi | lo | access | reset_hex | description | spec_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0x0300 | LMSM_TMR_SCALE | SCALE | 7 | 0 | RW | 0x00 | 代替向 LMSM 定时器 deposit。编码 **待定**（项目 TEST，规范无；建议 0 → 每拍 +1，非 0 → 每拍 +SCALE）。使训练沿真实路径到 Link_Active | proj; SPEC §10.4、§13 |
| 0x0300 | LMSM_TMR_SCALE | RSVD | 31 | 8 | RO | 0x0 | 保留 | proj |
| 0x0304 | CRD_TO_DIS | DIS | 0 | 0 | RW | 0x0 | 1=关闭 Crd_Ack 超时检错（不把 pending 钉 0）。0=检查使能 | proj; SPEC §10.4; UB-DL §4.8.1 |
| 0x0304 | CRD_TO_DIS | RSVD | 31 | 1 | RO | 0x0 | 保留 | proj |
| 0x0308 | PCS_TX_TEST | AM_IVL_SCALE | 7 | 0 | RW | 0x00 | 代替向 AM 符号计数器 deposit。缩放 PCS TX AMCTL 间隔。0=规范间隔。 非 0 编码 **待定**（建议与 LMSM_TMR_SCALE 相同） | proj; SPEC §10.4; UB-PHY §3.2.4 |
| 0x0308 | PCS_TX_TEST | RSVD | 31 | 8 | RO | 0x0 | 保留 | proj |

信用钩子（`tb_inj_crd_cells` / `tb_obs_crd_*`）固定对 **VL0**。 `tb_inj_crd_cells` 在 `tb_test_mode=1` 时每拍覆盖 cell 计数，HOOKS **不**增加存储寄存器。

不在本窗口提供：FSM 状态 force、叶子内部（CRC/FEC/deskew/缓冲）观察。见 SPEC §10.5。

`TEST_HOOKS=0` 时本窗同样读 0 / 写忽略 / `csr_err=0`（与上条相同，不是未映射）。

### 2.5 App. D 端口镜像（`0x1000`）

相对 `0x1000` 的偏移 = 规范 PORT0 相对 `0x0002_0000` 的偏移。 字段级位定义 **不在本仓库展开**；一行表示一个 32-bit 软件窗口或切片基址。 生成器可按节号对照规范展开。

| offset_hex | reg_name | field_name | hi | lo | access | reset_hex | description | spec_ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0x1000 | APPD_PORT_BASIC | WINDOW | 31 | 0 | MIX | NA | CFG0_PORT_BASIC 切片窗口（含 PORT_CAP Bitmap、Port Info、Port CNA、Port Rst）。 CNA 亦映射到 `0x0010` | App. D.5、D.5.1–D.5.6 |
| 0x1100 | APPD_LINK_CAP | WINDOW | 31 | 0 | MIX | NA | PORT_CAP1_LINK：能力 / 配置 / 状态（含协商后的粒度与 DLL SM 状态） | App. D.6.2、D.6.2.1–D.6.2.3 |
| 0x1200 | APPD_LINK_LOG | WINDOW | 31 | 0 | MIX | NA | PORT_CAP2_LINK_LOG：flit/LTB 错误日志与计数 | App. D.6.3 |
| 0x1E00 | APPD_LMSM_ST | WINDOW | 31 | 0 | MIX | NA | PORT_CAP20_LMSM_ST 切片镜像（M1 窗内地址；原 `0x2400`）。字段对照 D.6.21，不在此展开。`ub_lmsm` 只出 `lmsm_st[4:0]`（顶层编码，SPEC §10.3 / `STATUS.LMSM_ST`）；**不**把该 5-bit 塞进本窗。CSR 按 D.6.21 打切片 | App. D.6.21 |
| 0x1F00 | APPD_PORT_ERR | WINDOW | 31 | 0 | MIX | NA | PORT_CAP21_PORT_ERR_RECORD 镜像（M1 窗内地址；原 `0x2500`） | App. D.6.22 |

`MIX` = 切片内既有 RO 也有 RW/W1C，以对应节为准。`NA` 复位：对照该节，不在此抄。`APPD_LMSM_ST` 是 D.6.21 切片窗口，不是把 `STATUS.LMSM_ST` / `lmsm_st[4:0]` 重打包进 `0x1E00`。

M1 不实现的 PORT_CAP 切片（DATA_RATE2–9、EYE_MONITOR、QDLWS 等）在 Bitmap 中报不存在。DATA_RATE1（D.6.5）是否只读反映 Data Rate 0：规范未规定 M1 镜像策略，见 SPEC §13（建议最小只读、不实现改速）。

---

## 3. 生成约定

头文件 / Python 模型应按 §2 表逐行生成：

- 同一 `offset_hex` + `reg_name` 合成一个 32-bit 寄存器。
- 字段拼进该字；未列的位为保留，读 0。
- `WINDOW` 行不生成字段，只生成基址常量与 `spec_ref` 注释，提示从官方 App. D 展开。
- `TEST_*` 寄存器在 PRODUCT 网表绑定为无副作用（§2.4、SPEC §11）。

访问类型缩写供生成器使用，勿改拼写：`RW` `RO` `W1C` `WO` `MIX`。

App. D 窗口内地址迁徙（Q3）：`APPD_LMSM_ST` `0x2400`→`0x1E00`； `APPD_PORT_ERR` `0x2500`→`0x1F00`。两者落入 `0x1000`–`0x1FFF`， 避开规范相对偏移上的 DATA_RATE 等切片。
