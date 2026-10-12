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

**节号：** §5.1（NW 为 TP 与 TA 服务）、§5.2 NLP、§6.1–§6.2、§6.3（含 bypass）、§5.3.4–5、§5.3.7–8、§6.5.1.2（LBF / RT）、§6.6（CCI）。

**方向 / 单位：** TP Packet / 传输层响应（TPACK 等）/ CNP。bypass（优先通路）无 TPH，单位是「已带 NTH 规划的 TA 包」。

**项目口（建议名，规范无并行针脚；优先通路先锁这一套）**

| 方向 | 单位 | 建议口 |
| --- | --- | --- |
| TP→NW TX | 包 flit | `tp2nw_data/valid/ready/sop/eop`；`tp2nw_sl[3:0]`；`tp2nw_nlp[2:0]`；`tp2nw_bypass`（电平，1=无 TPH）；`tp2nw_dcna[15:0]`（目的 CNA，优先通路 16-b，§5.2.1）；`tp2nw_lbf[7:0]`（§5.2、§6.5.1.2）；`tp2nw_rt[1:0]`（§5.2、§6.5.1.2）；`tp2nw_cci[15:0]`（§5.2、§5.3.5、§6.6） |
| NW→TP RX | 包 flit | `nw2tp_data/valid/ready/sop/eop`；`nw2tp_err`（与 eop 对齐） |
| NW→TP 控制 | 电平 / 脉冲 | `nw2tp_flush`（电平：`dll_status_down` 期间保持 1 直到 TX/RX 空）；`nw2tp_drop`（1 拍，该包丢弃） |
| NW→TP 状态 | 电平 | `nw_link_up`（= `dll_status_up` 转发，§4.2） |

**数据宽度与每拍 flit**

| 项 | 值 |
| --- | --- |
| 拍宽 | 与 DLL 对齐 **160 b、1 flit/拍**（规范无并行口；不另做齿轮） |
| 每拍最大 flit | **1**；多 flit/拍本期不采用 |
| 包长 | ≥ 头+尾+最大净荷（§5.3.8）；具体字节上限 **未知** |
| TP MTU | 附录 D.1.13 有器件级取值；本仓库未锁，标 **未知**。优先通路走 bypass，不在本口切 RTP 段 |
| `valid==0` | sop/eop/sl/nlp/dcna/lbf/rt/cci/data/err **忽略** |

**字段（规范有宽）**

| 字段 | 宽 | 节号 | 备注 |
| --- | --- | --- | --- |
| LPH.CFG | 4 | §4.3.2.2.2 | 0=DLLCB，禁止出现在本口。CTP 取值 **6**（§6.3.2）；RTP 取值 **7**（§5.2.2）；bypass 取值 **9**（B.2.6） |
| LPH.RT | 2 | §4.3.2.2.2、§5.2 | 与 `tp2nw_rt` / NTH.RT 同源。LPH word 内位切片见该节，本文件不抄，标 **未知** |
| NTH.RT | 2 | §5.2、§6.5.1.2 | 与 TA 模式协调见 §7.3.4；四码取值见该节，本文件不抄 |
| NTH.SCNA/DCNA | 16 与 24 两档 | §5.2.1–2 | 规范同时给出两档。优先通路口 `tp2nw_dcna[15:0]`（16-b CNA，TRADEOFFS D19）。24-b 格式口宽 **未知** |
| NTH.CCI | 16 | §5.2、§5.3.5、§6.6 | TP CC 可读写；TX 边带 `tp2nw_cci[15:0]` |
| NTH.LBF | 8 | §5.2、§6.5.1.2 | 发送端生成，规范不约束取值；TX 边带 `tp2nw_lbf[7:0]` |
| NTH.SL | 4 | §5.2、§5.3.4 | NW 映 VL |
| NTH.NLP | 3 | §5.2 | 取值表见该节，本文件不抄。bypass 时 NLP 指向 TAH；TAH 码点 **未知**（PR #61） |
| NTH.Mgmt | 1 | §5.2.1、§10.4.1.1 | 仅部分 CFG |
| RTPH 整头 | 16 B | §6.2.1 | |
| RTPH.TPOpcode | 8 | §6.2.1 | `[7]` = last |
| RTPH.SrcTPN | 24 | §6.2.1 | |
| RTPH.DstTPN | 24 | §6.2.1 | 与 SrcTPN 同表 |
| RTPH.PSN | 24 | §6.2.1、§6.4.1 | 模 2^24；半空间比较见该节。工程窗深 **未知** |
| RTPH.TPMSN | 24 | §6.2.1、§6.7.1.2.1 | 整操作完成键 |
| RTPH.NLP / RSPST / RSPINFO | **未知** | §6.2.1 | 16 B 头内其余字段宽本仓库未锁 |
| CTPH | 1 B；TPOpcode 2 + NLP | §6.2.1 | |
| UTPH | 16 B；TPOpcode 8 | §6.2.1 | |
| ICRC | 算法在 §5.3.7 | bypass（CFG9）无 ICRC（B.2.6）。RTP（CFG7）带 ICRC（§5.3.7） |

**握手（项目建议，规范未知）**

- **TX / RX 均为 valid/ready。** 同一拍 `valid&&ready` 成交。`valid` 期间边带保持。`ready` 不得组合看本拍 `valid`。
- TX：TP 源，可撤 `valid`（未成交前保持边带）。NW 宿，可停：无路由、隔离失败、下行 `nw_tx_ready=0`、`nw_link_up=0`。
- RX：NW 源；TP 宿可停（重装配 / RTP 窗满）。**禁止** valid-only。
- `tp2nw_bypass==1`（优先通路）：同一握手，净荷从 TA 头开始、无 TPH 字节；NW 仍填 NTH。目的地址 / LBF / RT / CCI / SL / NLP 取本口边带。
- `tp2nw_dcna` / `tp2nw_lbf` / `tp2nw_rt` / `tp2nw_cci` 为请求边带，`valid` 期间保持到成交；NW 写入 NTH（§5.2、§6.5.1.2、§6.6）。
- `sop&&eop` 单 flit 包合法。同一包 flit 连续，中间不得插入另一包。

**反压 / 信用**

- 本口 **无** 规范信用细胞。反压 = `ready`。
- 链路信用在 DLL（§4.6）：NW 把 `nw_tx_ready` 传到 `tp2nw_ready`。SL→VL 在 NW 内（§5.3.4），不出现在本口。
- RTP 发送窗满（§6.5.1.4.1）时 TP 停发新包。拥塞窗见 §6.6，属 `ub_tp_cc`（可选）。优先通路 bypass 无 RTP 发送窗。

**序**

- 优先通路：bypass，不重排（§7.3.4）；NW `LPH.RT` / NTH.RT 走单径（建议 RT[0] 符合该节）。
- 后波：NW 可按 RT 多径（§5.3.2）；RTP 收端重排（§6.4、§6.5.1.4）。CTP 不重排。

**错误**

| 事件 | 建议信号 | 对齐 | 粘滞/irq/计数 |
| --- | --- | --- | --- |
| 路由/隔离丢弃 | `nw2tp_drop`（1 拍）+ 原因码 **未知** | 该包 sop 或 eop | 计数；是否 irq **未知** |
| ICRC 错 | `nw2tp_icrc_err` | 与包 eop | 计数。bypass（CFG9）无 ICRC，本信号保持 0。RTP（CFG7）与 eop 对齐 |
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
7. `valid` 期间 `tp2nw_dcna/lbf/rt/cci/sl/nlp` 保持。
8. 优先通路 `tp2nw_dcna` 为 16 b（§5.2.1）。

**未决（规范未给或本仓库未锁）**

- 24-b CNA 格式下 `tp2nw_dcna` 是否加宽到 24：**未知**（后波 CFG=7）。
- SCNA 是否由 TP 给出：**未知**（NW 可从 `PORT_CNA` / App. D.5.5 填）。
- RX 侧 `nw2tp_scna` / `nw2tp_cci` 是否另开边带：**未知**（NTH 可随 `nw2tp_data` 上送，或 NW 已剥 NTH；PR #58 Q-1）。
- 优先通路 CCI 复位取值：建议 0；规范是否要求非零 **未知**。
- NTH 由边带交给 NW 写入，或由 TP 写入 `tp2nw_data`：**本契约取边带**（与已有 `sl`/`nlp` 同形）。RX 是否已剥 NTH：**未知**。
- 包字节上限：**未知**（§5.3.8 只给头+尾+最大净荷关系；D.1.13 MTU 本仓库未锁）。PR #61。
- NTH.NLP→TAH 码点：**未知**（§5.2 有表，本文件不抄）。PR #61。
- LPH.RT 在 LPH word 内的位切片：**未知**（宽 2 b 已锁，§4.3.2.2.2）。PR #61。
- Go-Back-N 与选择重传：§6.4.2 两套都有；实现先做哪一套 **未知**。PR #61。

---

## 3. Transport ↔ Transaction（线 B；优先通路）

**节号：** §6.1、§6.7.1.2.1、§6.8、§6.8.2、§7.1、§7.3.3–4。

**方向 / 单位：** 事务操作（请求，可多 TP Packet）；TAACK/TANAK；ROL 时 TP 响应可携带事务完成（§6.8.2）。优先通路：bypass + Read/Write，一操作一请求（可多 flit 净荷）。

**项目口（建议名）**

| 方向 | 单位 | 建议口 |
| --- | --- | --- |
| TA→TP 提交 | 操作描述符 | `ta2tp_op_valid/ready`；`ta2tp_opcode[7:0]`；`ta2tp_tassn[15:0]`；`ta2tp_mode[1:0]`（ROI/ROT/ROL/UNO，编码 **未知**）；`ta2tp_bypass`（电平）；`ta2tp_dcna[15:0]`（目的 CNA，优先通路 16-b，§5.2.1；供 TP 填 `tp2nw_dcna`）；`ta2tp_op_len`（字节长度，宽 **未知**，PR #58 Q-8） |
| TA→TP 净荷 | flit 流 | `ta2tp_data/valid/ready/sop/eop`（160 b、1 flit/拍） |
| TP→TA 完成 | 操作 | `tp2ta_done`（1 拍，带 `tp2ta_tassn`）；`tp2ta_fail`（1 拍，与 done 互斥）；`tp2ta_err`（与最后净荷 eop 对齐的 Poison/失败） |
| TP→TA 整操作完成 | TPMSN | `tp2ta_msn_valid/ready`；`tp2ta_tpmsn[23:0]`（§6.2.1、§6.7.1.2.1）。该 TPMSN 下全部 TP Packet 收齐或对端确认后成交 |
| TP→TA 收向递交 | 操作+净荷 | 对称：`tp2ta_op_*` + `tp2ta_data_*`（目标侧 TA）；`tp2ta_op_*` 含 `tp2ta_tassn[15:0]`、`tp2ta_tpmsn[23:0]` |
| TA→TP 完成（ROL 目标） | 操作完成 | `ta2tp_cmp_valid/ready`；`ta2tp_cmp_tassn[15:0]`；`ta2tp_cmp_fail`（1=失败）；`ta2tp_cmp_opcode[7:0]`（取值见 §7.2）；`ta2tp_cmp_rspst` / `ta2tp_cmp_rspinfo`（宽 **未知**，§6.2.1、§6.8.2）。可选净荷：`ta2tp_cmp_data/valid/ready/sop/eop`（160 b、1 flit/拍） |

**数据宽度与每拍 flit**

| 项 | 值 |
| --- | --- |
| 描述符 | 操作级 valid/ready，每拍最多 **1** 个新操作 |
| 净荷 | **160 b、1 flit/拍**，与 NW/DLL 同宽 |
| 分段 | 优先通路 bypass：TA 不要求 TP 按 MTU 再切（§6.8.1 留给 RTP 第二波）。器件级 MTU 见附录 D.1.13，本仓库未锁，标 **未知** |
| UNO 净荷 | 不得超过 TP MTU（§7.3.3.5）；优先通路建议不用 UNO |

**字段**

| 字段 | 宽 | 节号 |
| --- | --- | --- |
| 操作整体 | 请求 ± 可选响应 | §7.1 |
| TAOpcode 等 | 见 TA 契约 | §7.2 |
| INI_TASSN | 16 | §7.2.1 |
| DCNA（优先通路） | 16 | §5.2.1 |
| last（RTP TPOpcode[7]） | 1 | §6.2.1 |
| TPMSN | 24 | §6.2.1、§6.7.1.2.1 |
| PSN | 24 | §6.2.1 |
| PSN 空间（窗口/初值） | **未知**（字段本身 24 b） | §6.4.1 |
| RSPST / RSPINFO | **未知** | §6.2.1、§6.8.2 |
| 角色 | TA：initiator/target；TP：sender/receiver 可在一次事务中对调 | §6.8 |

**握手（建议，规范只描述过程）**

- 操作级与净荷级都是 **valid/ready**。TA→TP 提交口 `ready=0` 的原因：发送窗满（§6.5.1.4.1）或下游 `tp2nw_ready=0`。ROL 等待走 `ta2tp_cmp_*`（§6.8.2）。
- `tp2ta_msn_valid/ready`：TP 源，TA 宿可停。成交键为 `tp2ta_tpmsn`（§6.7.1.2.1）。
- ROL 目标 TA 经 `ta2tp_cmp_valid/ready` 把操作完成交给 TP；TP 成交后再发该操作最后 TPACK（§6.8.2）。`ta2tp_cmp` 边带在 `valid` 期间保持。
- 发起端 `tp2ta_done` / `tp2ta_fail` 仍按 `tassn` 报告事务完成。
- 优先通路：`ta2tp_bypass==1`，无 TPACK 状态机；完成 = 对端 TAACK 或本地写完成（时序 **未知**，但必须有 `tp2ta_done` 或 `fail`）。bypass 下 `tp2ta_msn_*` 仍按该操作的 TPMSN 成交。
- 未成交的 `ta2tp_op_valid` 边带保持（含 `ta2tp_dcna`、`ta2tp_op_len`）。一操作的净荷 sop…eop 必须属于当前 `tassn`。
- CTP+ROI/ROT（第二波）：无 TPACK，只有 TAACK（§6.8.1）。

**反压 / 信用**

- 无层间信用细胞。RTP 发送窗满（§6.5.1.4.1）= `ta2tp_op_ready=0`（第二波）。拥塞窗见 §6.6，属 `ub_tp_cc`（可选）。优先通路：反压只来自 NW/DLL `ready`。
- 共享 TP 信道（§6.1、§6.3.1）：策略 **未知**；契约：不得对 TA 声明无限未决。建议优先通路未决上限 **未知**（实现后回填，至少 1）。
- TP 计时器为 RTO 与 ACK 合并（§6.4.2.1）。`RETRY_WAIT_CYC` 归 DLL（§4.7.3.3）。`PROBE_WAIT_CYC` 归 LMSM（§3.4.3.2）。

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

- `nw_link_up==0` / `nw2tp_flush`：有限拍内对每个未决 TASSN 给 `fail`（拍数 **未知**）；每个未决 TPMSN 经 `tp2ta_msn_*` 成交；ROL 未决 `ta2tp_cmp` 由 TA 以 `fail` 成交或随 Entity 复位清空。
- Entity 复位清 TA 未决，**不应**要求 DLL 回 Disabled（§4.2、§10.6.1）。

**契约级断言（可先写；优先通路）**

1. 净荷 160 b、1 flit/拍。
2. `done` 与 `fail` 互斥；都带 `tassn`。
3. `bypass==1` 时本操作不期待 TPACK 状态。
4. flush 结束前无残留未决 `tassn`。
5. 净荷 sop…eop 的 flit 数与该操作声明长度一致（长度字段宽 **未知**）。
6. `tp2ta_msn_valid&&ready` 成交时 `tp2ta_tpmsn` 为该整操作的 24 b 键（§6.7.1.2.1）。
7. ROL：`ta2tp_cmp` 成交后，TP 才对该 `tassn` 发末包 TPACK（§6.8.2）。
8. `ta2tp_cmp_fail==1` 与同拍成功完成互斥。
9. `valid` 期间 `ta2tp_dcna` 与 `ta2tp_cmp_*` 边带保持。

**未决（规范未给或本仓库未锁）**

- `ta2tp_mode[1:0]` 四模式编码：**未知**。PR #61。
- `ta2tp_op_len` / 净荷长度字段宽、TA 最大操作长度：**未知**（PR #58 Q-8、PR #61）。
- `ta2tp_op_ch`（信道号）是否每操作给出：**未知**（可随 TP 信道绑定）。
- RSPST / RSPINFO 宽：**未知**（§6.2.1、§6.8.2）；Compact ATAH Status 宽：**未知**。PR #58 草案 3 b / 5 b 标为假设。
- `tp2ta_fail` / TP NAK 原因码集合与编码：**未知**（PR #58 Q-9、PR #61）。
- flush 拍数：**未知**。flush 未确认操作一律 `fail`，或等 link 恢复后续传：**未知**（PR #58 Q-10、PR #61）。本口建议仍给 `fail`。
- 未决 TASSN 上限：**未知**（实现后回填，至少 1）。PR #61。
- 共享 TP 信道策略：**未知**（§6.1、§6.3.1）。PR #61。
- TPMSN 分配后回 TA 的拍位（提交成交拍 vs 仅 `tp2ta_msn_*`）：**未知**。
- DstTPN 是否每操作出现在 TA→TP 描述符：**未知**（可随 TP 信道绑定）。
- `tp2ta_msn_*` 与 `tp2ta_done` 的拍序：**未知**。
- TX 出口仲裁（bypass vs TPACK/重传）、CTX/RTB 实现、µs 节拍来源、`TP_ATOMIC_EN`、F=1 伪包 obs 名、HOOKS 点名存储：属微架构，标 **未知**（PR #58 Q-3..Q-7、Q-11、Q-13..Q-15）。

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
