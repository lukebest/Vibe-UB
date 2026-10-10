# Vibe-UB 层间契约（草案）

供 **契约级验证代理与断言** 在两侧 RTL 之前落地。只写节号与工程数值；规范未给的口协议标 **未知**，并给可测的项目建议（非规范）。不抄规范正文/表/图。

**D19 写作顺序：** §1 DLL↔NW、§2 NW↔TP、§3 TP↔TA **先写且最详**（卡线 A/B 与优先通路）。§4 TA↔Function。§5–§7 线 C（Function↔Memory / Resource / Security）。截止 Tue 2026-10-13。

**握手通则（项目，与 SPEC §3.1 对齐，规范不定义 valid/ready）：**

| 约定 | 规则（断言可直接写） |
| --- | --- |
| valid/ready | 同一拍 `valid&&ready` 成交。`valid` 期间数据/边带保持到成交。`ready` 不得组合看本拍 `valid`。 |
| valid-only | 无 `ready`；宿 **必须** 当拍收下。宿深度不足即契约违规。 |
| 复位后首拍 | 规范无。建议 `valid=0`；有 `ready` 时下游能收则为 1。 |
| 谁可停 | 下表每契约写明源/宿谁可以拉低 `ready`（或 valid-only 禁止停）。 |
| 节拍 | 默认 1 拍 = 1 `core_clk`。多 flit/拍 必须在该契约写死。 |

各层寄存器仍只进 `docs/regmap/regmap.yaml`（PR #11），本文件不列位域。

PHY↔DLL、LMSM 侧带已在 [SPEC.md](../SPEC.md) §3.3 写死（M1）。此处不重复，以免与 PR #9 冲突。

---

## 1. DLL ↔ Network（线 A；优先通路下沿）

**节号：** UB-DL §4.1–§4.3、§4.2（对上状态）、§4.5（VL 来自 NW）、§4.6（信用在 DLL 内）、§4.8.4；UB-PHY 不直接出现。M1 桩口：[SPEC.md](../SPEC.md) §3.2.2。

**方向 / 传送单位**

| 方向 | 单位 | 项目口（M1 已用名，后续 NW 接同一套） |
| --- | --- | --- |
| NW→DLL TX | DLLDP 净荷 flit（不含 LPH/LBH/BCRC） | `nw_tx_data/valid/ready/sop/eop/vl` |
| DLL→NW RX | 重组后净荷 flit | `nw_rx_data/valid/ready/sop/eop/vl/err` |
| DLL→NW 状态 | 电平 | `dll_status_up`、`dll_status_down` 互斥（§4.2） |

**数据宽度与每拍最大 flit（设计用来定 DLL TX/RX 缓冲 — 规范无并行口）**

| 项 | 值 | 依据 |
| --- | --- | --- |
| flit 宽 | **160 bit**（20 B） | §4.3.2.1；M1 `FLIT_W` |
| 每拍最大 flit | **1** | 规范未定义并行拍。项目锁定 1 flit/beat，与 M1 桩一致 |
| 单拍峰值 | 160 b × 80.57 MHz ≈ 12.89 Gbit/s | 工程；DR0 x1 线速率低于此 |
| DLLDP 长度 | 1–512 flit；>32 则最多 16 个 DLLDB | §4.3.2.1 |
| 单 flit 包 | 同一拍 `sop&&eop` 合法 | SPEC §3.2.2 |
| `valid==0` | sop/eop/vl/data/err **忽略** | SPEC §3.2.2 |

**字段（规范固定者）**

| 字段 | 宽 | 谁填 | 节号 |
| --- | --- | --- | --- |
| 净荷 flit | 160 | NW 交净荷；DLL 加 LPH/LBH/BCRC | §4.3.2 |
| VL | 4 | NW 按 SL→VL（§5.3.4）交给 DLL；LPH.VL 同源 | §4.5、§4.3.2.2.2 |
| CFG | 4 | DLLDP：NW 携带，DLL 不解释；禁止 0（0=DLLCB） | §4.3.2.2.2 |
| RT | 见 NTH | NW→DLL 写入 LPH.RT | §4.3.2.2.2、§5.3.2 |
| CRD/ACK/CRD_VL/PLENGTH | LPH 内 | **仅 DLL** 填，不出现在 NW 口 | §4.3.2.2.2 |
| NTH 及上层 | 在净荷里 | DLL 不解析 | §5.2 |

**握手**

- **TX（NW→DLL）：valid/ready。** NW 是源，可在任意拍撤 `valid`（未成交前保持边带）。DLL 是宿，可拉低 `ready`：无信用、非 `dll_status_up`、重传占用、内部反压（SPEC §3.2.2）。
- **RX（DLL→NW）：valid/ready。** DLL 是源；**NW 可停**（`nw_rx_ready=0`）。DLL **必须**能反压，不得改成 valid-only（否则与 M1 口冲突）。RX 缓冲深度 **未知**（SPEC §13）— 契约断言：不得在 `ready=0` 时丢已承诺的 DLLDP。
- 禁止：NW 在 `dll_status_down` 时期待 TX 成交（DLL 应 `ready=0` 并丢弃已收下的未完成包，§4.2 / §4.8.4）。

**反压 / 信用**

- **链路信用在 DLL 内、按 VL**（§4.6），**不**以 cell 计数出现在 NW 口。NW 只看见 `nw_tx_ready` 与 `dll_status_*`。
- NW 不得在 `ready=0` 时改已呈现的 `data/sop/eop/vl`。
- 信用耗尽：DLL TX `ready=0`，不是 `nw_rx_err`。
- 共享信用模式（§4.6.1.3）若开启：仍不改变本口形状，只改变 DLL 何时 `ready`。

**序**

- DLL 对每 VL 点到点保序交付（§4.1）。NW 多径/乱序是 NW 以上的事（§5.3.2、§6）。
- 同一 DLLDP 的 flit 必须连续 sop…eop，中间不得插入另一 DLLDP（断言）。

**错误报告（信号 / 对齐 / 粘滞 / irq / 计数）**

| 事件 | 口信号 | 对齐 | CSR / irq |
| --- | --- | --- | --- |
| 本包 `ERROR_FLAG` / 不完整上送 | `nw_rx_err` | **与该 DLLDP 的 `nw_rx_eop` 同拍**；`valid==0` 忽略（SPEC §3.2.2、§7） | 计数+粘滞 **未知**是否每因一源；M1 用 `nw_rx_err` 给上层 |
| 非法 VL | 整包不成交或丢弃 | 无 `eop` 给 NW | 计数 +1、粘滞（SPEC §7） |
| `link_up`/`LinkUp`→0 | `dll_status_down`；已上送部分填 0 并 `nw_rx_err` | 随最后一拍 eop 或立即 down | §4.8.4 |
| 信用下溢 | 不出现在 NW 数据口 | — | `CNT_CRD_UF` + `IRQ`（正确设计不可达） |

**复位 / link-down**

- 端口/设备复位→`DLL_Disabled`，对上 Down，丢弃来自 NW 与 PHY 的包（§4.2、§10.6.1）。
- Entity 复位 **不** 把 DLL SM 打进 Disabled（§4.2）。
- Down 期间 TX `ready=0`；RX 无新 `valid`。

**契约级断言（可先写）**

1. 160 b、1 flit/拍；`sop&&eop` 单拍合法。
2. `valid&&ready` 成交；`ready` 不组合看 `valid`。
3. Down ⇒ 无 TX 成交。
4. `nw_rx_err` 仅在 `valid&&eop` 时有意义。
5. `vl` 仅 0…NUM_VL-1；非法不出现在 RX。
6. 同一包 TX 与 RX 的 flit 计数 ≤512。

---

## 2. Network ↔ Transport（线 A∩B；优先通路）

**节号：** §5.1（NW 为 TP 与 TA 服务）、§5.2 NLP、§6.1–§6.2、§6.3（含 bypass）、§5.3.4–5、§5.3.7–8。

**方向 / 单位：** TP Packet / 传输层响应（TPACK 等）/ CNP。bypass（优先通路）无 TPH，单位是「已带 NTH 规划的 TA 包」。

**项目口（建议名，规范无并行针脚；优先通路先锁这一套）**

| 方向 | 单位 | 建议口 |
| --- | --- | --- |
| TP→NW TX | 包 flit | `tp2nw_data/valid/ready/sop/eop`；`tp2nw_sl[3:0]`；`tp2nw_nlp[2:0]`；`tp2nw_bypass`（电平，1=无 TPH） |
| NW→TP RX | 包 flit | `nw2tp_data/valid/ready/sop/eop`；`nw2tp_err`（与 eop 对齐） |
| NW→TP 控制 | 电平 / 脉冲 | `nw2tp_flush`（电平：`dll_status_down` 期间保持 1 直到 TX/RX 空）；`nw2tp_drop`（1 拍，该包丢弃） |
| NW→TP 状态 | 电平 | `nw_link_up`（= `dll_status_up` 转发，§4.2） |

**数据宽度与每拍 flit**

| 项 | 值 |
| --- | --- |
| 拍宽 | 与 DLL 对齐 **160 b、1 flit/拍**（规范无并行口；不另做齿轮） |
| 每拍最大 flit | **1**；多 flit/拍本期不采用 |
| 包长 | ≥ 头+尾+最大净荷（§5.3.8）；具体字节上限 **未知** |
| TP MTU | **未知**（§6.8 只称按 MTU 分段）。优先通路走 bypass，不在本口切 RTP 段 |
| `valid==0` | sop/eop/sl/nlp/data/err **忽略** |

**字段（规范有宽）**

| 字段 | 宽 | 节号 | 备注 |
| --- | --- | --- | --- |
| NTH.RT | 2 | §5.2 | 与 TA 模式协调见 §7.3.4 |
| NTH.SCNA/DCNA | 16 或 24 | §5.2.1–2 | IP 格式无 CNA |
| NTH.CCI | 16 | §5.2、§5.3.5 | TP CC 可读写 |
| NTH.LBF | 8 | §5.2 | 发送端生成，规范不约束取值 |
| NTH.SL | 4 | §5.2、§5.3.4 | NW 映 VL |
| NTH.NLP | 3 | §5.2 | CTPH/RTPH/UPIH/TAH… |
| NTH.Mgmt | 1 | §5.2.1、§10.4.1.1 | 仅部分 CFG |
| RTPH 主字段 | TPOpcode 8、SrcTPN 24、DstTPN、PSN、TPMSN 等 | §6.2.1 | 位宽未在概述列全者 **未知** |
| CTPH | TPOpcode 2 + NLP | §6.2.1 | |
| UTPH | TPOpcode 8 | §6.2.1 | |
| ICRC | 算法在 §5.3.7 | 是否每包都带：**未知** 是否全部模式 |

**握手（项目建议，规范未知）**

- **TX / RX 均为 valid/ready。** 同一拍 `valid&&ready` 成交。`valid` 期间边带保持。`ready` 不得组合看本拍 `valid`。
- TX：TP 源，可撤 `valid`（未成交前保持边带）。NW 宿，可停：无路由、隔离失败、下行 `nw_tx_ready=0`、`nw_link_up=0`。
- RX：NW 源；TP 宿可停（重装配 / RTP 窗满）。**禁止** valid-only。
- `tp2nw_bypass==1`（优先通路）：同一握手，净荷从 TA 头开始、无 TPH 字节；NW 仍填 NTH（CNA/SL/NLP=TAH）。
- `sop&&eop` 单 flit 包合法。同一包 flit 连续，中间不得插入另一包。

**反压 / 信用**

- 本口 **无** 规范信用细胞。反压 = `ready`。
- 链路信用在 DLL（§4.6）：NW 把 `nw_tx_ready` 传到 `tp2nw_ready`。SL→VL 在 NW 内（§5.3.4），不出现在本口。
- RTP 端到端窗（§6.6.1.1）表现为 TP 不再 `valid`，不是 NW 信用。优先通路 bypass **没有** RTP 窗。

**序**

- 优先通路：bypass，不重排（§7.3.4）；NW `LPH.RT` / NTH.RT 走单径（建议 RT[0] 符合该节）。
- 后波：NW 可按 RT 多径（§5.3.2）；RTP 收端重排（§6.4、§6.5.1.4）。CTP 不重排。

**错误**

| 事件 | 建议信号 | 对齐 | 粘滞/irq/计数 |
| --- | --- | --- | --- |
| 路由/隔离丢弃 | `nw2tp_drop`（1 拍）+ 原因码 **未知** | 该包 sop 或 eop | 计数；是否 irq **未知** |
| ICRC 错 | `nw2tp_icrc_err` | 与包 eop | 计数。优先通路是否带 ICRC：**未知**；建议 LS 通路先不做 ICRC |
| 无路由 | 不向 DLL 发；`tp2nw_ready` 可保持 1 并 `drop` | — | 计数 |
| DLL `nw_rx_err` | 上送 `nw2tp_err` | **与 `nw2tp_eop` 同拍** | 计数 |

**复位 / link-down**

- `nw_link_up==0`：`tp2nw_ready=0`；`nw2tp_valid=0`；`nw2tp_flush=1` 直到两侧无未完成 sop…eop。
- 规范未给 NW 刷新拍数。建议：flush 期间 TP 不得开始新包。

**契约级断言（可先写；优先通路）**

1. 160 b、1 flit/拍；`sop&&eop` 合法。
2. `valid&&ready` 成交；`ready` 不组合看 `valid`。
3. `nw_link_up==0` ⇒ 无 TX 成交。
4. `nw2tp_err` 仅在 `valid&&eop` 有意义。
5. `tp2nw_bypass==1` ⇒ 本包无 TPH（NLP 指向 TAH）。
6. bypass 包不得在 sop…eop 中插入另一包。

---

## 3. Transport ↔ Transaction（线 B；优先通路）

**节号：** §6.1、§6.8、§7.1、§7.3.3–4。

**方向 / 单位：** 事务操作（请求，可多 TP Packet）；TAACK/TANAK；ROL 时 TP 响应可携带事务完成（§6.8.2）。优先通路：bypass + Read/Write，一操作一请求（可多 flit 净荷）。

**项目口（建议名）**

| 方向 | 单位 | 建议口 |
| --- | --- | --- |
| TA→TP 提交 | 操作描述符 | `ta2tp_op_valid/ready`；`ta2tp_opcode[7:0]`；`ta2tp_tassn[15:0]`；`ta2tp_mode[1:0]`（ROI/ROT/ROL/UNO，编码 **未知**）；`ta2tp_bypass`（电平） |
| TA→TP 净荷 | flit 流 | `ta2tp_data/valid/ready/sop/eop`（160 b、1 flit/拍） |
| TP→TA 完成 | 操作 | `tp2ta_done`（1 拍，带 `tp2ta_tassn`）；`tp2ta_fail`（1 拍，与 done 互斥）；`tp2ta_err`（与最后净荷 eop 对齐的 Poison/失败） |
| TP→TA 收向递交 | 操作+净荷 | 对称：`tp2ta_op_*` + `tp2ta_data_*`（目标侧 TA） |

**数据宽度与每拍 flit**

| 项 | 值 |
| --- | --- |
| 描述符 | 操作级 valid/ready，每拍最多 **1** 个新操作 |
| 净荷 | **160 b、1 flit/拍**，与 NW/DLL 同宽 |
| 分段 | 优先通路 bypass：TA 不要求 TP 按 MTU 再切（§6.8.1 留给 RTP 第二波）。MTU **未知** |
| UNO 净荷 | 不得超过 TP MTU（§7.3.3.5）；优先通路建议不用 UNO |

**字段**

| 字段 | 宽 | 节号 |
| --- | --- | --- |
| 操作整体 | 请求 ± 可选响应 | §7.1 |
| TAOpcode 等 | 见 TA 契约 | §7.2 |
| last（RTP TPOpcode[7]） | 1 | §6.2.1 |
| PSN 空间 | **未知**（有 PSN 字段） | §6.4.1 |
| 角色 | TA：initiator/target；TP：sender/receiver 可在一次事务中对调 | §6.8 |

**握手（建议，规范只描述过程）**

- 操作级与净荷级都是 **valid/ready**。任一侧可停：TA 无完成槽、TP 窗满、下行 `tp2nw_ready=0`。
- **禁止** valid-only：ROL 要等目标 TA 完成才发最后 TPACK（§6.8.2）。
- 优先通路：`ta2tp_bypass==1`，无 TPACK 状态机；完成 = 对端 TAACK 或本地写完成（时序 **未知**，但必须有 `tp2ta_done` 或 `fail`）。
- 未成交的 `ta2tp_op_valid` 边带保持。一操作的净荷 sop…eop 必须属于当前 `tassn`。
- CTP+ROI/ROT（第二波）：无 TPACK，只有 TAACK（§6.8.1）。

**反压 / 信用**

- 无层间信用细胞。RTP 窗满 = `ta2tp_op_ready=0`（第二波）。优先通路：反压只来自 NW/DLL `ready`。
- 共享 TP 信道（§6.1、§6.3.1）：策略 **未知**；契约：不得对 TA 声明无限未决。建议优先通路未决上限 **未知**（实现后回填，至少 1）。

**序**

- 优先通路建议 ROL 或等价单径（与 bypass 对齐，§7.3.4）。
- ROI/ROT：TA 管执行/完成序；下层可乱序（第二波）。
- UNO：允许乱序；优先通路不用。
- 断言：`ta2tp_mode` × `ta2tp_bypass` 属于 §7.3.4 允许集（TEO+ROI 禁用 UTP）。

**错误**

| 事件 | 建议信号 | 对齐 | 粘滞/irq/计数 |
| --- | --- | --- | --- |
| 不可恢复事务 | `tp2ta_fail`；FUN 见 `ta_status`（§7.1） | 该 `tassn` 完成拍 | 上层处理；是否 irq **未知** |
| 可管理资源短缺 | TA 重试（§7.1） | 不结束操作；不打 fail | 计数 |
| TP NAK / 超时 | `tp2ta_fail` + 原因 **未知** | `INI_TASSN` 16 b（§7.2.1），不是随意拍 | 计数 |
| Poison | `tp2ta_err` | 该操作最后净荷 eop | 上送 FUN |
| 下行 flush | 每个未决 `tassn` 必须 `done` 或 `fail` | flush 撤销前清空 | 不得悬空 |

**复位 / link-down**

- `nw_link_up==0` / `nw2tp_flush`：有限拍内对每个未决 TASSN 给 `fail`（拍数 **未知**）。
- Entity 复位清 TA 未决，**不应**要求 DLL 回 Disabled（§4.2、§10.6.1）。

**契约级断言（可先写；优先通路）**

1. 净荷 160 b、1 flit/拍。
2. `done` 与 `fail` 互斥；都带 `tassn`。
3. `bypass==1` 时本操作不期待 TPACK 状态。
4. flush 结束前无残留未决 `tassn`。
5. 净荷 sop…eop 的 flit 数与该操作声明长度一致（长度字段宽 **未知**）。

---

## 4. Transaction ↔ Function（线 B；LS 优先）

**节号：** §7.1、§8.1、§8.3、§8.4、§8.2.2–3。

**方向 / 单位**

- LS：处理器访问 ↔ Read/Write/Atomic 操作（§8.3）。
- URMA：SQE 提交 / CQE 完成（§8.2.3、§8.4）。
- 管理/消息：同类操作码（§7.4）。

**数据宽度与每拍 flit**

| 项 | 值 |
| --- | --- |
| LS 主机口宽 | **未知**（NoC/CPU） |
| URMA 描述符宽 | **未知** |
| 到 TA 净荷 | 建议 160 b / 1 flit/拍 或字节使能块；**未知**规范值 |

**字段**

| 字段 | 宽 | 节号 |
| --- | --- | --- |
| TAOpcode | 8 | §7.2.1（取值表不抄，实现对照该节） |
| INI_TASSN | 16 | §7.2.1 |
| TAver | 2，当前 0 | §7.2.1 |
| EE_bits | 2 | §7.2.1；TEE 见 §11.6 |
| TV_EN / UD_Flag / Poison | 各 1 | §7.2.1 |
| Jetty 态 | Reset/Ready/Suspend/Error | §8.2.2.3 |

**握手（建议）**

- LS：主机 valid/ready 或总线协议 **未知**；进入 TA 前须收敛成操作级 valid/ready。FUN 可停（翻译未好）；TA 可停。
- URMA 门铃：写门铃后硬件拉 SQ；SQ 满时软件可见，不是 TA `ready` 口（具体 **未知**）。
- CQE：FUN→软件，队列满策略 **未知**（应反压发送或报异常，不得静默丢完成）。

**反压 / 信用**

- 无规范 FUN↔TA 信用。Jetty 未 Ready：收包静默丢、WR 错误完成（§8.2.2.3）— 代理按态断言。

**序**

- LS：处理器序 **未知**（SoC）；TA 模式须匹配。
- URMA：SQ 序 vs 完成序由服务模式决定。

**错误**

| 事件 | 信号/行为 | 对齐 | 粘滞/irq/计数 |
| --- | --- | --- | --- |
| Jetty Reset/Error 收包 | 静默丢 | 无 CQE 数据 | 可计数 |
| Reset 上 WR | 错误完成 | 该 WR | CQE 异常 |
| exception suspend | Ready→Suspend | 异常 SQE | 异常 CQE 或异步错（§8.2.2.3） |
| LS 失败 | 给主机错误 **未知**（总线 abort/响应码） | 该访问 | **未知** irq |

**复位 / link-down**

- Jetty 可从任意态回 Reset（§8.2.2.3）。
- link-down：建议所有 Ready Jetty→Suspend 或 Error（选哪 **未知**）；LS 未完成失败。

---

## 5. Function ↔ Memory（UMMU / decoder）（线 C；decoder 最小表可服务优先通路）

**节号：** §8.2.1、§8.3、§8.4、§9.2–§9.5。

**方向 / 单位：** User：PA→UBMD（decoder，§9.5）。Home：UBMD→PA+权限（UMMU，§9.4）。单位=一次内存事务的地址/权限查询，可与数据通道分离。

**数据宽度与每拍**

| 项 | 值 |
| --- | --- |
| UBA | **64 bit**（§9.3） |
| EID / TokenID / PA | **未知** |
| 每拍查询数 | **未知**；建议 1 查询/拍 valid/ready |
| 数据通道 | 与 TA 净荷相同建议 160 b；是否经 MEM：**未知**（可只查表、数据走旁路） |

**握手：** valid/ready。UMMU/decoder 可停（查表 miss/填表）。FUN/TA 可停。禁止 valid-only（miss 延迟 **未知**）。

**反压 / 信用：** 无。表 miss 是否同步等待或异步填表 **未知**。

**序：** 同一 TASSN 的查表与数据必须不乱配（断言：响应带查询 tag，tag 宽 **未知**，建议用 TASSN[15:0]）。

**错误**

| 事件 | 信号 | 对齐 | CSR |
| --- | --- | --- | --- |
| 翻译/权限失败 | `mem_fault` + 类（A/B/C 见 §10.6.2） | 该查询完成拍 | RAS 记录 + 可选 irq |
| Token/排他/类型 | 分因 **未知** 是否分开脚 | 同 | §9.4.4 |

**复位：** 删段前须排空相关事务（§8.2.1.1）— 断言：清表与未决 TASSN 不得重叠。Entity 复位清该 Entity 表项（§10.6.1.3）。

---

## 6. Function / Transaction ↔ Resource（管理）（线 C）

**节号：** §8.7、§10.3、§10.4、§7.4.5。

**单位：** 管理事务（TAOpcode Management）+ 本地 CSR 字。MSN 匹配请求/响应（§10.4.1.2）。

**宽度 / 每拍：** CSR 32 b、1 字/拍（已有 SPEC §3.2.3）。管理包走 TA/NW，160 b / 1 flit/拍（建议）。并发请求数 **未知**。

**握手：** 本地 CSR 已是 req/ready。远程管理：同 TA 操作 valid/ready。UBFM vs User 权限看 `NTH.Mgmt` 与 UPI（§10.4.1.1）— 断言：违规不写 CFG0。

**反压：** CSR ready=0 合法。管理响应未回：未决表满则停提交。

**错误：** 权限失败、MSN 失配：计数+不应答或 NAK（格式 **未知**）。记录进 §10.6.2。

**复位：** 设备/端口/Entity 分层（§10.6.1）。管理口在端口复位期间拒绝。

---

## 7. Function / Transaction / Network ↔ Security（线 C）

**节号：** §11.1.3、§11.2–§11.6、§7.2.1 EE_bits、§5.3.3 NPI。

**单位：** 控制（认证、分区、ACL）为消息/CSR；CIP 为包数据通路（§11.5）。

**宽度 / 每拍：** CIP 必须声明能否 1×160 b/拍无反压缺口；加密延迟拍数 **未知**。控制口 32 b CSR 或操作级。

**握手：** 控制 valid/ready。CIP：建议插在 NW 收发路径上，**valid/ready**，CIP 可停（密钥未就绪则必须停，不得漏明文）。

**反压：** 密钥未加载：CIP `ready=0`。不得 valid-only。

**错误：** 完整性失败（§11.5.2.5）与包 eop 对齐；丢包+计数+irq **未知**。禁止钩子观察密钥。

**复位 / 上电：** 先加载信任锚/密钥再允许 CIP `ready=1`（§11.5.2.1）。link-down 是否清会话 **未知**。

---

## 8. 与 M1 已定口的关系

| 契约 | 线 | 状态 |
| --- | --- | --- |
| DLL↔NW | A | 宽度/1 flit/拍/握手/err 对齐 **已按 SPEC §3.2.2 锁**；NW 换桩不得改这些 |
| NW↔TP | A∩B | 项目口 + 断言已写；优先通路 `bypass` |
| TP↔TA | B | 项目口 + 断言已写；优先通路 Read/Write + bypass |
| TA↔FUN | B | LS 收敛成操作级 valid/ready；URMA 第二波 |
| FUN↔MEM/RSC/SEC | C | 草案；decoder 最小表可提前服务 LS |
| PCS↔DLL、LMSM | A | 见 SPEC §3.3；本文件不改 |

契约代理先绑 §1–§3，再复制到 §4。D19 四项已定，本文件不再等 TRADEOFFS 改切线。
