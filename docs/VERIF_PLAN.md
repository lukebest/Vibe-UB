# Vibe-UB Controller 验证计划

| 项 | 内容 |
| --- | --- |
| 文档 | `docs/VERIF_PLAN.md`（draft） |
| 目标 DUT | 完整 UB controller RTL（pyCircuit / pyc4.0 生成 Verilog） |
| 规范基线 | UnifiedBus Base Specification **Rev 2.0**（2025-12-31），见 D1 |
| 验证框架 | 仅 uvm-python + cocotb 1.9.2 + cocotb-coverage 1.2.0，见 D7 / D8 |
| 状态 | draft，不自合；只新增本文件 |
| 配套决定 | [PR #2](https://github.com/lukebest/Vibe-UB/pull/2) `docs/DECISIONS.md`（draft，未合）。本计划按 **D1–D16** 编号引用，不改写那些文件。 |
| 设计规格 | **对齐 SPEC PR #4**（`docs/SPEC.md` / `docs/REGMAP.md` / `docs/CODING_STYLE.md`）。不引用任何 commit SHA。 |

职责与流程见 docs/TEAM.md、docs/PROCESS.md。

规范引用只写章节号（如 UB-PHY §3.2.5、UB-DL §4.6.1、SPEC §10、REGMAP TEST）和用自己的话概括的要点。不复制规范正文、表格、公式或寄存器位定义。与 SPEC 冲突处以 SPEC 为准；SPEC 自相矛盾处标「等 SPEC 澄清」，验证不选边。群结论已写入 PR #4 正文的，以文件为准，不标「待 SPEC 落实」。

---

## 0. 与 M0 决定的对照

船长 M0 十六项决定（Luke Liu via Firstmate，2026-10-09）在本计划中的落点：

| 决定 | 摘要 | 本计划落点 |
| --- | --- | --- |
| D1 | 锁 Rev 2.0；Rev 2.1 已知但不采用 | §1、规范出处列；**不再列为风险** |
| D2 | 一期 = PHY/PCS + DLL + LMSM + 寄存器/CDC；NW / TP / TA 推迟 | §2 范围；推迟层测试点状态 = **推迟** |
| D3 | SerDes/PMA 模拟不在 RTL；PCS-PMA 边界行为模型 | §2.3、§5.4；TB 提供模型与环回 |
| D4 | 一期只验强制行为，不做可选特性 | 测试点状态 = **一期不做 D4** |
| D5 | 全部业务 RTL 用 pyCircuit（lukebest/pyCircuit pyc4.0）出可综合 Verilog | §1 目标 DUT |
| D6 | 业务逻辑同步复位；手写 SV 仅白名单 cell（异步复位同步器、CDC 原语） | §5.3 |
| D7 | 唯一框架 uvm-python（钉扎见 D7 / 外仓，不引用本仓 SHA）+ cocotb 1.9.2；Icarus 12.0 主门；Verilator 5.032 对比与行覆盖 | §4 |
| D8 | 定向 + Python 黄金模型；功能覆盖 = 测试点矩阵；`randomize()`；允许 CoverPoint/CoverCross 支撑 TP；禁 pyvsc | §4.3、§8 |
| D9 | 只读参考并改造 Vibe-UB-Switch 的 pyCircuit / uvm-python TB | §6；本 PR **不拷代码** |
| D10 | 现有手写 `rtl/`、`tb/` 后续迁 `legacy/`（另 PR） | §1.3、§12；本 PR 不搬 |
| D11 | 一期无 FPGA | §2.4；不列入 FPGA 里程碑 |
| D12 | 验收 = 行覆盖 + 功能覆盖，**计入具名豁免后 100%**；不算 toggle | §9；门限已定，不再写「待定」 |
| D13 | TB 一律不 force 内部信号；注入只走端口或 SPEC 测试钩子 | §5.5、§7 |
| D14 | 默认参数船长已确认；RTT = 2µs；`F_CORE`≈80.57 MHz 已定；工艺节点仍未知 | §3；对齐 SPEC PR #4 §4.1 / §9 |
| D15 | 规范全文移出公开树（PR #2）；**本仓 git 历史将被改写，改写后所有 SHA 会变** | 本计划**不引用**任何 SHA；只写「对齐 SPEC PR #4」 |
| D16 | D7 钉扎写在决定里；`TOOLCHAIN.lock` 随基础设施 PR | §4.2；本 PR 不添加 lock |

---

## 1. 目标与硬约束

### 1.1 验证目标

对 **完整 UB controller** 做功能验证，覆盖一期范围（D2）：

- PHY / PCS 数据通路与链路状态管理（LMSM）
- DLL（成帧、credit、VL、ACK/重传、异常）
- 配置寄存器子集（规范附录 D）
- 白名单 CDC / 复位同步 cell（D6）

DUT 来源：pyCircuit（pyc4.0，lukebest/pyCircuit）生成的可综合 Verilog（D5）。业务逻辑同步复位（D6）。规范基线锁定 Rev 2.0（D1），Rev 2.1 不纳入本期符合性。

### 1.2 硬规则（验证侧）

1. **唯一框架（D7）**：uvm-python（lukebest/uvm-python，提交钉扎见 D7 / 外仓，**不引用本仓 SHA**）+ cocotb **1.9.2**（`>=1.9.2,<2`）+ cocotb-coverage **1.2.0**（必须 `<2.0`）。禁止 SV-UVM、禁止无结构的裸 cocotb、禁止 pyvsc（D8）。
2. **仿真器（D7）**：Icarus Verilog **12.0** 主仿并作为 PASS/FAIL 门；Verilator **5.032** 做对比仿真并给出行覆盖。cocotb 1.9.2 文档要求 Verilator `>=5.022`；未重新资格认定前不升到 `>=5.036`。
3. **不 force（D13）**：TB 不 force 内部层次信号。激励与错误注入只走端口，或 §7 列出的 `tb_inj_*` 钩子 / test 模式寄存器。原因：Verilator VPI 不认层次 Force；旧仓因此有 4 个 TC 只能在 Icarus 跑。
4. **验证不改 RTL / 不改 SPEC**。失败回设计并附复现；规范漏洞退回架构（Xia）。
5. **一期不做 FPGA（D11）**。
6. **一期不做可选特性（D4）**。
7. **本仓 SHA**：Vibe-UB 的 git 历史将被改写。本计划不引用任何 SHA，只写「对齐 SPEC PR #4」。
8. **与 SPEC 对齐**：功能需求以 SPEC PR #4 为准。目前无自相矛盾项（§14.3 空）。若再出现，标「等 SPEC 澄清」，验证不选边。

### 1.3 与当前树中手写 Verilog 的关系（D10）

本仓现有 `rtl/`、`tb/` 为手写 Verilog（含异步复位风格与不完整 LMSM）。按 D10，这些文件**后续**迁到 `legacy/`（另开 PR，本计划不搬）。官方回归的 DUT 是 pyc4.0 生成物。现有手写 TB 不计入官方门，仅可作对照参考。

---

## 2. 范围与层次

### 2.1 一期范围（D2）

| 层次 | 对象 | 说明 |
| --- | --- | --- |
| 单元级 | 每个 pyCircuit 模块 | PCS 编解码/分发/FEC/LMSM 叶模块；DLL 成帧/CRC/credit/retry/SM；附录 D 寄存器叶；CDC 白名单 cell |
| 子系统级 | PCS/FEC、DLL、LMSM+寄存器 | TX/RX 数据通路串接、FEC 纠错边界、DLL 成帧+流控+重传、LMSM 训练到 Link_Active |
| 顶层 | controller + 环回 | 网络侧 flit 口 ↔ PCS-PMA 边界行为模型（D3）环回；含训练、credit/retry、钩子注错 |

### 2.2 推迟范围（D2）

下列层次**只留占位测试点**，状态一律标 **推迟**，一期不实现 TC、不计入门限分母（除非船长改 D2）：

- 网络层（UB-NW 第 5 章）
- 传输层（UB-TP 第 6 章）
- 事务层（UB-TA 第 7 章）
- 功能 / 内存 / 资源 / 安全（第 8–11 章）

占位目的：避免后续把上层职责误写进 DLL/PCS 检查。

### 2.3 PMA / SerDes（D3）

模拟 PMA / 真实 SerDes **不在 RTL 范围**。验证在 **PCS-PMA 边界**使用 TB 提供的行为模型：

- ASIC **只做 PCS + DLL 数字部分**；PMA 不进网表，由 TB 行为模型承担（D3，船长已确认）
- 按 lane 接收/发送符号流（M1：32 bit/lane，见 §3）
- 提供对称环回（TX 边界直接接到 RX 边界，可加可配置 deskew 延迟）；模型须能产生**真实 AM**。`tb_inj_am_lock` / `tb_inj_lid_bad` 在 SPEC §10.2 **M1 保留**；是否在模型证明能出真实 AM 之后删除见 SPEC §13.2
- Gray / 预编码在 **PMA 模型**（SPEC §2.3），不在 PCS。M1 NRZ：Gray 不启用；`PRECODE_EN=0`
- RX **valid-only**：无 `pma_rx_ready`、无 `pcs2dll_ready`。PMA 每拍必到一字，PCS→DLL 只有 valid，DLL 每拍必收。DLL 内部缓冲深度见 SPEC §13.2。**PMA→PCS / PCS→DLL 没有反压 TP**
- 不模拟模拟均衡、CDR 抖动、光模块；保真度见 SPEC §13.2（待定）

顶层「含环回」= 该行为模型环回，不是 FPGA 板级环回（D11）。

### 2.4 明确不做（一期）

| 项 | 依据 | 处理 |
| --- | --- | --- |
| FPGA 原型 / 板级 | D11 | 无 FPGA 里程碑 |
| 可选规范特性 | D4 | 测试点标 **一期不做 D4** |
| NW / TP / TA 功能 | D2 | 测试点标 **推迟** |
| Toggle 覆盖 | D12 | 不算验收 |
| 层次 Force | D13 | 禁止；相关旧写法记 SKIP 而非改成 Force |
| 亚稳态统计 | — | M1 产品通路无 CDC（SPEC §4.1）；后续才用白名单原语 |
| `TEST_HOOKS=0` vs `=1` 在复位钩子口下不等价 | SPEC §11 (d) | Yosys eqy 失败则**不算交付** |
| 独立 `pma_clk` / 多时钟 | SPEC §1.2、§4.1 | M1 非目标；`USE_PMA_CLK=0` |

---

## 3. 默认参数（D14，船长已确认）

下表为 Xia 默认参数，**船长已确认**。激励与黄金期望按此表搭建。`F_CORE` 已定；工艺节点仍未知，不影响功能门。

| 项 | 确认值 | 备注 |
| --- | --- | --- |
| PHY 模式 | Mode-2 | D1 Rev 2.0；Mode-1 为一期不做 D4 |
| M1 速率 | 2.578125 Gbit/s，Data Rate 0，NRZ | 规范上限 106.25 Gbit/s PAM4，RTL 参数化，更高速率 = 后续 |
| Lane | M1：x1 起训到 x4；RTL 参数到 x8 | 宽度非对称规范支持，M1 默认关 → **一期不做 D4**；速率非对称不允许 |
| SerDes / PMA | M1：32 bit/lane；**PMA 用模型，不进 ASIC** | ASIC 只做 PCS + DLL 数字部分（D3） |
| FEC | 默认 RS(128,120,T=4)；T=2 / bypass 可协商 | 交织（双 codec）→ **一期不做 D4** |
| DLL VL | M1 = 2；参数到 16 | VL 3–15 为后续 |
| 重传缓冲 | M1 = 256 flit | 更大深度后续 |
| Credit | 1 flit/cell；返回粒度 32；独占模式；M1 每 VL 640 cell | 共享模式 → **一期不做 D4** |
| RTT | **2 µs** | 用于 credit / 重传往返时间假设 |
| 核时钟 | `core_clk` ≈ **80.57 MHz**（`2.578125e9/32`） | SPEC §4.1。仿真周期 **12.41 ns**。无 `pma_clk`，`USE_PMA_CLK=0` |
| 复位 | `rst_n` 低有效；异步置位、同步释放 | 经 `ub_rst_sync` → `ub_pyc_rst_adapt`（SPEC §4.2） |
| 预编码 | `PRECODE_EN=0` | SPEC §2.3、§9 |
| 训练 / 重传超时周期数 | 规范写「实现相关」的等 SPEC §13.2 | 用 `LMSM_TMR_SCALE`（REGMAP TEST / SPEC §10.4）跑真实路径 |
| ASIC 工艺节点 | 未知，待船长定 | SPEC §13.3。不阻功能门 |

---

## 4. 验证框架与工具链

### 4.1 方法

- **定向测试**为主，每个测试点至少一条可独立复现的 TC。
- **Python 黄金模型 + scoreboard**：PCS（FEC / 扰码 / 8-bit 符号分发）、PMA 模型（Gray 仅 PAM4）、DLL（LPH/LBH/BCRC、credit、retry）。
- 需要随机处使用 uvm-python 自带 `randomize()`（cocotb-coverage crv）。**每次运行把 seed 写入该 TC 日志**（D8）。
- 功能覆盖按 **测试点矩阵** 计算：一条 TP 在其映射 TC 全部 PASS 且对应 CoverPoint/CoverCross 命中后记覆盖。允许用 cocotb-coverage 的 **CoverPoint / CoverCross** 支撑 TP（D8），不引入 pyvsc。

### 4.2 钉扎与 TOOLCHAIN.lock（D7 / D16）

| 组件 | 钉扎 |
| --- | --- |
| Python | 3.11–3.13 |
| cocotb | 1.9.2（`>=1.9.2,<2`） |
| uvm-python | lukebest/uvm-python，提交钉扎见 D7（外仓；**不写本仓 SHA**） |
| cocotb-coverage | 1.2.0（`<2.0`） |
| cocotb-bus、regex | 从 Vibe-UB-Switch 已通过 venv 的 `pip freeze` 冻结（M2 引入 TB 时） |
| Icarus | 12.0（主门） |
| Verilator | 5.032（对比 + 行覆盖） |

`TOOLCHAIN.lock` **随基础设施 PR 落地（D16）**，本验证计划 PR 不新增该文件。未出 lock 前，以 D7 与上表为准。

### 4.3 覆盖采集

| 类型 | 来源 | 是否计入 D12 |
| --- | --- | --- |
| 行覆盖 | Verilator 5.032，**分母 = `TEST_HOOKS=1` 网表** | 是；钩子代码计入分母，不单独豁免。Icarus 无代码覆盖 |
| 功能覆盖 | 测试点矩阵 + CoverPoint/CoverCross（D8） | 是 |
| Toggle | — | **否** |

---

## 5. TB 架构

官方 TB 目录规划（基础设施 PR 落地，本 PR 不建树）：`tb/vibe/pyuvm/`，风格对齐 Switch 仓，但 env/agent 按 **controller** 重写。

### 5.1 uvm-python 组件

```
                    +------------------ ub_env ------------------+
                    |  clk_rst_agent   csr_agent   hook_agent    |
  seq / virtual seq |  nw_agent (flit)              pma_agent    |
                    |         \                    /             |
                    |          monitors -----> scoreboard         |
                    |                         + ref models       |
                    +--------------------------------------------+
                                      |
                    DUT: ub_controller (pyc4.0 Verilog)
                                      |
                    TB: pcs_pma_bfm (D3 边界行为模型 / 环回)
```

| 组件 | 职责 |
| --- | --- |
| `ub_env` | 组装 agent、scoreboard、覆盖收集器；按层次（unit / subsys / top）裁剪 |
| `nw_agent` | 网络侧 ready/valid flit（160 bit）driver/monitor；一期只作为 DLL 上边界，不实现 NW 协议（D2） |
| `pma_agent` | 驱动/监视 PCS-PMA 边界符号；可切到环回 BFM（D3） |
| `csr_agent` | SPEC §3.2.3 整字 CSR + REGMAP TEST（`LMSM_TMR_SCALE`、`CRD_TO_DIS`、`PCS_TX_TEST.AM_IVL_SCALE`）+ `PORT_CNA` |
| `hook_agent` | 仅驱动 SPEC §10 的 `tb_inj_*`、采样 `tb_obs_*`；`TEST_HOOKS` 与 `tb_test_mode` 两道门控 |
| `clk_rst_agent` | 单时钟 `core_clk`，周期 **12.41 ns**；`rst_n` 异步置位、同步释放 |
| `scoreboard` | 订阅各 monitor；与 Python 参考模型比对 |
| 参考模型 | `ref_fec`、`ref_scramble`、`ref_lane`、`ref_dll`（成帧/CRC/credit/retry） |
| 覆盖 | 每条 TP 对应 CoverPoint；需要交叉的用 CoverCross（D8） |

单元级：单模块 + 薄 harness + 对应 leaf agent，不强制拉满顶层 env。

### 5.2 时钟与复位（SPEC §4、CODING_STYLE §2）

- **单时钟**：`core_clk` ≈ 80.57 MHz，仿真周期 **12.41 ns**。`USE_PMA_CLK=0`，无 `pma_clk` / `pma_rst_n`。
- **复位**：顶层 `rst_n` 低有效，**异步置位、同步释放**，只经白名单 `ub_rst_sync`（**2 级**）得 `rst_n_sync`，再经 `ub_pyc_rst_adapt` 得 `rst_pyc`。业务模块只接 `rst_pyc`（同步复位，D6）。
- TB 在时钟沿对齐后释放复位，检查复位窗内输出安静。不注入亚稳态毛刺。
- 现有手写 `always @(posedge clk or negedge rst_n)` 属 D10 遗留（SPEC §12）。

### 5.3 多时钟域与 CDC

- M1 **产品通路无 CDC**（SPEC §4.1）。`pyc_cdc_sync` / `pyc_async_fifo` 仅后续阶段；对应 TP 标推迟。
- 禁止用 Force 打内部 CDC 节点（D13）。

### 5.4 PCS-PMA 行为模型与环回（D3）

TB 提供 `pcs_pma_bfm`：

1. **直通环回**：各 lane TX 符号延迟 N cycle 后送回 RX（N 可配，用于 deskew 窗口）。
2. **符号注错**：只改边界口上的符号（D3 模型），用于 FEC / BCRC / 重传。不另开比特翻转钩子。
3. **真实 AM**：模型须产生可锁定的 AM。`tb_inj_am_lock` 宽度为 `NLANE=NUM_LANES_RX`（SPEC §10.2），不是固定 4 bit。
4. **Gray / 预编码**：在模型内；M1 NRZ 不启用 Gray，`PRECODE_EN=0`。
5. **不实现**模拟前端、光通道、FFE/DFE；保真度待定（SPEC §13.2）。

顶层默认走环回 1。对端 LMSM/DLL 协商可用第二实例 controller 或轻量对端 BFM；对端 BFM 必须遵守同一套 Python 黄金模型，不能「对着 DUT 抄答案」。

### 5.5 禁止 Force（D13）

- 任何 TC 不得层次 Force。
- 注入只走端口、D3 PMA 模型，或 §7 的 `tb_inj_*`（且 `TEST_HOOKS=1` 且 `tb_test_mode=1`）。
- 观测只走端口、`tb_obs_*` 或寄存器读。不得为了打内部态把 FSM 停到指定态。
- 从 Switch 仓拷过来的编排若仍带 `VERILATOR_TOOL_SKIP`，只用于尚未改完的遗留 TC；新写 TC 不得再依赖 Force。

---

## 6. 可复用资产（D9，只读参考）

来源：<https://github.com/lukebest/Vibe-UB-Switch> 的 `tb/vibe/pyuvm/`（以及 `tb/vibe/scripts/summarize.sh`）。**本 PR 不拷贝任何代码。** 基础设施 / TB 实现 PR 再按下列清单搬。

### 6.1 拷过来改（保留骨架，换 DUT 映射）

| 资产 | 改什么 |
| --- | --- |
| `catalog.py`（及分册 catalog） | 重写 TC → toplevel / 源文件 / entry；删 fabric/switch 路由表 |
| `run_gate.py` | 桶改为 `unit / pcs / dll / top / gate`；保留 PASS/FAIL/SKIP 写 log |
| `scripts/summarize.sh` | 几乎原样；输出目录改到 `reports/regress/` |
| SKIP 记账（`VERILATOR_TOOL_SKIP`） | 保留「工具缺口记 SKIP、不记 PASS」；**新 TC 不得因 Force 进此表** |
| `Makefile.cocotb` | 保留 cocotb 1.9.2 调用方式；源列表对 pyc4.0 Verilog |
| `requirements.txt` 形态 | 钉到 D7；正式 freeze 进 TOOLCHAIN.lock（D16） |
| `vibe_uvm/report.py` | 保留 `PASS/FAIL/NOTE/SKIP` 行协议；复现行加上 seed |
| `vibe_uvm/tests/unit_base.py` | 保留 leaf TC 模板 |
| `vibe_uvm/prbs31.py` | 仅当 PMA idle 图案仍按 Switch 实现时改多项式/位宽后复用；PCS 扰码另写黄金模型 |
| `vibe_uvm/lph.py` 中与规范一致的 PLEN/DLLDB 切分 | 去掉 Switch overlay / CNA 路由假设，按 UB-DL §4.3 重对齐 |

### 6.2 必须重写（controller ≠ switch fabric）

| 资产 | 原因 |
| --- | --- |
| `env.py` / `agents.py` / `vif.py` | 端口是 flit + PCS-PMA 边界，不是 ingress/egress 交换 |
| `scoreboard.py` | 黄金模型是 PCS/DLL，不是路由/G1 drop |
| `items.py` / `seqs.py` | transaction 是 flit/DLLCB/符号，不是 NW512 beat |
| `entry_fab.py` / `entry_port.py` / `entry_switch.py` | 换成 `entry_unit` / `entry_pcs` / `entry_dll` / `entry_top` |
| 全部 `vibe_uvm/tests/unit_*.py`、`fab_tests.py`、`port_tests.py` | TC 标识与检查重写；FEC/CRC 叶测试可参考算法，不可照搬层次路径 |
| Switch 专用 `static_tests.py` 缺项扫描 | 按本仓模块清单重写 |

### 6.3 明确不搬

- Switch fabric / VOQ / 路由 / ICRC / CNA 配置空间 TC
- 依赖层次 Force 的 4 个旧 TC 写法（只吸收「记 SKIP」的教训）
- 任何 SV-UVM

---

## 7. 测试钩子与 TEST 寄存器（对齐 SPEC PR #4 §10、REGMAP TEST、§11）

注入与观察只走顶层功能端口、SPEC §10 的 `tb_*`、或 REGMAP 寄存器（D13；CODING_STYLE §4）。不发明额外钩子。

### 7.1 两道门控（SPEC §10.1、§11）

1. Python 生成期 **`TEST_HOOKS`**：PRODUCT=0（无 `tb_*` 端口）；HOOKS=1。
2. 顶层 **`tb_test_mode`**：HOOKS 且 =0 时注入不介入、观察输出保持 0；=1 时生效。

复位 = 不介入。`tb_inj_*` 为电平，mux 进目标模块输入，**不回灌**源模块输出。

### 7.2 注入钩子（SPEC §10.2，仅此三支）

| 端口 | 宽度 | 接入 | 含义 |
| --- | --- | --- | --- |
| `tb_inj_am_lock` | `NLANE=NUM_LANES_RX` | `ub_lmsm` | mux 到 LMSM 的 `am_locked`。M1 保留；删除条件见 SPEC §13.2 |
| `tb_inj_lid_bad` | 1 | `ub_lmsm` | mux 到 `lid_bad`。同上 |
| `tb_inj_crd_cells` | 16 | `ub_dll` 信用 | **只覆盖 VL0**。`tb_test_mode=1` 时**每拍 mux 覆盖** cell 计数；HOOKS 不另加存储。无 VL 选择寄存器 |

FEC / BCRC 错由 D3 PMA 模型改符号，无对应钩子。

### 7.3 观测钩子（SPEC §10.2–§10.3）

| 端口 | 宽度 | 含义（以 SPEC 为准） |
| --- | --- | --- |
| `tb_obs_link_ready` | 1 | **仅** `LMSM==Link_Active` |
| `tb_obs_link_up` | 1 | `Send_NullBlock` **或** `Link_Active` |
| `tb_obs_lmsm_st` | 5 | **只给顶层状态编码** 0–9（Idle…Equalization），不含子状态 |
| `tb_obs_crd_cells` / `pend` / `low` / `bp` / `to` | 16 / 16 / 1 / 1 / 11 | **仅 VL0**。`bp` 阈值 `CRD_BP_THRESHOLD` 草案 1024（SPEC §13.1） |
| `tb_obs_dll_sm_st` | 2 | Disabled/Param/Credit/Normal。编码在 SPEC §13.1 标草案 |
| `tb_obs_consume_flits` | 10 | 本拍 DLL TX 消耗 flit 数 |
| `tb_obs_nw_dll_data` | — | **不做**（D2 / SPEC §10.2） |

本端 CNA 走 REGMAP `PORT_CNA`（0x0010）/ App. D.5.5，无钩子。

**VL1**：不能用 `tb_inj_crd_cells`。VL1 的耗尽、回压、超时只靠对端少还或延迟还 credit 构造。

### 7.4 TEST 寄存器（SPEC §10.4、REGMAP §2.4）

仅 `TEST_HOOKS=1` 且 `tb_test_mode=1` 生效；否则写忽略、读 0。

| 寄存器 / 字段 | 偏移 | 行为 |
| --- | --- | --- |
| `LMSM_TMR_SCALE.SCALE` | 0x0300 [7:0] | 缩放 LMSM 超时，走**真实**状态路径到 Link_Active。编码 **待定**（SPEC §13.2） |
| `CRD_TO_DIS.DIS` | 0x0304 [0] | 关闭 Crd_Ack 超时检错 |
| `PCS_TX_TEST.AM_IVL_SCALE` | 0x0308 [7:0] | 缩放 TX AMCTL 间隔。编码 **待定**（SPEC §13.2） |

### 7.5 FSM 与 drain（SPEC §10.5）

- 非法态 / default 臂：具名 waiver，不停指定态。
- PCS RX unpack drain（`n==0 && have`）：SPEC §10.5 / §13.2 **待定**。等新 RTL 出来后再评估端口可达性，现在不删、不加钩子（TP-UNIT-PCS-026）。

---

## 8. 测试点矩阵

列定义：

| 列 | 含义 |
| --- | --- |
| ID | 稳定编号，映射 CoverPoint 名 |
| 规范 | 章节号 only |
| 描述 | 用自己的话 |
| 激励 | 端口 / 环回 BFM / 钩子 / `randomize()` |
| 检查 | scoreboard / 黄金模型 / 状态与计数 |
| 覆盖 | CoverPoint 或 CoverCross（D8） |
| 里程碑 | **M1** = 一期必做；**后续** = 参数化已留、本期不做完 |
| 状态 | **计划** / **RTL未就绪** / **待定** / **推迟**（D2） / **一期不做 D4/D11** |

计数规则：矩阵中每一行 = 1 条测试点。「推迟」「一期不做」计入总数，**不计入 D12 分母**，直到决定变更。原「待定（钩子）」已改指向 §7 的具体钩子、寄存器或 waiver。

### 8.1 单元级 — PCS / LMSM

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-UNIT-PCS-001 | SPEC §2.3；UB-PHY §3.3.1 | Gray 在 **PMA 模型**（非 PCS）；PAM4 映射 | 穷举 2-bit | Python Gray 表 | cp_gray_in | 后续 | 计划 |
| TP-UNIT-PCS-002 | SPEC §2.3；UB-PHY §3.3.1 | Gray 解码为编码的逆（PMA 模型） | 编码输出回灌 | 还原输入比特 | cp_gray_roundtrip | 后续 | 计划 |
| TP-UNIT-PCS-003 | UB-PHY §3.2.2.4 | 扰码：DLL 数据按 LSB→MSB 加扰 | 已知种子 + 定向/随机块 | 黄金 LFSR | cp_scram_seed | M1 | 计划 |
| TP-UNIT-PCS-004 | UB-PHY §3.2.3.2 | 解扰与扰码互逆 | 扰码输出回灌 | 还原明文 | cp_descram | M1 | 计划 |
| TP-UNIT-PCS-005 | UB-PHY §3.2.2.4 | AMCTL / EEIB 不扰；LTB 要扰 | D3 模型出真实 AM / LTB / EEIB | 对照规则 | cp_scram_exempt | M1 | 计划 |
| TP-UNIT-PCS-006 | UB-PHY §3.2.5、§3.2.2.3 | Lane 分发按 **8-bit 符号**、x4 | 已知码字 | 每 lane 符号序 = 黄金模型 | cp_dist_x4 | M1 | 计划 |
| TP-UNIT-PCS-007 | UB-PHY §3.2.5 | 分发 x1 / x2 / x8（参数化） | 扫 LaneNum | 同左 | cp_dist_width | 后续 | 计划 |
| TP-UNIT-PCS-008 | UB-PHY §3.2.3.3 | 解分发为分发的逆 | 环回符号 | 还原码字 | cp_dedist | M1 | 计划 |
| TP-UNIT-PCS-009 | UB-PHY §3.2.2.1 | RS(128,120) 编码，T=4 系统码 | 定向消息 + randomize | 校验子为 0；校验符=黄金 | cp_fec_enc | M1 | 计划 |
| TP-UNIT-PCS-010 | UB-PHY §3.2.2.1 | T=2 时 8 个校验符生成与 T=4 相同 | 同消息两模式 | 校验符相等 | cp_fec_t2_parity | M1 | 计划 |
| TP-UNIT-PCS-011 | UB-PHY §3.2.3.5 | 伴随式：无错全 0、有错非 0 | 0 / 1 符号错 | 伴随式向量 | cp_syndrome | M1 | 计划 |
| TP-UNIT-PCS-012 | UB-PHY §3.2.3.5 | iBM 出错误位置多项式 | 1–4 符号错 | λ 与黄金一致 | cp_ibm | M1 | 计划 |
| TP-UNIT-PCS-013 | UB-PHY §3.2.3.5 | Chien / Forney 纠错幅值 | 同上 | 掩码与幅值 | cp_chien | M1 | 计划 |
| TP-UNIT-PCS-014 | UB-PHY §3.2.3.5 | 解码 0 错：吐 120 符号、fail=0 | 干净码字 | 消息一致 | cp_dec_clean | M1 | 计划 |
| TP-UNIT-PCS-015 | UB-PHY §3.2.3.5 | 解码 1–T 符号错（T=4）全部纠正 | 扫错误个数与位置 | 消息恢复、fail=0 | cx_dec_t_pos | M1 | 计划 |
| TP-UNIT-PCS-016 | UB-PHY §3.2.3.5 | >T 不可纠：报失败 | T+1 及以上 | fec_fail；不静默当好包 | cp_dec_fail | M1 | 计划 |
| TP-UNIT-PCS-017 | UB-PHY §3.2.2.2 | 单 codec 预 FEC 按 8-bit 符号装入 | 串行流 | 符号下标=黄金 | cp_prefec | M1 | 计划 |
| TP-UNIT-PCS-018 | SPEC §2.4、§13.2；UB-PHY §3.2.2.3 | 双 codec 交织（`FEC_CODEC_NUM`） | — | CodecNum 待定，建议 1 | — | — | 一期不做 D4 |
| TP-UNIT-PCS-019 | UB-PHY §3.2.4 | eBCH-16 / AMCTL 结构叶 | 定向 AMCTL 场 | 编码与识别 | cp_amctl_enc | M1 | RTL未就绪 |
| TP-UNIT-PCS-020 | UB-PHY §3.3.2 | Precoding 叶 | — | — | — | — | 一期不做 D4 |
| TP-UNIT-PCS-021 | SPEC §6.1；UB-PHY §3.4.3.1；REGMAP `CTRL.LMSM_START` | LMSM Link_Idle：未开训保持、CSR 启动离开 | 写 `CTRL.LMSM_START`（0x0000 bit1）。SPEC §6.1 旧名 `LMSM_CTRL.START` **作废** | `tb_obs_lmsm_st==0` 再离开 | cp_lmsm_idle | M1 | 计划 |
| TP-UNIT-PCS-022 | SPEC §6.1、§10.4；REGMAP `LMSM_TMR_SCALE`；UB-PHY §3.4.3.2 | Probe：超时/完成进入下一态 | `LMSM_TMR_SCALE` 走真实路径；缩放编码 / 实现相关超时见 SPEC §13.2 | `tb_obs_lmsm_st` 顶层码 | cp_lmsm_probe | M1 | 计划 |
| TP-UNIT-PCS-023 | SPEC §6.1；UB-PHY §3.4.3.4–§3.4.3.7 | Discovery / Config / Send_NullBlock / Link_Active | D3 真实 AM + `LMSM_TMR_SCALE` | `tb_obs_lmsm_st` 0–6 合法路径 | cx_lmsm_fwd | M1 | RTL未就绪 |
| TP-UNIT-PCS-024 | SPEC §6.1、§10.2；UB-PHY §3.4.3.8 | Retrain（锁丢失 / 不可纠） | 优先 D3 丢锁；可选 `tb_inj_am_lock`/`tb_inj_lid_bad`（不回灌 PCS） | `tb_obs_lmsm_st==7` | cp_lmsm_retrain | M1 | 计划 |
| TP-UNIT-PCS-025 | SPEC §6.1 | M1：`Change_Speed` 实现状态但不改速率（或作非法请求） | 请求改速 | 速率仍 Data Rate 0；`tb_obs_lmsm_st` | cp_chgspd_norate | M1 | 计划 |
| TP-UNIT-PCS-026 | SPEC §10.5、§13.2 | PCS RX unpack drain（`n==0 && have`） | **等新 RTL** 后再评估端口是否可达 | 可达则测；不可达报 Xia 删或 waiver。现在不加钩子 | cp_unpack_drain | M1 | **待定** |
| TP-UNIT-PCS-027 | SPEC §10.5；D12 | LMSM 非法态 / default 臂 | 不注入、不停指定态 | 具名 waiver | cp_lmsm_default | M1 | 计划（waiver） |
| TP-UNIT-PCS-028 | SPEC §5、§13.2 | FEC 编解码拍数与并行度 | 实现后回填激励 | 拍数记入 scoreboard | cp_fec_lat | M1 | **待定**（§13） |
| TP-UNIT-PCS-029 | SPEC §6.1、§13.2 | Data Rate 0 下 EQ/RXEQ 空转策略 | 进入 EQ / RXEQ_Optimize | 空转超时退出或跳过（等 SPEC） | cp_eq_idle | M1 | **待定**（§13） |
| TP-UNIT-PCS-030 | SPEC §3.3.4；UB-PHY §3.4.1 | LMB 拼装：LMSM 给公共字段；PCS **按物理 lane** 填 Lane_ID，**每条 lane 单独**算 CRC（符号 12–13）和填充（14–15） | 训练期出 LTB，x4 | 各 lane CRC/填充不同；无独立 `pcs_fec_mode` | cp_lmb_src | M1 | 计划 |
| TP-UNIT-PCS-031 | SPEC §3.3.4、§5 | **LMB 中途改任意 `lmsm2pcs_*`**（字段、`pattern`、`ltb_valid`、`lane_id_mode`/`base`/`map`）：PCS 在每个 LMB **起始**锁存；当前 LMB 不变，下一 LMB 才生效。`lmsm2pcs_ltb_valid` 无多拍保持 | 一帧进行中改上述任一信号 | 当帧仍用旧锁存；下一 LMB 用新值 | cp_ltb_latch | M1 | 计划 |
| TP-UNIT-PCS-032 | SPEC §3.3.4 | `lmsm2pcs_pattern=0` 电气空闲 | 置 0 | 各 lane 电气空闲，无 LTB 字段口 | cp_pat_idle | M1 | 计划 |
| TP-UNIT-PCS-033 | SPEC §3.3.4；UB-PHY §3.4.1.2 | `lmsm2pcs_pattern=1` EEIB | 置 1 | PCS 按当前 Data Rate 出 EEIB；不用 LTB 字段 | cp_pat_eeib | M1 | 计划 |
| TP-UNIT-PCS-034 | SPEC §3.3.4 | `lmsm2pcs_pattern=2` LTB | 置 2 | 走字段口插入 LTB | cp_pat_ltb | M1 | 计划 |
| TP-UNIT-PCS-035 | SPEC §3.3.4 | `lmsm2pcs_pattern=3` DLL payload | 置 3 | 出 DLL 业务码流 | cp_pat_dll | M1 | 计划 |
| TP-UNIT-PCS-036 | SPEC §3.3.4 | `lmsm2pcs_lane_id_mode[1:0]=0` **PHYS**：Lane_ID=该物理 TX lane 号；`base`/`map` **忽略** | mode=0，乱填 base/map；x4 | 每 lane Lane_ID=物理号；每 lane 自算 CRC | cp_lid_phys | M1 | 计划 |
| TP-UNIT-PCS-037 | SPEC §3.3.4 | `lmsm2pcs_lane_id_mode[1:0]=1` **ASCEND**：用 `lane_id_map` / `lane_id_base` | mode=1；x4 | 各激活 lane 编号唯一、沿 Tx_0..Tx_M-1 递增（或该 lane NULL）；每 lane 自算 CRC | cp_lid_asc | M1 | 计划 |
| TP-UNIT-PCS-038 | SPEC §3.3.4 | `lmsm2pcs_lane_id_mode[1:0]=2` **NULL**：各激活 lane 写 §3.4.1.1 空值；`base`/`map` **忽略** | mode=2，乱填 base/map | Lane_ID 全空；每 lane 自算 CRC | cp_lid_null | M1 | 计划 |
| TP-UNIT-PCS-039 | SPEC §3.3.4 | `fec_mode_ctrl[2:0]` **取代** `pcs_fec_mode`；覆盖合法取值（对照 UB-PHY §3.4.1.1，含 T=4 / T=2 / bypass） | 扫合法编码 | PCS 数据通路 FEC 只跟此字段；无 `pcs_fec_mode` 口 | cp_fec_ctrl | M1 | 计划 |
| TP-UNIT-PCS-040 | SPEC §3.3.4 | RX：`pcs2lmsm_lane_id[7:0]` 与其它 `pcs2lmsm_*` 仅在 `pcs2lmsm_ltb_valid` 单拍（CRC 通过）有效 | 对端出 DLTB/CLTB | CRC 失败无 valid；TX 无 `lmsm2pcs_lane_id` | cp_ltb_rx | M1 | 计划 |
| TP-UNIT-PCS-041 | SPEC §3.3.4 | **ASCEND** 下 `lmsm2pcs_lane_id_base[7:0]` 与 `lmsm2pcs_lane_id_map[8*NUM_LANES_TX-1:0]`：字节 i 给物理 lane i；`base` 等于逻辑 Tx_0 那一字节 | mode=1；扫 map 递增 / 单 lane NULL / base≠map[Tx_0] | lane i 用 map 字节 i；base 仅对照。PHYS/NULL 不走本 TP | cp_lid_map | M1 | 计划 |
| TP-UNIT-PCS-042 | SPEC §3.3.4 | PCS leaf：端口驱动 `lmsm2pcs_lane_id_mode=3`（`RESERVED`）。与 `=2` **同一解码分支**，按 NULL（mode=2 或 3）处理；无不可达分支 | leaf TB 分别打 2 与 3 | Lane_ID/CRC 与 mode=2 相同。**无 waiver** | cp_lid_3 | M1 | 计划 |
| TP-UNIT-PCS-043 | SPEC §3.3.4 | LMSM **永不驱动** `lane_id_mode=3`。TB 断言：训练全过程 `lmsm2pcs_lane_id_mode != 3` | 完整 LMSM 路径（真实转移） | 断言永不触发。不 force LMSM 出 3 | cp_lid_no3 | M1 | 计划 |

### 8.2 单元级 — DLL

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-UNIT-DLL-001 | UB-DL §4.3.2.2.4、§4.7.2 | 并行 CRC-32 / BCRC 生成 | 定向块 + 随机 flit | 黄金 CRC | cp_bcrc_gen | M1 | 计划 |
| TP-UNIT-DLL-002 | UB-DL §4.7.2 | BCRC 检查：好包通过、单比特失败 | 好/坏尾 | pass/fail | cp_bcrc_chk | M1 | 计划 |
| TP-UNIT-DLL-003 | UB-DL §4.3.2.2.2 | Segmenter 在首 DLLDB 插入 LPH | SOP 包 | LPH 场与 PLEN 黄金 | cp_lph | M1 | 计划 |
| TP-UNIT-DLL-004 | UB-DL §4.3.2.2.3 | 中间/末 DLLDB 插入 LBH | 跨 32-flit 切段 | LBH 场 | cp_lbh | M1 | 计划 |
| TP-UNIT-DLL-005 | UB-DL §4.3.2.1 | DLLDP 1–512 flit、DLLDB ≤32 | 长度扫 + randomize | 切段数=黄金 | cx_len_nblk | M1 | 计划 |
| TP-UNIT-DLL-006 | UB-DL §4.3.4.3 | Reassembler 解析 LPH/LBH 还原包 | 合法段流 | SOP/EOP/数据 | cp_reasm | M1 | 计划 |
| TP-UNIT-DLL-007 | UB-DL §4.3.3.1 | CFG 区分 DLLCB 与 DLLDP | 两类帧 | CB 不上送网络口当数据 | cp_cfg | M1 | 计划 |
| TP-UNIT-DLL-008 | UB-DL §4.2 | DLL SM：Disabled→Param_Init→Credit_Init→Normal | LinkUp 与 Init/Crd 握手 | `tb_obs_dll_sm_st`、`tb_obs_link_up` | cx_dll_sm | M1 | RTL未就绪 |
| TP-UNIT-DLL-009 | UB-DL §4.4、§4.3.3.9 | Init Block 强制场协商（粒度、VL 使能、独占） | 对端 Init | 取交集规则 | cp_init_neg | M1 | RTL未就绪 |
| TP-UNIT-DLL-010 | UB-DL §4.5 | VL ID 写入 LPH/LBH；同 VL 内 FCFS | 双 VL 交错（M1=2） | 顺序与 VL 场 | cp_vl | M1 | RTL未就绪 |
| TP-UNIT-DLL-011 | UB-DL §4.6.1.2 | Credit 独占：每 VL 独立计数 | 单 VL 耗尽；可选 `tb_inj_crd_cells` | `tb_obs_crd_*`，无 credit 停发 | cp_crd_ex | M1 | RTL未就绪 |
| TP-UNIT-DLL-012 | UB-DL §4.6.2 | 发送扣 credit、返回加回；1 flit/cell | 精确长度包 | `tb_obs_crd_cells` / `tb_obs_consume_flits` = 黄金 | cp_crd_acc | M1 | RTL未就绪 |
| TP-UNIT-DLL-013 | UB-DL §4.6.3 | 返回粒度 32 cell | 积满再返 | 场粒度；`tb_obs_crd_*` | cp_crd_grain | M1 | 计划 |
| TP-UNIT-DLL-014 | UB-DL §4.3.3.5、§4.6.1 | Crd_Ack 初始化与补充返回 | Credit_Init + Normal | 初值 640 cell/VL；`tb_obs_crd_cells` | cp_crdack | M1 | 计划 |
| TP-UNIT-DLL-015 | UB-DL §4.6.1.3 | Credit 共享模式 | — | — | — | — | 一期不做 D4 |
| TP-UNIT-DLL-016 | UB-DL §4.5.1 | DLLCB 不耗 credit | 插 Null/NOP | credit 不变 | cp_cb_nocred | M1 | RTL未就绪 |
| TP-UNIT-DLL-017 | UB-DL §4.7.3.2 | Retry buffer 存发、ACK 释放 | 发包 + ACK | 占用/释放 | cp_retry_buf | M1 | RTL未就绪 |
| TP-UNIT-DLL-018 | UB-DL §4.7.3.3 | RETRY_REQ_SM | D3 模型打坏 BCRC（无 BCRC 钩子） | `tb_obs_dll_sm_st` 请求序 | cp_req_sm | M1 | RTL未就绪 |
| TP-UNIT-DLL-019 | SPEC §6.4；UB-DL §4.7.3.4 | RETRY_ACK_SM：对端请求时发应答集并从 retry buffer 重放。子条件见 SPEC §6.4 / §13.2 | 对端 Retry_Req | Ack 序。实现细节 **等 SPEC §13.2** | cp_ack_sm | M1 | **待定**（§13） |
| TP-UNIT-DLL-020 | UB-DL §4.7.3.2.4 | 防 lockout | 窗口打满 | 不永久卡死 | cp_lockout | M1 | RTL未就绪 |
| TP-UNIT-DLL-021 | UB-DL §4.3.2.3 | 非 CRC 封装模式 | — | — | — | — | 一期不做 D4 |
| TP-UNIT-DLL-022 | SPEC §10.5；D12 | DLL SM 非法态 / default 臂 | 不注入、不停指定态 | 具名 waiver | cp_dll_default | M1 | 计划（waiver） |
| TP-UNIT-DLL-023 | SPEC §7、§3.2.2；REGMAP `CNT_BAD_VL` / `IRQ_STATUS.BAD_VL` | 非法/未使能 VL：整包丢弃、计数、置 sticky | `nw_tx_vl`∉{0,1} 或未使能 | 不上送；计数+1；`BAD_VL` 粘滞 | cp_bad_vl | M1 | 计划 |
| TP-UNIT-DLL-024 | SPEC §7、§11 (e)、§13.4；REGMAP `CNT_CRD_UF` / `IRQ_STATUS.CRD_UF` | credit 下溢：计数、sticky、irq；**下溢断言放在 TB**；覆盖率用 `WAIVER_CRD_UF_CNT` / `WAIVER_CRD_UF_IRQ`，禁止 force 下溢 | 使计数在 0 时仍减（VL0 可用钩子辅助） | RTL 无 assert；TB assert；irq 源 | cp_crd_uf | M1 | 计划 |
| TP-UNIT-DLL-025 | SPEC §10.2 | `tb_inj_crd_cells` **只作用于 VL0** | 钩子预置 VL0；同时观察 VL1 | VL1 库存不变 | cp_inj_vl0 | M1 | 计划 |

### 8.3 单元级 — 寄存器与 CDC

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-UNIT-CSR-001 | SPEC §1.3；REGMAP §1 | CFG0_BASIC 设备级：M1 **不实现** | — | — | — | — | 推迟 |
| TP-UNIT-CSR-002 | SPEC §1.3；REGMAP §1 | CFG1_*：M1 **不实现** | — | — | — | — | 推迟 |
| TP-UNIT-CSR-003 | 附录 D.5–D.6 | 端口 BASIC/CAP：lane、速率、FEC 默认 | 上电读 | 与 §3 确认值一致 | cp_port_def | M1 | 计划 |
| TP-UNIT-CSR-004 | 附录 D.7 | ROUTE_TABLE | — | — | — | — | 推迟 |
| TP-UNIT-CSR-005 | SPEC §10.4；REGMAP §2.4 `LMSM_TMR_SCALE` | 缩放 LMSM 超时，ACTIVE 走真实路径 | `tb_test_mode=1` 写 SCALE | 不 force 状态；编码待定 §13.2 | cp_tmr_scale | M1 | 计划 |
| TP-UNIT-CSR-006 | SPEC §10.4；REGMAP `CRD_TO_DIS` | 关掉 Crd_Ack 超时检查 | test 模式置 DIS | `CNT_CRD_TO` 不递增 | cp_crd_to_dis | M1 | 计划 |
| TP-UNIT-CSR-007 | SPEC §10.4；REGMAP `PCS_TX_TEST.AM_IVL_SCALE` | 缩放 TX AMCTL 间隔 | 写 AM_IVL_SCALE | 仍走真实插入；编码待定 §13.2 | cp_am_scale | M1 | 计划 |
| TP-UNIT-CSR-008 | SPEC §10.2；REGMAP `PORT_CNA`；App. D.5.5 | 本端 CNA 寄存器读写，无钩子 | CSR 访问 0x0010 | 与软件值一致 | cp_cna_csr | M1 | 计划 |
| TP-UNIT-CSR-009 | SPEC §3.2.3；REGMAP 总线栏 | 只能 32-bit 整字写，无 `csr_wstrb` | 整字写；未对齐当地址未映射 | 未对齐 → `csr_err` | cp_csr_word | M1 | 计划 |
| TP-UNIT-CSR-010 | SPEC §3.2.3、§5；REGMAP 总线栏 | 读固定 1 拍：请求下一拍 `csr_rvalid`/`csr_rdata`/`csr_err` | 读已映射 / 未映射 | 以 SPEC §3.2.3 为准 | cp_csr_rdlat | M1 | 计划 |
| TP-UNIT-CSR-011 | SPEC §3.2.3、§7 | 未映射：读回 0+`csr_err`；写忽略+`csr_err` | 扫空洞地址 | 下一拍 `csr_err=1` | cp_csr_unmap | M1 | 计划 |
| TP-UNIT-CSR-012 | SPEC §3.2.6；REGMAP `IRQ_MASK`/`IRQ_EN` | `irq` 高有效；复位后全部屏蔽 | 复位后置错误源 | `IRQ_MASK=0x7F`、`IRQ_EN=0`，`irq=0` | cp_irq_mask | M1 | 计划 |
| TP-UNIT-CSR-013 | REGMAP `CTRL.PORT_RST`；SPEC §3.2.3、§4.2、§6.2 | `PORT_RST` 写 1 自清；内部 **16 拍**同步复位。**范围内清零**：PCS / LMSM / DLL（含 retry）/ 信用计数 | 业务通路有状态后写 PORT_RST | `tb_obs_lmsm_st==0`、`tb_obs_dll_sm_st==0`；信用回初值；retry 空 | cp_port_rst | M1 | 计划 |
| TP-UNIT-CSR-014 | SPEC §6.1；REGMAP `CTRL.LMSM_START` | 软件启动离开 Link_Idle。名字以 REGMAP 为准：`CTRL.LMSM_START`（0x0000 bit1）。SPEC §6.1 旧名 `LMSM_CTRL.START` **作废** | 写该位 | 离开 Idle | cp_lmsm_start | M1 | 计划 |
| TP-UNIT-CSR-015 | SPEC §9；REGMAP §2.2 | PARAM_* 读回等于确认默认。`NUM_LANES_TX[9:6]` / `NUM_LANES_RX[13:10]`：**二进制** lane 数，合法 **1/2/4/8** 均须读到，复位 **1** | 上电读；参数化扫 1/2/4/8 | 默认与扫到的值一致。保留值见 CSR-028 | cp_param_rb | M1 | 计划 |
| TP-UNIT-CSR-016 | REGMAP §2.3 | 九个 ERR 计数（`0x0200`–`0x0220`，含 `CNT_CRD_UF`）递增并**饱和到全 1** | 各源注错过量 | 停在全 1，不回绕 | cp_err_sat | M1 | 计划 |
| TP-UNIT-CSR-017 | SPEC §3.2.3；REGMAP §2.3 | `CNT_CLR` **0x0224** bit0–8 覆盖全部计数（bit8=`CNT_CRD_UF`）：每一位写 1 只清对应计数，该位**自清** | 九个计数非 0 后逐位写 1 | 对应 COUNT=0；再读 `CNT_CLR==0`；其它计数不动 | cp_cnt_clr | M1 | 计划 |
| TP-UNIT-CSR-018 | REGMAP §2.5 | `APPD_LMSM_ST`=**0x1E00**，`APPD_PORT_ERR`=**0x1F00**（窗内 `0x1000–0x1FFF`） | 读这两址及 `0x1000`/`0x1100`/`0x1200` | 已映射、`csr_err=0` | cp_appd_win | M1 | 计划 |
| TP-UNIT-CSR-019 | SPEC §3.2.3、§10、§11；REGMAP §2.4 | TEST 窗：`tb_test_mode=0` 读 0、写忽略、`csr_err=0`；**PRODUCT 网表永远如此** | HOOKS mode=0 与 PRODUCT 读写 `0x0300–0x03FF` | 已映射。列入产品冒烟（TOP-015） | cp_test_map | M1 | 计划 |
| TP-UNIT-CSR-020 | SPEC §3.2.3；REGMAP `CTRL.PORT_RST` | `PORT_RST` **范围外保留**：CSR 配置、错误计数、IRQ（status/mask）、TEST 不被脉冲复位 | 先写配置/注错/开 TEST，再 PORT_RST | 配置与计数/IRQ/TEST 保持。与 CSR-013 成对 | cp_port_rst_scope | M1 | 计划 |
| TP-UNIT-CSR-021 | SPEC §3.2.6、§7；REGMAP `IRQ_STATUS` | 七个 irq 源置位；粘滞 **W1C**；`IRQ_EN` 合成 `irq` | 分别打 FEC/CRC/RETRY/CRD_PROTO/TRAIN/BAD_VL/CRD_UF | 写 1 清对应位；禁读清 | cp_irq_w1c | M1 | 计划 |
| TP-UNIT-CSR-022 | REGMAP §2.1；SPEC §6.3、§6.4、§10.3；UB-DL §4.7.3.3、§4.7.3.4 | STATUS 镜像 `link_up`/`link_ready`/`LMSM_ST`/`DLL_SM_ST`。`RETRY_REQ_ST[12:10]` 合法 0=`NORMAL`/1=`REQ`/2=`WAIT`/3=`RETRAIN`/4=`ERROR` **均须读到**；`RETRY_ACK_ST[14:13]` 合法 0=`NORMAL`/1=`ACK` **均须读到** | 训练 + DLL 全序（含重传） | 与 `tb_obs_*` 一致；每个合法码在 STATUS 出现。保留值见 CSR-026/027 | cp_status_mirr | M1 | 计划 |
| TP-UNIT-CSR-023 | SPEC §3.2.3 | `csr_ready` M1 恒 1；写响应下一拍 `csr_rvalid=0` 且 `csr_err` 有效 | 连续写/读 | 无等待；以 SPEC §3.2.3 为准 | cp_csr_rdy | M1 | 计划 |
| TP-UNIT-CSR-024 | SPEC §5 | CSR 写生效到控制电平 1 拍 | 写 `LMSM_START` / `IRQ_EN` | 下一拍可见 | cp_csr_wr1 | M1 | 计划 |
| TP-UNIT-CSR-025 | SPEC §3.2.3；REGMAP §2.3 | 计数器 **只读**：写 COUNT 地址忽略且不清零；读计数不清零。无读清、无写即清 | 计数非 0 时写 COUNT、再读 | 值不变；只有 `CNT_CLR` 能清 | cp_cnt_ro | M1 | 计划 |
| TP-UNIT-CSR-026 | REGMAP §2.1；SPEC §6.3；UB-DL §4.7.3.3 | `STATUS.RETRY_REQ_ST` 保留 5–7：RTL **永不**产出。TB 断言全过程 `RETRY_REQ_ST` ∉ {5,6,7} | 完整重传路径（真实转移） | 断言永不触发。不 force 保留码。**无 waiver** | cp_req_rsvd | M1 | 计划 |
| TP-UNIT-CSR-027 | REGMAP §2.1；SPEC §6.4；UB-DL §4.7.3.4 | `STATUS.RETRY_ACK_ST` 保留 2–3：RTL **永不**产出。TB 断言全过程 `RETRY_ACK_ST` ∉ {2,3} | 完整重传应答路径（真实转移） | 断言永不触发。不 force 保留码。**无 waiver** | cp_ack_rsvd | M1 | 计划 |
| TP-UNIT-CSR-028 | SPEC §9；REGMAP §2.2 | `PARAM_PHY.NUM_LANES_TX` / `NUM_LANES_RX` 除 1/2/4/8 外保留：RTL **永不**产出。TB 断言读回只属于 {1,2,4,8} | 上电及参数化 1/2/4/8 | 断言永不触发。不 force 其它值。**无 waiver** | cp_nlane_rsvd | M1 | 计划 |
| TP-UNIT-CLK-001 | SPEC §4.1、§9 | 单时钟 `core_clk`≈80.57 MHz，`USE_PMA_CLK=0` | 顶层无 `pma_clk`；TB 周期 12.41 ns | 端口清单与频率 | cp_core_clk | M1 | 计划 |
| TP-UNIT-RST-001 | SPEC §4.2；CODING_STYLE §2 | `rst_n` 异步置位、同步释放，经 `ub_rst_sync` **2 级** | 异步拉低再同步释放 | 释放对齐 `core_clk`；级数=2 | cp_rst_sync | M1 | 计划 |
| TP-UNIT-RST-002 | SPEC §4.2 | `ub_pyc_rst_adapt`：业务只见 `rst_pyc` | 复位释放后写 CSR | 业务沿同步复位工作 | cp_rst_adapt | M1 | 计划 |
| TP-UNIT-IF-001 | SPEC §3.1 | valid/ready：同拍握手；`ready` 不组合依赖本拍 `valid` | 反压与突发 | 无组合环、无丢拍 | cp_vr | M1 | 计划 |
| TP-UNIT-IF-002 | SPEC §3.2.2 | 单 flit 包 `sop&&eop` 合法；`valid==0` 忽略边带 | 1-flit 包；valid=0 乱边带 | 只在 valid 时采样 | cp_sop_eop | M1 | 计划 |
| TP-UNIT-IF-003 | SPEC §3.2.2、§6.2 | `dll_status_up`/`down` 互斥；仅 Normal 报 up | 走完 DLL SM | 互斥与时序 | cp_dll_stat | M1 | 计划 |
| TP-UNIT-IF-004 | SPEC §3.2.6 | `irq` 高有效电平 | 开使能后打源 | 电平保持到清源/再屏蔽 | cp_irq_lvl | M1 | 计划 |
| TP-UNIT-IF-005 | SPEC §3.2.2、§13.2 | **上层** `nw_rx_ready` 反压与 DLL 内部 RX 缓冲深度（不是 PMA/PCS 反压） | 拉低 NW ready | 深度待定；不得丢已收 flit。无 `pma_rx_ready`/`pcs2dll_ready` TP | cp_rx_buf | M1 | **待定**（§13） |
| TP-UNIT-IF-006 | SPEC §3.1 | 复位撤销后首拍 `valid`/`ready` | 释放复位 | 建议 valid=0；取值 **待定** | cp_vr_rst | M1 | **待定**（§13） |
| TP-UNIT-CLK-002 | SPEC §5、§13.2 | flit 160b 与 PMA 字齿轮箱拍数（非跨时钟） | 连续 flit | 拍数关系待定 | cp_gear | M1 | **待定**（§13） |
| TP-UNIT-PMA-001 | SPEC §2.3、§9 | `PRECODE_EN=0` | 上电 / PARAM 读 | 预编码旁路 | cp_precode_off | M1 | 计划 |
| TP-UNIT-PMA-002 | SPEC §2.3、§12 | M1 NRZ：Gray 不启用；Gray 不在 PCS | 环回 NRZ 符号 | PCS 无 Gray 级 | cp_gray_off | M1 | 计划 |
| TP-UNIT-PMA-003 | SPEC §2.3、§13.2 | PMA 模型保真度（探测波形等） | 模型激励 | 保真度待定 | cp_pma_fid | M1 | **待定**（§13） |
| TP-UNIT-PMA-004 | SPEC §3.2.4、§13.2 | per-lane RX valid；AMCTL 是否与数据口共用 | 训练+业务 | 接口形态待定 | cp_pma_lane_v | M1 | **待定**（§13） |
| TP-UNIT-PMA-005 | SPEC §3.2.5、§13.2 | LMSM–PMA 训练侧带：`probe_pulse_en` / `term_detect` / `rx_eidle_exit` / `phy_ready`；`pma_tx_width` 编码见 §13.2 | Probe + 电气空闲进出 | 电平、非脉冲。width 编码 **等 SPEC** | cp_pma_side | M1 | **待定**（§13） |
| TP-UNIT-PMA-006 | SPEC §3.2.4、§5 | **无** `pma_rx_ready`。PMA 每拍必到一字；PCS 不得反压、必须收下 | 连续符号流 | 端口清单无该 ready；无丢字 | cp_pma_norby | M1 | 计划 |
| TP-UNIT-HOOK-001 | SPEC §10.3 | `tb_obs_lmsm_st` 只给顶层编码 0–9 | 走各主状态 | 无子状态码 | cp_lmsm_enc | M1 | 计划 |
| TP-UNIT-HOOK-002 | SPEC §10.2 | `link_ready` 仅 Active；`link_up` 为 Null 或 Active | 训练全过程 | 与状态编码一致 | cp_obs_link | M1 | 计划 |
| TP-UNIT-HOOK-003 | SPEC §10.2 | 全部 `tb_obs_crd_*` 仅 VL0 | 双 VL 流量 | VL1 不出现在钩子 | cp_obs_crd_vl0 | M1 | 计划 |
| TP-UNIT-HOOK-004 | SPEC §10.1、§10.2 | `tb_inj_crd_cells` 在 `tb_test_mode=1` 时**每拍 mux 覆盖** VL0 cell；HOOKS **不**另加存储寄存器 | 钩子电平变化 | 当拍库存=钩子值；关 mode 后回到功能计数 | cp_inj_mux | M1 | 计划 |
| TP-UNIT-CDC-001 | SPEC §4.2；CODING_STYLE §2–§3 | `ub_rst_sync` 叶：**2 级**；异步置位、同步释放 | 复位口 | 与 RST-001 同路径；禁止 1 级 | cp_rstsync | M1 | 计划 |
| TP-UNIT-CDC-002 | SPEC §4.1、§4.3 | `pyc_cdc_sync`（后续多时钟） | — | — | — | — | 推迟 |
| TP-UNIT-CDC-003 | SPEC §4.1、§4.3 | `pyc_async_fifo`（后续多时钟） | — | — | — | — | 推迟 |
| TP-UNIT-CDC-004 | D6 | 非白名单手写 SV 扫描（静态） | 源码/生成物扫描 | 仅白名单例外 | cp_whitelist | M1 | 计划 |

### 8.4 子系统级 — PCS / FEC / LMSM

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-SUB-PCS-001 | SPEC §2.4；UB-PHY §3.2.2 | TX：扰码→FEC→8-bit 分发（**无 Gray**，Gray 在 PMA） | 网络 flit 块 | 边界符号=黄金链 | cp_txpath | M1 | 计划 |
| TP-SUB-PCS-002 | UB-PHY §3.2.3 | RX：解分发→FEC→解扰 | 黄金符号流 | 还原 flit | cp_rxpath | M1 | 计划 |
| TP-SUB-PCS-003 | UB-PHY §3.2.3.5 | 子系统环回无错 | D3 环回 | 端到端一致 | cp_fec_lb_clean | M1 | 计划 |
| TP-SUB-PCS-004 | UB-PHY §3.2.3.5 | 环回注入 ≤T 符号错，纠正后 DLL 无重传 | D3 PMA 模型改符号（无 FEC 钩子） | 数据对、无 Retry_Req | cx_fec_t | M1 | 计划 |
| TP-SUB-PCS-005 | UB-PHY §3.2.3.5 | >T 失败上交 DLL 重传 | D3 PMA 模型改符号 | fec_fail 与 retry 联动 | cp_fec_to_dll | M1 | 计划 |
| TP-SUB-PCS-006 | SPEC §3.3.4；UB-PHY §3.2.2.1、§3.4.1.1、§3.4.2.8 | 协商 FEC：通路只跟 `fec_mode_ctrl[2:0]`（无 `pcs_fec_mode`） | CLTB/RLTB 改 ctrl | 编解码与字段一致（合法取值见 PCS-039） | cp_fec_mode | M1 | RTL未就绪 |
| TP-SUB-PCS-007 | UB-PHY §3.2.4、§3.2.3.1 | AMCTL 周期插入、锁定、deskew | 环回加 lane 延迟 | 对齐后数据正确 | cx_amctl_skew | M1 | RTL未就绪 |
| TP-SUB-PCS-008 | UB-PHY §3.2.4.3 | AMCTL 不进 FEC、不扰码 | 观察边界 AMCTL | 与明文规则一致 | cp_amctl_raw | M1 | RTL未就绪 |
| TP-SUB-PCS-009 | UB-PHY §3.4.2.1–§3.4.2.2 | 端口类型与链路宽度协商 x1→x4 | LMB 交换 | 最终宽度 x4 | cp_width_neg | M1 | RTL未就绪 |
| TP-SUB-PCS-010 | UB-PHY §3.4.2.5 | 速率协商落到 Data Rate 0 | LMB 能力交 | 工作速率=§3 | cp_rate0 | M1 | 计划 |
| TP-SUB-PCS-011 | SPEC §6.1、§10.2；UB-PHY §3.4.3 | 训练到 Active 后 `link_ready`；Null/Active 才 `link_up` | 完整 LMSM + `LMSM_TMR_SCALE` | 与 §10.2 定义一致 | cp_linkup | M1 | RTL未就绪 |
| TP-SUB-PCS-012 | UB-PHY §3.1.1、§3.4.2.3 | TX/RX 宽度非对称、QDLWS | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-013 | UB-PHY §3.4.2.4 | 快速宽度降级 | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-014 | UB-PHY §3.4.2.6–§3.4.2.7 | 极性翻转 / lane reversal | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-015 | UB-PHY §3.2.6 | 数据通路低功耗 | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-016 | UB-PHY §3.1.2 | PHY Mode-1 | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-017 | SPEC §3.3.1、§13.2 | DLL↔PCS 是否需要 sop/eop | 跨 FEC 组帧 | 待定后补检查 | cp_d2p_sop | M1 | **待定**（§13） |
| TP-SUB-PCS-018 | SPEC §3.3.2、§13.2 | FEC bypass 时 `fec_ok` 含义 | 协商 bypass | 待定后补检查 | cp_fec_ok_byp | M1 | **待定**（§13） |
| TP-SUB-PCS-019 | SPEC §3.3.3；UB-DL §4.7.3.3 | `dll_retrain_req` → LMSM Retrain；`lmsm_retrain_ack` 为电平（禁止脉冲） | DLL 进 RETRAIN | `tb_obs_lmsm_st==7`；ack 保持为电平 | cp_retrain_hs | M1 | 计划 |
| TP-SUB-PCS-020 | SPEC §3.3.2、§5 | **无** `pcs2dll_ready`。PCS→DLL 只有 valid；DLL 每拍必收 | 连续 RX flit | 端口清单无该 ready；DLL 不丢拍 | cp_dll_norby | M1 | 计划 |

### 8.5 子系统级 — DLL

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-SUB-DLL-001 | UB-DL §4.3.2 | CRC 模式 DLLDP 端到端成帧/解帧 | 合法包长扫 | 网络口还原 | cp_dllp_crc | M1 | 计划 |
| TP-SUB-DLL-002 | UB-DL §4.3.3 | 强制 DLLCB：Null、NOP、Retry_*、Crd_Ack、Init、Lane_Manage | 各类型 | 解析与响应 | cx_dllcb_type | M1 | RTL未就绪 |
| TP-SUB-DLL-003 | UB-DL §4.4 | Param_Init 自动协商完成才进 Credit_Init | 对端 Init | SM + 参数镜像 | cp_param | M1 | RTL未就绪 |
| TP-SUB-DLL-004 | UB-DL §4.6.1 | Credit_Init 交换后才进 Normal | Crd_Ack | Status_Up | cp_crd_init | M1 | RTL未就绪 |
| TP-SUB-DLL-005 | UB-DL §4.6、§4.5 | 双 VL 调度：有 credit 才发；同 VL FCFS | 双 VL 竞争 | 不超发、顺序 | cx_vl_sched | M1 | RTL未就绪 |
| TP-SUB-DLL-006 | SPEC §10.2；UB-DL §4.6.2 | VL0：640 cell 打满回压 | 长burst；可选 `tb_inj_crd_cells`（仅 VL0） | `tb_obs_crd_*`（仅 VL0） | cp_crd_sat | M1 | 计划 |
| TP-SUB-DLL-007 | UB-DL §4.7 | BCRC 失败走 ACK/重传，最终有序交付 | D3 模型打坏一块（无 BCRC 钩子） | 黄金重传序列 | cp_retry | M1 | 计划 |
| TP-SUB-DLL-008 | UB-DL §4.7.3.5 | 重传过程与 retry buffer 释放 | 多包 + 错 | 缓冲不泄漏 | cp_retry_rel | M1 | RTL未就绪 |
| TP-SUB-DLL-009 | UB-DL §4.8.1 | credit 异常上报、不静默错账 | 非法返回 | 异常路径 | cp_ex_crd | M1 | RTL未就绪 |
| TP-SUB-DLL-010 | SPEC §6.3、§7、§8；UB-DL §4.8.2 | 重传异常 | RTT=2µs；实现相关超时见 SPEC §13.2；`LMSM_TMR_SCALE`/`CRD_TO_DIS` | 上报 / ERROR | cp_ex_retry | M1 | 计划 |
| TP-SUB-DLL-011 | UB-DL §4.8.3 | 错误 DLLDP 处理 | 坏 CFG/长度 | 丢弃规则 | cp_ex_dllp | M1 | RTL未就绪 |
| TP-SUB-DLL-012 | UB-DL §4.8.4、§4.2 | LinkUp=0 回 Disabled，上送 Status_Down | 拉倒 LinkUp | `tb_obs_link_up` / `tb_obs_dll_sm_st`，丢弃上下行、停 CB | cp_linkdn | M1 | RTL未就绪 |
| TP-SUB-DLL-013 | UB-DL §4.3.3.8、UB-PHY §3.4.2.8 | Block 模式/FEC-CRC 协同切换 | LMSM 指示 | 两端模式一致 | cp_modechg | 后续 | RTL未就绪 |
| TP-SUB-DLL-014 | UB-DL §4.3.4.1 | 定界：SOP/EOP 与 DLLDB 边界 | 交错 CB/DP | 无粘连 | cp_delim | M1 | 计划 |
| TP-SUB-DLL-015 | SPEC §6.3；UB-DL §4.7.1 | 重传触发：CRC 失败 / FEC 不可纠 | D3 模型注错 | 仅规定触发源 | cp_retry_trig | M1 | 计划 |
| TP-SUB-DLL-016 | SPEC §10.2、§4.6、§7 | **VL1** 信用耗尽 / 回压 / 超时：对端少还或延迟还，**不加钩子** | 对端 BFM 扣住 VL1 Crd_Ack | `nw_tx_ready` 对 VL1 停发；超时上报；钩子仍只反映 VL0 | cx_vl1_crd | M1 | 计划 |
| TP-SUB-DLL-017 | SPEC §7、§13.2 | RX 缓冲溢出：上报、等复位。激励靠**上层** `nw_rx_ready=0`，不是 PMA/PCS ready | 对端狂发、NW 不取 | 深度 **待定**。无 `pcs2dll_ready` 反压 TP | cp_rx_ovf | M1 | **待定**（§13） |
| TP-SUB-DLL-018 | SPEC §7；UB-DL §4.8.1 | Flow Control Overflow（信用超初值） | 对端多还 | 上报、停安全态 | cp_crd_of | M1 | 计划 |
| TP-SUB-DLL-019 | SPEC §7；UB-DL §4.8.1 | 信用归还超时 | 对端延迟还（VL0 或 VL1） | `CNT_CRD_TO`；`CRD_TO_DIS=1` 时不递增 | cp_crd_rto | M1 | 计划 |
| TP-SUB-DLL-020 | SPEC §7；UB-DL §4.8.2 | retry 指针 / NumFreeBuf 溢出 | 异常 ACK | 上报、等复位 | cp_retry_ovf | M1 | RTL未就绪 |
| TP-SUB-DLL-021 | SPEC §7；UB-DL §4.8.3 | `ERROR_FLAG`：当正常包上送，不单因该标志重传；TX 是否置位 **待定** | 对端带 FLAG 的 DLLDP | 上送上层；无重传 | cp_err_flag | M1 | **待定**（§13） |

### 8.6 顶层（含 D3 环回）

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-TOP-001 | UB-PHY §3.2、UB-DL §4.3 | TX↔RX 环回冒烟：短包 | 网络口发包 | 还原、无 UVM_ERROR | cp_smoke | M1 | 计划 |
| TP-TOP-002 | 同上 | 1 flit 与 512 flit 边界包 | 极端长度 | 完整还原 | cx_top_len | M1 | 计划 |
| TP-TOP-003 | UB-PHY §3.4、UB-DL §4.2 | 训练 + DLL 初始化到 Normal 后才跑数据 | LMSM+DLL 全序 | 训练期无业务包 | cp_bringup | M1 | RTL未就绪 |
| TP-TOP-004 | UB-DL §4.6、§4.7 | 环回上 credit + 重传同时在线 | 双 VL + 注错 | 有序、不超 credit | cx_top_qos | M1 | RTL未就绪 |
| TP-TOP-005 | SPEC §10、§11；D13 | 仅经 SPEC §10 钩子 / D3 边界注错，禁止 Force | HOOKS + `tb_test_mode=1`：三支 `tb_inj_*`（crd 仅 VL0）；FEC/BCRC 用模型 | 复位值不干预 | cp_hook_only | M1 | 计划 |
| TP-TOP-006 | UB-PHY §3.2.5 | x4、32 bit/lane 环回 | 四 lane | 分发/对齐 | cp_x4 | M1 | 计划 |
| TP-TOP-007 | UB-PHY §3.1.1 | 参数化 x8 | 编译参数 | 同分发规则 | cp_x8 | 后续 | 计划 |
| TP-TOP-008 | D6 | 顶层同步复位：释放后安静再训练 | 复位口 | 无 X 泄漏到检查窗 | cp_top_rst | M1 | 计划 |
| TP-TOP-009 | SPEC §1.2、§4.1 | 多时钟 / `pma_clk` | — | M1 非目标 | — | — | 推迟 |
| TP-TOP-010 | D8 | `randomize()` 流量，日志写 seed | 多种子 | scoreboard 0 mismatch | cp_rand | M1 | 计划 |
| TP-TOP-011 | UB-DL §4.3 | 网络口反压 | 拉低 ready | 无丢、无重 | cp_bp | M1 | 计划 |
| TP-TOP-012 | D7 | 同一 TC 在 Icarus 与 Verilator 结果一致 | 双仿 | 比对 PASS 行 | cp_dualsim | M1 | 计划 |
| TP-TOP-013 | D3 | 环回 BFM 可配 deskew，超过规范窗则失败 | 扫延迟 | 窗内过、窗外失败 | cp_skew_win | M1 | RTL未就绪 |
| TP-TOP-014 | D11 | FPGA 板级 | — | — | — | — | 一期不做 D11 |
| TP-TOP-015 | SPEC §11 (c)；REGMAP §2.4 | PRODUCT（`TEST_HOOKS=0`）无钩子冒烟；**含 TEST 窗**：读 0、写忽略、`csr_err=0`（与 CSR-019 同子集） | 无 `tb_*` 端口；读写 `0x0300–0x03FF` | 短包环回 PASS；TEST 窗无副作用 | cp_prod_smoke | M1 | 计划 |
| TP-TOP-016 | SPEC §11 (b) | HOOKS 且 `tb_test_mode=0` | `tb_inj_*` 接复位值；观察保持 0 | 与产品行为一致 | cp_hook1_mode0 | M1 | 计划 |
| TP-TOP-017 | SPEC §11 (b) | HOOKS 且 `tb_test_mode=1` | SPEC §10 钩子 + TEST 寄存器 | 行覆盖含钩子 mux，不另开 waiver | cp_hook1_mode1 | M1 | 计划 |
| TP-TOP-018 | SPEC §11 (d) | Yosys eqy：PRODUCT ≡ HOOKS | `tb_test_mode=0` 且全部 `tb_inj_*` 接复位值 | 不等价则**不算交付** | cp_eqy | M1 | 计划 |
| TP-TOP-019 | SPEC §3.2.1、§4.1 | 顶层无 `pma_clk`/`pma_rst_n`；仿真 12.41 ns | 端口枚举 | 单时钟闭环 | cp_no_pma_clk | M1 | 计划 |
| TP-TOP-020 | SPEC §5、§8、§13.2 | 各通路周期延迟（NW↔PMA、FEC、重传首 flit、信用归还） | 实现后回填 | 拍数记报告 | cp_path_lat | M1 | **待定**（§13） |
| TP-TOP-021 | SPEC §11 (a)；CODING_STYLE §7 | PRODUCT 与 HOOKS 两套网表 `verilator --lint-only` 均为 0 error | 对两份生成物跑 lint | 无未记账 warning | cp_lint_dual | M1 | 计划 |

### 8.7 推迟占位（D2）

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-DEF-NW-001 | UB-NW §5.2 | NTH 解析 / 改写 | — | — | — | — | 推迟 |
| TP-DEF-NW-002 | UB-NW §5.3 | 路由、隔离、QoS、拥塞标记、ICRC | — | — | — | — | 推迟 |
| TP-DEF-TP-001 | UB-TP §6.2–§6.4 | RTP/CTP/UTP 与传输重传 | — | — | — | — | 推迟 |
| TP-DEF-TP-002 | UB-TP §6.5–§6.6 | 多路径与拥塞控制 | — | — | — | — | 推迟 |
| TP-DEF-TA-001 | UB-TA §7.2–§7.4 | 事务头与事务类型 | — | — | — | — | 推迟 |
| TP-DEF-UP-001 | 第 8–11 章 | FUN/MEM/RSC/SEC | — | — | — | — | 推迟 |
| TP-DEF-HOOK-001 | SPEC §10.2；D2 | `tb_obs_nw_dll_data` | — | — | — | — | 推迟 |

### 8.8 内存管理（轨道 C）

本小节为轨道 C 专属，只在此处增删内存管理测试点。列定义沿用上文 §8，不改公共表头。依据 `docs/arch/mem/UARCH.md`（叶子划分 §3、接口 §4、具名信号契约 §5、流水线与旁路 §6、失效 §7、错误与事件 §8、必选/可选 §9、大表项表 §10、待决 §11–§12）。设计与验证独立，只共享 SPEC、接口契约与断言；查表 / 译码的标准答案为 Xia 在 `model/` 的 Python 参考模型（UMMU 查表 / 译码参考模型尚未提交，检查列写「`model/` 参考模型（待 Xia）」）。

结构叶子的 TB 直接驱动 UARCH §5 的具名信号，不依赖字段布局。字段解码相关测试点只写到解码叶子名和 UARCH §5 具名信号。必选特性里程碑 = **M1**；UARCH §9 列为可选 / 延后的标 **后续**。RTL 尚未交付，故多数状态 = **RTL未就绪**；依赖待决项的标 **待定**，见 §8.8.5。本小节自带计数、待定清单与第 9 章反向追溯；公共 §8.7 / §13 / §14 / §15 由另 PR 并入。

#### 8.8.1 单元级 — 内存管理 UMMU

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-UNIT-MEM-001 | §11.6.4；UARCH §4 | `EE_bits` 非 0 直接失败（首轮无 TEE） | 查询口打非 0 `EE_bits` | 失败原因=配置类失败；`model/` 参考模型（待 Xia） | cp_mem_ee | M1 | RTL未就绪 |
| TP-UNIT-MEM-002 | §9.4；UARCH §6.1 | UBA 超出上下文有效位数 | 构造越界 UBA | 失败原因=UBA 越界；`model/` 参考模型（待 Xia） | cp_mem_uba_oob | M1 | RTL未就绪 |
| TP-UNIT-MEM-003 | UARCH §6.1 | 下标计算：TECT / TCT 缓存 / TLB 组按 UARCH 下标混合算法 | 扫 ENT_IDX、TokenID、页号组合 | 三处下标与模型一致；同拍发读 | cp_mem_idx | M1 | RTL未就绪 |
| TP-UNIT-MEM-004 | §9.4.2.1；UARCH §5.1 | `cfg_v`=0 | 驱动 `cfg_v=0` | 回失败；`model/` 参考模型（待 Xia） | cp_mem_cfg_v | M1 | RTL未就绪 |
| TP-UNIT-MEM-005 | §9.4.2.1；UARCH §5.1、§8 | `cfg_abort`：回失败、不记事件 | 驱动 `cfg_abort=1` | 失败；事件口无新记录 | cp_mem_cfg_abort | M1 | RTL未就绪 |
| TP-UNIT-MEM-006 | §9.4.2.1；UARCH §5.1、§8 | `cfg_illegal`：回错误并记事件（含合法但不支持的编码） | 驱动 `cfg_illegal` / `cfg_ill_cause` | 失败+事件；`model/` 参考模型（待 Xia） | cp_mem_cfg_ill | M1 | RTL未就绪 |
| TP-UNIT-MEM-007 | §9.4.2.1；UARCH §5.1 | 安全 / 特权 / 指令 / 内存属性覆盖 | 分别打 `cfg_*_ovr_*`、`cfg_mem_attr*` | 输出属性跟覆盖信号；`model/` 参考模型（待 Xia） | cx_mem_cfg_ovr | M1 | RTL未就绪 |
| TP-UNIT-MEM-008 | UARCH §4、§10 | CSR 读回与查找共用读口，查找优先 | 同拍 CSR 读与查询 | 查询得数据；CSR 读推迟或后一拍 | cp_mem_cfg_pri | M1 | RTL未就绪 |
| TP-UNIT-MEM-009 | §9.4.2.2；UARCH §6.1 | TCT 缓存命中 | 预装后查同一 {ENT_IDX, TokenID} | 命中；上下文束=`model/` 参考模型（待 Xia） | cp_mem_tct_hit | M1 | RTL未就绪 |
| TP-UNIT-MEM-010 | §9.4.2.2；UARCH §6.2 | TCT 缓存缺失 | 冷缓存查询 | 经 `ub_mem_tbl_rd` 填充后重放命中 | cp_mem_tct_miss | M1 | RTL未就绪 |
| TP-UNIT-MEM-011 | §9.4.2.2；UARCH §9 | 线性 TCT | `cfg_tct_2lvl=0`，缺失读 64 B | 填充项与模型一致 | cp_mem_tct_lin | M1 | RTL未就绪 |
| TP-UNIT-MEM-012 | §9.4.2.2；UARCH §9 | 两级 TCT | `cfg_tct_2lvl=1`，多一次 8 B | L1 描述符 + L2 项与模型一致 | cp_mem_tct_2lvl | M1 | RTL未就绪 |
| TP-UNIT-MEM-013 | §9.4.2.2.2；UARCH §5.2 | `ctx_illegal` | 驱动 `ctx_illegal` / `ctx_ill_cause` | 回错误并记事件；`model/` 参考模型（待 Xia） | cp_mem_ctx_ill | M1 | RTL未就绪 |
| TP-UNIT-MEM-014 | §9.4.2.2；UARCH §8 | TokenID 越界 | TokenID 超出 `cfg_tct_num` 范围 | 失败原因=TokenID 越界 | cp_mem_tid_oob | M1 | RTL未就绪 |
| TP-UNIT-MEM-015 | §9.4.4；UARCH §5.2、§6.1 | 上下文排他位 | 驱动 `ctx_e_bit` 与请求 `E_bit` 组合 | 拒绝/通过与模型一致 | cp_mem_ctx_excl | M1 | RTL未就绪 |
| TP-UNIT-MEM-016 | §9.4；UARCH §5.2、§6.2 | `ctx_matt_wd`：TLB 缺失不遍历，直接记事件 | `ctx_matt_wd=1` 且 TLB 缺失 | 无页表读；记事件；`model/` 参考模型（待 Xia） | cp_mem_matt_wd | M1 | RTL未就绪 |
| TP-UNIT-MEM-017 | §9.4.3；UARCH §4 | TLB 路 0 命中（one-hot 定向，锁定方向） | 只预装路 0 | 命中路 one-hot=路 0；翻译束=`model/` 参考模型（待 Xia） | cp_mem_tlb_w0 | M1 | RTL未就绪 |
| TP-UNIT-MEM-018 | §9.4.3；UARCH §4 | TLB 路 1 命中（one-hot 定向，锁定方向） | 只预装路 1 | 命中路=路 1；同上 | cp_mem_tlb_w1 | M1 | RTL未就绪 |
| TP-UNIT-MEM-019 | §9.4.3；UARCH §4 | TLB 路 2 命中（one-hot 定向，锁定方向） | 只预装路 2 | 命中路=路 2；同上 | cp_mem_tlb_w2 | M1 | RTL未就绪 |
| TP-UNIT-MEM-020 | §9.4.3；UARCH §4 | TLB 路 3 命中（one-hot 定向，锁定方向） | 只预装路 3 | 命中路=路 3；同上 | cp_mem_tlb_w3 | M1 | RTL未就绪 |
| TP-UNIT-MEM-021 | UARCH §6.1 | TLB 组冲突 | 同组不同标签连续填充 | 各标签独立命中/替换；`model/` 参考模型（待 Xia） | cp_mem_tlb_conf | M1 | RTL未就绪 |
| TP-UNIT-MEM-022 | UARCH §4、§6.1 | 伪 LRU 替换（白盒，按 UARCH 下标混合算法） | 同组填满后再填新项 | 替换路=模型给出的伪 LRU | cp_mem_tlb_plru | M1 | RTL未就绪 |
| TP-UNIT-MEM-023 | §9.4.3；UARCH §4、§6.2 | 块描述符拆成 4 KB 项填充 | 遍历遇到块描述符 | TLB 填 4 KB 项；`model/` 参考模型（待 Xia） | cp_mem_blk_split | M1 | RTL未就绪 |
| TP-UNIT-MEM-024 | UARCH §6.1 | 查表侧与参考模型逐位比对（自环只当补充） | 命中查询 | 查表输出逐位=`model/` 参考模型（待 Xia）。`docs/rules/verif_gate.md` 若落地则从其口径 | cp_mem_lkup_bits | M1 | RTL未就绪 |
| TP-UNIT-MEM-025 | UARCH §6.2 | 回填侧与参考模型逐位比对（自环只当补充） | 缺失后填充 | 填充写入逐位=`model/` 参考模型（待 Xia）。与 MEM-024 分开计 | cp_mem_fill_bits | M1 | RTL未就绪 |
| TP-UNIT-MEM-026 | §9.4.3；UARCH §4 | 页表遍历起始级由输入宽度推出 | 扫合法输入宽度 | 起始级=`model/` 参考模型（待 Xia） | cp_mem_ptw_slvl | M1 | RTL未就绪 |
| TP-UNIT-MEM-027 | §9.4.3；UARCH §4 | 页表遍历最多 4 级 | 需满 4 级才出页的表 | 恰好 4 次表读；不再多读 | cp_mem_ptw_4 | M1 | RTL未就绪 |
| TP-UNIT-MEM-028 | §9.4.3；UARCH §8 | 各类翻译故障 | 无效 / 保留 / 错误描述符 | 失败原因=翻译遍历故障；`model/` 参考模型（待 Xia） | cp_mem_ptw_flt | M1 | RTL未就绪 |
| TP-UNIT-MEM-029 | §9.4.3；UARCH §8 | AF 故障 | 描述符 `desc_af` 未置且须报 | 失败原因=AF 故障 | cp_mem_af | M1 | RTL未就绪 |
| TP-UNIT-MEM-030 | §9.4；UARCH §5.2、§8 | 记录位控制翻译故障 / AF 是否记事件 | 扫 `ctx_fbr` / `ctx_affd` | 记或不记与模型一致；其余须记情形始终记 | cx_mem_rec | M1 | RTL未就绪 |
| TP-UNIT-MEM-031 | §9.4.4.2；UARCH §5.4 | PLB/MAPT 闭区间范围边界：`mapte_base`、`mapte_limit`、base-1、limit+1 | 四点定向 UBA | 闭区间内命中、外失败；`model/` 参考模型（待 Xia） | cx_mem_rng | M1 | RTL未就绪 |
| TP-UNIT-MEM-032 | §9.4.4.2；UARCH §9 | 单项 MAPT | `ctx_mapt_multi=0`，1 次 32 B | 权限束=`model/` 参考模型（待 Xia） | cp_mem_mapt_s | M1 | RTL未就绪 |
| TP-UNIT-MEM-033 | §9.4.4.2；UARCH §9 | 多级 MAPT（4 KB、只用基块） | `ctx_mapt_multi=1`，最多 4 次 32 B | 逐级比范围、看终止位；与模型一致 | cp_mem_mapt_m | M1 | RTL未就绪 |
| TP-UNIT-MEM-034 | §9.4.4.2；UARCH §5.4 | `mapte_last` | 驱动最后一级 / 非最后一级 | 终止或继续与模型一致 | cp_mem_mapte_last | M1 | RTL未就绪 |
| TP-UNIT-MEM-035 | §9.4.4.2；UARCH §5.4 | `mapte_next_other_blk`：首轮视为非法 | 驱动该信号=1 | 回非法 / 失败；不跟到其他块 | cp_mem_mapte_oblk | M1 | RTL未就绪 |
| TP-UNIT-MEM-036 | §9.4.4.3.2；UARCH §5.4 | TokenValue 两值匹配 | 请求值等于 `mapte_tv0` 或 `mapte_tv1` | 比较通过 | cp_mem_tv_hit | M1 | RTL未就绪 |
| TP-UNIT-MEM-037 | §9.4.4.3.2；UARCH §5.4 | TokenValue 两值都不匹配 | 请求值不等于两值 | 失败原因=TokenValue 失败 | cp_mem_tv_miss | M1 | RTL未就绪 |
| TP-UNIT-MEM-038 | §9.4.4.3.2；UARCH §7 | TokenValue 变化后作废 PLB 项并重走 MAPT | PLB 命中但 TokenValue 不符 | 作废该项、重走再比；`model/` 参考模型（待 Xia） | cp_mem_tv_rewalk | M1 | RTL未就绪 |
| TP-UNIT-MEM-039 | §9.4.4.3；UARCH §5.4 | MAPT 排他位 | 驱动 `mapte_e_bit` 与请求 `E_bit` | 拒绝/通过与模型一致 | cp_mem_mapt_excl | M1 | RTL未就绪 |
| TP-UNIT-MEM-040 | §9.4.4.3；UARCH §5.4 | 访问类型读 | 读请求 vs `mapte_perm_r` | 无读许可则访问类型拒绝 | cp_mem_acc_r | M1 | RTL未就绪 |
| TP-UNIT-MEM-041 | §9.4.4.3；UARCH §5.4 | 访问类型写 | 写请求 vs `mapte_perm_w` | 无写许可则访问类型拒绝 | cp_mem_acc_w | M1 | RTL未就绪 |
| TP-UNIT-MEM-042 | §9.4.4.3；UARCH §5.4 | 访问类型原子（须写权限） | 原子请求 vs `mapte_perm_w` / `mapte_perm_a` | 无写许可则拒绝；`model/` 参考模型（待 Xia） | cp_mem_acc_a | M1 | RTL未就绪 |
| TP-UNIT-MEM-043 | §9.4.4.3.5；UARCH §6.1 | `ub_mem_perm_cmp` 按 §9.4.4.3.5 失败类别优先级 | 同拍构造多种权限失败 | 报出类别=`model/` 参考模型（待 Xia） | cx_mem_perm_pri | M1 | RTL未就绪 |
| TP-UNIT-MEM-044 | UARCH §4 | 表读口 `ub_mem_tbl_rd` 固定优先级 TCT > 页表 > MAPT | 三源同时请求 | 只放行 TCT，其余等待 | cp_mem_rd_pri | M1 | RTL未就绪 |
| TP-UNIT-MEM-045 | UARCH §4、§6.2 | 表读口只有一个未决 | 连续打缺失 | 至多一个 `mem2host_rd` 未决 | cp_mem_rd_one | M1 | RTL未就绪 |
| TP-UNIT-MEM-046 | UARCH §4、§8 | 表读错误映射成「表读错误」 | 响应带错误 | 失败原因=表读错误 | cp_mem_rd_err | M1 | RTL未就绪 |
| TP-UNIT-MEM-047 | UARCH §6.1 | 命中路径 3 拍（P0–P2） | 全缓存命中查询 | 握手到结果=3 拍 | cp_mem_hit3 | M1 | RTL未就绪 |
| TP-UNIT-MEM-048 | UARCH §4 | 每拍接收 1 个查询 | 连续 valid | 每拍收 1；无丢拍 | cp_mem_1qpc | M1 | RTL未就绪 |
| TP-UNIT-MEM-049 | UARCH §4 | 按序返回（`tag` 对齐） | 连续命中、不同 tag | 返回序=接收序 | cp_mem_ord | M1 | RTL未就绪 |
| TP-UNIT-MEM-050 | UARCH §6.2 | 缺失阻塞：后续请求 P0 的 ready=0 | 制造一个缺失后再打查询 | 缺失期间 ready=0 | cp_mem_blk | M1 | RTL未就绪 |
| TP-UNIT-MEM-051 | UARCH §6.2 | 填充后从 P0 重放；结果只经命中路径产生 | 缺失→填充 | 重放走 P0–P2；无第二条结果通路 | cp_mem_replay | M1 | RTL未就绪 |
| TP-UNIT-MEM-052 | UARCH §6.3 | 写后读旁路：填充与另一请求查找同拍、同址 | 定向：同拍 `we && re && waddr==raddr` | P1 用旁路数据，不得读到旧值；`model/` 参考模型（待 Xia） | cp_mem_bypass | M1 | RTL未就绪 |
| TP-UNIT-MEM-053 | §11.4.4；UARCH §7 | 全部失效：一拍清各缓存 valid | 发全部失效 | 下一拍查找全缺失 | cp_mem_inv_all | M1 | RTL未就绪 |
| TP-UNIT-MEM-054 | §11.4.4；UARCH §7 | 按 ENT_IDX / TokenID 扫描失效：TLB 64 拍 | 发按条件失效 | TLB 扫描 64 拍后目标项无效 | cp_mem_inv_tlb | M1 | RTL未就绪 |
| TP-UNIT-MEM-055 | §11.4.4；UARCH §7 | 按 ENT_IDX / TokenID 扫描失效：TCT 缓存 64 拍 | 同上 | TCT 缓存 64 拍后目标项无效 | cp_mem_inv_tct | M1 | RTL未就绪 |
| TP-UNIT-MEM-056 | §11.4.4；UARCH §7 | 按 ENT_IDX / TokenID 扫描失效：PLB 1 拍 | 同上 | PLB 1 拍清目标项 | cp_mem_inv_plb | M1 | RTL未就绪 |
| TP-UNIT-MEM-057 | UARCH §7 | 扫描失效期间查找口 ready=0 | 扫描中打查询 | ready=0，不接受新查 | cp_mem_inv_nrdy | M1 | RTL未就绪 |
| TP-UNIT-MEM-058 | UARCH §7 | 扫描后结果正确 | 扫描完成再查 | 已失效项缺失；未命中条件的项仍命中 | cp_mem_inv_post | M1 | RTL未就绪 |
| TP-UNIT-MEM-059 | UARCH §7 | SYNC：此前命令生效、无未决缺失，写完成事件 | 失效后发 SYNC | 完成事件；之后查找见新状态 | cp_mem_sync | M1 | RTL未就绪 |
| TP-UNIT-MEM-060 | UARCH §7 | CSR 改 TECT 不自动失效下游缓存 | 只写 TECT、不发失效 | TCT/TLB/PLB 仍命中旧项 | cp_mem_tect_noinv | M1 | RTL未就绪 |
| TP-UNIT-MEM-061 | UARCH §8 | 4 bit 失败原因枚举每一类至少一次 | 定向构造各类失败 | 覆盖：配置无效、配置终止、配置非法、TokenID 越界、上下文无效、上下文排他拒绝、UBA 越界、翻译遍历故障、AF 故障、页权限拒绝、MAPT 表项无效、MAPT 范围失败、TokenValue 失败、MAPT 排他拒绝、访问类型拒绝、表读错误 | cx_mem_cause | M1 | RTL未就绪 |
| TP-UNIT-MEM-062 | UARCH §8 | 除「配置终止」外都记事件 | 各类失败各一次 | 仅 `cfg_abort` 无事件；其余有 | cx_mem_evt | M1 | RTL未就绪 |
| TP-UNIT-MEM-063 | UARCH §8、§11 D-04 | 一次查询多种失败时报错优先级（流水级，非 §9.4.4.3.5） | 同拍打配置+上下文+越界等 | 报哪一类 **待定** | cp_mem_pri_d04 | M1 | **待定** |
| TP-UNIT-MEM-064 | UARCH §8、§11 D-12 | 事件队列溢出（满则置溢出、丢后续） | 灌满事件 FIFO 后再失败 | 溢出标志；格式等 Q-E09 | cp_mem_evt_ovf | M1 | **待定** |
| TP-UNIT-MEM-065 | UARCH §10；CODING_STYLE §10 | 每个 `ub_cmn_mem_1r1w` 实例（含译码器表）：有效位在原语外的复位触发器 | 复位；读各表 | valid 随 `rst_pyc` 清；阵列本体无复位 | cp_mem_vld_ff | M1 | RTL未就绪 |
| TP-UNIT-MEM-066 | UARCH §10 | TB 断言：有效位为 0 的表项读出数据不流到下游 | 预装无效项后查找 | 断言永不触发；不得当命中用 | cp_mem_vld_gate | M1 | RTL未就绪 |
| TP-UNIT-MEM-067 | UARCH §10 | 回归用 `+verilator+rand+reset+2` 随机化阵列初值 | Verilator 该 plusarg | 仍只认 valid=1 的项；MEM-066 断言成立 | cp_mem_rand_rst | M1 | RTL未就绪 |
| TP-UNIT-MEM-068 | UARCH §10 | 原语 `ASSERT_NO_UNINIT_READ=0`，由 MEM-066 断言接替 | 静态/仿真对照 | 原语侧该断言关闭；TB 断言在岗 | cp_mem_no_uninit | M1 | RTL未就绪 |
| TP-UNIT-MEM-069 | SPEC §10；UARCH §10 | `tb_<inst>_bd_*` 预装/读出与 `tb_<inst>_bd_vld_*` 同拍写 valid | HOOKS 后门预装后再查 | 读出与预装一致；命中行为正确 | cp_mem_bd | M1 | RTL未就绪 |
| TP-UNIT-MEM-070 | SPEC §10；UARCH §10 | 后门口由 `tb_test_mode` 门控 | mode=0 打后门；再 mode=1 | mode=0 不介入；mode=1 生效 | cp_mem_bd_mode | M1 | RTL未就绪 |
| TP-UNIT-MEM-071 | SPEC §10、§11；UARCH §10 | 后门只在 HOOKS 网表；PRODUCT 无这些端口 | 枚举两套网表端口 | PRODUCT 无 `tb_*_bd_*`；HOOKS 有 | cp_mem_bd_prod | M1 | RTL未就绪 |
| TP-UNIT-MEM-072 | §9.4.2.1；UARCH §5.1 | `ub_mem_tecte_dec`：解码输出与参考模型一致 | 喂原始 TECT 镜像 | §5.1 信号束=`model/` 参考模型（待 Xia）。字段布局能否进公开仓库待船长（S-01） | cp_mem_tecte_dec | M1 | **待定** |
| TP-UNIT-MEM-073 | §9.4.2.1；UARCH §5.1 | `ub_mem_tecte_dec`：非法编码折成 `cfg_illegal` / `cfg_ill_cause` | 保留 / 不支持编码 | 只看这两根信号。原因：S-01 | cp_mem_tecte_ill | M1 | **待定** |
| TP-UNIT-MEM-074 | §9.4.2.2.2；UARCH §5.2 | `ub_mem_tcte_dec`：解码输出与参考模型一致 | 喂原始 TCTE | §5.2 信号束=`model/` 参考模型（待 Xia）。原因：S-01 | cp_mem_tcte_dec | M1 | **待定** |
| TP-UNIT-MEM-075 | §9.4.2.2.2；UARCH §5.2 | `ub_mem_tcte_dec`：非法编码折成 `ctx_illegal` / `ctx_ill_cause` | 首轮不支持编码 | 只看这两根信号。原因：S-01 | cp_mem_tcte_ill | M1 | **待定** |
| TP-UNIT-MEM-076 | §9.4.2.2.3；UARCH §5.3 | `ub_mem_l1tct_dec`：解码输出与参考模型一致；非法折成 `l1tct_illegal` | 喂 L1 TCT 描述符 | §5.3 信号=`model/` 参考模型（待 Xia）。原因：S-01 | cp_mem_l1tct_dec | M1 | **待定** |
| TP-UNIT-MEM-077 | §9.4.4.2；UARCH §5.4 | `ub_mem_mapte_dec`：解码输出与参考模型一致 | 喂单项/多级 MAPTE | §5.4 信号束=`model/` 参考模型（待 Xia）。原因：S-01 | cp_mem_mapte_dec | M1 | **待定** |
| TP-UNIT-MEM-078 | §9.4.4.2；UARCH §5.4 | `ub_mem_mapte_dec`：非法编码折成对应 `*_illegal` | 非法 / 越界指针 | 结构叶子只看非法信号。原因：S-01 | cp_mem_mapte_ill | M1 | **待定** |
| TP-UNIT-MEM-079 | §9.4.3；UARCH §5.6 | `ub_mem_ptw_desc_dec`：解码输出与参考模型一致 | 喂页表描述符 | §5.6 信号束=`model/` 参考模型（待 Xia）。原因：S-01 | cp_mem_desc_dec | M1 | **待定** |
| TP-UNIT-MEM-080 | §9.4；UARCH §9 | 事件合并：接受 `cfg_em_en`，首轮不合并 | 连续同类失败、`cfg_em_en=1` | 仍逐条记；不合并 | cp_mem_em_nomrg | M1 | RTL未就绪 |
| TP-UNIT-MEM-081 | UARCH §9 | 流量监测标识只透传 | 预装 `cfg_mtm_*` / `ctx_mtm_*` | 边带原样出；不计数 | cp_mem_mtm | M1 | RTL未就绪 |
| TP-UNIT-MEM-082 | §9.4.4.2；UARCH §9 | 多级 MAPT 2 MB | — | 延后，需船长明确接受（Q-A17） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-083 | §9.4.3；UARCH §9 | 硬件更新访问 / 脏标志 | — | 延后，需船长明确接受（Q-A18） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-084 | §9.4.4.2；UARCH §9 | 多块 MAPT | — | 延后（Q-A16） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-085 | §9.4.3；UARCH §9 | Stage 2 / 安全态 Stage 2 | — | 延后（Q-A03） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-086 | UARCH §9 | Stall | — | 延后（Q-A19） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-087 | UARCH §9 | 事件真正合并 | — | 首轮只接受配置；真正合并后续（Q-A20） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-088 | §11.6.4；UARCH §9 | TEE（`EE_bits` 选表） | — | 延后；非 0 已由 MEM-001 回错（Q-E03） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-089 | UARCH §9 | Positive PLB 免失效优化 | — | 首轮只做小 PLB，不做该优化（Q-C04） | — | 后续 | RTL未就绪 |
| TP-UNIT-MEM-090 | §9.4.4.1；UARCH §9 | 委托非特权软件管 MAPT | — | 延后（Q-E12） | — | 后续 | RTL未就绪 |

#### 8.8.2 单元级 — 内存管理译码器

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-UNIT-DEC-001 | App. D.4.1.5；UARCH §6.4 | D0：主机 PA 减 MMIO 基址；与窗口比越界 | 窗内 / 窗外 PA | 窗外失败；窗内进入后续拍；`model/` 参考模型（待 Xia） | cp_dec_win | M1 | RTL未就绪 |
| TP-UNIT-DEC-002 | §9.5；UARCH §6.4 | 译码翻译缓存命中（1 MB 粒度，标签 `PA[43:20]`） | 预装后查同 1 MB 块 | 命中取结果束；`model/` 参考模型（待 Xia） | cp_dec_tlb_hit | M1 | RTL未就绪 |
| TP-UNIT-DEC-003 | §9.5.1；UARCH §5.5、§6.4 | L0 PTE 由 `PA[34:32]` 选 | 同一 64 B 大项、扫该切片 | 选中项=`dent_pte_v` 路径；`model/` 参考模型（待 Xia） | cp_dec_l0_sel | M1 | RTL未就绪 |
| TP-UNIT-DEC-004 | §9.5.1；UARCH §5.5、§6.4 | PTRE 范围与 `PA[34:20]` 比较的边界 | 打 range 边界 PA | 闭区间内命中、外转 L1 或失败 | cx_dec_ptr_rng | M1 | RTL未就绪 |
| TP-UNIT-DEC-005 | §9.5.1；UARCH §5.5 | PTRE 最后一级 → 得结果束 | 驱动 `dent_rng_last=1` 且范围命中 | 出结果、不走 L1。格式 / 该位待船长（D-05） | cp_dec_ptr_last | M1 | **待定** |
| TP-UNIT-DEC-006 | §9.5.1；UARCH §5.5 | PTRE 非最后一级 → 转 L1（完整方案）或回错误（最小表） | 驱动 `dent_rng_last=0` | 转 L1 或失败。待船长（D-05） | cp_dec_ptr_nlast | M1 | **待定** |
| TP-UNIT-DEC-007 | §9.5；UARCH §6.4 | L1 查找下标 `PA[31:20]`（页表项情形） | L0 为页表项、需 L1 | 下标与模型一致；读回经解码叶子 | cp_dec_l1_p31 | M1 | RTL未就绪 |
| TP-UNIT-DEC-008 | §9.5；UARCH §6.4 | L1 查找下标 `PA[34:20]`（范围未命中或非最后一级） | L0 为范围项且需 L1 | 下标与模型一致 | cp_dec_l1_p34 | M1 | RTL未就绪 |
| TP-UNIT-DEC-009 | §9.5.2；UARCH §4 | UBA 64 bit 加法，进位丢弃 | 扫基值与 PA 低位、含进位 | UBA=`model/` 参考模型（待 Xia）；进位不出现在结果 | cp_dec_uba_add | M1 | RTL未就绪 |
| TP-UNIT-DEC-010 | UARCH §6.4 | 命中路径 4 拍（D0–D3） | 翻译缓存或 L0 直接得结果 | 握手到结果=4 拍 | cp_dec_hit4 | M1 | RTL未就绪 |
| TP-UNIT-DEC-011 | App. D.4.1.7；UARCH §7 | 译码器全部失效 | 发全部失效 | 翻译缓存 valid 一拍清。Xia 提案，待船长（Q-B08） | cp_dec_inv_all | M1 | **待定** |
| TP-UNIT-DEC-012 | App. D.4.1.7；UARCH §7 | 按 PA 范围失效，扫描翻译缓存 32 拍 | 发范围失效 | 32 拍后范围内无效、范围外仍在。待船长（Q-B08） | cp_dec_inv_rng | M1 | **待定** |
| TP-UNIT-DEC-013 | App. D.4.1.7；UARCH §7 | 译码器 SYNC | 失效后发 SYNC | 完成事件；之后查找见新状态。待船长（Q-B08） | cp_dec_sync | M1 | **待定** |
| TP-UNIT-DEC-014 | UARCH §10 | L0 若选合成一块分段写：有效位按段（每行 8 位），与模型按段 `rdata_valid` 对应 | 分段写后读 | 各段 valid 与 `rdata_valid` 一一对应。依赖 D-14 | cp_dec_l0_seg | M1 | **待定** |
| TP-UNIT-DEC-015 | §9.5；UARCH §6.4、§11 D-14 | L0 表放片上：下标 `PA[43:35]`，8 块并读或整行读 | 片上方案编译 / 参数 | D1 同时读翻译缓存与 L0。L0 放置待船长（D-14 / C-D1） | cp_dec_l0_onchip | M1 | **待定** |
| TP-UNIT-DEC-016 | §9.5；UARCH §6.4、§11 D-14 | L0 表放内存：命中只读翻译缓存，缺失走 `ub_mem_dec_walk` | 内存方案 | 命中路径仍 4 拍；缺失先读 L0 再读 L1。待船长（D-14 / C-D1） | cp_dec_l0_mem | M1 | **待定** |
| TP-UNIT-DEC-017 | §9.5.1；UARCH §5.5 | `ub_mem_dec_ent_dec`：解码输出与参考模型一致 | 喂 L0/L1 原始数据 | §5.5 信号束=`model/` 参考模型（待 Xia）。原因：S-01 | cp_dec_ent_dec | M1 | **待定** |
| TP-UNIT-DEC-018 | §9.5.1；UARCH §5.5 | `ub_mem_dec_ent_dec`：非法编码折成对应 `*_illegal` / `*_ill_cause` | 非法大项 | 结构逻辑只看非法信号。原因：S-01 | cp_dec_ent_ill | M1 | **待定** |
| TP-UNIT-DEC-019 | §9.5.1；UARCH §5.5 | L0 PTE / L0 PTRE / L1 PTE 格式 | — | 格式待船长（D-05）。本 TP 占位，格式冻结后补激励 | — | M1 | **待定** |

#### 8.8.3 子系统级 — 内存管理

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-SUB-MEM-001 | §9.4；UARCH §6.1 | UMMU 命中路径端到端：请求检查→配置→上下文→TLB→权限，3 拍出结果 | 全缓存预装后查询 | PA / 属性 / 成功=`model/` 参考模型（待 Xia） | cp_sub_mem_hit | M1 | RTL未就绪 |
| TP-SUB-MEM-002 | §9.4.2.2；UARCH §6.2 | TCT 缺失→填充→从 P0 重放→命中路径出结果 | 冷 TCT | 只经命中路径出结果；表读优先级见 MEM-044 | cp_sub_mem_tct | M1 | RTL未就绪 |
| TP-SUB-MEM-003 | §9.4.3；UARCH §6.2 | TLB 缺失→页表遍历→填充→重放 | 冷 TLB、允许遍历 | 填充后命中；查表侧 / 回填侧分别对模型（MEM-024/025） | cp_sub_mem_ptw | M1 | RTL未就绪 |
| TP-SUB-MEM-004 | §9.4.4；UARCH §6.2 | PLB 缺失→MAPT 遍历→填 PLB→重放 | 冷 PLB、须权限检查 | 权限结果=`model/` 参考模型（待 Xia） | cp_sub_mem_mapt | M1 | RTL未就绪 |
| TP-SUB-MEM-005 | UARCH §4 | 表读口争用：TCT / 页表 / MAPT，固定优先级且单未决 | 交错制造三类缺失 | 服务序 TCT > 页表 > MAPT；同时最多一个未决 | cp_sub_mem_arb | M1 | RTL未就绪 |
| TP-SUB-MEM-006 | UARCH §7 | 全部失效后再查：应缺失并正确重填 | 命中后全部失效再查 | 先缺失，重填后与模型一致 | cp_sub_mem_inva | M1 | RTL未就绪 |
| TP-SUB-MEM-007 | UARCH §7 | 扫描失效期间 ready=0，扫描后结果正确 | 按 ENT_IDX / TokenID 扫描中打查询 | 扫描中不收新查；完成后目标无效、其余仍对 | cp_sub_mem_invs | M1 | RTL未就绪 |
| TP-SUB-MEM-008 | UARCH §6.3 | 写后读旁路定向：填充与另一请求查找同拍同址 | 子系统编排同拍冲突 | 查找见新值；`model/` 参考模型（待 Xia） | cp_sub_mem_byp | M1 | RTL未就绪 |
| TP-SUB-MEM-009 | UARCH §8 | 失败回请求方；除配置终止外记事件 | 扫失败类别 | 4 bit 原因与事件与模型一致（溢出见 MEM-064） | cx_sub_mem_err | M1 | RTL未就绪 |
| TP-SUB-MEM-010 | §9.5；UARCH §6.4 | 译码器命中 4 拍端到端 | 窗内 PA、翻译缓存或 L0 命中 | UBMD / TokenValue=`model/` 参考模型（待 Xia） | cp_sub_dec_hit | M1 | RTL未就绪 |
| TP-SUB-MEM-011 | §9.5；UARCH §6.4 | 译码器缺失：L0 / L1 再填翻译缓存，随后命中 | 冷翻译缓存 | 回填后 1 MB 粒度命中；下标切片见 DEC-003/007/008 | cp_sub_dec_fill | M1 | RTL未就绪 |
| TP-SUB-MEM-012 | SPEC §10、§11 | HOOKS 后门可预装；PRODUCT 无 `tb_*` 后门口 | 两套网表 | 与 MEM-069–071 同口径，覆盖 UMMU+译码器实例 | cp_sub_mem_net | M1 | RTL未就绪 |
| TP-SUB-MEM-013 | UARCH §5；D17 | 结构叶子 TB 只驱动 UARCH §5 具名信号，不依赖字段布局 | 子系统 / 叶 TB 端口清单 | 无表项字段切片激励；解码叶子隔离在 MEM-072–079、DEC-017–019 | cp_sub_mem_named | M1 | RTL未就绪 |

#### 8.8.4 本小节测试点统计

口径与公共 §13 相同（一行一桶），但**只统计本小节**，不改公共合计。

| 层 | 总行 | M1（本小节分母） | 后续 | 推迟 | 一期不做 |
| --- | --- | --- | --- | --- | --- |
| 单元 UMMU（§8.8.1） | 90 | 81 | 9 | 0 | 0 |
| 单元译码器（§8.8.2） | 19 | 19 | 0 | 0 | 0 |
| 子系统内存管理（§8.8.3） | 13 | 13 | 0 | 0 | 0 |
| **本小节合计** | **122** | **113** | **9** | **0** | **0** |

113 + 9 + 0 + 0 = 122。

本小节 M1 分母拆分：RTL未就绪 92 + 待定 21 = 113。无「计划」「计划（waiver）」。未实现的 RTL未就绪 / 待定 记 SKIP，不算 PASS，也不算功能覆盖达成。

#### 8.8.5 本小节待定清单

| 待决 | 事项 | 受影响 TP | 状态原因 |
| --- | --- | --- | --- |
| D-04 | 一次查询多种失败时的流水级报错优先级 | TP-UNIT-MEM-063 | 规范未写；UARCH 草案暂按配置→上下文→越界→翻译→权限 |
| Q-E09 / D-12 | UMMU 事件格式、寄存器切片、队列溢出行为 | TP-UNIT-MEM-064 | 事件 FIFO 溢出等 Q-E09 |
| S-01（UARCH D-01） | 解码叶子字段布局能否进公开仓库 | TP-UNIT-MEM-072–079、TP-UNIT-DEC-017–018 | 字段布局待船长；结构叶子不依赖布局 |
| D-05 | 译码器 L0 PTE / L0 PTRE / L1 PTE 格式；PTRE「最后一级」 | TP-UNIT-DEC-005、006、019 | 格式待船长 |
| Q-B08 | 译码器全部失效 / 按 PA 范围失效 / SYNC（Xia 提案） | TP-UNIT-DEC-011–013 | 待船长确认 |
| D-14 / C-D1 | 译码 L0 表放片上还是放内存；片上 8 块或单块分段写 | TP-UNIT-DEC-014–016 | 两种放置都列 TP，待船长选 |
| Q-A17 | 多级 MAPT 2 MB | TP-UNIT-MEM-082 | 后续 |
| Q-A18 | 硬件更新访问 / 脏标志 | TP-UNIT-MEM-083 | 后续 |
| Q-A16 | 多块 MAPT | TP-UNIT-MEM-084 | 后续 |
| Q-A03 | Stage 2 / 安全态 Stage 2 | TP-UNIT-MEM-085 | 后续 |
| Q-A19 | Stall | TP-UNIT-MEM-086 | 后续 |
| Q-A20 | 事件真正合并 | TP-UNIT-MEM-087 | 后续 |
| Q-E03 | TEE 选表 | TP-UNIT-MEM-088 | 后续；非 0 已由 MEM-001 覆盖 |
| Q-C04 | Positive PLB | TP-UNIT-MEM-089 | 后续 |
| Q-E12 | 委托非特权软件管 MAPT | TP-UNIT-MEM-090 | 后续 |

`model/` UMMU 查表 / 译码参考模型尚未提交（待 Xia）：所有「`model/` 参考模型（待 Xia）」检查在模型入库前记 SKIP，不记 PASS。

#### 8.8.6 本小节 SPEC→TP 反向追溯

第 9 章各节 → 本小节 TP。项目 SPEC 的钩子 / 双网表章节一并列出。非功能叙述不要求独立 TP。

| 规范 | 功能需求（短述） | 主 TP |
| --- | --- | --- |
| §9.1–§9.3 | 总述、Home-User、UBMD | TP-SUB-MEM-001、TP-UNIT-MEM-001–003 |
| §9.4.2.1 | TECT / 配置查找、非法与终止 | TP-UNIT-MEM-004–008、072–073 |
| §9.4.2.2 / §9.4.2.2.2 / §9.4.2.2.3 | 线性/两级 TCT、上下文非法、TokenID | TP-UNIT-MEM-009–016、074–076 |
| §9.4.3 | Stage 1 翻译、TLB、遍历、块拆 4 KB、AF | TP-UNIT-MEM-017–030、079；TP-SUB-MEM-003 |
| §9.4.4.1–§9.4.4.2 | 单项/多级 MAPT、范围闭区间、`mapte_*` | TP-UNIT-MEM-031–035、077–078；TP-SUB-MEM-004 |
| §9.4.4.3–§9.4.4.3.5 | TokenValue、排他、访问类型、失败类别优先级 | TP-UNIT-MEM-036–043 |
| §9.5 / §9.5.1 | 译码器表项选择、范围、L1 | TP-UNIT-DEC-002–008、017–019；TP-SUB-MEM-010–011 |
| §9.5.2 | UBA 加法、进位丢弃 | TP-UNIT-DEC-009 |
| App. D.4.1.5 | MMIO 基址相减与窗口越界 | TP-UNIT-DEC-001 |
| App. D.4.1.6 | 译码器中断向量 | 待 RSC 契约；本小节不单列 |
| App. D.4.1.7–D.4.1.10 | 译码器全部失效、按 PA 范围失效、SYNC | TP-UNIT-DEC-011–013 |
| §11.4.4 | 按组 / 按条件失效 | TP-UNIT-MEM-053–058；TP-SUB-MEM-006–007 |
| §11.6.4 | TEE / `EE_bits` | TP-UNIT-MEM-001、088 |
| SPEC §10、§11 | 后门、`tb_test_mode`、HOOKS vs PRODUCT | TP-UNIT-MEM-069–071；TP-SUB-MEM-012 |
| UARCH §6 | 命中 3/4 拍、缺失阻塞与重放、写后读旁路 | TP-UNIT-MEM-047–052、TP-UNIT-DEC-010；TP-SUB-MEM-001–008 |
| UARCH §7 | 全部失效、扫描失效、SYNC、CSR 改 TECT 不自动失效 | TP-UNIT-MEM-053–060 |
| UARCH §8 | 4 bit 失败原因、记事件、溢出 | TP-UNIT-MEM-061–064；TP-SUB-MEM-009 |
| UARCH §9 | 必选/可选边界 | TP-UNIT-MEM-080–090 |
| UARCH §10 | 原语外 valid、随机初值、后门 | TP-UNIT-MEM-065–071；TP-UNIT-DEC-014–016 |

本小节范围内：第 9 章已列功能需求均有 TP。App. D.4.1.6 中断接 RSC，等 ch10 契约，不记本小节漏项。

---

## 9. 覆盖率门限与豁免（D12）

门限**已由 D12 钉死**，本计划不再写「待 PM/船长定」。

| 项 | 门限 | 说明 |
| --- | --- | --- |
| 行覆盖 | **计入具名豁免后 100%** | 源：Verilator 5.032。**分母 = `TEST_HOOKS=1` 网表**；钩子代码计入，**不单独豁免**。未测到的非钩子死代码必须逐条豁免 |
| 功能覆盖 | **计入具名豁免后 100%** | 分母 = 里程碑 M1 且状态 ∈ {计划, RTL未就绪, 待定, 计划（waiver）}；「推迟」「一期不做」「后续」不进分母 |
| Toggle | **不算** | 不采集、不验收 |

豁免必须**具名**：编号、层次/文件或 TP ID、理由、批准人、日期。无批准人的条目不算豁免、计为缺口。记入 `reports/regress/waiver.md`。

| 标识 | 对象 | 理由 | 对应 TP |
| --- | --- | --- | --- |
| `WAIVER_CRD_UF_CNT` | `CNT_CRD_UF` 递增分支 | SPEC §13.4：正确设计不会把信用减过 0，计数仍保留；行/功能覆盖不可达。禁止 force 下溢 | TP-UNIT-DLL-024 |
| `WAIVER_CRD_UF_IRQ` | `IRQ_STATUS.CRD_UF` 置位与 `irq` 合成 | SPEC §13.4：同上 | TP-UNIT-DLL-024 |
| （FSM default） | LMSM / DLL SM 非法态、default 臂 | 不停指定态；具名 waiver，批准后落文件 | TP-UNIT-PCS-027、TP-UNIT-DLL-022 |

下溢由 **TB 断言**，不是 RTL assert。PCS RX unpack drain（TP-UNIT-PCS-026）等新 RTL 评估可达性，未决前不算豁免达成。

参考（旧项目习惯，已被 D12 吸收，不是另一套门限）：行覆盖常先做到 ≥95% 再把剩余写成豁免；功能覆盖本身就要 100%（豁免计入）。本期直接按 D12 的 100%（含豁免）验收。

---

## 10. 门限与记账

### 10.1 PASS / FAIL / SKIP

沿用 Switch `report.py` + `summarize.sh` 行协议，写入 `reports/regress/<tc>.log`：

| 结果 | 判定 | 是否算绿 |
| --- | --- | --- |
| **PASS** | 仿真退出 0、无 UVM_ERROR、无 Python 异常、日志有 `PASS <tc>`、scoreboard 0 mismatch | 是 |
| **FAIL** | 期望/实际不符、UVM_ERROR、traceback、非 0 退出；日志写 `FAIL` 及 stimulus / expected / actual / seed / 复现命令 | 否 |
| **SKIP** | 具名原因：工具缺口、RTL 未就绪、等 SPEC、D4/D2 排除。**不记 PASS、不记 FAIL** | 不进连续绿的分子，必须出现在 SKIP 账本 |

禁止：用 Force 让 Icarus 单独 PASS；把「未实现」写成 PASS；把工具 SKIP 当覆盖达成；在 `TEST_HOOKS=0` 上依赖钩子。

### 10.2 连续绿

同时满足才算连续绿：

1. Icarus 12.0：所有未 SKIP 的 M1 TC 为 PASS。
2. Verilator 5.032：所有未 SKIP 的 M1 TC 为 PASS（新 TC 不得再因 Force 进入工具 SKIP 表）。
3. D12：行 + 功能在计入已批准豁免后为 100%（行覆盖分母为 `TEST_HOOKS=1`）。
4. §10.4 两套网表该跑的桶都绿。
5. §10.5 Yosys eqy 通过。
6. 无新增未记账 FAIL。

### 10.3 报告与 seed

| 路径 | 内容 |
| --- | --- |
| `reports/regress/hooks0/` | `TEST_HOOKS=0` 冒烟 log |
| `reports/regress/hooks1_mode0/` | `TEST_HOOKS=1`、`tb_test_mode=0` |
| `reports/regress/hooks1_mode1/` | `TEST_HOOKS=1`、`tb_test_mode=1`（含钩子路径） |
| `reports/regress/eqy/` | Yosys eqy 日志与结论 |
| `reports/regress/*.log` | 每 TC 一份；**必须含 seed=** |
| `reports/regress/summary.txt` | `summarize.sh` 汇总 PASS/FAIL/SKIP 行数 |
| `reports/regress/skip.md` | SKIP 账本：TC、原因、对应决定/缺陷 |
| `reports/regress/waiver.md` | D12 具名豁免（含 FSM default） |
| `reports/regress/cov_line/` | Verilator 行覆盖（`TEST_HOOKS=1` 分母） |
| `reports/regress/cov_func/` | 测试点矩阵达成表 + CoverPoint 导出 |

随机 TC 每次运行打印 `SEED <n>`；复现命令必须带同一 seed。

### 10.4 双网表回归（Xia 已写进 SPEC）

Xia 已写死：存在两份网表，不得混用验收口径。

| 网表 | 编译 | 跑什么 |
| --- | --- | --- |
| **产品** | `TEST_HOOKS=0` | 不依赖钩子的冒烟子集：**TP-TOP-015 + TP-UNIT-CSR-019**（TEST 窗读 0 / 写忽略 / `csr_err=0`） |
| **回归 / 覆盖率** | `TEST_HOOKS=1` | `tb_test_mode=0` 与 `=1` **都跑**（TP-TOP-016 / 017） |

行覆盖分母按 `TEST_HOOKS=1` 那份算，钩子代码也计入，不单独豁免。`tb_test_mode=1` 负责打到钩子分支。

### 10.5 签核标准

在 §10.2 连续绿之外，交付还必须：

1. **Yosys eqy** 证明 `TEST_HOOKS=0` 与 `TEST_HOOKS=1` 形式等价。约束：`tb_test_mode=0`，且所有 `tb_*` 输入接**复位值**（不干预）。
2. **不等价就不算交付**。不得用「钩子网表仿真绿」代替 eqy。
3. 产品冒烟（hooks0）不得依赖任何 `tb_inj_*` / `tb_obs_*` 行为；必须含 TEST 窗 CSR-019。
4. FSM default 臂与 `WAIVER_CRD_UF_*` 仅允许已批准的具名 waiver。
5. 本计划不引用任何 Vibe-UB commit SHA（历史改写后全部失效）。

---

## 11. 流程

```
失败 TC
   │
   ├─ 复现稳定（仿真器 + seed + 命令 + 日志）
   │     写清：期望（黄金模型/规范章节号）vs 实际（波形/打印）
   │
   ├─ 根因在 RTL / 生成物  → 回设计（Xia / pyc4.0），验证不改 RTL
   ├─ 根因在规范歧义/漏洞 → 回架构（Xia），验证不改 SPEC
   ├─ 根因在 TB/黄金模型   → 验证修 TB，补回归
   ├─ 根因在工具           → SKIP 记账 + 基础设施，不放行 Force
   └─ eqy 不等价           → 回设计（钩子未在 tb_test_mode=0 下真正透明），**不算交付**
```

约束：

- 验证 **不修改** `rtl/`、SPEC、`DECISIONS.md`、`SPEC_INDEX.md`。
- 给设计的失败单至少含：TP ID、规范章节号、复现命令、seed、期望、实际、是否双仿复现、网表（`TEST_HOOKS` / `tb_test_mode`）。
- 规范争议只引用章节号，不粘贴规范原文。钩子见 SPEC §10，TEST 寄存器见 REGMAP §2.4，双网表/eqy 见 SPEC §11，开放问题见 SPEC §13。
- 不引用任何 Vibe-UB commit SHA。

---

## 12. 风险与待定

**D1 已锁 Rev 2.0，Rev 2.1 不列为风险。** 若未来改基线，先改 DECISIONS，再改本计划。

### 12.1 工具链

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| cocotb 锁 1.9.2（uvm-python 不支持 2.x） | 不能跟上游 2.x API | D7 钉死；D16 lock |
| Verilator 不认层次 Force | 旧写法无法双仿 | D13；新 TC 只走端口/钩子 |
| Icarus 无代码覆盖 | 行覆盖只来自 Verilator | D12 以 Verilator 为准；Icarus 只做功能门 |
| Verilator ≥5.036 未资格认定 | 贸然升级可能破 cocotb 1.9.2 | D7：先复资格 |

### 12.2 工程待定（不是规范版本风险）

钩子章节已落在 SPEC §10 / REGMAP TEST；双网表/eqy 在 SPEC §11；其余开放问题在 SPEC §13。下表只留实现与工程项。

| 项 | 状态 | 谁 |
| --- | --- | --- |
| SPEC §13.2 实现相关超时的**周期数** | 等 SPEC §13.2 | Xia（RTT 已定为 2µs） |
| PCS RX unpack drain（`n==0 && have`） | SPEC §10.5 / §13.2 | **等新 RTL** 后再评估端口可达性；现在不删、不加钩子 |
| 附录 D 镜像窗口内字段复位值 | SPEC §13.3；本仓不抄规范复位表 | Xia / 实现对照 |
| 对端是第二 DUT 还是轻量 BFM | 未定 | 验证 / Xia |
| ASIC 工艺节点 | SPEC §13.3 未知 | 船长；不阻功能门。`F_CORE` 已定 |
| pyc4.0 生成物未齐 | 大量 TP = RTL未就绪 | 按模块交付打开 TC |
| `TOOLCHAIN.lock` | 未落 | 基础设施 PR（D16） |
| 手写 `rtl/` `tb/` 迁 `legacy/` | 未做 | 另 PR（D10） |
| 本仓 git 历史改写 | 将做；SHA 全变 | 船长；本计划不引本仓 SHA |

### 12.3 技术风险

| 风险 | 说明 |
| --- | --- |
| 当前手写 lane 分发按 2-bit 切片，规范按 8-bit 符号 | 官方 DUT 必须以 §3.2.5 / §3.2.2.3 黄金模型为准 |
| 当前手写异步复位 vs D6 同步复位 | 只验收 pyc4.0 生成物 |
| 对端 BFM 若抄 DUT | 必须独立黄金模型 |
| 环回掩盖单向训练不对称 | 至少保留「单端 DUT + 对端 BFM」一条顶层路径 |

---

## 13. 测试点统计

互斥口径（一行只进一桶）：

- **M1 功能分母（D12）**：里程碑 = M1，且状态 ∈ {计划, 计划（waiver）, RTL未就绪, 待定}。
- **后续**：里程碑 = 后续，且不是「一期不做 / 推迟」。
- **推迟**：状态 = 推迟（D2），含 `tb_obs_nw_dll_data`、CFG0 设备级 / CFG1（SPEC §1.3）。
- **一期不做**：状态 = 一期不做 D4 或 一期不做 D11。

| 层 | 总行 | M1（D12 分母） | 后续 | 推迟 | 一期不做 |
| --- | --- | --- | --- | --- | --- |
| 单元 PCS/LMSM | 43 | 38 | 3 | 0 | 2（皆 D4） |
| 单元 DLL | 25 | 23 | 0 | 0 | 2（皆 D4） |
| 单元 CSR/CDC/IF/PMA/HOOK | 52 | 47 | 0 | 5 | 0 |
| 子系统 PCS | 20 | 15 | 0 | 0 | 5（皆 D4） |
| 子系统 DLL | 21 | 20 | 1 | 0 | 0 |
| 顶层 | 21 | 18 | 1 | 1 | 1（D11） |
| 推迟占位 NW/TP/TA/钩子 | 7 | 0 | 0 | 7 | 0 |
| **合计** | **189** | **161** | **5** | **13** | **10** |

161 + 5 + 13 + 10 = 189。

M1 分母拆分：计划 116 + 计划（waiver）2 + RTL未就绪 28 + 待定 15 = 161。未实现的 RTL未就绪 / 待定 记 SKIP，不算 PASS，也不算功能覆盖达成。

待定 15 条：SPEC §13 映射 14 + unpack drain 1（PCS-026）。无等 SPEC 澄清项。矛盾清单空。

---

## 14. 待定项与退回 Xia 的清单

已关闭：D14 参数表；RTT = 2µs；`F_CORE`≈80.57 MHz / 仿真 12.41 ns；钩子与 TEST 寄存器章节（SPEC §10、REGMAP §2.4）；双网表/eqy（SPEC §11）。

### 14.1 SPEC §13 开放问题 → 受影响 TP

| SPEC | 开放项 | 受影响 TP |
| --- | --- | --- |
| §13.1 | `NUM_RETRY_THRESHOLD=15`、`NUM_PHY_REINIT_THRESHOLD=4`（草案） | TP-SUB-DLL-010、TP-UNIT-CSR-015、TP-UNIT-CSR-022 |
| §13.1 | `CRD_BP_THRESHOLD=1024`（草案） | TP-UNIT-HOOK-003、TP-SUB-DLL-006 |
| §13.1 | `tb_obs_dll_sm_st` 编码（草案；LMSM 顶层码已定） | TP-UNIT-DLL-008、TP-UNIT-HOOK-001 |
| §13.2 | FEC `CodecNum` / 交织 | TP-UNIT-PCS-018（一期不做 D4，建议 1） |
| §13.2 | FEC 编解码拍数与并行度 | TP-UNIT-PCS-028、TP-TOP-020 |
| §13.2 | PMA 模型保真度（探测波形等）与存放路径 | TP-UNIT-PMA-003 |
| §13.2 | RX 缓冲深度（含吞 PCS valid-only） | TP-UNIT-IF-005、TP-SUB-DLL-017 |
| §13.2 | `LMSM_TMR_SCALE` / `AM_IVL_SCALE` 缩放编码 | TP-UNIT-CSR-005、TP-UNIT-CSR-007、TP-UNIT-PCS-022 |
| §13.2 | 各通路周期延迟；齿轮箱拍数（非跨时钟） | TP-TOP-020、TP-UNIT-CLK-002 |
| §13.2 | per-lane RX valid；AMCTL 是否与数据口共用 | TP-UNIT-PMA-004 |
| §13.2 | `pma_tx_width` 编码；均衡针脚 | TP-UNIT-PMA-005 |
| §13.2 | DLL↔PCS TX 是否要 sop/eop | TP-SUB-PCS-017 |
| §13.2 | FEC bypass 时 `fec_ok` 含义 | TP-SUB-PCS-018 |
| §13.2 | RETRY_ACK_SM 实现细节 | TP-UNIT-DLL-019 |
| §13.2 | TX 是否置 `ERROR_FLAG` | TP-SUB-DLL-021 |
| §13.2 | 规范写「实现相关」的超时（Probe 等待等） | TP-UNIT-PCS-022、TP-SUB-DLL-010 |
| §13.2 | Data Rate 0 下 EQ/RXEQ 空转 | TP-UNIT-PCS-029 |
| §13.2 | `MAX_DP_FLITS` | TP-UNIT-DLL-005 |
| §13.2 | `tb_inj_am_lock` / `tb_inj_lid_bad` 是否在真实 AM 后删除 | TP-UNIT-PCS-024 |
| §13.2 | PCS RX unpack `n==0 && have` | TP-UNIT-PCS-026 |
| §13.2 | 复位撤销后首拍 `valid`/`ready` | TP-UNIT-IF-006 |
| §13.3 | 工艺节点（船长） | 无功能 TP；不阻 M1 |
| §13.3 | Probe 端接检测电路级算法 | TP-UNIT-PCS-022（行为级；算法不编造） |
| §13.3 | 真实 SerDes 模拟参数 | 非目标（D3）；TP-UNIT-PMA-003 |
| §13.3 | 附录 D 字段复位值（本仓不抄） | TP-UNIT-CSR-003、TP-UNIT-CSR-018 |
| §13.4 | `WAIVER_CRD_UF_CNT` / `WAIVER_CRD_UF_IRQ` | TP-UNIT-DLL-024；禁止 force 下溢 |

### 14.2 已关闭（含 Q4）

Q4 已关：TX Lane_ID 口（`lmsm2pcs_lane_id_mode` / `base` / `map`）、LMB 起始锁存全部 `lmsm2pcs_*`、`ltb_valid` 无多拍保持（SPEC §3.3.4、§5）。`lane_id_mode=3` 为 `RESERVED`（SPEC §3.3.4）：LMSM 永不驱动（TB 断言 PCS-043）；PCS 与 2 同分支按 NULL（PCS-042 leaf 端口打 3，结果同 2）。无不可达分支，**无 waiver**，不再列 SPEC 缺口。§13.2 **不再**列 TX `lane_id` 改写或 valid 对齐拍数。

另已关：清零、APPD 址、`PORT_RST`、TEST 窗、信用钩子每拍覆盖、`ub_rst_sync` 2 级、`CRD_UF` waiver、valid-only RX。

名字与编码已关（Xia）：`CTRL.LMSM_START`（0x0000 bit1；SPEC §6.1 旧名 `LMSM_CTRL.START` 作废）；`STATUS.RETRY_REQ_ST` / `RETRY_ACK_ST` 合法码与保留（SPEC §6.3 / §6.4）；`PARAM_PHY.NUM_LANES_*` 二进制 1/2/4/8、复位 1。保留值 RTL 不产出，TB 断言，**无 waiver**。X1–X3 删除。

### 14.3 仍等 SPEC 澄清 / 缺口（验证不选边）

**无。** 矛盾清单已清空。

### 14.4 工程项（不阻规范对齐）

1. 顶层对端用第二 DUT 还是轻量 BFM。
2. D16 `TOOLCHAIN.lock` 尚未存在；以 D7 为准。
3. D10 `legacy/` 迁移未做；官方门不跑手写 `tb/*.v`。
4. pyc4.0 生成物未齐 → 对应 TP = RTL未就绪。

---

## 15. SPEC → TP 反向追溯

Xia 标准：每条 SPEC **功能需求**至少一条 TP。下表按 SPEC 章节列主 TP（REGMAP / CODING_STYLE 功能需求附后）。非功能叙述（框图、引用约定、与现网冲突对照）不要求独立 TP，在「无 TP」列说明。

| SPEC / 配套 | 功能需求（短述） | 主 TP |
| --- | --- | --- |
| §1.1 | M1 范围：PCS + LMSM + DLL + 寄存器子集 + 两套网表 | 各层 M1 TP；§11 → TOP-015–018 |
| §1.2 | 非目标：NW 及之后、可选、多时钟、真实 PMA、FPGA、多端口/路由/CFG1 | DEF-*、CSR-001/002/004、TOP-009、TOP-014、SUB-PCS-012–016 |
| §1.3 | 上边界只 flit；CFG0 设备级 / CFG1 / 路由表不实现 | CSR-001/002/004、IF-001/002、DEF-HOOK-001 |
| §2.1–§2.2 | 模块划分（结构） | 无独立功能 TP（结构约束，由顶层/子系统 TP 覆盖） |
| §2.3 | Gray/预编码在 PMA；NRZ 关 Gray；`PRECODE_EN=0`；探测在模型 | PMA-001–003、PCS-001/002 |
| §2.4 | FEC / 扰码 / 8-bit 分发 / AMCTL / deskew / 交织 | PCS-003–019、SUB-PCS-001–008 |
| §2.5 / §6.1 | LMSM 主状态与训练；启动位 = REGMAP `CTRL.LMSM_START` | PCS-021–025、029、CSR-014、HOOK-001/002、SUB-PCS-011 |
| §2.6 / §6.2 | DLL SM、分段、VL、信用、重传、CRC | DLL-001–025、SUB-DLL-* |
| §3.1 | valid/ready 同拍；ready 不组合看 valid；复位后首拍待定 | IF-001、IF-006 |
| §3.2.1 | 仅 `core_clk` / `rst_n`；无 `pma_clk` | CLK-001、RST-001、TOP-019 |
| §3.2.2 | 160b flit 边带；非法 VL 丢弃；**上层** `nw_rx_ready`；`dll_status_*` 互斥。PMA/PCS→DLL 无反压 | IF-002/003/005、DLL-023、TOP-011、PMA-006、SUB-PCS-020 |
| §3.2.3 | 整字写、1 拍读、未映射 `csr_err`；TEST 窗已映射；`PORT_RST` 16 拍与范围；W1C / `CNT_CLR` | CSR-009–013、016–021、023–024 |
| §3.2.4 | PMA 数据口；每拍一字；**无** `pma_rx_ready` | PMA-004、PMA-006、CLK-002、TOP-006 |
| §3.2.5 | LMSM–PMA 训练侧带 | PMA-005 |
| §3.2.6 | `link_up`/`link_ready`/`irq` 高有效、复位全屏蔽 | IF-004、CSR-012/021、HOOK-002 |
| §3.3.1 | DLL→PCS TX valid/ready；sop/eop 待定 | SUB-PCS-001、SUB-PCS-017 |
| §3.3.2 | PCS→DLL RX valid-only；**无** `pcs2dll_ready`；`fec_ok`/`uncorr` 对齐 | SUB-PCS-002/005/018/020、IF-005 |
| §3.3.3 | LMSM↔DLL `link_*` 与重训电平握手 | SUB-PCS-011/019、SUB-DLL-012 |
| §3.3.4 / §5 | LTB 字段口、`fec_mode_ctrl`、pattern 0–3、Lane_ID PHYS/ASCEND/NULL、ASCEND base+map、3=`RESERVED`（PCS 与 2 同 NULL 分支、无不可达分支、无 waiver）、LMSM 永不驱动 3（TB 断言）、中途改任意 `lmsm2pcs_*`、RX `pcs2lmsm_lane_id[7:0]` | PCS-030–043、SUB-PCS-006/009/010 |
| §3.3.5 | CSR→各块电平、无跨时钟脉冲 | CSR-024、CLK-001 |
| §4.1 | 单时钟 80.57 MHz，`USE_PMA_CLK=0` | CLK-001、TOP-019、TOP-009 |
| §4.2 | `rst_n` 异步置位同步释放；`ub_rst_sync` 2 级 + `ub_pyc_rst_adapt` | RST-001/002、CDC-001、TOP-008 |
| §4.3 | CDC 白名单；M1 产品通路无 CDC | CDC-002–004 |
| §5 | CSR 1 拍；FEC/齿轮/通路延迟待定 | CSR-010/023/024、PCS-028、CLK-002、TOP-020 |
| §6.3 | RETRY_REQ_SM；`RETRY_REQ_ST` 0–4 合法、5–7 保留不产出 | DLL-018、SUB-DLL-007/010/015、CSR-022/026 |
| §6.4 | RETRY_ACK_SM（转移细节待定）；`RETRY_ACK_ST` 0–1 合法、2–3 保留不产出 | DLL-019、SUB-DLL-008、CSR-022/027 |
| §7 | 异常表：FEC/BCRC/重传/信用/溢出/超时/非法 VL/未映射 | PCS-016、DLL-002/023/024、SUB-DLL-009–012/017–021、CSR-011/016/021 |
| §8 | 性能/延迟目标；RTT 2µs | TOP-020、SUB-DLL-010 |
| §9 | 已确认参数读回；`NUM_LANES_*` 二进制 1/2/4/8、复位 1 | CSR-015/028、PMA-001、CLK-001 |
| §10.1–§10.2 | 两道门控；仅三支 `tb_inj_*`；crd 仅 VL0；观测列表 | HOOK-001–004、DLL-025、TOP-005、SUB-DLL-016 |
| §10.3 | `tb_obs_lmsm_st` 仅顶层 0–9 | HOOK-001 |
| §10.4 | `LMSM_TMR_SCALE` / `CRD_TO_DIS` / `AM_IVL_SCALE` | CSR-005–007 |
| §10.5 | 非法态 waiver；unpack drain 待定 | PCS-026/027、DLL-022 |
| §11 (a)–(e) | 两套网表、双 mode、PRODUCT 冒烟（含 TEST 窗）、eqy、CRD_UF waiver | TOP-015–018/021、CSR-019、DLL-024 |
| §12 | 与现网冲突（重写对齐） | 非功能需求；PCS-006、PMA-002、RST-001、CDC-004 覆盖偏差 |
| §13 | 开放问题 | 见 §14.1，0 条无映射 |
| REGMAP §2.1 | CTRL/STATUS/IRQ/`PORT_CNA`；`RETRY_*_ST` 合法码与保留断言 | CSR-008/012–014/020–022/026–027 |
| REGMAP §2.2 | PARAM_*；`NUM_LANES_*` 合法值与保留断言 | CSR-015/028 |
| REGMAP §2.3 | ERR 饱和 + `CNT_CLR` 0x0224 bit0–8 + COUNT 只读 | CSR-016/017/025 |
| REGMAP §2.4 | TEST | CSR-005–007/019 |
| REGMAP §2.5 | APPD 窗口 | CSR-003/018 |
| CODING_STYLE §1/§7 | 生成两套网表；lint 0 error；钩子不另开行覆盖 waiver | TOP-015–018/021 |
| CODING_STYLE §2–§4 | 同步复位、白名单、禁止 force | RST-*、CDC-004、TOP-005 |
| CODING_STYLE §6 | 产品 RTL 禁 `$display` / 异步业务复位 | CDC-004（静态扫描） |

**没有对应 TP 的 SPEC 功能需求：0。**

下列章节不是功能 SHALL，故无独立 TP（不是漏项）：§2.1 框图、文首引用约定、CHANGELOG、CODING_STYLE §5 命名 / §8 原语可表达性 / §9 与现树关系。

---

## 16. 本草案不包含的工作

- 不改 `rtl/`、`tb/`、SPEC、`DECISIONS.md`、`SPEC_INDEX.md`、其它文档。
- 不拷贝 Switch TB 代码。
- 不自合本 PR。
- 不新增 `TOOLCHAIN.lock`（D16）。
- 不发明 §7 以外的钩子；不引用任何 Vibe-UB commit SHA。
