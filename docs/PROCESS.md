# 开发流程

| 项 | 值 |
| --- | --- |
| 文档 | `docs/PROCESS.md` |
| 决定 | [DECISIONS.md](DECISIONS.md) D17（Luke Liu via Firstmate，2026-10-10 16:48 Asia/Shanghai） |
| 配套分工 | [TEAM.md](TEAM.md) |
| 规则库 | [rules/](rules/)（v0.1 起，PM 每周打版本） |

本文件写节拍、流水线、REGMAP 流向、规则库、复盘指标与过渡安排。角色与所有权见 [TEAM.md](TEAM.md)。

---

## 1. 每模块节拍

每个模块走同一节拍：

1. **规格冻结**：接口契约 + Python 参考模型 + 接口断言齐备（架构师 Xia 交付）。
2. **设计与验证并行**：各自独立的 AI 会话；共享 SPEC、接口契约和断言；规格疑问统一问 Xia，答案写回 SPEC。
3. **工具流水线闭环**：每次提交跑 lint、CDC、formal、快速综合，结果回给 AI 迭代。
4. **高风险评审**：规格变更、接口契约、测试点清单、CDC、复位方案、时钟门控、时序约束、检查豁免（见 [TEAM.md](TEAM.md) §5）。
5. **合入**：PM 把关并 squash-merge；各团队把 main merge 进分支。

后端（实现）在每个模块合入前跑快速综合，向设计反馈面积 / 时序趋势。

---

## 2. 工具流水线

每次提交自动跑：

| 检查 | 目的 |
| --- | --- |
| lint | 网表风格与静态错误（现有门禁口径见 [CODING_STYLE.md](CODING_STYLE.md) §7） |
| CDC | 跨时钟路径 |
| formal | 等价与关键断言 |
| 快速综合 | 面积 / 时序趋势，供设计迭代 |

工具守门（验证负责人兼任）定检查规则、批准豁免。豁免书面记录，格式为 ID / 检查项 / 模块 / 理由 / 批准人 / 日期；清单文件 `docs/WAIVERS.md` 为后续（FUTURE）。现有具名 waiver 实践见 [CODING_STYLE.md](CODING_STYLE.md) §7（如 `CRD_UF`）。

流水线实现列为待办，由后续独立 PR 完成；本文件只定流程。

---

## 3. REGMAP 单一来源

`docs/regmap/regmap.yaml` 为单一来源（single source）。`docs/REGMAP.md` 由生成器写出，禁止手改。下游固件与验证共用同一份生成代码。约定见 [regmap/README.md](regmap/README.md)。

| 下游 | 路径 | 用途 |
| --- | --- | --- |
| (a) pyCircuit 寄存器读写逻辑 | `rtl/csr/ub_csr_regs.py` | 设计侧 CSR 实现 |
| (b) uvm-python 寄存器模型 | `gen/tb_ral/ub_regmodel.py`（PR #6 `tb/` 未合入前；日后迁 `tb/ral/`） | 验证侧 |
| (c) 固件驱动 | `sw/include/ub_regs.h`、`sw/hal/ub_regs_access.{h,c}` | 原型固件的寄存器访问层 |
| (d) Python 常量 | `model/regs.py` | 验证 / 模型共用 |

```bash
python3 scripts/gen_regmap.py          # 再生
python3 scripts/gen_regmap.py --check  # 与已提交产物 diff，漂移则非 0
```

---

## 4. 规则库结构与每周版本

规则库分块维护，骨架在 `docs/rules/`：

| 分册 | 维护者 | 类别 |
| --- | --- | --- |
| [architect.md](rules/architect.md) | Xia | 协议与接口规则 |
| [design.md](rules/design.md) | 设计 | 编码规范、复位风格、pyCircuit 用法 |
| [verification.md](rules/verification.md) | 验证 | 测试规范 |
| [backend.md](rules/backend.md) | 后端 | 约束与综合相关的坑 |

PM 每周汇总并打版本号（v0.1 起，本批骨架日期 2026-10-10）。每个后期 bug 的复盘至少产出一条规则。

规则条目格式（各分册沿用）：ID / 规则 / 来源（bug 复盘或评审） / 日期。

---

## 5. 每周复盘指标

每周一次复盘：看指标、更新规则库、调整下周人 / AI 分工。

采集：

| 指标 | 统计维度 | 用途 |
| --- | --- | --- |
| 首轮通过率、迭代轮数 | 按模块类型 | 某类模块首轮通过率持续偏低时，拆更小、补例子，或改由人写 |
| 规格问答次数 | 按模块 | 某模块规格问答多时，架构师补表格、时序图或参考模型 |
| 后期 bug 来源 | 规格缺陷 / 设计错误 / 验证漏测 | 分别回到架构师 / 设计 / 验证的规则库 |
| 逃逸 bug | AI 写模块 vs 人写模块 | 决定哪类模块扩大 AI 比重 |

---

## 6. PHY 先行

先在物理层（PHY / PCS / LMSM）跑通这套流程，积累规则和例子，再进入链路层（DLL）。PHY 阶段范围见 D2 / D3 / D14：PCS + DLL + LMSM + 寄存器 / CDC；PMA 为行为模型。模块边界清晰、标准模块多，适合先把节拍、守门和复盘跑顺。

---

## 7. 过渡安排

文档落地、现有工作继续推进；实现类改动走后续独立 PR。

- 当前 open PR #6（`tb/models` 中的 golden models，由验证编写，base 为 `cursor/docs-m1-architecture-b2d2`）合入后，这些参考模型的所有权转给架构师 Xia；验证继续负责把它们接入 scoreboard。
- Open PR #5、#6、#7（以及 #9）按现行规则继续推进。
- 工具流水线（每次提交 lint / CDC / formal / 快速综合）与 REGMAP 自动生成器尚未实现，列为待办，由后续独立 PR 完成；本 PR 只定流程。

产品 RTL 继续按 D5 / D6 用 pyCircuit 生成、同步复位。验证继续按 D7 / D13 使用 uvm-python + cocotb，经端口或 test hook 注入。一期原型固件消费 REGMAP 生成的驱动与寄存器访问层（D11）。
