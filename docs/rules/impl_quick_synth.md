# 实现规则库 — 合入前快速综合（Sky130 proxy）

| 项 | 值 |
| --- | --- |
| 分册 | `docs/rules/impl_quick_synth.md` |
| 所有者 | 后端实现 |
| 版本 | v0.4 (2026-10-10) |
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

脚本对每个叶子 top 做（默认：相对 `main` 的 diff 里 `rtl/<block>/*.v` 被改到的文件；HOOKS 文件改到则同一 stem 也进表；可用 `--tops` 覆盖）：

1. **网表变体（SPEC §2.2）**
   - 每个文件一个 top：模块名 = 文件名。pycc 不发 Verilog `parameter`；参数集是固定网表 `<leaf>_<tag>`（例：`rtl/pcs/ub_pcs_lane_dist_x4.v` / `_x8` / `_vl2`）。只有一套参数的叶子无 tag。
   - PRODUCT：`rtl/<block>/<leaf>_<tag>.v`（白名单 `.sv` 同样）。
   - HOOKS：同名，放 `rtl/<block>/hooks/`，作次行。生成期展开，Verilog 里无 `` `ifdef ``。
   - `_placeholder` 变体（用占位值生成、仅 lint / TB）进 **单独表**，**不计入 PRODUCT 面积合计**。
   - 待删除遗留：`ub_dll_crc32`、`ub_dll_crc_check`、`ub_controller_tx`、`ub_controller_rx` 只进 **「待删除 / to be deleted」** 行，**不综合、不进合计、不对 baseline**。
   - 任何 `pyc_*` 模块是库单元（`rtl/pyc_lib/`），不是报告 top。
   - **不**再默认 `chparam`。`--chparam KEY=VAL` / `TOP:KEY=VAL` 只作可选覆盖（模块里若已无该 parameter 则跳过并注明）。
2. **Yosys**
   - `read_verilog`（`.sv` 加 `-sv`）。默认 **`-I rtl/pyc_lib`**（pycc runtime 原语，如 `pyc_reg.v`，从 TOOLCHAIN.lock 钉住的 pyCircuit 原样拷入）。`--incdir` / 环境变量 `QS_INCDIRS` 可再加目录。
   - `rtl/pyc_lib/` 尚未落地时（#21 / #5 之前）**回退 `-I rtl/common`**，报告里打一行 `WARN`；临时，定库目录后去掉回退。
   - 不把 `` `include `` 目标再列进 `QS_FILES`（否则 `pyc_reg` 会重定义）。
   - 大 SRAM 用 `read_verilog -lib` 作黑盒。
   - `synth -top <m> -flatten`。
   - `dfflibmap` + `abc -liberty` 映到 Sky130 hd tt。
   - **高扇出缓冲（默认开）**：abc 映射之后、STA 之前，对非时钟 / 非复位网插 `sky130_fd_sc_hd__buf_4` / `buf_8` 树，使每个驱动点扇出 ≤ **16**（`--max-fanout`）。OpenROAD 若在 PATH 里可用 `repair_design`，本脚本仍走确定性 Yosys 树（proxy 无 floorplan；OpenROAD 未装）。`--no-buffer` 关掉，便于对照。每叶子报告 **max fanout**（缓冲后；notes 里带 before→after 与插入 buf 数）。
   - `stat -liberty`：mapped **cell 数**、**面积 um²**、**flop 数**（`df*` / `edf*` / `sdf*`）。黑盒 SRAM 实例从 cell 数里扣掉。缓冲后的 buf 计入 cell / 面积。
   - 另记 `hierarchy; proc; opt; stat` 的 generic cell 数，便于和设计侧 Yosys `proc; opt; stat` 对拍。
   - `ltp`：与工艺无关的最长拓扑路径长度（sanity）。
3. **OpenSTA**（或 OpenROAD 的 `sta`）
   - 单时钟，SDC 名 **`core_clk`**。模块口若叫 `clk` 等，映射到该名。
   - 周期取 [SPEC.md](../SPEC.md) 已写的目标频率（M1：`F_CORE` ≈ 80.57 MHz，§4.1 / §9，`2.578125e9/32` → **12.412121212 ns**）。SPEC **未**写频率时用 **500 MHz（2.0 ns）** 并标明 `placeholder`。
   - 输入 / 输出 0 delay、ideal；不加 wire-load（只用 liberty 默认）。
   - 最差建立路径：**max comb logic depth（cell levels）**、**data arrival (ns)**、**该周期下 slack**。
   - 纯组合叶子：虚时钟约束 I/O，arrival 为组合延迟。
   - 黑盒 `ub_cmn_mem_1r1w`：STA stub 把 **rdata 建成 1 拍 registered read**（每 bit 一只 `sky130_fd_sc_hd__dfxtp_1`，D 接 0），下游 compare / select 从该 launch 计时。存储本身不建模。
4. **相对 baseline 的趋势**
   - `--baseline-report`（旧 markdown 表）或 `--baseline-json`。
   - 同名叶子对同名 + 同 variant（HOOKS 优先对 HOOKS，否则 PRODUCT）。
   - 迁移后的 tag 可用 `--baseline-map NEW=OLD[:VARIANT]`。无显式 map 时启发式：`_x4` → 旧模块 `PRODUCT`（历史上 `NUM_LANES=4`），`_x8` → `PRODUCT_NUM_LANES=8`，BCRC 等无 tag 的同名对 PRODUCT。例：`ub_pcs_lane_dist_x4` vs 报告 `2026-10-10_PR5_6875f611` 的 `ub_pcs_lane_dist` PRODUCT。
   - 新模块：delta = `new`。
   - **QoR >10%**：cells / area / max comb logic depth / slack 任一相对 baseline 的 `|Δ| / |baseline| > 10%` 则标旗（0 vs 0 不标；baseline 为 0 且新值非 0 则标）。只标旗，不门禁。
5. **SRAM 估算列（estimate，不是宏）**
   - 共享存储原语：`ub_cmn_mem_1r1w`（pycc `pycircuit/cmn/`，网表 `rtl/cmn/`，变体按 §2.2 命名）。若存在 `scripts/gate/blackbox.yml`，其中列出的模块同样参加判断。
   - `depth × width >` **`--sram-bit-threshold`（默认 4096，环境变量 `QS_SRAM_BIT_THRESHOLD`）**：综合作黑盒，面积走 **SRAM est** 列，不进 stdcell 面积。
   - 不超过阈值：当普通 flop 综合进 mapped 面积。
   - 公式（**估算，不是 foundry 宏**）：

     `est_um² = N_inst × depth × width × 0.5 µm²/bit × 1.35`

     - `0.5 µm²/bit`：SkyWater 130nm 6T bit 的数量级（公开 HD bit 约 0.3–0.5 µm²）。
     - `1.35`：译码 / sense-amp / I/O 周边（教材常见 25–50%）。
     - 工艺未定（PR #9 §13）前用此 proxy；**定节点后重看阈值与公式**。
   - PRODUCT 面积合计只加非 `_placeholder`、非待删除的 PRODUCT 行的 liberty stdcell；SRAM est 另报一列、另合计。HOOKS 不进 PRODUCT 合计。
6. **工具与 liberty 出处**
   - 报告写死 Yosys / OpenSTA 版本，以及 liberty 的来源 URL / commit。PDK **不进仓库**；脚本下载或读 `SKY130_HD_LIB`。

不报、不算签核的：

- 顶层 WNS / TNS、多 corner、SI、CTS、布线后、IR drop。
- 产品工艺的绝对面积或频率收敛（工艺未定，见 PR #9 §13）。
- 全芯片 floorplan / 利用率。
- SRAM 估算列（不是宏编译器结果）。

---

## 异常（只标旗，不门禁）

| 现象 | 为何标 |
| --- | --- |
| latch | 业务应用同步 `pyc_reg`；latch 通常是推断错误 |
| 推断 memory 未落到 flop | 叶子不该默默长出 RAM（黑盒 `ub_cmn_mem_1r1w` 除外） |
| 组合环 | SPEC 禁止 ready 组合看本拍 valid 等；环是功能风险 |
| 逻辑深度明显吃不进周期 | proxy 下 slack < 0，给设计看，不是签核 fail |
| undriven / unused 把逻辑优掉，细胞数接近 0 | 口没接上或逻辑被折没了 |
| 叶子面积异常大 | 相对同批叶子或相对 baseline 数量级不对 |
| QoR 相对 baseline 超 10% | cells / area / depth / slack 趋势异常，给设计看 |

OPEN §13 参数已按 §2.2 做成 `_placeholder` 固定网表时：综合进 placeholder 表，不 skip。不再用命令行 placeholder `chparam` 当必经路径。

---

## 规则条目

| ID | 规则 | 来源 | 日期 |
| --- | --- | --- | --- |
| IMP-QS-001 | 合入前快速综合用 Sky130 hd tt_025C_1v80 作 proxy，直到 Luke 在 PR #9 §13 定工艺；数字是趋势，不是签核 | 本分册；SPEC §8 / §9 工艺未知 | 2026-10-10 |
| IMP-QS-002 | 本报告 informational；合入 pass/fail 归验证门禁，快速综合不单独 block merge | PROCESS §2；TEAM 工具守门 | 2026-10-10 |
| IMP-QS-003 | 不报顶层 WNS/TNS；只报叶子最差建立路径（max comb logic depth、arrival、slack @ SPEC `F_CORE`） | 本分册 | 2026-10-10 |
| IMP-QS-004 | 默认 PRODUCT 网表；PR 若带 HOOKS 变体则另报，不把 HOOKS 面积当产品面积 | SPEC §11 | 2026-10-10 |
| IMP-QS-005 | SPEC §2.2 固定网表：每文件一个 top，无必经 `chparam`。`--chparam` 仅为可选覆盖，不得改 RTL / pycircuit 填默认 | SPEC §2.2 / §13 | 2026-10-10 |
| IMP-QS-006 | `_placeholder` 变体单独列表，不计入 PRODUCT 面积合计 | SPEC §2.2 | 2026-10-10 |
| IMP-QS-007 | 可用 `--baseline-map` 把迁移后的 `<leaf>_<tag>` 对到旧模块+参数；cells / area / depth / slack 相对 baseline 超 10% 标旗 | 本分册 | 2026-10-10 |
| IMP-QS-008 | `ub_cmn_mem_1r1w`（及 `scripts/gate/blackbox.yml` 中的模块）depth×width 超过可配阈值（默认 4096 bit）作黑盒，SRAM est 列用标明的 bit 面积公式；小实例按 flop 综合；STA 按 1 拍 registered read。阈值与公式在工艺确定后重看 | 本分册；PR #9 §13 | 2026-10-10 |
| IMP-QS-009 | Yosys 默认 `-I rtl/pyc_lib`（TOOLCHAIN.lock 钉住的 pyCircuit 原语）。目录未到时回退 `rtl/common` 并 WARN。`--incdir` / `QS_INCDIRS` 为额外路径。`pyc_*` 不作报告 top | 本分册；#21 / #5 | 2026-10-10 |
| IMP-QS-010 | `ub_dll_crc32` / `ub_dll_crc_check` / `ub_controller_tx` / `ub_controller_rx` 只报「待删除 / to be deleted」，不进合计、不对 baseline | 本分册 | 2026-10-10 |
| IMP-QS-011 | abc 映射后默认对高扇出数据网插确定性 `buf_4`/`buf_8` 树（max fanout 16）。`--no-buffer` 可关。每叶子报告缓冲后 max fanout。时钟 / 复位网不插。这是 proxy，用来避免无 wire-load 时单 cell 灌数千 load 的悲观 WNS | 本分册 | 2026-10-10 |

---

## 怎么跑

```
scripts/impl/quick_synth.sh --ref <git-ref> --out reports/impl/quick_synth/<run>
# 或
scripts/impl/quick_synth.sh --work-tree . --tops ub_lmsm --out /tmp/qs

# 对照旧报告（例：x4 对 PR #5 的 NUM_LANES=4）
scripts/impl/quick_synth.sh --ref <git-ref> --out /tmp/qs \
  --baseline-report reports/impl/quick_synth/2026-10-10_PR5_6875f611.md \
  --baseline-map ub_pcs_lane_dist_x4=ub_pcs_lane_dist:PRODUCT \
  --baseline-map ub_pcs_lane_dist_x8=ub_pcs_lane_dist:PRODUCT_NUM_LANES=8

# 可选 chparam 覆盖（默认不需要）
scripts/impl/quick_synth.sh --work-tree . --tops ub_foo --chparam NUM_LANES=4 --out /tmp/qs

# 额外 include（默认已有 -I rtl/pyc_lib）
scripts/impl/quick_synth.sh --work-tree . --incdir /tmp/extra --out /tmp/qs

# 对照：关掉扇出缓冲（默认 ON）
scripts/impl/quick_synth.sh --work-tree . --tops ub_foo --no-buffer --out /tmp/qs-nobuf

scripts/impl/quick_synth.sh --self-check
```

环境变量 `SKY130_HD_LIB` 指向已下载的 `sky130_fd_sc_hd__tt_025C_1v80.lib`。未设置时脚本从 OpenROAD-flow-scripts 的对应路径拉取（commit 写进报告），缓存到 `~/.cache/vibe-ub/sky130/`。

`scripts/gate/blackbox.yml` 若存在，接受：

```yaml
modules:
  - ub_cmn_mem_1r1w
  - name: other_mem
    depth: 512
    width: 16
```

列出的名字及其 §2.2 带 tag 变体参加 bit 阈值判断。文件不存在则只认 `ub_cmn_mem_1r1w*`。
