# 模块清单

本文件只收当前需要冻结的叶子。其余层/叶子后续补行。

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

职责：在 PCS 内**观察**已有 flit 流，检测 Null / 非 Null Block，向 LMSM 给出 SPEC §3.3.4 / §6.1 的三路 1 拍脉冲。本叶不插入数据通路。8/16 计数在 `ub_lmsm`。

下列输入与判别均为 **Xia 裁定 2026-10-12**。

### 输入

| 信号 | 方向 | 宽 | 时钟 | 含义 |
| --- | --- | --- | --- | --- |
| `core_clk` | in | 1 | — | M1 唯一时钟 |
| `rst_pyc` | in | 1 | `core_clk` | 同步复位 |
| `pcs2dll_data` | in | 160 | `core_clk` | 观察 PCS→DLL 已 deskew、已对齐的 flit（SPEC §3.3.2）。本叶旁路取样，不打断该通路 |
| `pcs2dll_valid` | in | 1 | `core_clk` | 同上，本拍 flit 有效（valid-only） |
| `dll2pcs_data` | in | 160 | `core_clk` | 观察 DLL→PCS 待发 flit（SPEC §3.3.1） |
| `dll2pcs_valid` | in | 1 | `core_clk` | 同上 valid |
| `dll2pcs_ready` | in | 1 | `core_clk` | PCS 收下该拍的条件（§3.1：`valid==1 && ready==1` 完成一次传送） |
| `pcs_deskew_ok` | in | 1 | `core_clk` | deskew 完成（§3.3.4） |
| `pcs_rx_sdf_seen` | in | 1 | `core_clk` | 内部电平，见下节。`ub_pcs_amctl_rx` 驱动 |

**RX（Xia 裁定 2026-10-12）：** 本叶观察 PCS 已经交给 DLL 的 deskew 对齐流：`pcs2dll_data` / `pcs2dll_valid`（§3.3.2 原文口名）。旁路取样。

**TX（Xia 裁定 2026-10-12）：** 观察 DLL→PCS 在 PCS **收下**当拍的点：`dll2pcs_data` / `dll2pcs_valid`，收下条件 `dll2pcs_valid && dll2pcs_ready`（§3.3.1 / §3.1）。每收下一个 Null Block flit 给出一拍 `pcs2lmsm_tx_null_blk`。

**已配置 lane（Xia 裁定 2026-10-12）：** 不设 lane 集合/宽度输入。检测看 deskew 之后的聚合 flit，该流已经覆盖全部已配置 lane。

### 内部信号 `pcs_rx_sdf_seen`（Xia 裁定 2026-10-12）

PCS 内部电平，1 bit，`core_clk`。`ub_pcs_amctl_rx`（SPEC §2.4 AMCTL 接收叶子）驱动。

| 项 | 值 |
| --- | --- |
| 置位 | 全部已配置 lane 收到带 SDF 的 AMCTL 的当拍 |
| 清零 | `rst_pyc`；以及 LMSM 顶层状态离开 `Send_NullBlock` / `Link_Active`。状态出口用现有名 `tb_obs_lmsm_st`（编码同 `STATUS.LMSM_ST`，SPEC §10.3：5=`Send_NullBlock`，6=`Link_Active`） |
| 用途 | RX 两路脉冲门控：`pcs_deskew_ok && pcs_rx_sdf_seen` |

### Null Block 判别（Xia 裁定 2026-10-12）

对照 UB-DL §4.3.3.2：flit 的 block-type 字段等于该节 block-type 表中的 Null Block 码，且 `CLENGTH` 等于 `5'b00000`，则该 flit 为 Null Block。字段名与表号以该节为准；本仓库不抄其余位布局（与 SPEC 对 Init Block 字段「只作标识符、不抄表」同一口径，§2.6）。

- 门控内、`pcs2dll_valid==1`、且为 Null Block → 一拍 `pcs2lmsm_null_blk`
- 门控内、`pcs2dll_valid==1`、且为其它有效 flit → 一拍 `pcs2lmsm_rx_nonnull_blk`
- TX：`dll2pcs_valid && dll2pcs_ready` 且该 flit 为 Null Block → 一拍 `pcs2lmsm_tx_null_blk`

### 输出

| 信号 | 方向 | 宽 | 时钟 | 形式 | 含义（SPEC §3.3.4 / §6.1） |
| --- | --- | --- | --- | --- | --- |
| `pcs2lmsm_null_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | `pcs_deskew_ok && pcs_rx_sdf_seen` 下，对齐 flit 为 Null Block 给一拍 |
| `pcs2lmsm_rx_nonnull_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | 同一门控；对齐 flit 为非 Null Block 给一拍 |
| `pcs2lmsm_tx_null_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | PCS 收下的一个 Null Block flit 给一拍 |

接口断言：`pcs2lmsm_null_blk` 与 `pcs2lmsm_rx_nonnull_blk` 同拍互斥（§3.3.4 / §6.1）。

### 延迟（Xia 裁定 2026-10-12）

寄存 1 拍。检测条件在取样当拍成立，下一拍给出对应脉冲。实现后回填 SPEC §5。

---

## `ub_pcs_amctl_rx`（本表只记 `pcs_rx_sdf_seen`）

| 项 | 值 |
| --- | --- |
| 叶子名 | `ub_pcs_amctl_rx` |
| 层 | `pcs` |
| 所有者 | 线 A 设计 |
| 时钟 | `core_clk` |
| 复位 | `rst_pyc`（同步） |

驱动内部电平 `pcs_rx_sdf_seen`（Xia 裁定 2026-10-12）。置位 / 清零见上节。本表不展开 AMCTL 其余端口。

---

## `ub_lmsm`（本表只记消费侧）

| 项 | 值 |
| --- | --- |
| 叶子名 | `ub_lmsm` |
| 层 | `lmsm` |
| 所有者 | 线 A 设计 |
| 时钟 | `core_clk` |
| 复位 | `rst_pyc`（同步） |

消费 `ub_pcs_nullblk_det` 的三路脉冲（方向相对 LMSM 为 in，§3.3.4 / §6.1）：`pcs2lmsm_null_blk`、`pcs2lmsm_rx_nonnull_blk`、`pcs2lmsm_tx_null_blk`。顶层状态出口 `tb_obs_lmsm_st`（§10.3）供 `ub_pcs_amctl_rx` 判断是否离开 `Send_NullBlock` / `Link_Active`。`Send_NullBlock` 的 8/16 计数见 SPEC §6.1。本表不展开 LMSM 其余端口。
