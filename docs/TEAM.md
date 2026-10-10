# 团队分工

| 项 | 值 |
| --- | --- |
| 文档 | `docs/TEAM.md` |
| 决定 | [DECISIONS.md](DECISIONS.md) D17（Luke Liu via Firstmate，2026-10-10 16:48 Asia/Shanghai） |
| 配套流程 | [PROCESS.md](PROCESS.md) |
| 规则库 | [rules/architect.md](rules/architect.md)、[rules/design.md](rules/design.md)、[rules/verification.md](rules/verification.md)、[rules/backend.md](rules/backend.md) |

团队按信息流组织：架构师交付可执行规格；设计与验证从同一份规格各自出发、会话隔离；工具流水线自动守门；人把评审集中在高代价区；规则库分块维护、PM 汇总；每周用指标复盘。

最值钱的产出按交付物管理：规格、参考模型、规则库、例子库。角色交接一律用低歧义载体（机器可读寄存器表、时序图、Python 参考模型、断言），文字补背景。人把时间放在协议状态机、仲裁、反压、CDC、出错处理；偶然部分交给 AI。写 RTL 的一方与写检查器的一方共享规格。lint / 仿真 / formal / 快速综合组成自动流水线，每次提交都跑，结果直接回给 AI。

---

## 1. 角色表

「人/AI 比重」是起步建议，用每周复盘指标按模块类型校准（见 [PROCESS.md](PROCESS.md) §5）。

| 角色 | 人负责 | AI 负责 | 人/AI 比重 | 交出的东西 |
| --- | --- | --- | --- | --- |
| PM | 排期、交接物质量把关、主持复盘、规则库汇总 | 整理进度、汇总指标看板 | 人为主 | 指标看板、规则库版本 |
| 架构师 Xia | 定 SPEC 和 REGMAP、定接口契约、写参考模型和接口断言的核心逻辑 | 挑规格漏洞、补全参考模型代码、生成时序图 | 人为主 | 可执行规格：SPEC + 机器可读 REGMAP + Python 参考模型 + 接口断言 |
| 设计 | 本质部分的微架构、CDC/复位方案、高风险模块实现 | 用 pyCircuit 写偶然部分和标准模块、按反馈迭代 | AI 写大部分代码，人定关键结构 | pyCircuit 源码、生成的 Verilog、模块内部断言 |
| 验证 | VERIF_PLAN、测试点清单、覆盖率目标、失败归因 | uvm-python/cocotb 组件骨架、测试序列、日志初筛 | AI 写大部分代码，人定测什么 | 测试平台、覆盖率报告 |
| 工具守门 | 定检查规则、批准豁免 | 每次提交自动跑 lint、CDC、formal、快速综合 | AI/脚本为主 | 每次提交的检查报告 |
| 原型固件 | 上板调试策略 | 从 REGMAP 生成驱动和寄存器访问层、自检程序 | AI 为主 | 驱动、自检程序 |
| 后端实现 | 时序约束、物理决策 | 解析报告、写流程脚本、提约束修改建议 | 人为主 | 约束文件、时序/面积报告 |

---

## 2. 所有权

| 交付物 | 所有者 | 说明 |
| --- | --- | --- |
| `docs/SPEC.md`、`docs/REGMAP.md` | 架构师 Xia | 可执行规格与机器可读寄存器表 |
| Python 参考模型（golden reference models） | 架构师 Xia | 设计与验证共用的、独立于 RTL 的标准答案 |
| 接口断言（interface assertions） | 架构师 Xia | 同上，与参考模型一起构成接口契约 |
| pyCircuit 源码、生成 Verilog、模块内部断言 | 设计 | 产品 RTL 由 pyCircuit 生成（D5） |
| `docs/VERIF_PLAN.md`、测试点清单、覆盖率目标、TB | 验证 | 验证负责把参考模型接入 scoreboard，并补端到端测试点 |
| 检查规则、豁免清单（waiver list） | 工具守门（验证负责人兼任） | 见 §4 |
| 约束文件、时序/面积报告 | 后端实现 | 每模块合入前快速综合，向设计反馈趋势 |
| 驱动、寄存器访问层、自检程序 | 原型固件 | 消费 REGMAP 生成代码 |
| 指标看板、规则库版本号 | PM | 每周汇总，版本从 v0.1 起 |

架构师 Xia 除 `docs/SPEC.md`、`docs/REGMAP.md` 外，还负责 Python 参考模型与接口断言。

---

## 3. 角色接口

| 从 | 到 | 交接物 |
| --- | --- | --- |
| 架构师 Xia | 设计、验证 | SPEC、REGMAP、接口契约、Python 参考模型、接口断言 |
| 设计 | 工具守门、后端 | pyCircuit 源码、生成 Verilog、模块内部断言 |
| 验证 | 工具守门、PM | 测试平台、覆盖率报告、失败归因 |
| 设计 / 验证 | 架构师 Xia | 规格疑问；Xia 作答并写回 SPEC |
| 工具守门 | 设计、验证、AI | 每次提交的 lint / CDC / formal / 快速综合报告 |
| 后端实现 | 设计 | 面积 / 时序趋势（每模块合入前快速综合） |
| REGMAP 生成器 | 设计、验证、原型固件 | pyCircuit 寄存器读写逻辑、cocotb/uvm-python 寄存器模型、固件驱动（同一份生成代码） |
| PM | 全员 | 排期、指标看板、规则库版本 |

设计与验证互相独立工作，使用各自独立的 AI 会话。双方共享 SPEC、接口契约和断言。所有规格疑问统一问 Xia，答案写回 SPEC。

---

## 4. 工具守门与豁免

新增「工具守门（tool gatekeeper）」职责，暂由验证（负责人）兼任：每次提交自动跑 lint、CDC、formal、快速综合。规模变大后再设专人。本文件只定职责，CI 配置由后续独立 PR 落地。

任何检查豁免（waiver）都需要守门人书面批准，并记录在豁免清单（waiver list）中。

| 项 | 约定 |
| --- | --- |
| 清单落点 | `docs/WAIVERS.md` 为后续文件（FUTURE）；落地前条目仍按下列格式书面记录，并由守门人批准 |
| 条目格式 | ID / 检查项 / 模块 / 理由 / 批准人 / 日期 |
| 现有实践 | [CODING_STYLE.md](CODING_STYLE.md) §7 具名 waiver（如 `WAIVER_CRD_UF_CNT`、`WAIVER_CRD_UF_IRQ`）；覆盖率豁免见 [VERIF_PLAN.md](VERIF_PLAN.md) §9 |

人工评审覆盖每一条豁免；其余检查以工具结果为准。

---

## 5. 人工评审重点

人把时间集中在：

- 规格变更
- 接口契约
- 测试点清单
- CDC
- 复位方案
- 时钟门控
- 时序约束
- 检查豁免

其余模块以工具结果为准，人抽查。

---

## 6. 项目约束（与 D5–D13 对齐）

- 产品 RTL 用 pyCircuit（pyc4.0 fork `lukebest/pyCircuit`，D5）生成可综合 Verilog；业务逻辑同步复位，手写单元走白名单（D6）。
- 验证使用 uvm-python（tpoikela/uvm-python，经 fork `lukebest/uvm-python`）跑在 cocotb 上（D7）。
- TB 经端口或显式 test hook 注入与观察（D13）。
- 所有代码改动经 Cursor cloud agent 完成；PM 把关并 squash-merge PR；各团队把 main merge 进分支。
- PHY 阶段范围见 D2 / D3 / D14：PCS + DLL + LMSM + 寄存器 / CDC；PMA 为行为模型。
- 一期按 D11：原型固件消费 REGMAP 生成的驱动与寄存器访问层；上板调试留到后续阶段。
