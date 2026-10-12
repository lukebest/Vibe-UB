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

SPEC §2.4 已点名该叶子。main 无 `pycircuit/` / `rtl/` 实现。清单在此补 `pcs_rx_sdf_seen` 出口；与 `ub_pcs_nullblk_det` **同一次 RTL PR** 交付。

| 项 | 值 |
| --- | --- |
| 叶子名 | `ub_pcs_amctl_rx` |
| 层 | `pcs` |
| 所有者 | 线 A 设计 |
| 时钟 | `core_clk` |
| 复位 | `rst_pyc`（同步） |
| 新增出口 | `pcs_rx_sdf_seen`（寄存电平，见上） |
| 新增入口 | `lmsm2pcs_nb_phase`（置位/清零条件） |

本表不展开 AMCTL 其余端口。

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
