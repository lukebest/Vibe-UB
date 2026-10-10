# 验证规则库

| 项 | 值 |
| --- | --- |
| 分册 | `docs/rules/verification.md` |
| 所有者 | 验证 |
| 版本 | v0.1 (2026-10-10) |
| 类别 | 测试规范 |
| 配套 | [TEAM.md](../TEAM.md)、[PROCESS.md](../PROCESS.md)、[VERIF_PLAN.md](../VERIF_PLAN.md)、[DECISIONS.md](../DECISIONS.md) |

规则条目格式：ID / 规则 / 来源（bug 复盘或评审） / 日期。

PM 每周汇总打版本。每个后期 bug 复盘至少产出一条规则。验证漏测类后期 bug 回到本分册。

---

## 测试规范

| ID | 规则 | 来源 | 日期 |
| --- | --- | --- | --- |
| VER-TB-001 | TB 经端口或显式 test hook 注入与观察 | D13；[CODING_STYLE.md](../CODING_STYLE.md) §4 | 2026-10-10 |
