# Vibe-UB Controller 验证计划

| 项 | 内容 |
| --- | --- |
| 文档 | `docs/VERIF_PLAN.md`（draft） |
| 目标 DUT | 完整 UB controller RTL（pyCircuit / pyc4.0 生成 Verilog） |
| 规范基线 | UnifiedBus Base Specification **Rev 2.0**（2025-12-31），见 D1 |
| 验证框架 | 仅 uvm-python + cocotb 1.9.2 + cocotb-coverage 1.2.0，见 D7 / D8 |
| 状态 | draft，不自合；只新增本文件 |
| 配套决定 | [PR #2](https://github.com/lukebest/Vibe-UB/pull/2) `docs/DECISIONS.md`（draft，未合）。本计划按 **D1–D16** 编号引用，不改写那些文件。 |

规范引用只写章节号（如 UB-PHY §3.2.5、UB-DL §4.6.1）和用自己的话概括的要点。不复制规范正文、表格、公式或寄存器位定义。章节目录以 PR #2 将合入的 `docs/SPEC_INDEX.md` 为准。

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
| D7 | 唯一框架 uvm-python（`96a06eee`）+ cocotb 1.9.2；Icarus 12.0 主门；Verilator 5.032 对比与行覆盖 | §4 |
| D8 | 定向 + Python 黄金模型；功能覆盖 = 测试点矩阵；`randomize()`；允许 CoverPoint/CoverCross 支撑 TP；禁 pyvsc | §4.3、§8 |
| D9 | 只读参考并改造 Vibe-UB-Switch 的 pyCircuit / uvm-python TB | §6；本 PR **不拷代码** |
| D10 | 现有手写 `rtl/`、`tb/` 后续迁 `legacy/`（另 PR） | §1.3、§12；本 PR 不搬 |
| D11 | 一期无 FPGA | §2.4；不列入 FPGA 里程碑 |
| D12 | 验收 = 行覆盖 + 功能覆盖，**计入具名豁免后 100%**；不算 toggle | §9；门限已定，不再写「待定」 |
| D13 | TB 一律不 force 内部信号；注入只走端口或 SPEC 测试钩子 | §5.5、§7 |
| D14 | PHY / SerDes / DLL / 工艺参数：Xia 草案，待船长批准 | §3 标「草案 / D14」 |
| D15 | 规范全文移出公开树（PR #2）；历史改写未做 | 本计划不引用已删正文；不改那些文件 |
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

1. **唯一框架（D7）**：uvm-python（lukebest/uvm-python 提交 `96a06eee7dda1edae2013154b3d3756b040c71ad`）+ cocotb **1.9.2**（`>=1.9.2,<2`）+ cocotb-coverage **1.2.0**（必须 `<2.0`）。禁止 SV-UVM、禁止无结构的裸 cocotb、禁止 pyvsc（D8）。
2. **仿真器（D7）**：Icarus Verilog **12.0** 主仿并作为 PASS/FAIL 门；Verilator **5.032** 做对比仿真并给出行覆盖。cocotb 1.9.2 文档要求 Verilator `>=5.022`；未重新资格认定前不升到 `>=5.036`。
3. **不 force（D13）**：TB 不 force 内部层次信号。激励与错误注入只走端口，或 Xia SPEC 定义的测试钩子端口。原因：Verilator VPI 不认层次 Force；旧仓因此有 4 个 TC 只能在 Icarus 跑。
4. **验证不改 RTL / 不改 SPEC**。失败回设计并附复现；规范漏洞退回架构（Xia）。
5. **一期不做 FPGA（D11）**。
6. **一期不做可选特性（D4）**。

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

- 按 lane 接收/发送符号流（M1：32 bit/lane，见 §3 草案）
- 提供对称环回（TX 边界直接接到 RX 边界，可加可配置 deskew 延迟）
- 不模拟模拟均衡、CDR 抖动、光模块；这些标 **一期不做 D4** 或与 D3 一并排除

顶层「含环回」= 该行为模型环回，不是 FPGA 板级环回（D11）。

### 2.4 明确不做（一期）

| 项 | 依据 | 处理 |
| --- | --- | --- |
| FPGA 原型 / 板级 | D11 | 无 FPGA 里程碑 |
| 可选规范特性 | D4 | 测试点标 **一期不做 D4** |
| NW / TP / TA 功能 | D2 | 测试点标 **推迟** |
| Toggle 覆盖 | D12 | 不算验收 |
| 层次 Force | D13 | 禁止；相关旧写法记 SKIP 而非改成 Force |
| 亚稳态统计 | — | 靠设计 CDC 工具；TB 只做 CDC 功能层 |

---

## 3. 默认参数（草案 / D14，待船长确认）

下表是 Xia 草案，**不是**已批准配置。未确认前：激励默认按草案搭，与草案冲突的参数组合标「待定」，不写死门限外的黄金期望。

| 项 | 草案值 | 备注 |
| --- | --- | --- |
| PHY 模式 | Mode-2 | D1 Rev 2.0；Mode-1 为一期不做 D4 |
| M1 速率 | 2.578125 Gbit/s，Data Rate 0，NRZ | 规范上限 106.25 Gbit/s PAM4，RTL 参数化，更高速率 = 后续 |
| Lane | M1：x1 起训到 x4；RTL 参数到 x8 | 宽度非对称规范支持，M1 默认关 → **一期不做 D4**；速率非对称不允许 |
| SerDes 接口 | M1：32 bit/lane | PCS-PMA 边界模型宽度（D3） |
| FEC | 默认 RS(128,120,T=4)；T=2 / bypass 可协商 | 交织（双 codec）→ **一期不做 D4** |
| DLL VL | M1 = 2；参数到 16 | VL 3–15 为后续 |
| 重传缓冲 | M1 = 256 flit | 更大深度后续 |
| Credit | 1 flit/cell；返回粒度 32；独占模式；M1 每 VL 640 cell | 共享模式 → **一期不做 D4** |
| ASIC 工艺 / 核频 | 未知 | 时序/STA 不在本功能计划；功能 TB 用可配周期 |
| RTT / 超时 | 未知 | 重传/训练超时用可配周期；具体数值 **待定** |

---

## 4. 验证框架与工具链

### 4.1 方法

- **定向测试**为主，每个测试点至少一条可独立复现的 TC。
- **Python 黄金模型 + scoreboard**：PCS（FEC / 扰码 / 8-bit 符号分发 / Gray）、DLL（LPH/LBH/BCRC、credit、retry）。
- 需要随机处使用 uvm-python 自带 `randomize()`（cocotb-coverage crv）。**每次运行把 seed 写入该 TC 日志**（D8）。
- 功能覆盖按 **测试点矩阵** 计算：一条 TP 在其映射 TC 全部 PASS 且对应 CoverPoint/CoverCross 命中后记覆盖。允许用 cocotb-coverage 的 **CoverPoint / CoverCross** 支撑 TP（D8），不引入 pyvsc。

### 4.2 钉扎与 TOOLCHAIN.lock（D7 / D16）

| 组件 | 钉扎 |
| --- | --- |
| Python | 3.11–3.13 |
| cocotb | 1.9.2（`>=1.9.2,<2`） |
| uvm-python | `git+https://github.com/lukebest/uvm-python@96a06eee7dda1edae2013154b3d3756b040c71ad` |
| cocotb-coverage | 1.2.0（`<2.0`） |
| cocotb-bus、regex | 从 Vibe-UB-Switch 已通过 venv 的 `pip freeze` 冻结（M2 引入 TB 时） |
| Icarus | 12.0（主门） |
| Verilator | 5.032（对比 + 行覆盖） |

`TOOLCHAIN.lock` **随基础设施 PR 落地（D16）**，本验证计划 PR 不新增该文件。未出 lock 前，以 D7 与上表为准。

### 4.3 覆盖采集

| 类型 | 来源 | 是否计入 D12 |
| --- | --- | --- |
| 行覆盖 | Verilator 5.032 | 是；Icarus 无代码覆盖，不作为行覆盖源 |
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
| `csr_agent` | 附录 D 寄存器子集读写 |
| `hook_agent` | 只打 SPEC 已定义的测试钩子端口（§7）；无钩子则该 agent 空接 |
| `clk_rst_agent` | 多时钟产生、同步复位释放（D6） |
| `scoreboard` | 订阅各 monitor；与 Python 参考模型比对 |
| 参考模型 | `ref_fec`、`ref_scramble`、`ref_lane`、`ref_dll`（成帧/CRC/credit/retry） |
| 覆盖 | 每条 TP 对应 CoverPoint；需要交叉的用 CoverCross（D8） |

单元级：单模块 + 薄 harness + 对应 leaf agent，不强制拉满顶层 env。

### 5.2 时钟与复位（D6）

- 业务逻辑：单时钟沿采样，**同步复位**。TB 在时钟沿对齐后释放复位，并检查复位期内输出进入已知安静态。
- 白名单手写 SV：异步复位同步器、CDC 原语。TB 对同步器做「异步断言、同步释放」功能检查；不注入亚稳态毛刺。
- 当前手写 `rtl/` 里 `always @(posedge clk or negedge rst_n)` 属于 D10 遗留，**不作为**官方 DUT 复位约定。

### 5.3 多时钟域与 CDC

- 功能层：跨时钟握手、异步 FIFO 水位、复位释放顺序，用定向 + 可配相位差激励，在端口上检查不丢/不重/不破坏 ready-valid。
- 亚稳态：不在 uvm-python TB 里统计；交给设计 CDC 工具。
- 禁止用 Force 打内部 CDC 节点（D13）。

### 5.4 PCS-PMA 行为模型与环回（D3）

TB 提供 `pcs_pma_bfm`：

1. **直通环回**：各 lane TX 符号延迟 N cycle 后送回 RX（N 可配，用于 deskew 窗口）。
2. **符号注错**：只改边界口上的符号（或 SPEC 钩子），用于 FEC / BCRC / 重传。
3. **不实现**模拟前端、光通道、FFE/DFE 自适应（一期不做 D4）。

顶层默认走环回 1。对端 LMSM/DLL 协商可用第二实例 controller 或轻量对端 BFM；对端 BFM 必须遵守同一套 Python 黄金模型，不能「对着 DUT 抄答案」。

### 5.5 禁止 Force（D13）

- 任何 TC 不得层次 Force。
- 若某检查离开内部探针就无法完成：先走钩子清单（§7）向 Xia 要端口；钩子未定义前该 TP 保持「RTL/SPEC 未就绪」，**不得**用 Force 在 Icarus 单开绿灯。
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

## 7. 测试钩子（D13）

注入与内部可观测性**只走端口或 SPEC 定义的测试钩子**。

Xia 的设计 SPEC 将另开 PR。本节引用该 SPEC 中的「测试钩子」章节，**待 SPEC 定义**。验证不在本文件发明钩子时序或位宽。

验证将**另行**给 Xia 一份钩子需求清单（本 PR 不包含 RTL）。预期类别（需求，不是已定义接口）：

| 类别 | 用途 | 对应 TP 例 |
| --- | --- | --- |
| 符号/码字注错 | FEC 纠错边界、不可纠后触发 DLL 重传 | TP-SUB-PCS-004、TP-TOP-005 |
| BCRC / 比特翻转 | DLL 检错与 RETRY_REQ | TP-SUB-DLL-007 |
| LinkUp / 训练事件 | DLL SM、LMSM 转态 | TP-UNIT-DLL-014、TP-SUB-PCS-010 |
| credit / ACK 观察 | 计数器与粒度，避免探内部 RAM | TP-SUB-DLL-006 |
| 复位 / CDC 控制 | 仅白名单 cell 的端口 | TP-UNIT-CDC-* |

钩子未进 SPEC 之前：依赖钩子的 TP 状态保持 **待定（钩子）**，TC 不得用 Force 抢跑（D13）。

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
| 状态 | **计划** / **RTL未就绪** / **待定** / **推迟**（D2） / **一期不做 D4** |

计数规则：矩阵中每一行 = 1 条测试点。「推迟」「一期不做 D4」计入总数，**不计入 D12 分母**，直到决定变更。

### 8.1 单元级 — PCS / LMSM

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-UNIT-PCS-001 | UB-PHY §3.3.1 | PAM4 Gray 编码叶模块：2-bit 符号映射 | 穷举 2-bit 与向量 | 与 Python Gray 表一致 | cp_gray_in | 后续 | 计划 |
| TP-UNIT-PCS-002 | UB-PHY §3.3.1 | Gray 解码为编码的逆 | 编码输出回灌 | 还原输入比特 | cp_gray_roundtrip | 后续 | 计划 |
| TP-UNIT-PCS-003 | UB-PHY §3.2.2.4 | 扰码：DLL 数据按 LSB→MSB 加扰 | 已知种子 + 定向/随机块 | 黄金 LFSR | cp_scram_seed | M1 | 计划 |
| TP-UNIT-PCS-004 | UB-PHY §3.2.3.2 | 解扰与扰码互逆 | 扰码输出回灌 | 还原明文 | cp_descram | M1 | 计划 |
| TP-UNIT-PCS-005 | UB-PHY §3.2.2.4 | AMCTL / EEIB 不扰；LTB 要扰 | 分类符号块（端口或钩子标类型） | 对照规则 | cp_scram_exempt | M1 | 待定（钩子） |
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
| TP-UNIT-PCS-018 | UB-PHY §3.2.2.2 | 双 codec 交织 | — | — | — | — | 一期不做 D4 |
| TP-UNIT-PCS-019 | UB-PHY §3.2.4 | eBCH-16 / AMCTL 结构叶 | 定向 AMCTL 场 | 编码与识别 | cp_amctl_enc | M1 | RTL未就绪 |
| TP-UNIT-PCS-020 | UB-PHY §3.3.2 | Precoding 叶 | — | — | — | — | 一期不做 D4 |
| TP-UNIT-PCS-021 | UB-PHY §3.4.3.1 | LMSM Link_Idle：未开训保持、开训离开 | start_train 端口 | 状态序 | cp_lmsm_idle | M1 | 计划 |
| TP-UNIT-PCS-022 | UB-PHY §3.4.3.2 | LMSM Probe：超时/完成进入下一态 | 可配超时 | 不卡死 | cp_lmsm_probe | M1 | 计划 |
| TP-UNIT-PCS-023 | UB-PHY §3.4.3.4–§3.4.3.7 | Discovery / Config / Send_NullBlock / Link_Active 强制转态 | LMB/AMCTL 端口激励 | 合法路径覆盖 | cx_lmsm_fwd | M1 | RTL未就绪 |
| TP-UNIT-PCS-024 | UB-PHY §3.4.3.8 | Retrain 入口（锁丢失 / 不可纠连锁） | 钩子或边界注错 | 进入 Retrain | cp_lmsm_retrain | M1 | 待定（钩子） |
| TP-UNIT-PCS-025 | UB-PHY §3.4.3.9–§3.4.3.10 | Change_Speed / Equalization 全流程 | — | — | — | 后续 | 一期不做 D4 |

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
| TP-UNIT-DLL-008 | UB-DL §4.2 | DLL SM：Disabled→Param_Init→Credit_Init→Normal | LinkUp 与 Init/Crd 握手 | 状态与 Status_Up/Down | cx_dll_sm | M1 | RTL未就绪 |
| TP-UNIT-DLL-009 | UB-DL §4.4、§4.3.3.9 | Init Block 强制场协商（粒度、VL 使能、独占） | 对端 Init | 取交集规则 | cp_init_neg | M1 | RTL未就绪 |
| TP-UNIT-DLL-010 | UB-DL §4.5 | VL ID 写入 LPH/LBH；同 VL 内 FCFS | 双 VL 交错（M1=2） | 顺序与 VL 场 | cp_vl | M1 | RTL未就绪 |
| TP-UNIT-DLL-011 | UB-DL §4.6.1.2 | Credit 独占：每 VL 独立计数 | 单 VL 耗尽 | 无 credit 停发 | cp_crd_ex | M1 | RTL未就绪 |
| TP-UNIT-DLL-012 | UB-DL §4.6.2 | 发送扣 credit、返回加回；1 flit/cell | 精确长度包 | 计数=黄金 | cp_crd_acc | M1 | RTL未就绪 |
| TP-UNIT-DLL-013 | UB-DL §4.6.3 | 返回粒度 32 cell（草案） | 积满再返 | 场粒度 | cp_crd_grain | M1 | 待定（D14） |
| TP-UNIT-DLL-014 | UB-DL §4.3.3.5、§4.6.1 | Crd_Ack 初始化与补充返回 | Credit_Init + Normal | 初值 640 cell/VL（草案） | cp_crdack | M1 | 待定（D14） |
| TP-UNIT-DLL-015 | UB-DL §4.6.1.3 | Credit 共享模式 | — | — | — | — | 一期不做 D4 |
| TP-UNIT-DLL-016 | UB-DL §4.5.1 | DLLCB 不耗 credit | 插 Null/NOP | credit 不变 | cp_cb_nocred | M1 | RTL未就绪 |
| TP-UNIT-DLL-017 | UB-DL §4.7.3.2 | Retry buffer 存发、ACK 释放 | 发包 + ACK | 占用/释放 | cp_retry_buf | M1 | RTL未就绪 |
| TP-UNIT-DLL-018 | UB-DL §4.7.3.3 | RETRY_REQ_SM | 钩子打坏 BCRC | 请求序 | cp_req_sm | M1 | RTL未就绪 |
| TP-UNIT-DLL-019 | UB-DL §4.7.3.4 | RETRY_ACK_SM | 对端 Retry_Req | Ack 序 | cp_ack_sm | M1 | RTL未就绪 |
| TP-UNIT-DLL-020 | UB-DL §4.7.3.2.4 | 防 lockout | 窗口打满 | 不永久卡死 | cp_lockout | M1 | RTL未就绪 |
| TP-UNIT-DLL-021 | UB-DL §4.3.2.3 | 非 CRC 封装模式 | — | — | — | — | 一期不做 D4 |

### 8.3 单元级 — 寄存器与 CDC

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-UNIT-CSR-001 | 附录 D.1–D.2 | CFG0_BASIC / CAP 强制可读身份 | CSR 读 | 场与 SPEC 一致（不在此复述位） | cp_cfg0 | M1 | RTL未就绪 |
| TP-UNIT-CSR-002 | 附录 D.3–D.4 | CFG1_BASIC / CAP 一期子集 | CSR 读写 | 只验强制场 | cp_cfg1 | M1 | RTL未就绪 |
| TP-UNIT-CSR-003 | 附录 D.5–D.6 | 端口 BASIC/CAP：lane、速率、FEC 草案默认 | 上电读 | 与 §3 草案一致 | cp_port_def | M1 | 待定（D14） |
| TP-UNIT-CSR-004 | 附录 D.7 | ROUTE_TABLE | — | — | — | — | 推迟 |
| TP-UNIT-CDC-001 | D6 | 异步复位同步器：异步断言、同步释放 | 复位口 | 释放对齐目的时钟 | cp_rstsync | M1 | RTL未就绪 |
| TP-UNIT-CDC-002 | D6 | 双拍同步器功能 | 单比特跨域 | 若干拍后稳定，无毛刺要求仅功能 | cp_sync2 | M1 | RTL未就绪 |
| TP-UNIT-CDC-003 | D6 | 异步 FIFO 水位与满空 | 两侧不同频 | 不丢不重、满停 | cp_afifo | M1 | RTL未就绪 |
| TP-UNIT-CDC-004 | D6 | 非白名单手写 SV 扫描（静态） | 源码/生成物扫描 | 仅白名单例外 | cp_whitelist | M1 | 计划 |

### 8.4 子系统级 — PCS / FEC / LMSM

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-SUB-PCS-001 | UB-PHY §3.2.2 | TX：扰码→FEC→（Gray）→8-bit 分发 | 网络 flit 块 | 边界符号=黄金链 | cp_txpath | M1 | 计划 |
| TP-SUB-PCS-002 | UB-PHY §3.2.3 | RX：解分发→FEC→解扰 | 黄金符号流 | 还原 flit | cp_rxpath | M1 | 计划 |
| TP-SUB-PCS-003 | UB-PHY §3.2.3.5 | 子系统环回无错 | D3 环回 | 端到端一致 | cp_fec_lb_clean | M1 | 计划 |
| TP-SUB-PCS-004 | UB-PHY §3.2.3.5 | 环回注入 ≤T 符号错，纠正后 DLL 无重传 | 边界注错 | 数据对、无 Retry_Req | cx_fec_t | M1 | 待定（钩子） |
| TP-SUB-PCS-005 | UB-PHY §3.2.3.5 | >T 失败上交 DLL 重传 | 边界注错 | fec_fail 与 retry 联动 | cp_fec_to_dll | M1 | 待定（钩子） |
| TP-SUB-PCS-006 | UB-PHY §3.2.2.1、§3.4.2.8 | 协商 T=2 / bypass | LMSM/LMB 场 | 编解码模式一致 | cp_fec_mode | M1 | RTL未就绪 |
| TP-SUB-PCS-007 | UB-PHY §3.2.4、§3.2.3.1 | AMCTL 周期插入、锁定、deskew | 环回加 lane 延迟 | 对齐后数据正确 | cx_amctl_skew | M1 | RTL未就绪 |
| TP-SUB-PCS-008 | UB-PHY §3.2.4.3 | AMCTL 不进 FEC、不扰码 | 观察边界 AMCTL | 与明文规则一致 | cp_amctl_raw | M1 | RTL未就绪 |
| TP-SUB-PCS-009 | UB-PHY §3.4.2.1–§3.4.2.2 | 端口类型与链路宽度协商 x1→x4 | LMB 交换 | 最终宽度 x4 | cp_width_neg | M1 | RTL未就绪 |
| TP-SUB-PCS-010 | UB-PHY §3.4.2.5 | 速率协商落到 Data Rate 0（草案） | LMB 能力交 | 工作速率=草案 | cp_rate0 | M1 | 待定（D14） |
| TP-SUB-PCS-011 | UB-PHY §3.4.3 | 训练走到 Link_Active 后才给 DLL LinkUp | 完整 LMSM | LinkUp 时序 | cp_linkup | M1 | RTL未就绪 |
| TP-SUB-PCS-012 | UB-PHY §3.1.1、§3.4.2.3 | TX/RX 宽度非对称、QDLWS | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-013 | UB-PHY §3.4.2.4 | 快速宽度降级 | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-014 | UB-PHY §3.4.2.6–§3.4.2.7 | 极性翻转 / lane reversal | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-015 | UB-PHY §3.2.6 | 数据通路低功耗 | — | — | — | — | 一期不做 D4 |
| TP-SUB-PCS-016 | UB-PHY §3.1.2 | PHY Mode-1 | — | — | — | — | 一期不做 D4 |

### 8.5 子系统级 — DLL

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-SUB-DLL-001 | UB-DL §4.3.2 | CRC 模式 DLLDP 端到端成帧/解帧 | 合法包长扫 | 网络口还原 | cp_dllp_crc | M1 | 计划 |
| TP-SUB-DLL-002 | UB-DL §4.3.3 | 强制 DLLCB：Null、NOP、Retry_*、Crd_Ack、Init、Lane_Manage | 各类型 | 解析与响应 | cx_dllcb_type | M1 | RTL未就绪 |
| TP-SUB-DLL-003 | UB-DL §4.4 | Param_Init 自动协商完成才进 Credit_Init | 对端 Init | SM + 参数镜像 | cp_param | M1 | RTL未就绪 |
| TP-SUB-DLL-004 | UB-DL §4.6.1 | Credit_Init 交换后才进 Normal | Crd_Ack | Status_Up | cp_crd_init | M1 | RTL未就绪 |
| TP-SUB-DLL-005 | UB-DL §4.6、§4.5 | 双 VL 调度：有 credit 才发；同 VL FCFS | 双 VL 竞争 | 不超发、顺序 | cx_vl_sched | M1 | RTL未就绪 |
| TP-SUB-DLL-006 | UB-DL §4.6.2 | 640 cell/VL（草案）打满回压 | 长burst | 停发/恢复 | cp_crd_sat | M1 | 待定（D14） |
| TP-SUB-DLL-007 | UB-DL §4.7 | BCRC 失败走 ACK/重传，最终有序交付 | 钩子打坏一块 | 黄金重传序列 | cp_retry | M1 | 待定（钩子） |
| TP-SUB-DLL-008 | UB-DL §4.7.3.5 | 重传过程与 retry buffer 释放 | 多包 + 错 | 缓冲不泄漏 | cp_retry_rel | M1 | RTL未就绪 |
| TP-SUB-DLL-009 | UB-DL §4.8.1 | credit 异常上报、不静默错账 | 非法返回 | 异常路径 | cp_ex_crd | M1 | RTL未就绪 |
| TP-SUB-DLL-010 | UB-DL §4.8.2 | 重传异常 | 超次/超时（RTT **待定**） | 上报 | cp_ex_retry | M1 | 待定（RTT） |
| TP-SUB-DLL-011 | UB-DL §4.8.3 | 错误 DLLDP 处理 | 坏 CFG/长度 | 丢弃规则 | cp_ex_dllp | M1 | RTL未就绪 |
| TP-SUB-DLL-012 | UB-DL §4.8.4、§4.2 | LinkUp=0 回 Disabled，上送 Status_Down | 拉倒 LinkUp | 丢弃上下行、停 CB | cp_linkdn | M1 | RTL未就绪 |
| TP-SUB-DLL-013 | UB-DL §4.3.3.8、UB-PHY §3.4.2.8 | Block 模式/FEC-CRC 协同切换 | LMSM 指示 | 两端模式一致 | cp_modechg | 后续 | RTL未就绪 |
| TP-SUB-DLL-014 | UB-DL §4.3.4.1 | 定界：SOP/EOP 与 DLLDB 边界 | 交错 CB/DP | 无粘连 | cp_delim | M1 | 计划 |
| TP-SUB-DLL-015 | UB-DL §4.7.1 | 重传触发模式（强制子集） | 注错 | 仅规定触发源 | cp_retry_trig | M1 | 待定（钩子） |

### 8.6 顶层（含 D3 环回）

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-TOP-001 | UB-PHY §3.2、UB-DL §4.3 | TX↔RX 环回冒烟：短包 | 网络口发包 | 还原、无 UVM_ERROR | cp_smoke | M1 | 计划 |
| TP-TOP-002 | 同上 | 1 flit 与 512 flit 边界包 | 极端长度 | 完整还原 | cx_top_len | M1 | 计划 |
| TP-TOP-003 | UB-PHY §3.4、UB-DL §4.2 | 训练 + DLL 初始化到 Normal 后才跑数据 | LMSM+DLL 全序 | 训练期无业务包 | cp_bringup | M1 | RTL未就绪 |
| TP-TOP-004 | UB-DL §4.6、§4.7 | 环回上 credit + 重传同时在线 | 双 VL + 注错 | 有序、不超 credit | cx_top_qos | M1 | RTL未就绪 |
| TP-TOP-005 | D13 | 仅经钩子/边界注错，禁止 Force | 钩子清单 | 错误被检出 | cp_hook_only | M1 | 待定（钩子） |
| TP-TOP-006 | UB-PHY §3.2.5 | x4、32 bit/lane（草案）环回 | 四 lane | 分发/对齐 | cp_x4 | M1 | 待定（D14） |
| TP-TOP-007 | UB-PHY §3.1.1 | 参数化 x8 | 编译参数 | 同分发规则 | cp_x8 | 后续 | 计划 |
| TP-TOP-008 | D6 | 顶层同步复位：释放后安静再训练 | 复位口 | 无 X 泄漏到检查窗 | cp_top_rst | M1 | 计划 |
| TP-TOP-009 | D6 | 多时钟功能（若生成物有跨域） | 相位扫 | 不丢包 | cp_top_cdc | M1 | RTL未就绪 |
| TP-TOP-010 | D8 | `randomize()` 流量，日志写 seed | 多种子 | scoreboard 0 mismatch | cp_rand | M1 | 计划 |
| TP-TOP-011 | UB-DL §4.3 | 网络口反压 | 拉低 ready | 无丢、无重 | cp_bp | M1 | 计划 |
| TP-TOP-012 | D7 | 同一 TC 在 Icarus 与 Verilator 结果一致 | 双仿 | 比对 PASS 行 | cp_dualsim | M1 | 计划 |
| TP-TOP-013 | D3 | 环回 BFM 可配 deskew，超过规范窗则失败 | 扫延迟 | 窗内过、窗外失败 | cp_skew_win | M1 | RTL未就绪 |
| TP-TOP-014 | D11 | FPGA 板级 | — | — | — | — | 一期不做 D11 |

### 8.7 推迟占位（D2）

| ID | 规范 | 描述 | 激励 | 检查 | 覆盖 | 里程碑 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TP-DEF-NW-001 | UB-NW §5.2 | NTH 解析 / 改写 | — | — | — | — | 推迟 |
| TP-DEF-NW-002 | UB-NW §5.3 | 路由、隔离、QoS、拥塞标记、ICRC | — | — | — | — | 推迟 |
| TP-DEF-TP-001 | UB-TP §6.2–§6.4 | RTP/CTP/UTP 与传输重传 | — | — | — | — | 推迟 |
| TP-DEF-TP-002 | UB-TP §6.5–§6.6 | 多路径与拥塞控制 | — | — | — | — | 推迟 |
| TP-DEF-TA-001 | UB-TA §7.2–§7.4 | 事务头与事务类型 | — | — | — | — | 推迟 |
| TP-DEF-UP-001 | 第 8–11 章 | FUN/MEM/RSC/SEC | — | — | — | — | 推迟 |

---

## 9. 覆盖率门限与豁免（D12）

门限**已由 D12 钉死**，本计划不再写「待 PM/船长定」。

| 项 | 门限 | 说明 |
| --- | --- | --- |
| 行覆盖 | **计入具名豁免后 100%** | 源：Verilator 5.032。未测到的死代码必须逐条豁免 |
| 功能覆盖 | **计入具名豁免后 100%** | 分母 = 状态为「计划 / RTL未就绪 / 待定」且里程碑 M1 的 TP；「推迟」「一期不做 D4」「后续」不进分母 |
| Toggle | **不算** | 不采集、不验收 |

豁免必须**具名**：编号、层次/文件或 TP ID、理由、批准人、日期。无批准人的条目不算豁免、计为缺口。

参考（旧项目习惯，已被 D12 吸收，不是另一套门限）：行覆盖常先做到 ≥95% 再把剩余写成豁免；功能覆盖本身就要 100%（豁免计入）。本期直接按 D12 的 100%（含豁免）验收。

---

## 10. 门限与记账

### 10.1 PASS / FAIL / SKIP

沿用 Switch `report.py` + `summarize.sh` 行协议，写入 `reports/regress/<tc>.log`：

| 结果 | 判定 | 是否算绿 |
| --- | --- | --- |
| **PASS** | 仿真退出 0、无 UVM_ERROR、无 Python 异常、日志有 `PASS <tc>`、scoreboard 0 mismatch | 是 |
| **FAIL** | 期望/实际不符、UVM_ERROR、traceback、非 0 退出；日志写 `FAIL` 及 stimulus / expected / actual / seed / 复现命令 | 否 |
| **SKIP** | 具名原因：工具缺口、RTL 未就绪、D14 未批、钩子未进 SPEC、D4/D2 排除。**不记 PASS、不记 FAIL** | 不进连续绿的分子，必须出现在 SKIP 账本 |

禁止：用 Force 让 Icarus 单独 PASS；把「未实现」写成 PASS；把工具 SKIP 当覆盖达成。

### 10.2 连续绿

同时满足才算连续绿：

1. Icarus 12.0：所有未 SKIP 的 M1 TC 为 PASS。
2. Verilator 5.032：所有未 SKIP 的 M1 TC 为 PASS（新 TC 不得再因 Force 进入工具 SKIP 表）。
3. D12：行 + 功能在计入已批准豁免后为 100%。
4. 无新增未记账 FAIL。

### 10.3 报告与 seed

| 路径 | 内容 |
| --- | --- |
| `reports/regress/*.log` | 每 TC 一份；**必须含 seed=** |
| `reports/regress/summary.txt` | `summarize.sh` 汇总 PASS/FAIL/SKIP 行数 |
| `reports/regress/skip.md` | SKIP 账本：TC、原因、对应决定/缺陷 |
| `reports/regress/waiver.md` | D12 具名豁免 |
| `reports/regress/cov_line/` | Verilator 行覆盖 |
| `reports/regress/cov_func/` | 测试点矩阵达成表 + CoverPoint 导出 |

随机 TC 每次运行打印 `SEED <n>`；复现命令必须带同一 seed。

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
   └─ 根因在工具           → SKIP 记账 + 基础设施，不放行 Force
```

约束：

- 验证 **不修改** `rtl/`、SPEC、`DECISIONS.md`、`SPEC_INDEX.md`。
- 给设计的失败单至少含：TP ID、规范章节号、复现命令、seed、期望、实际、是否双仿复现。
- 规范争议只引用章节号，不粘贴规范原文。

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

| 项 | 状态 | 谁 |
| --- | --- | --- |
| §3 全部默认参数 | 草案 / D14 | 船长批 Xia |
| RTT、训练/重传超时的周期数 | 待定 | Xia 提案，船长批 |
| 测试钩子端口清单 | 待定 | 验证提需求，写入 Xia SPEC |
| ASIC 工艺与核频 | 未知 | 不影响功能门，影响后续时序 |
| pyc4.0 生成物未齐 | 大量 TP = RTL未就绪 | 按模块交付打开 TC |
| `TOOLCHAIN.lock` | 未落 | 基础设施 PR（D16） |
| 手写 `rtl/` `tb/` 迁 `legacy/` | 未做 | 另 PR（D10） |
| git 历史中的规范全文 | D15 改写未做 | 船长；验证不依赖公开树正文 |

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

- **M1 功能分母（D12）**：里程碑 = M1，且状态 ∈ {计划, RTL未就绪, 待定（钩子/D14/RTT）}。
- **后续**：里程碑 = 后续，且不是「一期不做 / 推迟」（更高速率、x8、Gray/PAM4 等）。
- **推迟**：状态 = 推迟（D2）。
- **一期不做**：状态 = 一期不做 D4 或 一期不做 D11。

| 层 | 总行 | M1（D12 分母） | 后续 | 推迟 | 一期不做 |
| --- | --- | --- | --- | --- | --- |
| 单元 PCS/LMSM | 25 | 19 | 3 | 0 | 3（皆 D4） |
| 单元 DLL | 21 | 19 | 0 | 0 | 2（皆 D4） |
| 单元 CSR/CDC | 8 | 7 | 0 | 1 | 0 |
| 子系统 PCS | 16 | 11 | 0 | 0 | 5（皆 D4） |
| 子系统 DLL | 15 | 14 | 1 | 0 | 0 |
| 顶层 | 14 | 12 | 1 | 0 | 1（D11） |
| 推迟占位 NW/TP/TA | 6 | 0 | 0 | 6 | 0 |
| **合计** | **105** | **82** | **5** | **7** | **11** |

82 + 5 + 7 + 11 = 105。

M1 分母中的「RTL未就绪 / 待定」未实现前记 SKIP，不算 PASS，也不算功能覆盖达成。后续里程碑留在矩阵里，便于参数打开后改里程碑并纳入分母。

---

## 14. 待定项清单（计划执行用）

1. D14：船长确认 §3 全部草案参数（速率、lane、FEC 默认、VL=2、256 flit 重传、credit 640/粒度 32/独占、SerDes 32b）。
2. RTT 与各类超时的时钟周期假设。
3. Xia SPEC（另 PR）中的测试钩子章节：名称、方向、复位值、是否仿真专用。
4. 附录 D 一期寄存器强制场子集的最终清单。
5. 对端是「第二 DUT」还是「轻量 BFM」的顶层默认。
6. 核频未定导致的仿真时间单位（功能上可配，不阻 M1）。
7. D16 `TOOLCHAIN.lock` 尚未存在；以 D7 为准。
8. D10 `legacy/` 迁移未做；官方门不跑手写 `tb/*.v`。
9. 钩子未定义前，所有「待定（钩子）」TP 不得用 Force 抢跑（D13）。

---

## 15. 本草案不包含的工作

- 不改 `rtl/`、`tb/`、SPEC、`DECISIONS.md`、`SPEC_INDEX.md`、其它文档。
- 不拷贝 Switch TB 代码。
- 不自合本 PR。
- 不新增 `TOOLCHAIN.lock`（D16）。
- 不发明测试钩子时序（等 Xia SPEC）。
