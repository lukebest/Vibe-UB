# Vibe-UB 全层模块清单（草案）

船长已定：Vibe-UB 做成 **完整 UB 控制器**，覆盖 UB Base Spec Rev 2.0 第 3–11 章及规范定义的管理功能。PHY+DLL 为 **batch 1（M1）**。本文件按层列出拟实现模块，供并行拆分与验证规划。**草案**，不冻结端口。**D19 线：** A = PHY→DLL→NW；B = TP→TA→Function；C = Memory→Resource→Security。优先通路 NW→TP→TA→Load/Store 争资源时赢。可选标「延后」。附录管理在 M10 之后。

**引用约定：** 只写节号与工程数值。不抄规范正文、表、图、寄存器字段说明。规范未裁定处写 **未知**。

**寄存器：** 各层软件可见寄存器一律进入 `docs/regmap/regmap.yaml`（PR #11）。本 PR **不**改 `regmap.yaml` / `REGMAP.md`。

**命名：** `ub_<层>_<功能>`，见 [CODING_STYLE.md](../CODING_STYLE.md) §5。时钟复位默认沿用 M1：`core_clk` + `rst_n`→`ub_rst_sync`→`rst_pyc`（[SPEC.md](../SPEC.md) §4）。后续层是否仍单时钟：**未知**（见 [TRADEOFFS.md](TRADEOFFS.md)）。面积/时序依赖 PR #9 工艺节点；未定前以 Sky130 作代理。

**列（已冻结）：** 模块 / **线 (A/B/C)** / 节号；必做 vs 可选（可选=延后）；上游 / 下游；复杂度 S/M/L（含一句理由）；可观察性 / 测试钩子；数据通路宽 / 吞吐目标；时钟复位域 + 目标频率；存储（深×宽，需 SRAM 宏则标明；行为模型+stub 须写读延迟 / 端口 1RW|1R1W / 同址冲突；默认见 §12；开源 PDK SRAM 宏有限）；软件可见面。

**M1 覆盖：** 标「是」= 已在 [SPEC.md](../SPEC.md) 立项；「部分」= 骨架或参数在、功能未齐；「否」= 后续里程碑。

**吞吐目标（草案，规范不给并行口速率）：** Data Rate 0、x1：线 2.578125 Gbit/s → `F_CORE`≈80.57 MHz、每拍每 lane 32 bit（SPEC §4.1 / §9）。DLL flit = 20 B = 160 bit（UB-DL §4.3.2.1）。更高速率 / 多 lane：**未知**（后续里程碑）。

---

## 0. 公共 / 顶层（线 A/B/C）

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子（`TEST_HOOKS=1`） | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_controller` | A/B/C | 工程顶层；栈见 §2.2 | 必做 | 上：软件/NoC/Entity；下：各层 | M — 例化与时钟复位汇聚 | `tb_test_mode` 总门；obs 链路/irq | 汇聚各层口 | `core_clk` / `rst_n`；M1 ≈80.57 MHz。多时钟 **未知** | 无大存储 | 顶层 `irq`；CSR 窗见 yaml |
| `ub_csr` | A/B/C | App. D；§10.4.1 | 必做（窗随里程碑长） | 上：CSR 主机；下：各块电平 | M — 译码/W1C/计数；全附录后变 L | obs 译码 `csr_err`；禁 force 内部 | 32-bit CSR 字，1 拍（SPEC §3.2.3） | 同 `core_clk` / `rst_pyc` | 寄存器堆：现 M1 窗小（FF）；全 CFG0/1 + ROUTE_TABLE **需 SRAM**。应当例化 `ub_cmn_mem_1r1w`。ROUTE stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 全部块进 `regmap.yaml`。上电：`PORT_RST`、`CTRL.LMSM_START`（M1） |
| `ub_rst_sync` | A/B/C | 工程；SPEC §4.2 | 必做 | 上：`rst_n`；下：`rst_n_sync` | S — 2 级同步器 | 无钩子（白名单） | 1 bit | `core_clk`；异步置位同步释放。释放须时钟在跑 | 2 flop | 无 |
| `ub_pyc_rst_adapt` | A/B/C | 工程；SPEC §4.2 | 必做 | `rst_n_sync`→`rst_pyc` | S — 极性适配 | 无 | 1 bit | combo | 无 | 无 |

---

## 1. 第 3 章 PHY（PCS / PMA 模型 / LMSM）— M1 batch 1；线 A

规范必做：PCS 数据通路、AMCTL、LMSM（UB-PHY §3.2、§3.4.3）。PMA 数字不进 ASIC（D3）。可选/后期：QDLWS §3.4.2.3、快速降宽 §3.4.2.4、DR1+ 改速/EQ §3.4.2.5 / §3.4.2.9、光互连、低功耗 PRBS 通路 §3.2.6。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_pcs` | A | §3.2 | 必做。M1 **是** | 上：`ub_dll`；下：PMA 模型；侧：`ub_lmsm` | L — 整条 PCS 编排 | AM 锁定、deskew、FEC 成败；无叶子内部钩子（SPEC §10.5） | 汇聚：TX 160b flit→N×32；RX 反 | `core_clk` / `rst_pyc`；≈80.57 MHz | 齿轮/码字缓冲深 **未知**（SPEC §13） | `PARAM_PHY` / `PARAM_FEC`；AM 间隔缩放 TEST |
| `ub_pcs_fec_enc` / `ub_pcs_fec_dec` | A | §3.2.2.1、§3.2.3.5 | 必做（bypass 可协商）。M1 **是** | PCS 内部 | L — RS(128,120) T=4/2 | obs 纠/不可纠计数（建议 CSR，非 `tb_*`） | 码字符号流 8-bit；拍数 **未知** | 同 `core_clk` | 码字暂存：约 128 符号×8b，可 FF；T=4 工作区中 | FEC 模式只读；不可纠→重传源 |
| `ub_pcs_scrambler` / `ub_pcs_descrambler` | A | §3.2.2.4、§3.2.3.2、§3.2.6 | 必做。M1 **是**（抽头/种子 **未知**） | 每物理 lane | M — 23b LFSR×N | 无产品钩子；TB 走叶子口 `seed_load`/`en` | 32 b/lane/拍 | 同 | 23 b×N FF | 无独立 CSR |
| `ub_pcs_lane_dist` / `ub_pcs_lane_dedist` | A | §3.2.2.3、§3.2.5 | 必做。M1 **是** | FEC↔lane | S — 组合 8-bit 分发 | 无 | `N*32` | combo，无复位 | 无 | 无 |
| `ub_pcs_amctl_tx` / `ub_pcs_amctl_rx` | A | §3.2.4、§3.2.3.1 | 必做。M1 **是** | PCS↔LMSM | L — eBCH、滑窗、EDF/SDF | `tb_inj_am_lock`（M1 保留）；obs 每 lane lock | 插入占用符号槽，不另开 PMA 口 | 同 | 滑窗/确认：深 **未知**，偏 FF | AM 间隔；锁定状态可进 STATUS |
| `ub_pcs_deskew` | A | §3.2.3.1 | 必做（x>1）。M1 **是** | AMCTL RX→解扰 | M — 多 lane 对齐 | obs `deskew_ok` | 每 lane 32 b | 同 | 每 lane 弹性：深 **未知**；x8 时可能 SRAM。若走 stub：应当例化 `ub_cmn_mem_1r1w`；读 1 拍寄存、1R1W、同址 read-old（Xia 提案，非规范） | 无 |
| `ub_pcs_nullblk_det` | A | §3.3.4、§6.1、§13 A-23 | 必做。M1 **是**。所有权：线 A 设计 | 上：PCS flit 旁路、`ub_pcs_amctl_rx`（`pcs_rx_sdf_seen`）；下：`ub_lmsm` | S — 观察 160 b flit、1 拍寄存脉冲 | 无产品钩子；接口断言 `pcs2lmsm_null_blk` 与 `pcs2lmsm_rx_nonnull_blk` 同拍互斥 | 观察 `pcs2dll_*` / `dll2pcs_*`；出 `pcs2lmsm_null_blk` / `pcs2lmsm_rx_nonnull_blk` / `pcs2lmsm_tx_null_blk`（各 1 bit、1 拍脉冲、复位 0） | 同 `core_clk` / `rst_pyc` | 无 | 无 |
| `ub_pcs_interleave` / `ub_pcs_deinterleave` | A | §3.2.2.3、§3.2.3.4、§3.2.3.6 | 可选（延后）（CodecNum=2）。M1 **部分**（建议 1） | FEC 旁 | M — 交织排 | 无 | 同 FEC 符号 | 同 | 交织缓存 **未知** | `PARAM_FEC.CODEC_NUM` |
| `ub_lmsm` | A | §3.4、§3.4.3 | 必做。M1 **是** | CSR / PCS / PMA / DLL | L — 10 主态+子态+定时器 | `tb_obs_lmsm_st`（仅顶层）、`tb_obs_link_up/ready`；`tb_inj_lid_bad`；`LMSM_TMR_SCALE` | 侧带电平+LMB 字段，非数据吞吐 | 同；超时周期=规范 ms×`F_CORE` | 定时器 32 b；无大缓冲 | `CTRL.LMSM_START`、`STATUS.LMSM_ST`/`LINK_*`、`CNT_TRAIN_TO`、`IRQ.TRAIN_FAIL`、`APPD_LMSM_ST`。上电：PHY ready 后写 `LMSM_START` |
| `ub_pma_model` | A | §3.3、§3.4.3.2 | 必做行为模型，不进 ASIC。M1 **部分** | LMSM / PCS | M — 行为；高保真 **可选** | `pma_term_detect`/`phy_ready` 针脚；不 force 模拟态 | N×32 @ `F_CORE` | 仿真可与 `core_clk` 同拍 | 无产品 SRAM | 无产品 CSR |

---

## 2. 第 4 章 DLL — M1 batch 1；线 A

规范 SHALL：封装/解析 DLLCB/DLLDP、CRC/非 CRC、最多 16 VL、每 VL 信用、点到点重传、DLL SM（§4.1–§4.2）。可选/可配：非 CRC、信用共享 §4.6.1.3、>2 VL。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_dll` | A | §4.2–§4.8 | 必做。M1 **是** | 上：NW（M1 为桩）；下：PCS；侧：LMSM | L — SM+调度 | `tb_obs_dll_sm_st`、`tb_obs_consume_flits` | **1×160 b flit/拍**（项目；规范无并行拍）。峰值 ≈12.89 Gbit/s @80.57 MHz，DR0 x1 用不满 | 同 `core_clk` | 见子块 | `STATUS.DLL_SM_ST`/`LINK_*`；`dll_status_up/down` |
| `ub_dll_segmenter` / `ub_dll_reassembler` | A | §4.3、§4.3.2.1 | 必做。M1 **是** | NW 包↔DLLDB | M — 1–512 flit、最多 16 DB | obs sop/eop/非法 VL 计数 | 160 b；DLLDP 最长 512 flit | 同 | TX 组包：**未知**（可 1 flit 流过）。RX 重组：最坏 512×160，**SRAM 候选**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | `CNT` 非法 VL / 错包 |
| `ub_dll_vl` | A | §4.5、§4.5.1–2 | 必做 VL0；M1 开 2，上限 16。**是** | 与信用/调度 | S — VL 标签与使能 | obs 当前 VL | 边带 4 b | 同 | 每 VL 使能位 | `PARAM` VL 数 |
| `ub_dll_credit` | A | §4.6、§4.6.1.2 | 必做独占。共享 **可选（延后）**。M1 **是** | 每 VL | M — 初值/归还/超时 | `tb_inj_crd_cells`、`tb_obs_crd_*`（VL0）；`CRD_TO_DIS` | 不承载数据 | 同 | 每 VL cell/pend：16 b 量级 FF。INIT 640 cell | `PARAM_DLL`（`CREDIT_EXCL` 等）、`CNT_CRD_UF`、`IRQ.CRD_UF`。上电：Credit_Init 随 SM |
| `ub_dll_retry` | A | §4.7、§4.7.3 | 必做。M1 **是** | TX 历史 / RX 请求 | L — 双 SM+缓冲 | obs `RETRY_*_ST`；禁 force SM | 160 b 重放 | 同 | **256×160（M1）/ 最大 8192×160（§4.7.3.2）— SRAM**。开源 PDK 宏有限，优先单口编译器或外挂模型。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | `PARAM_RETRY`、阈值 15/4（草案）、`IRQ` 重传异常 |
| `ub_dll_bcrc` / `ub_dll_bcrc_check` | A | §4.3.2.2.4、§4.7.2 | CRC 模式必做。非 CRC **可选（延后）**。M1 **是** | 每 DLLDB | M — CRC30 流式 | 无钩子；叶子口 `crc_ok`/`error_flag_rx` | 160 b/拍 | 同 | 30 b 余数 FF | TX `ERROR_FLAG` 恒 0（M1） |
| `ub_dll_init` | A | §4.3.3.9、§4.4 | 必做（可并入 `ub_dll`）。M1 **部分** | SM Param_Init | M — Init Block 协商 | obs 协商完成 | DLLCB 160 b | 同 | 协商影子 FF | 粒度/VL 读回 |

---

## 3. 第 5 章 Network — 线 A

必做（控制器）：地址、路由处理、SL→VL、对上层交付（§5.1、§5.3.1–2、§5.3.4）。ICRC §5.3.7、死锁避免 §5.3.6、拥塞标记 §5.3.5：控制器侧需做的最小集 **未知**（部分写 Switch）。IP/NPI §5.2.3 / §5.3.3：**可选**。多端口/ROUTE_TABLE：非单端口 M1。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_nw` | A★ | §5.1 | 必做。M1 **否**（桩） | 上：TP/TA(bypass)；下：DLL | L — 编解码+路由+QoS | obs 路由命中/丢弃、SL、NLP；建议 `tb_obs_nw_st` | 建议仍 **1×160 b/拍** 对接 DLL；包长受 §5.3.8 | 建议同 `core_clk`；跨时钟 **未知** | 见子块 | CNA、SL-VL 表、ROUTE（后期）→ yaml |
| `ub_nw_nth` | A★ | §5.2.1–3 | 必做至少一种 NTH。16-b CNA 优先（草案）。24-b / IP **可选（延后）** | 组包/拆包 | M — 三种头 | obs RT/NLP/CFG | 头字段拼进 160 b 流 | 同 | 无大存储 | 地址格式选择 |
| `ub_nw_addr` | A★ | §5.3.1 | 必做 | UBFM/软件 | S — CNA/IP 绑定 | obs 本端 CNA | 控制 | 同 | 本端地址 FF；多 Entity 表深 **未知** | 静态/动态配置（§5.3.1） |
| `ub_nw_route` | A★ | §5.3.2、§5.3.2.2 | 单端口最小：本端/转发判定。多端口表 **可选（延后）** | NTH.RT / LBF | L — 若上全表 | `tb_inj` 路由失败（建议） | 包流 160 b | 同 | App. D ROUTE_TABLE 切片地址空间大（§10.4.1.3）— **必 SRAM / 或外置**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | `CFG0_ROUTE_TABLE`（M1 不做） |
| `ub_nw_qos` | A★ | §5.3.4、§4.5 | 必做 SL→VL | 上 SL；下 `nw_tx_vl[3:0]` | S — 映射表 | obs SL/VL | 边带 | 同 | 16×4 b 级 FF | SL-VL 映射窗 |
| `ub_nw_cng` | A | §5.3.5 | 标记模式可选（延后）组合。最小集 **未知** | CCI 16 b | M — FECN/CAQM | obs 标记事件 | CCI 随包 | 同 | 无 | 拥塞模式 |
| `ub_nw_npi` | A | §5.3.3 | 可选（延后）（IP 隔离） | IP NTH | M | obs NPI 失配丢弃 | 25 b NPI | 同 | 分区表深 **未知** | NPI |
| `ub_nw_icrc` | A | §5.3.7 | 控制器是否 SHALL 全程：**未知**（节有算法） | 包尾 | M — CRC+位反 | 无钩子 | 流式，宽 **未知**（建议按字节） | 同 | CRC 状态 FF | 错 ICRC 计数 |
| `ub_nw_deadlock` | A | §5.3.6 | 避免策略可选（延后）组合。最小 **未知** | 路由/VL | M | obs 超时丢包 | 控制 | 同 | 超时器 | 超时阈值 |

---

## 4. 第 6 章 Transport — 线 B

模式：RTP / CTP / UTP / TP bypass（§6.3）。bypass 对 Load/Store 常用（§6.3、§7.1）— 开通数据通路建议先做。RTP 可靠+多径+拥塞：大。CTP：依赖下层可靠。UTP：轻。TPG/共享信道 §6.5：**可选至 RTP 需要时**。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_tp` | B★ | §6.1、§6.3 | 至少一种模式+bypass。M1 **否** | 上：TA；下：NW | L — 多模式 | obs 模式、TPEP、PSN | 包；拍宽 **未知**（建议 160 b 流或整包 valid/ready） | 建议 `core_clk` | 见子块 | TP 信道/MTU |
| `ub_tp_bypass` | B★ | §6.3、§7.1 | Load/Store 通路 **建议先做** | TA↔NW 直通 | S — 无 TPH | obs bypass 使能 | 与 NW 同宽 | 同 | 无 | 模式位 |
| `ub_tp_rtp` | B | §6.3.1、§6.4、§6.7.1 | 可靠业务必做（非 LS 捷径）。可后加 | TA 操作↔TP Packet | L — PSN/ACK/NAK/SACK | obs PSN/EPSN、ACK/NAK；禁 force 窗口 | 分段按 TP MTU（数值 **未知**） | 同 | 发送窗+重传/重排：**SRAM 候选**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 信道、窗口、定时器 |
| `ub_tp_ctp` | B | §6.3.2、§6.7.2 | 可选（延后）（直连/高质量） | 同 | M — 无 TPACK | obs CNP | 同 | 同 | 小于 RTP | Entity/VL 拥塞态 |
| `ub_tp_utp` | B | §6.3.3 | 可选（延后）（建链等） | 同 | S | obs 丢包不上报策略 | 同 | 同 | 无重传 | 无 |
| `ub_tp_retry` | B | §6.4.2 | RTP 必做。Go-Back-N vs 选择重传：实现选一 **未知** | RTP | L | obs 重传原因/次数 | 同 RTP | 同 | 同 RTP 窗 **SRAM**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 阈值 |
| `ub_tp_tpg` | B | §6.5.1 | RTP 多径 **可选（延后）** | 多信道 | L | obs 成员信道 | 调度 | 同 | TPG 上下文 **未知** | TPG 管理 |
| `ub_tp_cc` | B | §6.6 | RTP/CTP 拥塞 **可选（延后）至需要** | CETPH/CCI | L — 窗/速率/CAQM | obs 窗/速率 | 控制 | 同 | 每信道状态 | CC 模式 |

---

## 5. 第 7 章 Transaction — 线 B

必做：BTAH、与下层协调、至少内存 Read/Write（§7.2、§7.3.4、§7.4.2）。消息/原子/维护/管理：按功能层需要。服务模式 ROI/ROT/ROL/UNO 与 TP 绑定（§7.3.3–4）。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_ta` | B★ | §7.1 | 必做。M1 **否** | 上：FUN；下：TP/NW | L | obs 模式/Opcode/TASSN | 操作；拍宽 **未知** | 建议 `core_clk` | 未完成事务表 **SRAM 候选**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 模式、MTU |
| `ub_ta_hdr` | B★ | §7.2 | 必做 BTAH；扩展头随操作 | 组包 | M — 全/紧凑头 | obs TAOpcode、Poison | 头字段宽见表 7-1 量级（8/16/…）；不抄表 | 同 | 无 | 无 |
| `ub_ta_mem` | B★ | §7.4.2 | Read/Write **建议先做**。atomic/BE/notify **可选（延后）后加** | FUN LS/URMA；MEM | L | obs 完成/失败；`INI_TASSN` | 净荷；最大受下层 MTU | 同 | 分段重组 **未知** | 无（完成走 FUN） |
| `ub_ta_msg` | B | §7.4.3 | URMA/消息时必做 | Jetty | M | obs Send 完成 | 同 | 同 | 同 | 无 |
| `ub_ta_atomic` | B | §7.4.2.3 | 可选（延后） | MEM | M | obs 原子完成 | 最长 64 B 量级（§7.4.2.3） | 同 | 小 | 无 |
| `ub_ta_maint` | B | §7.4.4 | 可选（延后） | 目标维护 | S | obs Prefetch | 小 | 同 | 无 | 无 |
| `ub_ta_mgmt` | B | §7.4.5、§10.4.3 | 管理消息时必做 | RSC | M | obs MSN 匹配 | 管理净荷 | 同 | 未决 MSN 表深 **未知** | 与配置访问共用 |
| `ub_ta_order` | B | §7.3.2–3 | 按所选模式必做 | TA 内部 | M — TEO/TCO | obs 序违规 | 控制 | 同 | 序队列深 **未知** | 模式 |

---

## 6. 第 8 章 Function — 线 B

编程模型：Load/Store 同步 §8.3、URMA 异步 §8.4。高级：URPC §8.5、多 Entity §8.6、Entity 管理 §8.7（与第 10 章重叠）。开通端到端通路建议先 **Load/Store**。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_fun_ls` | B★ | §8.3 | 开通通路 **建议先做** | 上：NoC/CPU；下：TA；侧：decoder | M — 指令→事务 | obs 未完成 LS、Poison | CPU 口宽 **未知**（SoC）；内部到 TA 同 TA | 域 **未知**（可能相对 `core_clk` 为 SoC 时钟→需 CDC） | 未完成 LS 表 | 无独立 UB 窗（映射走 decoder） |
| `ub_fun_urma` | B | §8.4、§8.2.3 | 异步模型必做（可后于 LS） | 软件队列↔TA | L — SQ/CQ | obs SQE/CQE、异常模式 | 队列元素宽 **未知** | 建议 `core_clk` | SQ/CQ：**SRAM**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | Jetty/JFC 基址、门铃 |
| `ub_fun_jetty` | B | §8.2.2、§8.2.2.3 | URMA 必做 | URMA / 对端 | L — Reset/Ready/Suspend/Error | **`tb_obs_jetty_st`**；禁 force 非法态 | 控制+数据描述符 | 同 | 每 Jetty 上下文 **SRAM 候选**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | Jetty 属性、修改/销毁 API 对应 CSR |
| `ub_fun_seg` | B | §8.2.1 | 内存段创建/删 | MEM/UMMU | M | obs 段在用 | 控制 | 同 | 段表深 **未知 SRAM**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | UBMD 句柄 |
| `ub_fun_urpc` | B | §8.5、App. H | 可选（延后） | LS/URMA | L | obs RPC 未决 | 消息 | 同 | 参数缓冲 **未知** | URPC 端点 |
| `ub_fun_coord` | B | §8.6 | 可选（延后） | 多 Entity | L | obs 集合进度 | 控制 | 同 | **未知** | 协调组 |
| `ub_fun_entity` | B | §8.7、§10.3 | 与 RSC 合并或薄封装 | RSC | M | 见 `ub_rsc_*` | 控制 | 同 | 见 RSC | 见 RSC |

---

## 7. 第 9 章 Memory — 线 C（decoder 最小表可服务优先通路）

UMMU（Home）§9.4、UB decoder（User）§9.5、UBMD §9.3。查表结构大，**优先 SRAM**。延迟分配 MAY（§8.2.1.1）。大表钩子：每张表 backdoor 预载 + 回读，仅 HOOKS 网表；待与表格式一并写入 SPEC §10。

C 线命名、所有权与公开/私有边界对齐 [mem/contracts/README.md](mem/contracts/README.md) 与 [mem/UARCH.md](mem/UARCH.md) §3。六片解码叶子为 S-01(b) 私有叶子（契约作者 架构 Xia，实现所有权 设计-C）。结构叶子公开，所有权 设计-C。私有叶子公开面为端口桩与本目录契约。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_mem_ummu` | C | §9.4 | Home 内存访问必做。公开结构；所有权 设计-C | TA 目标；表 | L — 查表流水 | obs 翻译/权限失败（Class 错，§10.6.2）。大表 backdoor 在子块 | UBA 64 b（§9.3）；PA 宽 **未知** | 建议 `core_clk`；表口频率 **未知** | 见子块 | UMMU 配置/失效 |
| `ub_mem_cfg_lkup` | C | §9.4.2.1 | 必做。公开结构；所有权 设计-C | UMMU；例化 `ub_mem_tecte_dec` | M | obs 配置未命中；每张大表 backdoor 预载 + 回读，经 `tb_<inst>_bd_we/addr/wdata`、`tb_<inst>_bd_re/rdata`（宽随表项格式，格式未关前 **未知**）；仅 HOOKS；见 SPEC §10.5 | 控制 | 同 | 配置表深 **未知 SRAM**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 配置基址 |
| `ub_mem_tecte_dec` | C | §9.4.2.1；契约 `ub_mem_tecte_dec.md` | 必做。S-01(b) 私有叶子；所有权 设计-C；契约 架构 Xia | 上：CSR 写 TECT；父级 `ub_mem_cfg_lkup` | S — TECTE 解码，1 拍寄存 | 公开契约口；原始表项切分在独立私有仓库 | `raw` 512；出 `cfg_*` 束 | 同 `core_clk` / `rst_pyc` | 无 | 无 |
| `ub_mem_ctx_lkup` | C | §9.4.2.2 | 必做（线性/两级选一或都做：**未知**）。公开结构；所有权 设计-C | UMMU；例化 `ub_mem_tcte_dec`、`ub_mem_l1tct_dec` | L | obs TCT 未命中；每张大表 backdoor 预载 + 回读，经 `tb_<inst>_bd_we/addr/wdata`、`tb_<inst>_bd_re/rdata`（宽随表项格式，格式未关前 **未知**）；仅 HOOKS；见 SPEC §10.5 | 同 | 同 | TCT **SRAM**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | TCT 基/格式 |
| `ub_mem_tcte_dec` | C | §9.4.2.2.2；契约 `ub_mem_tcte_dec.md` | 必做。S-01(b) 私有叶子；所有权 设计-C；契约 架构 Xia | 上：TCT 填充；父级 `ub_mem_ctx_lkup` | S — TCTE 解码，1 拍寄存 | 公开契约口；原始表项切分在独立私有仓库 | `raw` 512；出 `ctx_*` 束；`ILL_MAP_2MB` 只对应 TCTE 范围表 2 MB 颗粒度 | 同 `core_clk` / `rst_pyc` | 无 | 无 |
| `ub_mem_l1tct_dec` | C | §9.4.2.2.3；契约 `ub_mem_l1tct_dec.md` | 必做。S-01(b) 私有叶子；所有权 设计-C；契约 架构 Xia | 上：两级 TCT；父级 `ub_mem_ctx_lkup` | S — L1 TCT 描述符解码，1 拍寄存 | 公开契约口；原始表项切分在独立私有仓库 | `raw` 64；出 `l1tct_*` 束 | 同 `core_clk` / `rst_pyc` | 无 | 无 |
| `ub_mem_xlat` | C | §9.4.3 | 必做。公开结构父级（`ub_mem_tlb` + `ub_mem_ptw`）；所有权 设计-C | UBA→PA；`ub_mem_ptw` 例化 `ub_mem_ptw_desc_dec` | L | obs 页失败；每张大表 backdoor 预载 + 回读，经 `tb_<inst>_bd_we/addr/wdata`、`tb_<inst>_bd_re/rdata`（宽随表项格式，格式未关前 **未知**）；仅 HOOKS；见 SPEC §10.5 | 同 | 同 | MATT **SRAM**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 失效/填表 |
| `ub_mem_ptw_desc_dec` | C | §9.4.3；契约 `ub_mem_ptw_desc_dec.md` | 必做。S-01(b) 私有叶子；所有权 设计-C；契约 架构 Xia | 上：`ub_mem_ptw`（TLB 回填 / 页表遍历） | S — 页表描述符解码，1 拍寄存 | 公开契约口；原始表项切分在独立私有仓库 | `raw` 64；`AP_PTW_KIND`：`desc_v` 当且仅当 `desc_kind≠0` | 同 `core_clk` / `rst_pyc` | 无 | 无 |
| `ub_mem_perm` | C | §9.4.4 | 必做。委托软件 MAY。公开结构父级（`ub_mem_plb` + `ub_mem_perm_walk` + `ub_mem_perm_cmp`）；所有权 设计-C | Token/MAPT；`ub_mem_perm_walk` / `ub_mem_plb` 例化 `ub_mem_mapte_dec` | L | obs Token/排他/类型失败；每张大表 backdoor 预载 + 回读，经 `tb_<inst>_bd_we/addr/wdata`、`tb_<inst>_bd_re/rdata`（宽随表项格式，格式未关前 **未知**）；仅 HOOKS；见 SPEC §10.5 | Token 宽 **未知** | 同 | MAPT **SRAM**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 权限失效（与 §11.4 交叠） |
| `ub_mem_mapte_dec` | C | §9.4.4.2；契约 `ub_mem_mapte_dec.md` | 必做。S-01(b) 私有叶子；所有权 设计-C；契约 架构 Xia | 上：`ub_mem_perm_walk` / `ub_mem_plb` | S — MAPTE 解码，1 拍寄存 | 公开契约口；原始表项切分在独立私有仓库 | `raw` 256；出 `mapte_*` 束 | 同 `core_clk` / `rst_pyc` | 无 | 无 |
| `ub_mem_decoder` | C★ | §9.5、§8.3 | User LS 必做。公开结构父级（`ub_mem_dec_walk` + `ub_mem_dec_tlb` + `ub_mem_dec_uba`）；所有权 设计-C | PA→UBMD；`ub_mem_dec_walk` 例化 `ub_mem_dec_ent_dec` | M | obs 翻译失败；每张大表 backdoor 预载 + 回读，经 `tb_<inst>_bd_we/addr/wdata`、`tb_<inst>_bd_re/rdata`（宽随表项格式，格式未关前 **未知**）；仅 HOOKS；见 SPEC §10.5 | PA→EID+TokenID+UBA | 同 | 解码表 **SRAM 候选**。**须**例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 用户侧映射 |
| `ub_mem_dec_ent_dec` | C | §9.5.1；契约 `ub_mem_dec_ent_dec.md` | 必做。S-01(b) 私有叶子；所有权 设计-C；契约 架构 Xia | 上：`ub_mem_dec_walk`（已寄存的 L0/L1 读回） | S — 译码器表项解码，L0/L1 各 1 拍寄存 | 公开契约口；原始表项切分在独立私有仓库 | L0 `raw` 512；L1 宽见契约 §5 暂缓；出 `dent_*` 束 | 同 `core_clk` / `rst_pyc` | 无 | 无 |
| `ub_mem_ubmd` | C | §9.3 | 描述符格式；可并入上列。公开解码；所有权 设计-C | 各内存口 | S | 无 | EID/TokenID 宽 **未知**；UBA 64 b | 同 | 无 | 无 |

---

## 8. 第 10 章 Resource + 规范管理功能 — 线 C

配置空间 §10.4.1、管理命令/枚举 §10.4.3、LNA §10.4.4、中断/事件 §10.3.4–5、池化 Entity §10.4.5、虚拟化 §10.5（**可选**）、RAS/复位 §10.6。附录 F 链路网管、附录 G 热插拔：见 §11 管理行。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_rsc_cfg` | C | §10.4.1、App. D | 必做；窗分期 | 管理消息 / 本地 CSR | L — 切片译码 | obs 权限拒绝（NTH.Mgmt/UPI） | 32 b 窗；并发 MSN（§10.4.1.2） | 同 `core_clk` | 切片体：多数 FF；ROUTE **SRAM**。应当例化 `ub_cmn_mem_1r1w`。ROUTE stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | **全部写入 `regmap.yaml`**。CFG0 vs CFG1 权限 |
| `ub_rsc_cmd` | C | §10.4.3 | 必做管理事务通路 | TA mgmt | M | obs 命令/响应 MSN | 管理包 | 同 | 未决请求深 **未知** | 命令状态 |
| `ub_rsc_enum` | C | §10.4.3.2、App. B.3 | 枚举必做（可后于数据通路） | UPIH | M | obs 枚举进度 | 控制 | 同 | 拓扑缓存 **未知** | 枚举表 |
| `ub_rsc_irq` | C | §10.3.4 | 必做一类中断（Type1/2 选配 **未知**） | 软件 / 消息 | M | obs 中断 pend；合成进顶层 `irq` | 寄存器/消息 | 同 | 每源 1 b | Type1/2 窗、mask |
| `ub_rsc_event` | C | §10.3.5 | 本地必做；远端可后 | 各层事件 | M | obs 事件队列水位 | 队列 | 同 | 事件 Q **SRAM 候选**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 事件 Q 基/头尾 |
| `ub_rsc_cna` | C | §10.4.4 | LNA 必做（邻接） | NW 地址 | S | obs 邻接 CNA | 控制 | 同 | 邻接表小 | LNA / `PORT_CNA` |
| `ub_rsc_pool` | C | §10.4.5、§8.7 | 池化 **可选（延后）至 UBFM** | UBFM | L | obs 注册态 | 控制 | 同 | 角色表 | 注册/注销 |
| `ub_rsc_virt` | C | §10.5 | 可选（延后） | Entity | L | obs VF 复位 | 控制 | 同 | 每 Entity 副本 **SRAM**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | VF 初始化/中断/复位 |
| `ub_rsc_ras` | C | §10.6 | 复位+错误记录必做 | 全芯片 | M | obs Class A/B/C；**禁 force 造错打满** | 控制 | 含销级复位（§10.6.1.2.3）域 **未知** | 错误记录/消息 Q（§10.6.2.4）**SRAM 候选**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 复位命令、错误记录。上电：设备/端口/Entity 复位分层 |

---

## 9. 第 11 章 Security — 线 C

功能可按场景裁剪（§11.1.3）。接入认证、分区、访问控制、CIP、TEE 扩展。密钥加载属软件可见上电序列。

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_sec_auth` | C | §11.2 | 场景可选（延后）；产品是否必做 **未知** | 设备/互连 | L | obs 认证成败；**无明文密钥 obs** | 控制 | 同或安全岛 **未知** | 证书/测量 **未知 SRAM**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 认证状态。上电：**密钥/信任锚加载**（介质 **未知**） |
| `ub_sec_part` | C | §11.3、§5.3.3 | 与 NPI/UPI 一起 | NW/TA | M | obs 分区失配 | 边带 | 同 | 分区表 | UPI/NPI |
| `ub_sec_acl` | C | §11.4、§9.4.4 | 与 UMMU 权限交叠 | MEM/Jetty | L | obs 拒绝；失效命令 | 控制 | 同 | 与 MAPT 共用 **SRAM**。应当例化 `ub_cmn_mem_1r1w`。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 权限分配/失效 |
| `ub_sec_cip` | C | §11.5 | 可选（延后）（数据通路保护） | 包流 | L — 建链/加解密/完整性 | obs 通道态、完整性失败；禁导出密钥 | 须跟上包吞吐；加解密并行度 **未知** | 同或加速器时钟 **未知** | 密钥/会话 **安全存储，非普通 SRAM 开源宏**。行为 stub 应当例化 `ub_cmn_mem_1r1w`（换安全宏仍不改功能口）。stub 时序（Xia 提案，非规范）：读 1 拍寄存、1R1W、同址 read-old | 通道建立、**密钥加载/更新**（§11.5.2.1、§11.5.2.6） |
| `ub_sec_tee` | C | §11.6 | 可选（延后） | EE_bits（§7.2.1） | L | obs TEE 模式 | 控制+隔离 | **未知** | 隔离存储 **未知** | TEE 配置 |

---

## 10. 附录管理（规范定义的管理功能）— 延后，M10 之后

| 模块 | 线 | 节号 | 必做 / 可选 | 上游 / 下游 | S/M/L | 可观察性 / 钩子 | 数据通路 / 吞吐 | 时钟复位 + 频率 | 存储 | 软件可见面 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ub_mgmt_lna` | 延后 | §10.4.4；可与 `ub_rsc_cna` 合一 | 邻接广告 | NW | S | obs 邻接刷新 | 控制 | `core_clk` | 小 | LNA |
| `ub_mgmt_net` | 延后 | App. F | 可选（延后）（链路网管） | 管理协议 | M — 协议选哪支 **未知** | obs 管理会话 | 管理包 | 同 | **未知** | App. F 协议窗 |
| `ub_mgmt_hotplug` | 延后 | App. G | 可选（延后） | 端口/电源 | M | obs 热插拔事件（G.5） | 事件 | 销/电源域 **未知** | 小 | 热插拔事件/命令 |
| `ub_mgmt_eth` | 延后 | App. E | 可选（延后）（UBoE/以太） | NW IP | L | 非 M 前期 | 以太 | **未知** | **未知** | 非本栈前期 |

UBFM 本体是域管理器（§2.2），**不是** 本控制器必做 RTL；控制器实现被管接口（配置空间、管理消息、LNA）。

---

## 11. 各层模块计数（S/M/L）

行按上表「模块」列计（enc/dec 等成对行计 1）。

| 层 | 线 | 章 | 模块数 | S | M | L | M1 已覆盖（是/部分） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 公共 | A/B/C | — | 4 | 2 | 2 | 0 | 4 |
| PHY | A | 3 | 10 | 2 | 4 | 4 | 10（交织部分） |
| DLL | A | 4 | 7 | 1 | 4 | 2 | 7 |
| NW | A | 5 | 9 | 2 | 5 | 2 | 0 |
| TP | B | 6 | 8 | 2 | 1 | 5 | 0 |
| TA | B | 7 | 8 | 1 | 5 | 2 | 0 |
| FUN | B | 8 | 7 | 0 | 3 | 4 | 0 |
| MEM | C | 9 | 13 | 7 | 2 | 4 | 0 |
| RSC | C | 10 | 9 | 1 | 5 | 3 | 0（CSR 窗仅端口子集） |
| SEC | C | 11 | 5 | 0 | 1 | 4 | 0 |
| 附录管理 | 延后（M10+） | F/G/E | 4 | 1 | 2 | 1 | 0 |
| **合计** | | | **84** | **19** | **34** | **31** | **21** |

★ = 优先通路（NW→TP→TA→LS）争资源时赢。`ub_mem_decoder` 属线 C，最小表可提前服务优先通路。

不可达章：无。第 3–11 章及附录 D/F/G/E/H 节标题均从私有 Rev 2.0 副本读到。附录 E/H 只作索引，未在本清单展开字段。

---

## 12. SRAM / PDK / stub 时序

开源 PDK（如 Sky130 代理）编译器宏种类/最大深度有限。优先 SRAM 的块：`ub_dll_retry`、DLL RX 重组（若按 512 flit 存）、`ub_nw_route`（多端口时）、RTP 重传窗、Jetty SQ/CQ、UMMU MATT/MAPT/TCT、RAS 错误 Q、CIP 密钥库（后者还有安全属性，普通宏可能不够）。其余优先 FF。深度未裁定者保持 **未知**，不在本文件锁死。

**行为 stub 时序（Xia 提案，非规范；规范未裁定处用此默认）：**

- 读延迟：1 拍寄存读
- 端口：1R1W
- 同址冲突：read-old
- 约束：stub 可换成 SRAM 宏，**不改端口、不改测试**。规范若另给时序，以规范为准并在该格写明。

**统一原语：** 上列时序与口形对应 `ub_cmn_mem_1r1w`（CODING_STYLE 存储节：`DEPTH`/`WIDTH`；`clk`；阵列无复位；`we/waddr/wdata` + `re/raddr/rdata`）。线 B RTP 重传/重排、TA 未决与线 C UMMU/decoder 大表 **必须**例化；其它 SRAM / stub 大缓冲 **应当**例化，避免第二套口。换宏不改口/测试。

第 9 章 UMMU / decoder 大表另有 HOOKS-only backdoor（`tb_<inst>_bd_we/addr/wdata`、`tb_<inst>_bd_re/rdata`）；口宽随表项格式，格式未关前 **未知**。点名表与门控见 SPEC §10.5。PRODUCT 无这些 `tb_*`。

---

## 13. 线 A 本批叶子细则

§1 表已登记 `ub_pcs_nullblk_det`（出 `pcs2lmsm_null_blk` / `pcs2lmsm_rx_nonnull_blk` / `pcs2lmsm_tx_null_blk`）。LMSM↔PCS 口表见 [SPEC.md](../SPEC.md) §3.3.4；[LAYER_CONTRACTS.md](LAYER_CONTRACTS.md) 不重复该口。PCS 本批三叶的 §3 表见 [pcs/UARCH.md](pcs/UARCH.md)。下列为线 A 本批冻结细则（Xia 裁定 2026-10-12），不改 §0–§12 表行列。

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
| 置位 | 全部已配置 lane（`pma_rx_width`）的分 lane「已收 SDF」旗都立起之后，再寄一拍。末已配置 lane 的 AMCTL **末字**在 **t** → `cw_dec` 输出在 **t+1** → `pcs_rx_sdf_seen` 从 **t+2** 起为 1。旗在 `amctl_vld` 且 `ctrl_ok` 且 `lid_ok` 且 `LW_SWITCH`+{`X1`,`X2`,`X4`,`X8`} 且 `lmsm2pcs_nb_phase==1` 时置。SDF / EDF 与稳健性见 `ub_pcs_amctl_rx` |
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
| 3 | SDF / EDF | Xia 裁定 2026-10-12（M3） | 「带 SDF」：`CTRL_TYPE` = `LW_SWITCH` 且 `CTRL_DETAIL` ∈ {`X1`,`X2`,`X4`,`X8`}（§3.2.4.2「AMCTL Controlling」），且当拍 `lmsm2pcs_nb_phase==1`。「带 EDF」：同类型且 `CTRL_DETAIL` = `X0`。`amctl_rx` 为每 lane 记「已收 SDF」旗（在 `amctl_vld` 且 `ctrl_ok` 且 `lid_ok` 上置；见稳健性）。`pcs_rx_sdf_seen` 仍要全部已配置 lane；拍位 **t / t+1 / t+2** 见下表 |
| 4 | 「全部已配置 lane」来源 | 已有配置口 | `pma_rx_width[3:0]`（§3.2.5，与 `PARAM_PHY.NUM_LANES_RX[13:10]` 同编码，§9）；参数 `NUM_LANES_RX`。§3.3.4 无 LMSM→PCS 宽度口 |
| 5 | LID 出口 | Xia 裁定 2026-10-12 | `pcs_rx_lid` 宽 **4**：lane 0..7 加空身份，公开只称 `LID_NULL`（`LID_NULL` 的线码/半场编码是 `ub_pcs_amctl_cw_dec` 私有叶细节）。`pcs_rx_lid_vld`：全部已配置 lane 上 LID 一致解码时 **1 拍脉冲** |
| 6 | 对私有叶输出的稳健性 | 本清单 | 见下节。`amctl_rx` 对 `cw_dec` **任意**输出保持合法状态；formal 把 `cw_dec` 出口当自由输入 |

### 对私有叶输出的稳健性

`ub_pcs_amctl_rx` 必须对 `ub_pcs_amctl_cw_dec` 的**任意**输出保持合法状态。形式化把各 `cw_dec` 出口当作自由输入；默认任务**不**把契约 `AP_CWDEC_*` 当 assume。

1. 限定场与各 `*_ok`（`end_ok` / `lid` / `lid_ok` / `ctrl_type` / `ctrl_type_ok` / `ctrl_detail` / `ctrl_detail_ok`）**只在** `amctl_vld=1` 时采用；`amctl_vld=0` 时忽略。
2. `amctl_vld=1` 且（`ctrl_ok=0` 或 `lid_ok=0`）视为「不是 AMCTL」：不置 SDF/EDF，不更新 LID。此处 `ctrl_ok` = `ctrl_type_ok && ctrl_detail_ok`。
3. 分 lane「已收 SDF」旗与 `pcs_rx_sdf_seen` **只**按本清单已写的置位/清零规则变化（核对表 #3 与拍位表）。

`end_hit` 不受 `amctl_vld` 限定，仍供锁定/滑窗（核对表 #1）。

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
| **t+1** | 该 lane 的 `ub_pcs_amctl_cw_dec` 输出（`amctl_vld` 及限定场）。`amctl_rx` 在 `amctl_vld` 且 `ctrl_ok` 且 `lid_ok` 且 `LW_SWITCH`+{`X1`,`X2`,`X4`,`X8`} 且 `lmsm2pcs_nb_phase==1` 时置该 lane「已收 SDF」旗（`ctrl_ok` / 非 AMCTL 见上节稳健性） |
| **t+2** | 全部已配置 lane 旗已立时，`pcs_rx_sdf_seen` 从本拍起为 1（`amctl_rx` 多一拍寄存） |

清零：`lmsm2pcs_nb_phase==0` 或复位的下一拍；分 lane 旗一并清。

`ub_pcs_scrambler` / `ub_pcs_descrambler` 在 `_placeholder` 期间（§13 A-01 / A-02，D20）不接 `pcs_rx_lid`：该输入口悬空并 Tie 到占位常量，种子保持 placeholder。lint waiver 注记：`placeholder, D20`。

---

## `ub_pcs_amctl_cw_dec`

**船长已确认：** 走 C 线 S-01(b)。公开仓只留端口桩；源码在 `lukebest/Vibe-UB-private`；码字表不进公开 SPEC。契约 [docs/arch/pcs/contracts/ub_pcs_amctl_cw_dec.md](pcs/contracts/ub_pcs_amctl_cw_dec.md)。YAML 头 schema 源：[docs/arch/mem/contracts/README.md](mem/contracts/README.md) §8（main `73cfa6e1`，#49；含必填 `assertions:`）。

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
