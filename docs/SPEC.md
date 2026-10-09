# Vibe-UB M1 功能规格

| 项 | 值 |
| --- | --- |
| 文档状态 | 草案 |
| 适用范围 | M1：开源 UnifiedBus（UB，灵衢）控制器的 PHY/PCS/PMA 模型边界 / LMSM / DLL |
| 规范基线 | UB Base Specification Rev 2.0（2025-12-31），见 [DECISIONS.md](DECISIONS.md) D1 |
| 阶段范围 | [SPEC_INDEX.md](SPEC_INDEX.md) phase 1：第 3 章 PHY/PCS/PMA/LMSM，第 4 章 DLL，附录 D 寄存器子集 |
| 实现语言 | 产品 RTL 一律由 pyCircuit（pyc4.0）生成，见 [CODING_STYLE.md](CODING_STYLE.md)、D5/D6 |
| 配套寄存器 | [REGMAP.md](REGMAP.md) |

**引用约定：** 本仓库不收录规范正文、表格、图或寄存器字段说明。行为以节号引用（例如「见 UB-PHY §3.2.2.3」）；需要落到设计时，只用自己的短句转述。完整规范须从 [unifiedbus.com](https://www.unifiedbus.com) 取得，并遵守 UB Specification License Agreement。

**未知 / 待定 / 草案：** 未决事项写「未知」或「待定」，不编造。§9 的 M1 默认参数已由船长确认（关闭 D14 中该项）；工艺节点仍为「未知，待船长定」。其余未决项见 §13。

**现有 `rtl/`：** 仅作参考，将按 D10 迁入 `legacy/` 后重写。本规格与现网 RTL 的已知冲突见 §12。

---

## 1. 范围与非目标

### 1.1 M1 范围（目标）

M1 实现一条 **单端口** UB 链路控制器的数字部分，使上层（M1 用 Network Layer 桩）能在链路训练完成后，按 flit 收发、按 VL 流控、按 CRC/FEC 触发重传。

| 块 | M1 做什么 | 规范锚点 |
| --- | --- | --- |
| PMA 模型边界 | 行为模型，不进产品 RTL（D3）。Gray / 预编码 / 串并转换 / CDR 在模型侧 | UB-PHY §3.3、§3.3.1、§3.3.2 |
| PCS | FEC、加扰/解扰、按 **8-bit 符号** 分发与回收、AMCTL 插入/锁定/deskew | UB-PHY §3.2 |
| LMSM | 链路训练与恢复（电气、Mode-2、Data Rate 0 为 M1 默认） | UB-PHY §3.4、§3.4.3 |
| DLL | DLL 状态机、DLLCB/DLLDP、VL、信用、重传、Init Block 协商 | UB-DL §4.2–§4.8 |
| 寄存器 | 附录 D **端口/链路子集** + M1 本地控制/状态/计数/参数读回 + 测试窗 | UB-spec App. D；[REGMAP.md](REGMAP.md) |
| 两套网表 | Python 生成期展开 `TEST_HOOKS`，PRODUCT 与 HOOKS | §11；[CODING_STYLE.md](CODING_STYLE.md) §1 |
| CDC | 业务逻辑同步复位；跨时钟只走白名单单元（D6） | 见 §4 |

M1 默认参数（船长已确认，出处见 §9）：

- PHY Mode-2，速率 Data Rate 0：2.578125 Gbit/s NRZ
- lane：bring-up 从 x1 做到 x4；RTL 参数化到 x8
- 非对称 lane 数：规范允许，M1 **默认关**；TX/RX lane 数仍各自参数化
- FEC：RS(128,120,T=4) 默认；T=2 / bypass 可协商
- VL：2（VL0+VL1），参数上限 16
- 重传缓冲：256 flit
- 信用：1 flit/cell，credit/ACK 粒度 32，独占模式，每 VL INIT 640 cell

### 1.2 非目标（M1 不做）

| 非目标 | 依据 |
| --- | --- |
| 第 5 章 Network Layer 及之后（TP/TA/FUN/MEM/RSC/SEC） | D2；SPEC_INDEX deferred |
| 规范可选特性（D4）：不把「可选」当成 M1 必做 | D4 |
| M1 多时钟域（独立 `pma_clk`） | 架构已定：单时钟；见 §4.1 |
| 真实 SerDes / PMA 模拟电路 | D3 |
| FPGA 原型 | D11 |
| 多端口、路由表、Entity / CFG1、热插拔、光模块管理、眼图监测 | App. D 中与 NW/设备管理相关的切片；UB-PHY 光互连细节 |
| QDLWS、运行中快速降宽、速率爬升到 25.78125G / PAM4 | UB-PHY §3.4.2.3、§3.4.2.4、§3.4.2.5；M1 固定 Data Rate 0 |
| 手写产品 SystemVerilog、SV-UVM、对内部信号 `force` | D5、D7、D13 |
| 把规范全文或字段表写进本仓库 | D15 |

速率不对称：规范不允许（见 UB-PHY §3.1.1、§3.4.2.5）。M1 不提供 TX/RX 不同 Data Rate。

### 1.3 与后续里程碑的边界

- M1 对上只提供 **flit + 链路状态**，不解析 Network Header。
- 附录 D 的 CFG0_BASIC 设备级字段、CFG1_*、CFG0_ROUTE_TABLE：M1 **不实现**；软件若需要完整配置空间，属后续阶段。
- 测试钩子端口与门控见 §10；验证名 `vibe_lmsm` / `vibe_dll_credit` / `vibe_pcs_tx_pack` 分别对应本规格的 `ub_lmsm`、`ub_dll` 信用子块、`ub_pcs` TX。

---

## 2. 框图与模块划分

### 2.1 顶层框图

```mermaid
flowchart LR
  subgraph host [Host / 上层桩]
    NW[NW flit 接口]
    SW[CSR 主机]
  end

  subgraph ub [ub_controller]
    CSR[ub_csr]
    DLL[ub_dll]
    PCS[ub_pcs]
    LMSM[ub_lmsm]
  end

  subgraph pma [ub_pma_model 非产品 RTL]
    PMA[PMA 行为模型]
  end

  NW <-->|160b flit valid/ready| DLL
  SW <-->|32b CSR| CSR
  CSR --> DLL
  CSR --> PCS
  CSR --> LMSM
  DLL <-->|码流 + FEC 成败| PCS
  LMSM -->|LinkUp / LinkReady / 训练控制| DLL
  LMSM --> PCS
  LMSM --> PMA
  PCS <-->|每 lane 并行字| PMA
```

PMA 模型在仿真里实例化，与 PCS 的边界是 M1 的 **PHY 数字/模型切分点**（D3）。综合网表不含 `ub_pma_model`。

### 2.2 模块职责

| 模块 | 目录（生成后） | 职责 |
| --- | --- | --- |
| `ub_controller` | `rtl/ub_controller.py` → `.v` | 顶层：例化 CSR / DLL / PCS / LMSM；PMA 模型仅 sim |
| `ub_csr` | `rtl/csr/` | 寄存器堆、译码、W1C；把控制打到各块，回收状态/计数 |
| `ub_dll` | `rtl/dll/` | DLL 状态机、组包/拆包、VL、信用、重传、CRC |
| `ub_pcs` | `rtl/pcs/` | FEC、扰码、8-bit 符号分发、AMCTL、deskew |
| `ub_lmsm` | `rtl/lmsm/` | LMSM 及与 PMA 模型的训练握手 |
| `ub_pma_model` | 不进产品 `rtl/`（路径 **待定**） | Gray（仅 PAM4）、预编码、串并、探测/电气空闲的行为 |

现有 `rtl/pcs/ub_pcs_lmsm.v` 骨架不代表规范 LMSM，M1 以 §6.1 为准重写。

### 2.3 PMA 模型边界

PCS 交给 PMA 的是 **已按 8-bit 符号分发到各 lane 的并行比特**（见 UB-PHY §3.2.2.3、§3.2.5）。下列功能 **不在 PCS**：

| 功能 | 放哪 | 说明 |
| --- | --- | --- |
| Gray 编码/解码 | PMA 模型 | 见 UB-PHY §3.3、§3.3.1。现有 RTL 放在 PCS，M1 纠正 |
| 预编码/解预编码 | PMA 模型 | 见 UB-PHY §3.3.2 |
| 串并转换、CDR、均衡模拟 | PMA 模型 | 见 UB-PHY §3.3。M1 模型深度 **待定** |
| Probe 脉冲与远端端接检测 | PMA 模型 + LMSM | 见 UB-PHY §3.4.3.2。检测算法 **未知**（实现相关） |

M1 默认 NRZ Data Rate 0：Gray **不启用**（Gray 针对 PAM4）。预编码默认 **关**（已定）。ASIC 范围已确认：只做 PCS + DLL 数字；PMA 为行为模型（D3）。

### 2.4 PCS

TX 处理顺序以 UB-PHY §3.2.1–§3.2.2 为准，**不以** 现有 `rtl/ub_controller_tx.v` 的「先扰码再 FEC、再 Gray、再按 2-bit 分 lane」为准。

M1 PCS 子块：

| 子块 | 方向 | 行为（短述） | 节号 |
| --- | --- | --- | --- |
| `pcs_fec_enc` / `pcs_fec_dec` | TX/RX | RS(128,120)，T=4 默认；T=2 / bypass 可协商 | §3.2.2.1、§3.2.3.5 |
| `pcs_scrambler` / `pcs_descrambler` | TX/RX | 加扰/解扰 | §3.2.2.4、§3.2.3.2 |
| `pcs_lane_dist` / `pcs_lane_dedist` | TX/RX | **8-bit FEC 符号** 跨 lane 分发/回收，不是 2-bit | §3.2.2.3、§3.2.5 |
| `pcs_amctl_tx` / `pcs_amctl_rx` | TX/RX | AMCTL 插入、锁定、滑窗、确认 | §3.2.4、§3.2.3.1 |
| `pcs_deskew` | RX | 多 lane 对齐 | §3.2.3.1 |
| 交织/解交织 | TX/RX | 仅当 FEC 交织（CodecNum=2）开启；M1 默认 **待定**（建议 CodecNum=1） | §3.2.2.3、§3.2.3.4、§3.2.3.6 |

### 2.5 LMSM（链路训练）

独立模块 `ub_lmsm`，不塞进 PCS 数据通路。它读 CSR 目标宽度/速率，驱 PMA 模型与 PCS 训练图案（LMB/LTB、AMCTL），向 DLL 输出 `link_up` / `link_ready`（见 UB-PHY §3.4、§3.4.3）。状态见 §6.1。

### 2.6 DLL（VL / 信用 / 重传）

```mermaid
flowchart TB
  subgraph dll_tx [DLL TX]
    SEG[segmenter LPH/LBH]
    CRC_TX[BCRC]
    VL_TX[VL 仲裁]
    CRD_TX[credit 记账]
    RET_TX[retry buffer + RETRY_ACK_SM]
  end
  subgraph dll_rx [DLL RX]
    REASM[reassembler]
    CRC_RX[BCRC check]
    VL_RX[按 VL 投递]
    CRD_RX[credit 归还]
    RET_RX[RETRY_REQ_SM]
  end
  SM[DLL SM]
  NW_IN[nw_tx flit] --> SEG --> CRC_TX --> RET_TX --> PCS_TX[to PCS]
  PCS_RX[from PCS] --> CRC_RX --> REASM --> NW_OUT[nw_rx flit]
  SM --- VL_TX
  SM --- CRD_TX
  SM --- RET_TX
  SM --- RET_RX
```

| 子块 | 行为（短述） | 节号 |
| --- | --- | --- |
| DLL SM | Disabled → Param_Init → Credit_Init → Normal；`link_up==0` 回到 Disabled | UB-DL §4.2 |
| segmenter / reassembler | DLLDP 分段为 DLLDB（最大 32 flit/段），DLLCB 收发 | §4.3 |
| VL | 每链路最多 16 VL；M1 启用 VL0+VL1；VL0 必须开 | §4.5、§4.5.1、§4.5.2 |
| credit | 独占模式；cell=1 flit；归还/ACK 粒度 32 | §4.6、§4.6.1.2 |
| retry | 重传缓冲、RETRY_REQ_SM、RETRY_ACK_SM | §4.7、§4.7.3 |
| CRC | CRC 模式做 BCRC；与 FEC 成败共同决定是否重传 | §4.3.2.2、§4.7.2 |

Init Block 字段名只作标识符使用，位定义见 UB-DL §4.3.3.9，本仓库不抄表。协商流程见 §4.4。

---

## 3. 顶层与模块间接口

### 3.1 握手通则（valid/ready）

凡下表标「valid/ready」的流：

1. **同一拍** `valid==1 && ready==1` 才完成一次传送。
2. `valid==1` 时数据与边带必须保持，直到 `ready==1`。
3. `ready` 不得组合依赖于本拍的 `valid`（避免组合环）。允许 `valid` 组合看 `ready`。
4. 复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。
5. 无 valid/ready 的旁路（纯状态线）是电平，不是脉冲；跨时钟不得传脉冲（pyc 无 pulse/req-ack 同步原语）。

CSR 用独立的 req/ready，不用 valid/ready 数据流语义，见 §3.3。

### 3.2 顶层端口 `ub_controller`

时钟域列 `core_clk` 表示 M1 **唯一**时钟域（见 §4）。宽度中的参数见 §9。无 `pma_clk` / `pma_rst_n` 端口。

#### 3.2.1 时钟复位

| 端口 | 方向 | 宽度 | 时钟域 | 含义 |
| --- | --- | --- | --- | --- |
| `core_clk` | in | 1 | — | 唯一时钟。等于 PMA 并行字时钟：2.578125 Gb/s / 32 bit ≈ **80.57 MHz** |
| `rst_n` | in | 1 | 异步输入 | 低有效。异步置位、经白名单同步器同步释放；下游见 §4.2 |

#### 3.2.2 上层 flit（替代 Network Layer）

Flit 宽度 160 bit 来自项目既有设计说明与 Xia 重传公式（160b），与 UB flit 概念对齐。边带为项目接口，不是规范抄录。

| 端口 | 方向 | 宽度 | 时钟域 | 含义 |
| --- | --- | --- | --- | --- |
| `nw_tx_data` | in | 160 | `core_clk` | 上层要发送的 flit 净荷（不含 LPH/LBH/BCRC） |
| `nw_tx_valid` | in | 1 | `core_clk` | TX valid |
| `nw_tx_ready` | out | 1 | `core_clk` | DLL 可收。无信用、未 `dll_status_up`、或重传占用时可为 0 |
| `nw_tx_sop` | in | 1 | `core_clk` | DLLDP 首 flit |
| `nw_tx_eop` | in | 1 | `core_clk` | DLLDP 末 flit |
| `nw_tx_vl` | in | 4 | `core_clk` | VL ID。未使能的 VL（M1 合法为 0–1）：整包丢弃，计数 +1，置位粘滞状态（见 §7） |
| `nw_rx_data` | out | 160 | `core_clk` | 投递给上层的 flit 净荷 |
| `nw_rx_valid` | out | 1 | `core_clk` | RX valid |
| `nw_rx_ready` | in | 1 | `core_clk` | 上层可收。DLL 必须能反压；RX 缓冲深度 **待定** |
| `nw_rx_sop` | out | 1 | `core_clk` | 重组后 DLLDP 首 flit |
| `nw_rx_eop` | out | 1 | `core_clk` | 重组后 DLLDP 末 flit |
| `nw_rx_vl` | out | 4 | `core_clk` | 该包 VL |
| `dll_status_up` | out | 1 | `core_clk` | 可向对端发 DLLDP（见 UB-DL §4.2 对上层状态） |
| `dll_status_down` | out | 1 | `core_clk` | 与 `dll_status_up` 互斥 |

单 flit 包：同一拍 `sop==1 && eop==1` 合法。`valid==0` 时 sop/eop/vl/data **忽略**。

#### 3.2.3 CSR

| 端口 | 方向 | 宽度 | 时钟域 | 含义 |
| --- | --- | --- | --- | --- |
| `csr_req` | in | 1 | `core_clk` | 本拍有一次访问 |
| `csr_wr` | in | 1 | `core_clk` | 1=写，0=读 |
| `csr_addr` | in | 16 | `core_clk` | 字节地址，须 4 字节对齐 |
| `csr_wdata` | in | 32 | `core_clk` | 写数据。**仅 32-bit 整字写**，无 `csr_wstrb` |
| `csr_ready` | out | 1 | `core_clk` | 当拍接受 `csr_req`。M1 恒 1（无等待） |
| `csr_rvalid` | out | 1 | `core_clk` | 读响应：请求的 **下一拍** 为 1（固定 1 拍延迟） |
| `csr_rdata` | out | 32 | `core_clk` | 与 `csr_rvalid` 同拍。未映射读回 0 |
| `csr_err` | out | 1 | `core_clk` | 与响应同拍（请求的下一拍）。未映射：读回 0 且本位置 1；写忽略且本位置 1 |

无 `csr_wstrb`。未对齐地址按未映射处理。写响应：下一拍 `csr_rvalid=0`，`csr_err` 有效。

#### 3.2.4 PCS–PMA 数据（模型边界）

`PMA_W = 32`（已确认）。`NUM_LANES_TX` / `NUM_LANES_RX` 见 §9。

| 端口 | 方向 | 宽度 | 时钟域 | 含义 |
| --- | --- | --- | --- | --- |
| `pma_tx_data` | out | `NUM_LANES_TX*PMA_W` | `core_clk` | 每 lane 并行字，lane0 在 LSB |
| `pma_tx_valid` | out | 1 | `core_clk` | 本拍字有效。训练期由 LMSM/PCS 出图案 |
| `pma_tx_ready` | in | 1 | `core_clk` | 模型常就绪时恒 1 |
| `pma_tx_elec_idle` | out | `NUM_LANES_TX` | `core_clk` | 每 lane 电气空闲请求 |
| `pma_rx_data` | in | `NUM_LANES_RX*PMA_W` | `core_clk` | 每 lane 并行字（模型已完成串并；PAM4 时已 Gray 反变换） |
| `pma_rx_valid` | in | 1 | `core_clk` | RX 字有效 |
| `pma_rx_ready` | out | 1 | `core_clk` | PCS 可收 |
| `pma_rx_data_valid_lane` | in | `NUM_LANES_RX` | 同上 | **待定**。是否需要 per-lane valid（deskew 前） |

位序、AMCTL 与数据字是否共用 `pma_tx_data`：**待定**（建议共用，由 PCS 在数据流里插 AMCTL，见 §3.2.4）。

#### 3.2.5 LMSM–PMA 训练侧带

| 端口 | 方向 | 宽度 | 时钟域 | 含义 |
| --- | --- | --- | --- | --- |
| `pma_data_rate_sel` | out | 4 | `core_clk` | 目标/当前 Data Rate 编号。M1 只用 0 |
| `pma_tx_width` | out | 4 | `core_clk` | 激活的 TX lane 数编码。编码表 **待定** |
| `pma_rx_width` | out | 4 | `core_clk` | 激活的 RX lane 数编码 |
| `pma_lane_reverse_tx` | out | 1 | `core_clk` | TX lane 反转（见 UB-PHY §3.4.2.7） |
| `pma_lane_reverse_rx` | out | 1 | `core_clk` | RX lane 反转 |
| `pma_polarity_inv` | out | `NUM_LANES_RX` | `core_clk` | 极性翻转（§3.4.2.6）。每 bit 对应一 lane |
| `pma_probe_pulse_en` | out | 1 | `core_clk` | 请求模型发探测脉冲 |
| `pma_term_detect` | in | `NUM_LANES_TX` | `core_clk` | 模型报告远端端接 |
| `pma_rx_eidle_exit` | in | `NUM_LANES_RX` | `core_clk` | RX 退出电气空闲（电平，不是脉冲） |
| `pma_phy_ready` | in | 1 | `core_clk` | 模型就绪 |

均衡系数、FEC 模式旁路到 PMA 的其它针脚：**未知**（M1 Data Rate 0 / NRZ 可能用不到）。需要时只加电平信号，不加脉冲。

#### 3.2.6 对外状态

| 端口 | 方向 | 宽度 | 时钟域 | 含义 |
| --- | --- | --- | --- | --- |
| `link_up` | out | 1 | `core_clk` | LMSM 置位，DLL 用来离开 Disabled（§3.4.3、§4.2） |
| `link_ready` | out | 1 | `core_clk` | 物理层可承载业务（§3.4.3.7） |
| `irq` | out | 1 | `core_clk` | 高有效电平。任一未屏蔽源为 1。复位后 **全部源屏蔽**（见 REGMAP `IRQ_MASK`） |

测试钩子：顶层另有 `tb_test_mode` 与 `tb_inj_*` / `tb_obs_*`，见 §10。`TEST_HOOKS=0` 时这些端口不存在。

### 3.3 模块间接口

均在 `core_clk`，同步复位后的业务域。宽度随参数变。

#### 3.3.1 DLL ↔ PCS（TX）

| 信号 | 方向（相对 DLL） | 宽度 | 含义 |
| --- | --- | --- | --- |
| `dll2pcs_data` | out | 160 | 已带 LPH/LBH/BCRC 的 flit，或 DLLCB flit |
| `dll2pcs_valid` | out | 1 | valid |
| `dll2pcs_ready` | in | 1 | PCS 可收（FEC 组帧会反压） |
| `dll2pcs_is_cb` | out | 1 | 1=DLLCB，0=DLLDP。PCS 不解析内容，只当数据 |
| `dll2pcs_sop` / `dll2pcs_eop` | out | 1 | 块/包边界。PCS 是否需要：**待定**（FEC 组帧可能只按字节流） |

#### 3.3.2 PCS ↔ DLL（RX）

| 信号 | 方向（相对 PCS） | 宽度 | 含义 |
| --- | --- | --- | --- |
| `pcs2dll_data` | out | 160 | 解扰后的 flit |
| `pcs2dll_valid` | out | 1 | valid |
| `pcs2dll_ready` | in | 1 | DLL 可收 |
| `pcs2dll_fec_ok` | out | 1 | 本 flit 所属 FEC 码字可纠正或无错 |
| `pcs2dll_fec_uncorr` | out | 1 | 本码字不可纠正。与 `fec_ok` 互斥 |
| `pcs2dll_bypass` | out | 1 | 当前为 FEC bypass。此时 `fec_ok` 含义 **待定** |

`fec_ok` / `fec_uncorr` 必须与对应 flit 对齐（同一拍）。跨 FEC 码字的延迟由 PCS 内部对齐，不把「后到的成败」单独用脉冲送给 DLL。

#### 3.3.3 LMSM ↔ DLL

| 信号 | 方向（相对 LMSM） | 宽度 | 含义 |
| --- | --- | --- | --- |
| `link_up` | out | 1 | 见 §3.2.6 |
| `link_ready` | out | 1 | 见 §3.2.6 |
| `dll_retrain_req` | in | 1 | DLL 请求物理层重训（RETRY_REQ_SM 进 RETRAIN，见 UB-DL §4.7.3.3） |
| `lmsm_retrain_ack` | out | 1 | 电平：LMSM 已进入 Retrain。禁止用脉冲 |

#### 3.3.4 LMSM ↔ PCS

| 信号 | 方向（相对 LMSM） | 宽度 | 含义 |
| --- | --- | --- | --- |
| `lmsm_tx_pattern_sel` | out | 4 | 训练图案选择。枚举 **待定**（Idle / LTB / AMCTL-only / Null / 业务） |
| `pcs_am_locked` | in | `NLANE`（=`NUM_LANES_RX`） | 每 lane AM/AMCTL 锁定。进 `ub_lmsm` 前可被 `tb_inj_am_lock` 旁路（§10），**不回灌** PCS 输出 |
| `pcs_lid_bad` | in | 1 | 训练所见 link ID 非法/不一致。进 `ub_lmsm` 前可被 `tb_inj_lid_bad` 旁路（§10），**不回灌** PCS |
| `pcs_deskew_ok` | in | 1 | deskew 完成 |
| `pcs_fec_mode` | out | 2 | 0=T4，1=T2，2=bypass。编码 **待定** |

LTB/CLTB/RLTB 比特级布局见 UB-PHY §3.4.1，本仓库不抄。谁拼 LMB（LMSM 还是 PCS）：**待定**（建议 LMSM 出字段，PCS 负责装进码流/AMCTL 规则）。

#### 3.3.5 CSR → 各块

CSR 输出均为 `core_clk` 电平寄存器，不握手。各块输出的计数/状态为同步采样。跨模块禁止用「写 CSR 产生的单拍脉冲」穿过可能的时钟域；M1 单时钟下可用同步 1 拍选通，但选通不得送出 `core_clk` 域。

---

## 4. 时钟与复位

### 4.1 M1 单时钟域（已定）

M1 **只有** `core_clk`。它就是 PMA 并行字时钟：

`F_CORE = 2.578125 Gb/s / 32 bit ≈ 80.57 MHz`

- 无独立 `pma_clk`。`USE_PMA_CLK=0` **已定**（不是草案）。
- 多时钟是 M1 **非目标**。产品通路不做 CDC。
- PMA 模型与 PCS 同拍于 `core_clk`。xN 时接口宽度 `N*32`，无需跨时钟齿轮箱。
- 工艺节点仍为 **未知，待船长定**。`F_CORE` 已按上式确定。

pyc4.0 的 CDC 原语仍只允许按 §4.3 使用；M1 生成网表中不应出现跨时钟 FIFO。后续里程碑若引入第二时钟，再开新决策，不在 M1 预留 `pma_clk` 端口。

### 4.2 复位（已定）

| 规则 | 说明 |
| --- | --- |
| 顶层端口 | `rst_n`，低有效 |
| 置位 / 释放 | **异步置位、同步释放**，只允许经白名单复位同步器（见 [CODING_STYLE.md](CODING_STYLE.md)） |
| 业务逻辑 | **同步复位**（D6）。`always` 只对 `posedge core_clk` 敏感 |
| 极性对接 | 同步器之后用封装把复位接到 `pyc_reg` 的 **原生极性**（见下） |
| Entity vs 端口复位 | 规范区分二者（UB-DL §4.2）。M1 无 Entity：`rst_n` 与 CSR 端口复位都回到 LMSM Link_Idle + DLL Disabled |

**封装（唯一对接点）：**

1. 白名单单元 `ub_rst_sync`：输入异步 `rst_n` + `core_clk`，输出 `rst_n_sync`（仍低有效；异步置位、同步释放）。
2. 生成逻辑封装 `ub_pyc_rst_adapt`：把 `rst_n_sync` 转成 `rst_pyc`，极性等于 **pyc4.0 `pyc_reg` 原生极性**。若库原生已是低有效，本封装退化为连线。业务模块只看见 `rst_pyc`，不直接采样顶层 `rst_n`。

现有 `rtl/` 使用 `posedge clk or negedge rst_n`，**不合**本规格，重写时删除。

### 4.3 CDC 白名单

| 原语 | 用途 | 限制 |
| --- | --- | --- |
| 手写 `ub_rst_sync` | 异步置位、同步释放 `rst_n` → `rst_n_sync` | 仅复位；M1 只对 `core_clk` |
| `pyc_cdc_sync` | 1-bit 电平 | 禁止多 bit、禁止脉冲 |
| `pyc_async_fifo` | 多 bit 总线 | 数据通路跨时钟的唯一手段 |
| 其它手写 CDC | 禁止 | 无 pulse/req-ack 原语可用，故接口不得依赖它们 |

---

## 5. 时序

均为 **目标**，不是已关门的约束。具体拍数在 pyCircuit 实现后回填；未测写「待定」。

| 路径 | 目标 | 备注 |
| --- | --- | --- |
| CSR 写生效到控制电平 | 1 拍 | 同步寄存器 |
| CSR 读 | 固定 1 拍：请求下一拍 `csr_rvalid` | 见 §3.2.3；无 `csr_wstrb` |
| NW TX valid/ready | 无气泡当 `ready==1` | 信用不足时 `ready==0` |
| DLL 分段插入 LPH/LBH/BCRC | **待定** | 至少 1 拍打头、BCRC 在段末 |
| FEC 编码 | **待定** | RS(128,120) 组 120 符号；并行度 **待定** |
| FEC 解码 | **待定** | 含伴随式/关键方程/Chien |
| AMCTL 插入造成的周期气泡 | 按 §3.2.4 规则 | 间隔/长度不在此抄录 |
| PCS 组帧反压 DLL | 允许持续 `ready==0` | 不得丢 flit |
| 重传从 REQ 到重发首 flit | **待定** | 受 retry buffer 读口约束 |
| 信用归还从 RX 收齐到 TX 发出 | **待定** | 粒度 32（已确认） |

Data Rate 0、x1、32 bit/lane：线速率与 160-bit flit 不对齐，PCS 必须用 valid/ready 做齿轮，而不是假定 1 flit/拍。拍数关系：**待定**（实现时按 PMA 字与 FEC 码字长度计算，不在文档里编造）。

---

## 6. 状态机

图为项目转述，不是规范附图的复制。转移条件只写设计需要的短句，细节见节号。

### 6.1 LMSM（UB-PHY §3.4.3）

主状态（标识符与规范一致）：

`Link_Idle`，`Probe`，`RXEQ_Optimize`，`Discovery`，`Config`，`Send_NullBlock`，`Link_Active`，`Retrain`，`Change_Speed`，`Equalization`

Probe / Discovery / Config / Retrain / Equalization 的子状态按对应小节实现（如 Probe.Wait / Probe.Confirm）。子状态清单以规范为准，此处不展开抄录。

```mermaid
stateDiagram-v2
  [*] --> Link_Idle: 复位
  Link_Idle --> Probe: 电气且不 bypass Probe，PHY ready，软件启动
  Link_Idle --> RXEQ_Optimize: 固定速率模式且启动
  Link_Idle --> Discovery: bypass Probe 且非固定速率且启动
  Probe --> Discovery: 端接检测成功
  Probe --> Probe: 未检测到端接
  RXEQ_Optimize --> Discovery: 自适应结束或超时
  Discovery --> Config: 训练块握手成功
  Discovery --> Link_Idle: 失败/超时
  Config --> Send_NullBlock: 配置块握手成功
  Config --> Link_Idle: 失败/超时
  Send_NullBlock --> Link_Active: 连续空块满足
  Send_NullBlock --> Retrain: 次数未满
  Send_NullBlock --> Discovery: 需重回发现
  Send_NullBlock --> Link_Idle: 重训次数耗尽
  Link_Active --> Retrain: 收到/发出重训指示
  Retrain --> Discovery: 重训后需发现
  Retrain --> Change_Speed: 需改速率
  Retrain --> Send_NullBlock: 可直接收尾
  Retrain --> Equalization: 需均衡
  Retrain --> Link_Idle: 失败
  Change_Speed --> Retrain: 改速成功
  Change_Speed --> Link_Idle: 超时
  Equalization --> Retrain: 均衡结束或放弃
```

M1 bring-up 裁剪（默认参数已确认）：

| 项 | M1 |
| --- | --- |
| 互联 | 电气；`bypass_Probe=0`，除非 CSR 置位 |
| 速率 | 固定 Data Rate 0；`Change_Speed` 实现状态但不改变速率，或直接视为非法请求 |
| 均衡 | Data Rate 0 下 `Equalization` / `RXEQ_Optimize` 是否空转超时退出：**待定** |
| 非对称 | 默认 Tx_M==Rx_N |
| 光学旁路 Probe/EQ | 非目标 |

`link_up` / `link_ready` 在哪些状态置位：见 UB-PHY §3.4.3.6–§3.4.3.8，不在此复制条件表。设计要求：`link_up` 为电平；DLL 只看电平，不看边沿脉冲。

软件启动 LMSM：CSR 写「启动」位（见 REGMAP `LMSM_CTRL.START`）。这是实现手段，对应规范「上层指示进入下一状态」（§3.4.3.1）。

### 6.2 DLL 状态机（UB-DL §4.2）

| 状态 | 含义（短述） | 主要出口 |
| --- | --- | --- |
| `DLL_Disabled` | 复位后或 `link_up==0`。对上 `dll_status_down`。不发 DLLDP | `link_up==1` → `DLL_Param_Init` |
| `DLL_Param_Init` | 交换 Init Block，协商粒度/VL 等（§4.3.3.9、§4.4） | 协商完成且 `link_up==1` → `DLL_Credit_Init`；`link_up==0` → Disabled |
| `DLL_Credit_Init` | 按协商结果做信用初值（§4.6.1） | 信用初始化完成且 `link_up==1` → `DLL_Normal`；`link_up==0` → Disabled |
| `DLL_Normal` | 可收发 DLLDP | `link_up==0` → Disabled |

```mermaid
stateDiagram-v2
  [*] --> DLL_Disabled: 端口复位
  DLL_Disabled --> DLL_Param_Init: link_up
  DLL_Param_Init --> DLL_Credit_Init: Init 协商完成
  DLL_Param_Init --> DLL_Disabled: link_up 撤销
  DLL_Credit_Init --> DLL_Normal: 信用初始化完成
  DLL_Credit_Init --> DLL_Disabled: link_up 撤销
  DLL_Normal --> DLL_Disabled: link_up 撤销
```

对上：仅 `DLL_Normal` 报 `dll_status_up`（见 §4.2）。Param/Credit 期间可发规定的 DLLCB，不发上层 DLLDP。

### 6.3 RETRY_REQ_SM（UB-DL §4.7.3.3）

状态：`NORMAL`，`REQ`，`WAIT`，`RETRAIN`，`ERROR`。

| 从 → 到 | 条件（短述） |
| --- | --- |
| NORMAL → REQ | CRC 失败，或 FEC 不可纠正，或需重传的物理层事件 |
| REQ → WAIT | 重传请求集已发出 |
| WAIT → REQ | 等 ACK 超时 |
| WAIT → NORMAL | 收到重传应答集 |
| NORMAL 或 REQ → RETRAIN | 物理层重训，或 `NUM_RETRY` 达到阈值 |
| RETRAIN → REQ | 重训成功 |
| RETRAIN → ERROR | `NUM_PHY_REINIT` 达到阈值 |
| ERROR → NORMAL | 需 UBFM/软件复位（M1：CSR 端口复位） |

阈值默认：采用 §4.7.3.3 的推荐量级 15 与 4（**草案**，非 Xia 已确认集），并在 REGMAP 读回。实现时对照该节，不在此抄正文。

### 6.4 RETRY_ACK_SM（UB-DL §4.7.3.4）

两个状态（标识符见该节）。职责：对端请求时发应答集，并从 retry buffer 重放。未实现细节：**待定**（按该节，不在此发明子条件）。

---

## 7. 异常与错误处理

原则：错误经 CSR 计数/状态/可选 `irq` 可见；TB 不得 `force` 内部节点，注入走端口或测试钩子（D13）。不可恢复错误停在安全态，等软件复位。

| 异常 | 检测 | 动作（短述） | 节号 |
| --- | --- | --- | --- |
| FEC 不可纠正 | PCS 解码失败 | 对齐 flit 标 `pcs2dll_fec_uncorr`；DLL 按模式触发重传；计数 +1 | UB-PHY §3.2.3.5；UB-DL §4.7.2 |
| BCRC 失败 | DLL RX | 触发 RETRY_REQ_SM；丢弃该块；计数 +1 | §4.7.2、§4.3.2.2 |
| 重传次数过多 | `NUM_RETRY` | 进 RETRAIN / 上报 | §4.7.3.3、§4.8.2 |
| 重传仍失败 | `NUM_PHY_REINIT` | 进 ERROR；停发停收；等复位 | §4.7.3.3、§4.8.2 |
| Retry ACK 超时 | WAIT 计时 | 回 REQ 或按 §4.8.2 上报 | §4.7.3.3、§4.8.2 |
| 信用为 0（正常反压） | TX credit == 0 | 停发 DLLDP，`nw_tx_ready=0`。不是错误 | UB-DL §4.6 |
| 信用下溢（计数被减到负 / 在 0 时仍减） | TX credit 记账 | RTL：计数 +1、粘滞状态、`irq` 源。**不是** RTL assertion。TB 另外 assert | proj |
| Receive Buffer Overflow | RX | 上报，链路不能继续，等复位 | §4.8.1 |
| Flow Control Overflow | 信用超过初值 | 同上 | §4.8.1 |
| 信用归还超时 | 定时器 | 上报 DL Protocol Error，等复位 | §4.8.1 |
| retry 指针/NumFreeBuf 溢出 | ACK 释放 | 上报，等复位 | §4.8.2 |
| `link_up` 变 0 | LMSM | DLL → Disabled；丢弃已从上层收下、未完成的发送；RX 丢弃未完成重组 | §4.8.4 |
| LMSM 训练超时 | 各状态超时 | 回 Link_Idle 或 Retrain，见 §3.4.3 | §3.4.3 |
| 非法 / 未使能 VL | NW TX `nw_tx_vl` | 整包丢弃；`CNT_BAD_VL` +1；粘滞 `IRQ_STATUS.BAD_VL` | §4.5 |
| CSR 未映射地址 | 译码 | 读返回 0 且 `csr_err=1`；写忽略且 `csr_err=1`（响应在请求下一拍） | 项目约定 |

超时的具体微秒/拍数：规范有的以节号为准（例如部分 LMSM 超时在 §3.4.3.x），实现时对照，**不抄进本仓库**。规范写「实现相关」的：标 **待定**。

信用：0 信用只反压。下溢（实现把计数减过 0）才走错误计数 / 粘滞 / irq。对端少归还走超时（§4.8.1）。RTL 不对下溢做 assertion。

带 `ERROR_FLAG` 的 DLLDP：按 §4.8.3 当正常包交给上层，不单因该标志重传。M1 是否在 TX 路径置位该标志：**待定**（无 ECC 存储器时可能用不到）。

---

## 8. 性能与延迟目标

工艺节点：**未知，待船长定。** `core_clk` ≈ **80.57 MHz**（已定，见 §4.1）。

| 指标 | M1 目标 | 说明 |
| --- | --- | --- |
| 线速率 | 2.578125 Gbit/s NRZ / lane | 已确认 |
| 宽度 | x1 功能闭环，x4 为 bring-up 目标，RTL 到 x8 | 已确认 |
| 有效吞吐 | 扣除 FEC 8/128、AMCTL、DLL 头开销后的 flit 率 | 具体 Gbps **待定**（依赖 AMCTL 间隔与是否满信用） |
| 链路 RTT 假设 | 2 µs（算 retry 深度） | 已确认（M1）；spec-max 档按 1 µs |
| NW 口到 PMA 口 TX 延迟 | **待定** | 实现后回填拍数 |
| PMA 口到 NW 口 RX 延迟 | **待定** | 含 FEC 解码，预期占主导 |
| 重传恢复 | 在 RTT 假设内不饿死 retry 深度 | 深度公式见 UB-DL §4.7.3.2，数值用 Xia 档 |

旧设计说明里 250–400 MHz / 100 Gbps+ **不是** M1 目标（那是按 53G/106G 写的）。M1 以 Data Rate 0 能训练、能带信用与重传跑通为准。

---

## 9. 参数表

M1 列中 Xia 提出的默认值已由船长确认。仍标「草案」的是规范推荐或验证侧阈值。工艺节点仍未知；`F_CORE` 已定。

| 参数 | 标识符 | M1 | spec-max | 出处 / 备注 |
| --- | --- | --- | --- | --- |
| PHY 模式 | `PHY_MODE` | Mode-2 | Mode-2 | UB-PHY §3.1.2；已确认 |
| 数据速率 | `DATA_RATE` | 2.578125G NRZ（Data Rate 0） | 106.25G PAM4 | §3.1.2、§3.4.2.5；已确认 |
| TX lane 数 | `NUM_LANES_TX` | 1…4 bring-up；参数到 8 | 8 | §3.1.1、§3.4.2.2；已确认 |
| RX lane 数 | `NUM_LANES_RX` | 默认等于 TX | 8 | 非对称默认关；已确认 |
| 非对称 | `ALLOW_ASYM` | 0 | 规范允许 | §3.1.1；已确认 |
| PMA–PCS 每 lane 位宽 | `PMA_W` | 32 | 256 | 已确认。与 `F_CORE` 对齐 |
| FEC | `FEC_MODE` | RS(128,120,T=4)；T=2/bypass 可协商 | 同 | §3.2.2.1–2；已确认 |
| FEC 交织 CodecNum | `FEC_CODEC_NUM` | **待定**（建议 1） | **待定** | §3.2.2.3 |
| VL 数 | `NUM_VL` | 2 | 16 | UB-DL §4.5.1；已确认 |
| 重传缓冲 | `RETRY_BUF_DEPTH` | 256 flit | 8192 flit | §4.7.3.2；已确认。M1 RTT 假设 2 µs |
| cell 大小 | `FLOW_CTRL_SIZE` | 1 flit/cell | 同左或按协商 | §4.6、Init Block；已确认 |
| credit/ACK 粒度 | `*_GRAIN_SIZE` | 32 | 按公式/协商 | §4.6.1–4.6.3；已确认 |
| 信用模式 | `CREDIT_MODE` | 独占 | 独占或共享 | §4.6.1.2 / §4.6.1.3；共享为非默认；已确认独占 |
| 每 VL 初始信用 | `INIT_CRD` | 640 cell | 按公式 | §4.6.1；已确认 |
| flit 宽度 | `FLIT_W` | 160 | 160 | 项目接口 |
| 每 DLLDB 最大 flit | `MAX_DB_FLITS` | 32 | 32 | §4.3 |
| DLLDP 最大 flit | `MAX_DP_FLITS` | **待定**（规范上限对照 §4.3.2） | 同 | 不抄具体表 |
| `NUM_RETRY_THRESHOLD` | 同名 | 15（规范推荐，草案） | 同 | §4.7.3.3 |
| `NUM_PHY_REINIT_THRESHOLD` | 同名 | 4（规范推荐，草案） | 同 | §4.7.3.3 |
| 预编码 | `PRECODE_EN` | 0（关） | **待定** | UB-PHY §3.3.2；M1 默认关，已定 |
| 工艺 | — | **未知，待船长定** | — | 船长未定 |
| 目标频率 | `F_CORE` | ≈80.57 MHz | **待定** | `2.578125e9/32`；已定。工艺仍未知 |
| ASIC 范围 | — | 仅 PCS+DLL 数字；PMA 行为模型 | 同 | D3；已确认 |
| 单时钟 | `USE_PMA_CLK` | 0 | 多时钟为后续阶段 | §4.1；已定。M1 无 `pma_clk` |
| 测试钩子生成 | `TEST_HOOKS` | 见 §11：Python 生成期展开，两套网表 | 同 | §10、§11 |
| 钩子 lane 宽 | `NLANE` | `NUM_LANES_RX` | 同 | §10。`tb_inj_am_lock` 宽度 |
| 信用反压观察阈值 | `CRD_BP_THRESHOLD` | 1024 | **待定** | §10 `tb_obs_crd_bp`；**草案** |

Retry 深度下界公式见 UB-DL §4.7.3.2（含 FEC 120/128 与 RTT）。M1 256 / max 8192 是 Xia 按 RTT 2 µs / 1 µs 的取值，不是把公式抄进仓库。

---

## 10. 测试钩子端口

测试钩子端口替代验证对内部信号的任何 `force` / `deposit`。TB 只能通过顶层端口、本节省的 `tb_*` 钩子、或寄存器注入/观察（D13；[CODING_STYLE.md](CODING_STYLE.md)）。

验证侧曾用模块名 `vibe_lmsm`、`vibe_dll_credit`、`vibe_pcs_tx_pack`。本规格对应关系：

| 验证名 | 本规格模块 |
| --- | --- |
| `vibe_lmsm` | `ub_lmsm` |
| `vibe_dll_credit` | `ub_dll` 内信用子块 |
| `vibe_pcs_tx_pack` | `ub_pcs` TX（组帧 / AMCTL 插入） |

### 10.1 门控

每个钩子同时受下列两者门控：

1. 编译参数 `TEST_HOOKS`（产品综合默认 0，仿真 1）。
2. 顶层输入端口 `tb_test_mode`。

规则（两套网表的生成与门禁见 §11）：

- `TEST_HOOKS=0`：钩子端口与 mux **综合掉**；产品网表无 `tb_*`。
- `TEST_HOOKS=1` 且 `tb_test_mode=0`：端口存在，但注入 **不介入**（mux 选功能路径）；观察口输出保持 0。
- `TEST_HOOKS=1` 且 `tb_test_mode=1`：注入/观察生效。
- **复位值 = 不介入**：`tb_test_mode` 复位为 0；所有 `tb_inj_*` 视为 0 或不驱动功能路径；测试寄存器（`LMSM_TMR_SCALE`、`CRD_TO_DIS`、PCS TX AM 间隔缩放）复位为不缩放 / 检查使能。
- 注入只做 **mux 进目标模块输入**，**不回灌** 源模块输出（例如不改写 PCS 的 `pcs_am_locked` 端口）。

`tb_test_mode` 与全部 `tb_*` 均在 `core_clk` 域，同步采样。`tb_inj_*` 为电平，不是脉冲。

### 10.2 顶层钩子端口

`NLANE = NUM_LANES_RX`。非对称时 AM 锁定按 RX lane 数。

| 端口 | 方向 | 宽度 | 时钟域 | 接入模块 | 含义 |
| --- | --- | --- | --- | --- | --- |
| `tb_test_mode` | in | 1 | `core_clk` | 顶层门控 | 为 1 且 `TEST_HOOKS=1` 时钩子生效 |
| `tb_inj_am_lock` | in | `NLANE` | `core_clk` | `ub_lmsm` | 电平。mux 到 LMSM 的 `am_locked` 输入，不回灌 PCS。M1 **保留**。是否在 PMA 模型证明能出真实 AM 之后删除： **待定**（触发条件仅此） |
| `tb_inj_lid_bad` | in | 1 | `core_clk` | `ub_lmsm` | 电平。mux 到 LMSM 的 `lid_bad` 输入，不回灌 PCS。M1 **保留**。删除条件同 `tb_inj_am_lock` |
| `tb_inj_crd_cells` | in | 16 | `core_clk` | `ub_dll` 信用子块 | 电平。预置 **VL0** 远端信用库存（cell）。M1 信用钩子只对 VL0 |
| `tb_obs_link_ready` | out | 1 | `core_clk` | `ub_lmsm` | `LMSM==Link_Active`（ACTIVE） |
| `tb_obs_link_up` | out | 1 | `core_clk` | `ub_lmsm` | `LMSM==Send_NullBlock`（NULL）或 `Link_Active`（ACTIVE） |
| `tb_obs_lmsm_st` | out | 5 | `core_clk` | `ub_lmsm` | **仅** LMSM 顶层状态，不含子状态。编码见 §10.3（已定） |
| `tb_obs_crd_cells` | out | 16 | `core_clk` | `ub_dll` 信用子块 | **VL0** 远端信用库存 |
| `tb_obs_crd_pend` | out | 16 | `core_clk` | `ub_dll` 信用子块 | **VL0** 未决信用（项目计数，单位 cell） |
| `tb_obs_crd_low` | out | 1 | `core_clk` | `ub_dll` 信用子块 | VL0 `cells==0` |
| `tb_obs_crd_bp` | out | 1 | `core_clk` | `ub_dll` 信用子块 | VL0 `pend >= CRD_BP_THRESHOLD`。阈值 **草案** 1024 |
| `tb_obs_crd_to` | out | 11 | `core_clk` | `ub_dll` 信用子块 | VL0 Crd_Ack 超时计数器 |
| `tb_obs_dll_sm_st` | out | 2 | `core_clk` | `ub_dll` | DLL SM 编码，见 §10.3 |
| `tb_obs_consume_flits` | out | 10 | `core_clk` | `ub_dll` TX | 本拍 DLL TX 消耗的 flit 数 |

**本阶段没有的钩子：**

| 名称 | 处理 |
| --- | --- |
| `tb_obs_nw_dll_data` | **不做**（NW 按 D2 推迟） |
| 本地 CNA | **无钩子**；软件经寄存器读（见 [REGMAP.md](REGMAP.md) `PORT_CNA` / App. D.5.5） |

### 10.3 观察编码（项目约定）

`tb_obs_lmsm_st[4:0]`：**只编码顶层 LMSM 状态**，不含 Probe.Wait 等子状态。未列出的值保留。项目编码（已定）：

| 值 | 状态 |
| --- | --- |
| 0 | `Link_Idle` |
| 1 | `Probe` |
| 2 | `RXEQ_Optimize` |
| 3 | `Discovery` |
| 4 | `Config` |
| 5 | `Send_NullBlock` |
| 6 | `Link_Active` |
| 7 | `Retrain` |
| 8 | `Change_Speed` |
| 9 | `Equalization` |

`tb_obs_dll_sm_st[1:0]`：

| 值 | 状态 |
| --- | --- |
| 0 | `DLL_Disabled` |
| 1 | `DLL_Param_Init` |
| 2 | `DLL_Credit_Init` |
| 3 | `DLL_Normal` |

### 10.4 改为寄存器、不做成钩子

下列能力用 CSR 实现，**仅当 `tb_test_mode=1`（且 `TEST_HOOKS=1`）时生效**，除非寄存器表另注。复位 = 不介入。位域见 [REGMAP.md](REGMAP.md)。

| 寄存器 / 字段 | 代替的验证手段 | 行为（短述） |
| --- | --- | --- |
| `LMSM_TMR_SCALE` | 向 LMSM 定时器 `deposit` 计数值 | 缩放 LMSM 超时计数，使训练能沿 **真实状态路径** 走到 `Link_Active`，而不是 force 状态 |
| `CRD_TO_DIS` | 把 pending 钉成 0 | 关闭 Crd_Ack 超时检错；信用数据通路仍按功能走 |
| `PCS_TX_TEST.AM_IVL_SCALE` | 向 AM 符号计数器 `deposit` | 缩放 PCS TX AMCTL 插入间隔 |

### 10.5 明确不是钩子

| 对象 | 原因与做法 |
| --- | --- |
| force / deposit FSM 当前态或非法态 | 禁止。默认分支用 [CODING_STYLE.md](CODING_STYLE.md) 的 **具名 waiver** 覆盖。到达 `Link_Active` 必须走真实转移，并用 `LMSM_TMR_SCALE` 缩短等待 |
| PCS RX unpack 中 `n==0 && have` 的 drain 分支 | **待定：验证确认端口可达性，否则删除分支或 waiver**。不为此加产品钩子 |
| CRC / FEC / deskew / 缓冲等叶子内部状态 | 不在产品顶层加钩子。叶子端口或 wrapper 共仿真观察 |
| 内部信号 `force` / `deposit` | 禁止。只允许端口、`tb_*`、寄存器 |

---

## 11. 两套生成网表（`TEST_HOOKS`）

pyCircuit 在 **Python 生成期** 展开 `TEST_HOOKS`，产出 **两套** Verilog，而不是在 Verilog 里用 `ifdef` 再分叉一次。编码与门控约定见 §10、[CODING_STYLE.md](CODING_STYLE.md)。

| 网表 | 生成参数 | 用途 |
| --- | --- | --- |
| **PRODUCT** | `TEST_HOOKS=0` | **没有** `tb_*` 端口。用于 lint、CDC、综合、实现、FPGA。这是交付网表 |
| **HOOKS** | `TEST_HOOKS=1` | 含钩子端口与 mux。必须过 lint 与 CDC，**不得**进入实现/FPGA |

规则：

**(a) 实现只用 PRODUCT。** lint / CDC / 综合 / P&R / FPGA 的签字网表是 `TEST_HOOKS=0`。`TEST_HOOKS=1` 也必须过 lint 与 CDC，但永不进入实现。

**(b) 回归与覆盖率跑 HOOKS。** 在 `TEST_HOOKS=1` 网上跑，且 **两种** `tb_test_mode` 都要覆盖：`tb_test_mode=0` 与 `tb_test_mode=1`。行覆盖率分母是 `TEST_HOOKS=1` 网表（含钩子 mux 代码）；钩子代码 **不另开 waiver**。

**(c) PRODUCT 烟测。** `TEST_HOOKS=0` 网表跑一套与钩子无关的 smoke 子集（证明无钩子端口时功能闭环）。

**(d) 形式等价门禁。** 用 Yosys eqy 或同等开源工具：`TEST_HOOKS=0` 对比 `TEST_HOOKS=1`，且后者 `tb_test_mode=0`、全部 `tb_inj_*` 接到各自复位值（不介入）。两者必须等价；不等价则 **阻断交付**。

---

## 12. 与现有 `rtl/` 的冲突（重写时必须对齐本规格）

| 现有实现 | 本规格 / 规范 | 处理 |
| --- | --- | --- |
| `always @(posedge clk or negedge rst_n)` 异步复位 | 业务逻辑同步复位（D6） | 重写为 `pyc_reg` |
| lane 按 2-bit 切开（`ub_pcs_lane_dist`） | 8-bit 符号分发 | 见 UB-PHY §3.2.2.3 |
| Gray 在 PCS | Gray 在 PMA | 见 UB-PHY §3.3、§3.3.1 |
| LMSM 只有 Idle/Probe/Disc 三态调试骨架 | 完整 §3.4.3 | 重写 `ub_lmsm` |
| TX 先扰码再 FEC，且无 AMCTL/信用/重传 | 顺序与功能以 §3.2、§4 为准 | 不沿用顶层流水线 |
| 手写 SV | 产品 RTL 只由 pyc4.0 生成 | D5、D10 |

旧设计说明 `docs/superpowers/specs/2026-03-28-ub-controller-bottom-up-design.md` 中的 53G/106G、Gray-in-PCS、250–400 MHz 目标，对 M1 **不再生效**。

---

## 13. 开放问题汇总

实现与船长确认前不得假装已关闭。

### 13.1 草案（非已确认的 Xia 默认集）

- `NUM_RETRY_THRESHOLD=15`、`NUM_PHY_REINIT_THRESHOLD=4`（规范推荐）。
- `CRD_BP_THRESHOLD=1024`。
- `tb_obs_dll_sm_st` 项目编码（§10.3；LMSM 顶层编码已定）。

### 13.2 待定

- RX 缓冲深度。
- per-lane RX valid；AMCTL 是否与数据口共用。
- `pma_tx_width` 编码；均衡针脚。
- LMB 由谁拼装；`lmsm_tx_pattern_sel` 枚举。
- DLL↔PCS 是否需要 sop/eop；FEC bypass 时 `fec_ok` 含义。
- FEC 交织 CodecNum；并行度与编解码拍数。
- RETRY_ACK_SM 实现细节；ERROR_FLAG 发送。
- 规范写「实现相关」的超时（Probe 等待、部分计数）。
- PMA 模型存放路径与模型保真度（是否模拟 RC 探测波形）。
- Data Rate 0 下 EQ/RXEQ 空转策略。
- `MAX_DP_FLITS` 取值。
- 齿轮箱拍数关系（flit 160b 与 PMA 字宽不对齐时的拍数，不是跨时钟）。
- `pcs_fec_mode` 编码。
- `LMSM_TMR_SCALE` / `AM_IVL_SCALE` 的具体缩放编码。
- `tb_inj_am_lock` / `tb_inj_lid_bad`：M1 保留；**待定**是否在 PMA 模型证明能出真实 AM 之后删除。
- PCS RX unpack `n==0 && have` drain 分支：验证确认端口可达性，否则删除分支或 waiver。

### 13.3 未知

- 工艺节点（**未知，待船长定**）。
- Probe 端接检测的电路级算法（规范交给实现）。
- 真实 SerDes 的模拟参数（M1 不包含）。
- 完整附录 D 字段复位值（本仓库不抄规范复位表；镜像窗口复位标「见对应节 / 待实现对照」）。
