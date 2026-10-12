# 模块清单

本文件只收当前需要冻结的叶子。其余层/叶子后续补行。LMSM↔PCS 口表在 SPEC §3.3.4（仓库无 `LAYER_CONTRACTS`）。

命名：`ub_<层>_<功能>`（[CODING_STYLE.md](../CODING_STYLE.md) §5）。PCS 已有叶子用协议词作一段：`ub_pcs_amctl_tx` / `ub_pcs_deskew` / `ub_pcs_lane_dist`。本叶用 `ub_pcs_nullblk_det`（`nullblk` 一段，`det` = 检测）。

---

## `ub_pcs_nullblk_det`

| 项 | 值 |
| --- | --- |
| 叶子名 | `ub_pcs_nullblk_det` |
| 层 | `pcs` |
| 源码 | `pycircuit/pcs/ub_pcs_nullblk_det.py`（待写） |
| 生成网表 | `rtl/pcs/ub_pcs_nullblk_det.v` |
| 所有者 | 线 A 设计 |
| 时钟 | `core_clk` |
| 复位 | `rst_pyc`（同步） |
| TEST_HOOKS 观察口 | 无 |
| 参考模型 | `tb/models/ub_pcs_nullblk_det.py`（Xia 所有，待写） |

职责：在 PCS 内**观察**已有 flit 流，检测 Null / 非 Null Block，向 LMSM 给出 SPEC §3.3.4 / §6.1 的三路 1 拍脉冲。本叶不插入数据通路。8/16 计数在 `ub_lmsm`。与 `ub_pcs_amctl_rx` 同一次 RTL PR 交付。

下列输入、门控、拍位均为 **Xia 裁定 2026-10-12**。

### 输入

| 信号 | 方向 | 宽 | 时钟 | 含义 |
| --- | --- | --- | --- | --- |
| `core_clk` | in | 1 | — | M1 唯一时钟 |
| `rst_pyc` | in | 1 | `core_clk` | 同步复位 |
| `pcs2dll_data` | in | 160 | `core_clk` | 观察 PCS→DLL 已 deskew、已对齐的 flit（SPEC §3.3.2）。旁路取样 |
| `pcs2dll_valid` | in | 1 | `core_clk` | 同上，本拍 flit 有效（valid-only） |
| `dll2pcs_data` | in | 160 | `core_clk` | 观察 DLL→PCS 待发 flit（SPEC §3.3.1） |
| `dll2pcs_valid` | in | 1 | `core_clk` | 同上 valid |
| `dll2pcs_ready` | in | 1 | `core_clk` | PCS 收下该拍：`valid==1 && ready==1`（§3.1） |
| `pcs_deskew_ok` | in | 1 | `core_clk` | deskew 完成（§3.3.4） |
| `pcs_rx_sdf_seen` | in | 1 | `core_clk` | 内部寄存电平，见下。`ub_pcs_amctl_rx` 驱动 |
| `lmsm2pcs_nb_phase` | in | 1 | `core_clk` | LMSM→PCS 电平（§3.3.4）。本叶只读作对照；SDF 置位/清零在 `ub_pcs_amctl_rx` |

**RX：** 观察 `pcs2dll_data` / `pcs2dll_valid`。旁路取样。

**TX：** 观察 `dll2pcs_data` / `dll2pcs_valid`，收下点 `dll2pcs_valid && dll2pcs_ready`。每收下一个 Null Block flit 给出一拍 `pcs2lmsm_tx_null_blk`。

**已配置 lane：** 不设 lane 集合/宽度输入。检测看 deskew 之后的聚合 flit。

**每拍上限：** DLL↔PCS 在最宽 lane（x8）仍是单条 160-bit flit + 1-bit valid（SPEC §3.3.1 `dll2pcs_data`/`dll2pcs_valid`，§3.3.2 `pcs2dll_data`/`pcs2dll_valid`）。每拍至多一个 block，三口保持 1-bit 脉冲。

### 内部信号 `pcs_rx_sdf_seen`（Xia 裁定 2026-10-12）

PCS 内部**寄存**电平，1 bit，`core_clk`。`ub_pcs_amctl_rx`（SPEC §2.4）驱动。

| 项 | 值 |
| --- | --- |
| 置位 | 全部已配置 lane（`pma_rx_width`）的分 lane「已收 SDF」旗都立起之后，再寄一拍。末已配置 lane 的 AMCTL **末字**在 **t** → `cw_dec` 输出在 **t+1** → `pcs_rx_sdf_seen` 从 **t+2** 起为 1。旗在 `amctl_vld` 且 `LW_SWITCH`+{`X1`,`X2`,`X4`,`X8`} 且 `lmsm2pcs_nb_phase==1` 时置。SDF / EDF 语义见 `ub_pcs_amctl_rx` |
| 保持 | 置位后保持 |
| 清零 | `lmsm2pcs_nb_phase==0` 或复位的**下一拍**清 0；分 lane 旗一并清 |

### Null Block 判别（Xia 裁定 2026-10-12）

对照 UB-DL §4.3.3.2：flit 的 block-type 字段等于该节 block-type 表中的 Null Block 码，且 `CLENGTH` 等于 `5'b00000`。本仓库不抄其余位布局。

### 门控与输出寄存（Xia 裁定 2026-10-12）

- **仅 RX 两口**门控：`pcs_deskew_ok && pcs_rx_sdf_seen`。加在**输出寄存之前**（到达当拍）。门控撤下时，已进寄存器的块仍给出脉冲。
- **`pcs2lmsm_tx_null_blk` 无该门控。** LMSM 只在 `Send_NullBlock` 内计数，进入/离开清零（SPEC §6.1 / #41）。

### 输出与拍位（Xia 裁定 2026-10-12）

| 信号 | 方向 | 宽 | 时钟 | 形式 | 含义 |
| --- | --- | --- | --- | --- | --- |
| `pcs2lmsm_null_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | RX 门控下 Null Block。`pcs2dll_valid` 在 **t** → 脉冲在 **t+1** |
| `pcs2lmsm_rx_nonnull_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | 同一 RX 门控与拍位；非 Null 有效 flit |
| `pcs2lmsm_tx_null_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | 无 RX 门控。PCS 收下 Null Block 在 **t** → 脉冲在 **t+1** |

接口断言：`pcs2lmsm_null_blk` 与 `pcs2lmsm_rx_nonnull_blk` 同拍互斥。

LMSM 进入 `Send_NullBlock` 当拍 **s**（状态寄存器更新于 s）；`lmsm2pcs_nb_phase` 从 **s** 起为 1。LMSM 只计到达拍 **≥ s+1** 的脉冲（进入拍 s 的脉冲不计，与 #41 进入拍规则一致）。

延迟：寄存 1 拍（Xia 裁定 2026-10-12）。实现后回填 SPEC §5。

---

## `ub_pcs_amctl_rx`

SPEC §2.4 已点名该叶子。main 无 `pycircuit/` / `rtl/` 实现。与 `ub_pcs_nullblk_det` **同一次 RTL PR** 交付。静态例化 `NUM_LANES_RX` 份 `ub_pcs_amctl_cw_dec`（单 lane；编号 ≥ `pma_rx_width` 忽略）。下列端口、锁定、识别、SDF 均为 **Xia 裁定 2026-10-12**（出处：UB-PHY §3.2.4.2 AMCTL Structure、表 3-7..3-10、「AMCTL Identification Mechanism」、§3.2.4.4）。公开文本只写语义与节/表号；**不**抄码字取值、CW 编号、符号下标区间。

### 完备性核对（设计写叶用）

| # | 项 | 状态 | 口径 |
| --- | --- | --- | --- |
| 1 | 全端口表 | Xia 裁定 2026-10-12（M1） | **无** 分 lane valid 输入。输入保持 `pma_rx_data` + 共享 `pma_rx_valid`（§3.2.4；§13 A-05 / A-CL-3）。本叶含 §3.2.4.4 分 lane AMCTL 锁定（在固定插入间隔上做 END 检测，滑窗），分 lane 锁定位在叶内产生；`pcs_am_locked` = 全部已配置 lane（`pma_rx_width`）已锁定 |
| 2 | AMCTL 识别与字段 | Xia 裁定 2026-10-12（M2） | 公开只写语义：END 场经 eBCH-16 纠正后在预期位置匹配，即识别为 AMCTL（「AMCTL Identification Mechanism」）。场名 BODY / END / LID / CTRL_TYPE / CTRL_DETAIL（表 3-7）。LID 仅两半一致时有效；连续两次相同的已纠正 LID 才更新 lane ID。CTRL_TYPE / CTRL_DETAIL：任一半解出合法码字即有效；两半解出**不同**合法码字则忽略该控制。码字级解码（eBCH-16 纠正、码字表、场符号位置）在私有叶 `ub_pcs_amctl_cw_dec` |
| 3 | SDF / EDF | Xia 裁定 2026-10-12（M3） | 「带 SDF」：`CTRL_TYPE` = `LW_SWITCH` 且 `CTRL_DETAIL` ∈ {`X1`,`X2`,`X4`,`X8`}（§3.2.4.2「AMCTL Controlling」），且当拍 `lmsm2pcs_nb_phase==1`。「带 EDF」：同类型且 `CTRL_DETAIL` = `X0`。`amctl_rx` 为每 lane 记「已收 SDF」旗（在 `amctl_vld` 上置）。`pcs_rx_sdf_seen` 仍要全部已配置 lane；拍位 **t / t+1 / t+2** 见下表 |
| 4 | 「全部已配置 lane」来源 | 已有配置口 | `pma_rx_width[3:0]`（§3.2.5，与 `PARAM_PHY.NUM_LANES_RX[13:10]` 同编码，§9）；参数 `NUM_LANES_RX`。§3.3.4 无 LMSM→PCS 宽度口 |
| 5 | LID 出口 | Xia 裁定 2026-10-12 | `pcs_rx_lid` 宽 **4**：lane 0..7 加空身份，公开只称 `LID_NULL`（`LID_NULL` 的线码/半场编码是 `ub_pcs_amctl_cw_dec` 私有叶细节）。`pcs_rx_lid_vld`：全部已配置 lane 上 LID 一致解码时 **1 拍脉冲** |

#### 1. 端口表

| 信号 | 方向 | 宽 | 出处 | 说明 |
| --- | --- | --- | --- | --- |
| `core_clk` | in | 1 | §4.1 | M1 唯一时钟 |
| `rst_pyc` | in | 1 | §4.2 | 同步复位 |
| `pma_rx_data` | in | `NUM_LANES_RX*PMA_W`（`PMA_W=32`） | §3.2.4 | 每 lane 并行字，lane0 在 LSB。AMCTL 与数据共用此口（§13 A-CL-3） |
| `pma_rx_valid` | in | 1 | §3.2.4 | 共享 1 bit，每拍一字。**无** 分 lane valid（`pma_rx_data_valid_lane` 已删，§13 A-05） |
| `pcs_deskew_ok` | in | 1 | §3.3.4 | deskew 完成 |
| `lmsm2pcs_nb_phase` | in | 1 | §3.3.4 | `Send_NullBlock` / `Link_Active` 为 1 |
| `pma_rx_width` | in | 4 | §3.2.5 | 已配置 RX lane 数；二进制 1/2/4/8 |
| `pcs_rx_sdf_seen` | out | 1 | 本清单；Xia 裁定 2026-10-12 | 寄存电平。末已配置 lane AMCTL 末字 **t** → `cw_dec` **t+1** → 本口从 **t+2** 起为 1（`amctl_rx` 多一拍寄存）。清零：`nb_phase==0` 或复位的下一拍；分 lane 旗一并清 |
| `pcs_am_locked` | out | 1 | §3.3.4；Xia 裁定 2026-10-12 | 全部已配置 lane（`pma_rx_width`）已锁定。分 lane 锁定位在叶内，不出口 |
| `pcs_rx_lid` | out | 4 | Xia 裁定 2026-10-12 | 已解码 LID：lane 0..7 或 `LID_NULL` |
| `pcs_rx_lid_vld` | out | 1 | Xia 裁定 2026-10-12 | 全部已配置 lane 上 LID 一致解码时 **1 拍脉冲** |

`pcs_rx_sdf_seen` 拍位（Xia 裁定 2026-10-12）：

| 拍 | 事件 |
| --- | --- |
| **t** | 末已配置 lane 的 AMCTL **末字**到达（滑窗后 `word` / `word_vld`） |
| **t+1** | 该 lane 的 `ub_pcs_amctl_cw_dec` 输出（`amctl_vld` 及限定场）。`amctl_rx` 在 `amctl_vld` 且 `LW_SWITCH`+{`X1`,`X2`,`X4`,`X8`} 且 `lmsm2pcs_nb_phase==1` 时置该 lane「已收 SDF」旗 |
| **t+2** | 全部已配置 lane 旗已立时，`pcs_rx_sdf_seen` 从本拍起为 1（`amctl_rx` 多一拍寄存） |

清零：`lmsm2pcs_nb_phase==0` 或复位的下一拍；分 lane 旗一并清。

`ub_pcs_scrambler` / `ub_pcs_descrambler` 在 `_placeholder` 期间（§13 A-01 / A-02，D20）不接 `pcs_rx_lid`：该输入口悬空并 Tie 到占位常量，种子保持 placeholder。lint waiver 注记：`placeholder, D20`。

---

## `ub_pcs_amctl_cw_dec`

**船长已确认：** 走 C 线 S-01(b)。公开仓只留端口桩；源码在 `lukebest/Vibe-UB-private`；码字表不进公开 SPEC。契约 [docs/arch/pcs/contracts/ub_pcs_amctl_cw_dec.md](pcs/contracts/ub_pcs_amctl_cw_dec.md)。YAML 头 schema 源：[docs/arch/mem/contracts/README.md](mem/contracts/README.md) §8（PR #43 @ `3d08513a`，尚未合入 main；本 PR 不合并该分支）。

| 项 | 值 |
| --- | --- |
| 叶子名 | `ub_pcs_amctl_cw_dec` |
| 层 | `pcs` |
| 所有者 | 设计（线 A） |
| 父叶 | `ub_pcs_amctl_rx` |
| 粒度 | **单 lane 一份**。父叶静态例化 `NUM_LANES_RX` 份（`PARAM_PHY.NUM_LANES_RX` 同参数族）；编号 ≥ `pma_rx_width` 的实例由 `amctl_rx` 忽略。面积按单实例证明 |
| 时钟 | `core_clk`，`period_ns` 12.412 |
| 复位 | `rst_pyc`（同步） |
| 延迟 | **1 拍寄存**（`kind: registered`，`cycles: 1`）。无 `comb_budget_ns` |
| 公开仓 | 仅端口桩 `rtl/pcs/ub_pcs_amctl_cw_dec.v`（待写；与 `ub_pcs_amctl_rx` 同一次 RTL PR） |
| 源码 | `lukebest/Vibe-UB-private`（S-01(b)，生成物不入库） |
| attest | `reports/private/` 拷贝私有侧 `attest/ub_pcs_amctl_cw_dec.yml`（待写；与 C 线同一套） |
| 参考模型 | 私有仓；Xia 所有 |
| TEST_HOOKS 观察口 | 无 |

本叶内部持有 40 符号 AMCTL 窗口及场/符号位置（不入库）。父叶只认具名口。输入：`word[31:0]`（该 lane 经 `amctl_rx` 滑窗后的字）、`word_vld`（来自共享 `pma_rx_valid`）。

### 每实例输出（Xia 裁定 2026-10-12；相对输入字 1 拍）

| 信号 | 宽 | 含义 |
| --- | --- | --- |
| `end_hit` | 1 | 本字 END 经 eBCH-16 纠正后匹配。`amctl_rx` 锁定/滑窗用。**不受** `amctl_vld` 限定 |
| `amctl_vld` | 1 | 1 拍脉冲；末符号字之后 1 拍 |
| `end_ok` | 1 | 本窗 END 有效。仅 `amctl_vld` |
| `lid` | 4 | 已纠正 LID；空身份公开称 `LID_NULL` |
| `lid_ok` | 1 | 两半一致。仅 `amctl_vld` |
| `ctrl_type` | 3 | 项目枚举：`FEC_CTRL` / `LW_SWITCH` / `EI` / `PERIOD_CTRL` / `REMOTE_LW_SWITCH` / `RSVD` / `NO_CMD` |
| `ctrl_type_ok` | 1 | 任一半合法；两半不同合法码字则 0。仅 `amctl_vld` |
| `ctrl_detail` | 4 | 项目枚举：`X0` / `X1` / `X2` / `X4` / `X8` / `EEI` / `PERIOD0` / `PERIOD1` / `OPEN_FEC` / `CLOSE_FEC` / `RSVD` / `NO_CMD` |
| `ctrl_detail_ok` | 1 | 与 `ctrl_type_ok` 同一半场规则。仅 `amctl_vld` |

断言：`amctl_vld=0` 时除 `end_hit` 外输出为 0；`*_ok` 只随 `amctl_vld`。枚举取值见契约，不是规范码字。

---

## `ub_lmsm`（本表只记本接口）

| 项 | 值 |
| --- | --- |
| 叶子名 | `ub_lmsm` |
| 层 | `lmsm` |
| 所有者 | 线 A 设计 |
| 时钟 | `core_clk` |
| 复位 | `rst_pyc`（同步） |

驱动 `lmsm2pcs_nb_phase`（LMSM 内寄存；`Send_NullBlock` / `Link_Active` 为 1，从进入拍 s 起拉高）。消费三路脉冲；只计到达 ≥ s+1。`Send_NullBlock` 的 8/16 计数见 SPEC §6.1。本表不展开其余端口。
