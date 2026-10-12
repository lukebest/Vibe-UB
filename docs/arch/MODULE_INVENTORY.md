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

职责：在 PCS 内检测 Null / 非 Null Block，向 LMSM 给出 SPEC §3.3.4 / §6.1 的三路 1 拍脉冲。8/16 计数在 `ub_lmsm`。

### 输入

§3.3.4 已命名、本叶直接用到的门控：

| 信号 | 方向 | 宽 | 时钟 | 含义 |
| --- | --- | --- | --- | --- |
| `core_clk` | in | 1 | — | M1 唯一时钟 |
| `rst_pyc` | in | 1 | `core_clk` | 同步复位 |
| `pcs_deskew_ok` | in | 1 | `core_clk` | deskew 完成。RX 两路脉冲的门控之一（§3.3.4） |

§3.3.4 未命名、检测仍需要的上游（**未知**，待 Xia）：

| 需要 | 说明 |
| --- | --- |
| RX 对齐后的 flit 数据与有效 | 判定「全部已配置 RX lane 对齐的 flit」是否为 Null Block。§3.3.4 无此数据/valid 口名 |
| AMCTL with SDF 已过 / 本拍指示 | RX 门控写「deskew 完成且 AMCTL+SDF 之后」。`pcs_am_locked`（§3.3.4）只表达每 lane 锁定，SDF 事件未命名 |
| Null Block 判别字段 | 仓库 SPEC 未点名编码/字段 |
| TX 本拍发出的数据与有效 | 「全部已配置 TX lane 发出一个 Null Block」。§3.3.4 无 TX 数据/valid 口名 |
| 已配置 RX / TX lane 集合 | 「全部已配置 lane」。§3.3.4 无宽度/掩码口 |

### 输出

| 信号 | 方向 | 宽 | 时钟 | 形式 | 含义（SPEC §3.3.4 / §6.1） |
| --- | --- | --- | --- | --- | --- |
| `pcs2lmsm_null_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | deskew 完成且 AMCTL+SDF 之后，全部已配置 RX lane 对齐的一个 Null Block 给一拍 |
| `pcs2lmsm_rx_nonnull_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | 与 `pcs2lmsm_null_blk` 同一对齐点与门控；对齐 flit 为非 Null Block 时给一拍 |
| `pcs2lmsm_tx_null_blk` | out | 1 | `core_clk` | **1 拍脉冲**，复位 0 | 全部已配置 TX lane 发出一个 Null Block 时给一拍 |

接口断言：`pcs2lmsm_null_blk` 与 `pcs2lmsm_rx_nonnull_blk` 同拍互斥（§3.3.4 / §6.1）。

### 延迟

SPEC 规定三口均为 1 拍脉冲、复位 0；RX 两口同拍互斥。对齐点与门控与事件同拍给出，SPEC 未写组合或寄存。

**Xia 提议：** 寄存 1 拍。检测条件在对齐点当拍成立，下一拍给出对应脉冲。实现后回填 §5。

---

## `ub_lmsm`（本表只记消费侧）

| 项 | 值 |
| --- | --- |
| 叶子名 | `ub_lmsm` |
| 层 | `lmsm` |
| 所有者 | 线 A 设计 |
| 时钟 | `core_clk` |
| 复位 | `rst_pyc`（同步） |

消费 `ub_pcs_nullblk_det` 的三路脉冲（方向相对 LMSM 为 in，§3.3.4 / §6.1）：`pcs2lmsm_null_blk`、`pcs2lmsm_rx_nonnull_blk`、`pcs2lmsm_tx_null_blk`。`Send_NullBlock` 的 8/16 计数与进入拍规则见 SPEC §6.1。本表不展开 LMSM 其余端口。
