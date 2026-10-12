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
| 置位 | 全部已配置 lane 收到带 SDF 的 AMCTL、且当拍 `lmsm2pcs_nb_phase==1`：下一拍置 1 |
| 保持 | 置位后保持 |
| 清零 | `lmsm2pcs_nb_phase==0` 或复位的下一拍清 0 |

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

SPEC §2.4 已点名该叶子。main 无 `pycircuit/` / `rtl/` 实现。与 `ub_pcs_nullblk_det` **同一次 RTL PR** 交付。

### 完备性核对（设计写叶用）

| # | 项 | 状态 | SPEC 出处 |
| --- | --- | --- | --- |
| 1 | 全端口表 | 见下表。每 lane 锁定后的 **分 lane valid** 无独立口名 | 数据/共享 valid：§3.2.4；宽度：§3.2.5 / §9；时钟复位：§4.1 / §4.2 |
| 2 | AMCTL 识别规则（sync header / block type / marker）与字段位置 | **MISSING** | 近文：§2.4 职责「锁定、滑窗、确认」指向 UB-PHY §3.2.4 / §3.2.3.1；§5「间隔/长度不在此抄录」；§2.4 只写解码后 LID「不是 eBCH 码字」 |
| 3 | SDF 比特位置 | **MISSING** | 近文：§2.4 / §3.4.3.6 只写事件「AMCTL with SDF / EDF」，无字段位号 |
| 4 | 「全部已配置 lane」来源 | 已有配置口 | `pma_rx_width[3:0]`（§3.2.5，与 `PARAM_PHY.NUM_LANES_RX[13:10]` 同编码，§9）；参数 `NUM_LANES_RX`。§3.3.4 无 LMSM→PCS 宽度口 |
| 5 | LID 出口 | Xia 裁定 2026-10-12 | `pcs_rx_lid` 宽 **4**（§2.4 `amctl_lid`：已解码 `AMCTL.LID`，0–7 / `NULL`=8 / 9–15 保留）；`pcs_rx_lid_vld` 1 拍脉冲。线格式/eBCH 位布局仍见 #2 |

#### 1. 端口表

| 信号 | 方向 | 宽 | 出处 | 说明 |
| --- | --- | --- | --- | --- |
| `core_clk` | in | 1 | §4.1 | M1 唯一时钟 |
| `rst_pyc` | in | 1 | §4.2 | 同步复位 |
| `pma_rx_data` | in | `NUM_LANES_RX*PMA_W`（`PMA_W=32`） | §3.2.4 | 每 lane 并行字，lane0 在 LSB。AMCTL 与数据共用此口（§13 A-CL-3）。SPEC 无「block lock 之后」另开口名 |
| `pma_rx_valid` | in | 1 | §3.2.4 | 共享 1 bit，每拍一字。**无** per-lane valid（`pma_rx_data_valid_lane` 已删，§13 A-05） |
| 每 lane、block lock 之后的 valid | — | — | **MISSING** | 近文只有共享 `pma_rx_valid` 与锁定电平 `pcs_am_locked` |
| `pcs_deskew_ok` | in | 1 | §3.3.4 | deskew 完成 |
| `lmsm2pcs_nb_phase` | in | 1 | §3.3.4 | `Send_NullBlock` / `Link_Active` 为 1 |
| `pma_rx_width` | in | 4 | §3.2.5 | 已配置 RX lane 数；二进制 1/2/4/8 |
| `pcs_rx_sdf_seen` | out | 1 | 本清单；Xia 裁定 2026-10-12 | 寄存电平；置位/清零见 `ub_pcs_nullblk_det` 节 |
| `pcs_am_locked` | out | `NLANE`=`NUM_LANES_RX` | §3.3.4、§10.2 | 每 lane AM/AMCTL 锁定 |
| `pcs_rx_lid` | out | 4 | §2.4 `amctl_lid`；Xia 裁定 2026-10-12 | 已解码 LID |
| `pcs_rx_lid_vld` | out | 1 | Xia 裁定 2026-10-12 | 全部已配置 lane 上 LID 一致解码时 **1 拍脉冲** |

`ub_pcs_scrambler` / `ub_pcs_descrambler` 在 `_placeholder` 期间（§13 A-01 / A-02，D20）不接 `pcs_rx_lid`：该输入口悬空并 Tie 到占位常量，种子保持 placeholder。lint waiver 注记：`placeholder, D20`。

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
