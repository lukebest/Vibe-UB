# 实现规则库 — 合入前快速综合（Sky130 proxy）

| 项 | 值 |
| --- | --- |
| 分册 | `docs/rules/impl_quick_synth.md` |
| 所有者 | 后端实现 |
| 版本 | v0.1 (2026-10-10) |
| 类别 | 合入前快速综合的面积 / 时序反馈（proxy，非签核） |
| 配套 | [backend.md](backend.md)、[TEAM.md](../TEAM.md)、[PROCESS.md](../PROCESS.md)、[SPEC.md](../SPEC.md) |
| 脚本 | `scripts/impl/quick_synth.sh` |

规则条目格式：ID / 规则 / 来源 / 日期。

本分册写清 **量什么、不算什么、谁判 pass/fail**。工艺节点在 PR #9 §13 由 Luke 决定之前，综合用 SkyWater Sky130 `sky130_fd_sc_hd` **tt_025C_1v80** 作 proxy，数字只用于趋势，不是产品签核。

---

## 角色

| 角色 | 职责 |
| --- | --- |
| 后端实现 | 跑快速综合，向设计反馈面积 / 时序趋势；维护本分册与脚本 |
| 验证 / 工具守门 | **唯一** 合入 pass/fail 门禁（lint / 仿真 / 后续 CDC、formal） |
| 设计 | 看趋势、决定是否改 RTL；本报告不阻塞 merge |
| PM | 把报告当信息，不把 proxy WNS 当合入条件 |

快速综合 **informational only**。本脚本失败、slack 为负、或面积变大，都 **不** 单独否决 PR。验证门禁才判合入。

---

## 量什么

脚本对每个叶子 top（默认：相对 `main` 的 diff 里 `rtl/` 下被改到的叶子；可用 `--tops` 覆盖）做：

1. **网表变体**
   - 默认 PRODUCT（`TEST_HOOKS=0`）：`rtl/<block>/<module>.v` 或白名单 `.sv`。
   - 若 PR 带 HOOKS 网表（`rtl/<block>/hooks/<module>.v`），另报一列。生成期展开，Verilog 里无 `` `ifdef ``。
2. **Yosys**
   - `read_verilog`（`.sv` 加 `-sv`）。
   - 需要 OPEN 参数才能有意义地elaborate 的叶子：只在 Yosys 命令行 `chparam` 传入 **标明的 placeholder**（例如加扰 `SCR_TAPS` / `SEED_MAP` / `LFSR_INIT`）。不得把 placeholder 写进 RTL。
   - `synth -top <m> -flatten`。
   - `dfflibmap` + `abc -liberty` 映到 Sky130 hd tt。
   - `stat -liberty`：mapped **cell 数**、**面积 um²**、**flop 数**（`df*` / `edf*` / `sdf*`）。
   - 另记 `hierarchy; proc; opt; stat` 的 generic cell 数，便于和设计侧 Yosys `proc; opt; stat` 对拍。
   - `ltp`：与工艺无关的最长拓扑路径长度（sanity）。
3. **OpenSTA**（或 OpenROAD 的 `sta`）
   - 单时钟，SDC 名 **`core_clk`**。模块口若叫 `clk` 等，映射到该名。
   - 周期取 [SPEC.md](../SPEC.md) 已写的目标频率（M1：`F_CORE` ≈ 80.57 MHz，§4.1 / §9，`2.578125e9/32` → **12.412121212 ns**）。SPEC **未**写频率时用 **500 MHz（2.0 ns）** 并标明 `placeholder`。
   - 输入 / 输出 0 delay、ideal；不加 wire-load（只用 liberty 默认）。
   - 最差建立路径：**逻辑深度（cell levels）**、**data arrival (ns)**、**该周期下 slack**。
   - 纯组合叶子：虚时钟约束 I/O，arrival 为组合延迟。
4. **相对 main 的趋势**
   - main 上已有同名模块：对 main 同脚本再跑一列，报 delta。
   - 新模块：delta = `new`。
5. **工具与 liberty 出处**
   - 报告写死 Yosys / OpenSTA 版本，以及 liberty 的来源 URL / commit。PDK **不进仓库**；脚本下载或读 `SKY130_HD_LIB`。

不报、不算签核的：

- 顶层 WNS / TNS、多 corner、SI、CTS、布线后、IR drop。
- 产品工艺的绝对面积或频率收敛（工艺未定，见 PR #9 §13）。
- 全芯片 floorplan / 利用率。

---

## 异常（只标旗，不门禁）

| 现象 | 为何标 |
| --- | --- |
| latch | 业务应用同步 `pyc_reg`；latch 通常是推断错误 |
| 推断 memory 未落到 flop | 叶子不该默默长出 RAM |
| 组合环 | SPEC 禁止 ready 组合看本拍 valid 等；环是功能风险 |
| 逻辑深度明显吃不进周期 | proxy 下 slack < 0，给设计看，不是签核 fail |
| undriven / unused 把逻辑优掉，细胞数接近 0 | 口没接上或参数全 0 把 LFSR 折没了 |
| 叶子面积异常大 | 相对同批叶子或相对 main 数量级不对 |

加扰等 OPEN 参数：能用 labeled placeholder `chparam` 就跑；否则记 `skipped: required params pending §13`，写清缺的参数。

---

## 规则条目

| ID | 规则 | 来源 | 日期 |
| --- | --- | --- | --- |
| IMP-QS-001 | 合入前快速综合用 Sky130 hd tt_025C_1v80 作 proxy，直到 Luke 在 PR #9 §13 定工艺；数字是趋势，不是签核 | 本分册；SPEC §8 / §9 工艺未知 | 2026-10-10 |
| IMP-QS-002 | 本报告 informational；合入 pass/fail 归验证门禁，快速综合不单独 block merge | PROCESS §2；TEAM 工具守门 | 2026-10-10 |
| IMP-QS-003 | 不报顶层 WNS/TNS；只报叶子最差建立路径（深度、arrival、slack @ SPEC `F_CORE`） | 本分册 | 2026-10-10 |
| IMP-QS-004 | 默认 PRODUCT 网表；PR 若带 HOOKS 变体则另报，不把 HOOKS 面积当产品面积 | SPEC §11 | 2026-10-10 |
| IMP-QS-005 | OPEN 参数只许 Yosys 命令行 placeholder，或 skip 并写 §13；不得改 RTL / pycircuit 填默认 | SPEC §13；设计 OPEN 约定 | 2026-10-10 |

---

## 怎么跑

```
scripts/impl/quick_synth.sh --ref <git-ref> --out reports/impl/quick_synth/<run>
# 或
scripts/impl/quick_synth.sh --work-tree . --tops ub_lmsm --out /tmp/qs
```

环境变量 `SKY130_HD_LIB` 指向已下载的 `sky130_fd_sc_hd__tt_025C_1v80.lib`。未设置时脚本从 OpenROAD-flow-scripts 的对应路径拉取（commit 写进报告），缓存到 `~/.cache/vibe-ub/sky130/`。
