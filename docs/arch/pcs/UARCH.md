# PCS 微架构草案 — 线 A

| 项 | 值 |
| --- | --- |
| 作者 | 架构 Xia |
| 日期 | 2026-10-12 |
| 状态 | **草案**。本批只收门禁需要认 `parent` 的三叶；其余 PCS 叶子后续补行 |
| 规范 | UB-PHY §3.2.4 / UB-DL §4.3.3.2；项目口径见 [MODULE_INVENTORY.md](../MODULE_INVENTORY.md) |
| 引用约定 | 只写章节号和项目短句。不抄码字取值、CW 编号、符号下标 |
| 裁定 | Xia 裁定 2026-10-12；`ub_pcs_amctl_cw_dec` 走 C 线 S-01(b) |

---

## 1. 范围

本批三叶：

1. `ub_pcs_nullblk_det`：观察 deskew 后聚合 flit，向 LMSM 给 Null / 非 Null 三路 1 拍脉冲。
2. `ub_pcs_amctl_rx`：分 lane AMCTL 锁定、SDF/EDF、驱动 `pcs_rx_sdf_seen`。
3. `ub_pcs_amctl_cw_dec`：私有码字解码（S-01(b)）。公开仓只留端口桩与契约；源码在独立私有仓库。

端口、拍位、门控写在 [MODULE_INVENTORY.md](../MODULE_INVENTORY.md)。契约只覆盖私有解码叶：[ub_pcs_amctl_cw_dec.md](contracts/ub_pcs_amctl_cw_dec.md)。

单时钟 `core_clk`，叶子只接 `rst_pyc`。本文件不冻结端口。

## 3. 叶子划分（对照 PR #18 MODULE_INVENTORY §7）

| PR #18 模块 | 本草案叶子 | 类型 | 职责（一句话） |
| --- | --- | --- | --- |
| `ub_pcs_nullblk_det` | `ub_pcs_nullblk_det` | 结构 | 观察 `pcs2dll_*` / `dll2pcs_*`，出三路 1 拍脉冲；细则 [MODULE_INVENTORY.md](../MODULE_INVENTORY.md) |
| `ub_pcs_amctl_rx` | `ub_pcs_amctl_rx` | 结构 | AMCTL 锁定与 SDF/EDF；例化 `NUM_LANES_RX` 份 `ub_pcs_amctl_cw_dec`；细则 [MODULE_INVENTORY.md](../MODULE_INVENTORY.md) |
| `ub_pcs_amctl_cw_dec` | `ub_pcs_amctl_cw_dec` | 解码 | 私有 S-01(b)；公开仓只留端口桩；契约 [ub_pcs_amctl_cw_dec.md](contracts/ub_pcs_amctl_cw_dec.md) |
