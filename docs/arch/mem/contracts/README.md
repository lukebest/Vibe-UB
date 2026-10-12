# C 线私有解码叶子 — 公开信号契约

| 项 | 值 |
| --- | --- |
| 作者 | 架构 Xia |
| 日期 | 2026-10-12 |
| 状态 | 草案 |
| 规范 | UB Base Spec Rev 2.0（D1 / D20 第 9 条）第 9 章 |
| 裁定 | 船长 2026-10-12：D20，C 线 S-01 = (b)；本目录接口补丁见下「Xia 裁定 2026-10-12」 |
| 工艺代理 | Sky130（D20 第 4 条） |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；每个私有叶子内部不做 CDC |

本目录是 C 线私有解码叶子的 **公开信号契约**。每个私有叶子一份 Markdown，文件名等于叶子名。公开仓库为每个私有叶子提交 **只含端口的桩**；位布局 YAML、生成器、参考拆包和字段级向量放在独立的私有仓库。本目录与上层接口文件（`docs/arch/mem/UARCH.md` §5、本契约、后续桩端口）是结构叶子与验证可以依赖的公开面。

本仓库对私有侧一律称「独立私有仓库」。

---

## 1. 契约规则

1. **公开面只写字段级语义。** 每个端口给出名字、方向、宽度、含义。含义写到解码后的语义（有效、许可、页基址 / PA、页粒度类别、属性 / 内存类型、非法配置标志与原因码）。原始表项作为一根输入总线可以写宽度（桩口可见）。
2. **原始表项内部怎么切字段，只存在于私有叶子源。** 公开契约、桩、上层接口、`CHANGELOG`、评语都保持这一边界。
3. **时钟与复位** 与 [CODING_STYLE.md](../../../CODING_STYLE.md) §2 / SPEC §4.2 一致：单时钟 `core_clk`；业务寄存器同步复位，叶子只接 `rst_pyc`。目标周期 12.412 ns（SPEC §4.1 `F_CORE` 80.57 MHz），估计走 Sky130 代理。每个私有叶子内部不做 CDC。**Xia 裁定 2026-10-12。**
4. **握手** 与 SPEC §3.1 一致：同一拍 `valid==1 && ready==1` 成交；`valid==1` 期间数据与边带保持到成交；`ready` 不组合依赖本拍 `valid`。时序在各叶子文件写清：组合 0 拍，或寄存 N 拍，并给出延迟上界。
5. **首轮不支持的配置**（D20 第 6 条）：2 MB 映射粒度、硬件写回 Access / Dirty。叶子给出 §3 共用非法原因码，且 `*_illegal == (*_ill_cause != 0)`。**Xia 裁定 2026-10-12。**
6. **复位值** 写在各叶子文件。寄存输出在 `rst_pyc` 有效期间为 0。
7. **断言** 是接口级、自然语言性质，带稳定名字。公开桩的行为模型与私有叶子都要满足同一组性质。
8. **规范没有裁定的事项** 写「未知」，放在各文件末尾短列表。依赖 D-05 译码器格式的项写入 §5「暂缓」表。本目录不补猜测值。
9. **门禁 `private-leaf-attest`（随 D20 落地）。** 私有侧 CI 产出 `attest/<leaf>.yml`，公开 PR 把它拷进 `reports/private/`。门禁核对 sha256 一致，并检查：**桩、本目录契约、上层接口文件** 相对被证明的公开提交到 PR 头保持不变。改契约或上层接口需要新的证明。

---

## 2. 私有叶子清单

来源：`docs/arch/mem/UARCH.md` §3 / §5（类型「解码」）；`docs/SPEC.md` C 线 §10.5（`mem_tlb_w*` / `mem_dec_*` 登记，第 9 章正文仍 deferred）；仓库内无 `private_leaves.yml`；PR #27 `ub_mem_tlb` 填充口吃的是已经解码的 `fill_pfn` / `fill_attr` / `fill_ap` / `fill_uxn` / `fill_pxn` / `fill_af`，TLB 回填路径上的页表描述符解码叶子是 `ub_mem_ptw_desc_dec`。

D20 S-01 (b) 覆盖 C 线表项位布局。UARCH 把每一种规范表项做成独立解码叶子，本目录按 §5 六片全部立约。

| 叶子 | 父级例化点 | 契约 | 原始表项（桩口可见宽度） |
| --- | --- | --- | --- |
| `ub_mem_ptw_desc_dec` | `ub_mem_ptw`（TLB 回填 / 页表遍历） | [ub_mem_ptw_desc_dec.md](ub_mem_ptw_desc_dec.md) | 64（一次 8 B 描述符读） |
| `ub_mem_dec_ent_dec` | `ub_mem_decoder`（接 `ub_mem_dec_walk`；第一波 L0 在内存） | [ub_mem_dec_ent_dec.md](ub_mem_dec_ent_dec.md) | L0 大项 512；L1 见 §5 暂缓 |
| `ub_mem_tecte_dec` | `ub_mem_cfg_lkup`（CSR 写 TECT） | [ub_mem_tecte_dec.md](ub_mem_tecte_dec.md) | **未知** |
| `ub_mem_tcte_dec` | `ub_mem_ctx_lkup`（TCT 缓存填充） | [ub_mem_tcte_dec.md](ub_mem_tcte_dec.md) | 512（一次 64 B 读） |
| `ub_mem_l1tct_dec` | `ub_mem_ctx_lkup`（两级 TCT） | [ub_mem_l1tct_dec.md](ub_mem_l1tct_dec.md) | 64（一次 8 B 读） |
| `ub_mem_mapte_dec` | `ub_mem_perm_walk` / `ub_mem_plb` | [ub_mem_mapte_dec.md](ub_mem_mapte_dec.md) | 256（一次 32 B 读；最终宽度见 §6 未知） |

结构叶子（`ub_mem_tlb`、`ub_mem_ptw`、`ub_mem_dec_walk` 等）只认本目录与 UARCH §5 的具名信号。

---

## 3. 共用非法原因编码

**Xia 裁定 2026-10-12。** 六片叶子共用同一套 4 bit `*_ill_cause`。`cfg_ill_cause` 与 `l1tct_ill_cause` 加宽到 `[3:0]`。`*_illegal == (*_ill_cause != 0)`。

| 码 | 符号 | 含义 |
| --- | --- | --- |
| 0 | `ILL_NONE` | 无非法；`*_illegal=0` |
| 1 | `ILL_MAP_2MB` | 原始表项要求 2 MB 映射粒度（首轮，D20） |
| 2 | `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty（首轮，D20） |
| 3 | `ILL_RSVD` | 保留编码 |
| 4 | `ILL_PTR_OOB` | 指针高位越界 |
| 5 | `ILL_STALL` | Stall 配置（首轮） |
| 6 | `ILL_ENDIAN` | 首轮不支持的字节序 |
| 7 | `ILL_MAC` | MAC 模式（首轮） |
| 8 | `ILL_MAPT_MULTI_BLK` | 多块 MAPT（首轮） |
| 9 | `ILL_MAPT_OTHER_BLK` | 下一级在其他块（首轮） |
| 10 | `ILL_S2` | Stage 2 开启（首轮） |
| 11 | `ILL_UNSUP` | 其余首轮不支持、且已折成非法的合法编码 |
| 12–15 | 保留 | 叶子不得产出 |

各叶子文件引用本表，不再各自编号。

---

## 4. Xia 裁定 2026-10-12（接口补丁）

下列六条对六片叶子同时生效。各叶子文件用同一标记引用。

1. **共用 4 bit 非法码。** 见 §3。`*_illegal == (*_ill_cause != 0)`。
2. **非法拍清零。** `*_illegal=1` 的同一 `out_valid` 拍，该叶子其余解码输出为 0。该拍只有 `*_illegal` 与 `*_ill_cause` 携带信息。
3. **原因优先级。** 配置非法（`ILL_MAP_2MB`、`ILL_HW_AD`）先于翻译故障（例如 AF=0）报告。多个非法原因同时成立时，取最小非 0 码。PTW 路径：描述符 `AF=0` 且需要硬件写回 Access / Dirty → 报 `ILL_HW_AD`；`AF=0` 且不要求硬件写回 → `illegal=0`，`desc_af=0`，由遍历器按普通 AF 故障处理。
4. **`desc_kind[1:0]`。** 0 = invalid，1 = table，2 = block，3 = page。
5. **`out_ready`。** 每片叶子保留该口。第一波遍历器可以把 `out_ready` Tied 为 1。叶子在 `out_valid && !out_ready` 期间保持 `out_valid` 与全部输出稳定。各叶子接口断言 `AP_<LEAF>_OUT_HOLD` 写明本条。
6. **复位撤销后的 `in_ready`。** SPEC §3.1 原文：「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。本目录按下列规则：复位撤销后的第一拍 `in_ready` 可以为 0；从第二拍起，在输出侧未停（`out_ready=1` 或本拍无未决输出）时 `in_ready=1`。
7. **L0 组合预算。** `ub_mem_dec_ent_dec` 的 L0 路径 `comb_budget_ns: 5.0`（12.412 ns 周期内、输入到输出的最大延迟；周期余量留给其前的存储器读出通路与其后的遍历器寄存器建立时间）。L1 路径仍为寄存 1 拍。**Xia 裁定 2026-10-12。**

---

## 5. 暂缓：随 D-05 译码器表项格式 PR 关闭

**Xia 裁定 2026-10-12。** 下列项依赖项目自定的译码器表项格式，等 D-05 PR 关闭。

| 项 | 出现位置 |
| --- | --- |
| 译码器 L0 PTE / L0 范围项 / L1 PTE 格式与宽度（含 `dent_rng_last` 是否写入格式、L1 原始表项宽度、是否与 L0 共用 512 bit `raw`） | `ub_mem_dec_ent_dec` |
| `dent_l1_base`、`dent_attr` 最终宽度 | `ub_mem_dec_ent_dec` |
| `_eid128` 变体是否出、何时出（D-06） | `ub_mem_dec_ent_dec` |
| 范围比较放在本叶子还是下游结构叶子 | `ub_mem_dec_ent_dec` |
| L1 TCT / 译码器格式能否编码 2 MB 映射 | `ub_mem_l1tct_dec`、`ub_mem_dec_ent_dec` |

---

## 6. 未知（待 Xia 另裁）

纯规范宽度 / 体系结构项，本批保持「未知」：

- `ub_mem_tecte_dec` 的 `raw` 宽度
- `ub_mem_mapte_dec` 的 `raw` 最终宽度（单项 / 多级是否恒为 256）
- `ub_mem_mapte_dec` 的 `lvl` 宽度与合法范围
- `ctx_mapt_bb_sz` 表示 2 MB 的对数值
- 1 GB 块描述符是否出现、出现时的原因码

---

## 7. 与上层文档的关系

- 具名信号束的字段名与位宽以 [UARCH.md](../UARCH.md) §5 为底稿；本目录补握手口、原始表项口、D20 要求的非法口，以及接口断言。`cfg_ill_cause` / `l1tct_ill_cause` 按本目录加宽到 4 bit。
- 本目录冻结的是 **公开语义**。UARCH 仍标草案、端口未冻；改契约走新证明（§1 第 9 条）。
- 验证测试点见 `docs/VERIF_PLAN.md` §8.8（`TP-UNIT-MEM-072`–`079`、`TP-UNIT-DEC-017`–`018`）。结构叶子的 TB 只打本契约端口。

---

## 8. YAML 机读头

每份叶子契约文件以一个 ` ```yaml ` 围栏块开头，供后续门禁脚本解析；围栏之后的 Markdown 给人对读。本仓库本批只写契约，不增加检查脚本。

固定键：

| 键 | 类型 | 含义 |
| --- | --- | --- |
| `leaf` | 字符串 | 叶子名，与文件名一致 |
| `parent` | 字符串 | 父级例化点（主实例名） |
| `clock` | 对象 | `{name: core_clk, period_ns: 12.412, reset: rst_pyc, reset_type: sync}` |
| `latency` | 对象 | `{kind: registered \| combinational, cycles: <int>, max_cycles: <int>}`。记录第一波主路径 |
| `comb_budget_ns` | 数 | 仅 `kind: combinational` 出现。`ub_mem_dec_ent_dec` L0 = `5.0`（Xia 裁定 2026-10-12） |
| `ports` | 列表 | 每项 `{name, dir, width, desc}`。`dir` 为 `in` / `out`。`width` 为整数、参数表达式（如 `EID_W`）、或 `unknown`（§6 未关的规范宽度） |
| `params` | 列表 | 每项 `{name, default}`；无参数时为 `[]` |
| `ill_cause_width` | 整数 | 恒为 `4` |
| `status` | 字符串 | 恒为 `draft` |

`ub_mem_dec_ent_dec` 的 YAML `latency` 写 L0 组合路径；L1 寄存 1 拍只出现在正文。`clock` / `rst_pyc` 同时列入 `ports`。`desc` 写字段级语义，不含原始表项内部切分。
