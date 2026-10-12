# C 线私有解码叶子 — 公开信号契约

| 项 | 值 |
| --- | --- |
| 作者 | 架构 Xia |
| 日期 | 2026-10-12 |
| 状态 | 草案 |
| 规范 | UB Base Spec Rev 2.0（D1 / D20 第 9 条）第 9 章 |
| 裁定 | 船长 2026-10-12：D20，C 线 S-01 = (b) |
| 工艺代理 | Sky130（D20 第 4 条） |

本目录是 C 线私有解码叶子的 **公开信号契约**。每个私有叶子一份 Markdown，文件名等于叶子名。公开仓库为每个私有叶子提交 **只含端口的桩**；位布局 YAML、生成器、参考拆包和字段级向量放在独立的私有仓库。本目录与上层接口文件（`docs/arch/mem/UARCH.md` §5、本契约、后续桩端口）是结构叶子与验证可以依赖的公开面。

本仓库对私有侧一律称「独立私有仓库」。

---

## 1. 契约规则

1. **公开面只写字段级语义。** 每个端口给出名字、方向、宽度、含义。含义写到解码后的语义（有效、许可、页基址 / PA、页粒度类别、属性 / 内存类型、非法配置标志与原因码）。原始表项作为一根输入总线可以写宽度（桩口可见）。
2. **原始表项内部怎么切字段，只存在于私有叶子源。** 公开契约、桩、上层接口、`CHANGELOG`、评语都保持这一边界。
3. **时钟与复位** 与 [CODING_STYLE.md](../../../CODING_STYLE.md) §2 / SPEC §4.2 一致：单时钟 `core_clk`；业务寄存器同步复位，叶子只接 `rst_pyc`。
4. **握手** 与 SPEC §3.1 一致：同一拍 `valid==1 && ready==1` 成交；`valid==1` 期间数据与边带保持到成交；`ready` 不组合依赖本拍 `valid`。时序在各叶子文件写清：组合 0 拍，或寄存 N 拍，并给出延迟上界。
5. **首轮不支持的配置**（D20 第 6 条）：2 MB 映射粒度、硬件写回 Access / Dirty。叶子拉高已定义的非法输出，并给出已定义的原因码。原因码用符号名列出；符号到数值的编码 **未知**（见各文件 §未知）。
6. **复位值** 写在各叶子文件。寄存输出在 `rst_pyc` 有效期间为 0。
7. **断言** 是接口级、自然语言性质，带稳定名字。公开桩的行为模型与私有叶子都要满足同一组性质。
8. **规范没有裁定的事项** 写「未知」，放在各文件末尾短列表。本目录不补猜测值。
9. **门禁 `private-leaf-attest`（随 D20 落地）。** 私有侧 CI 产出 `attest/<leaf>.yml`，公开 PR 把它拷进 `reports/private/`。门禁核对 sha256 一致，并检查：**桩、本目录契约、上层接口文件** 相对被证明的公开提交到 PR 头保持不变。改契约或上层接口需要新的证明。

---

## 2. 私有叶子清单

来源：`docs/arch/mem/UARCH.md` §3 / §5（类型「解码」）；`docs/SPEC.md` C 线 §10.5（`mem_tlb_w*` / `mem_dec_*` 登记，第 9 章正文仍 deferred）；仓库内无 `private_leaves.yml`；PR #27 `ub_mem_tlb` 填充口吃的是已经解码的 `fill_pfn` / `fill_attr` / `fill_ap` / `fill_uxn` / `fill_pxn` / `fill_af`，TLB 回填路径上的页表描述符解码叶子是 `ub_mem_ptw_desc_dec`。

D20 S-01 (b) 覆盖 C 线表项位布局。UARCH 把每一种规范表项做成独立解码叶子，本目录按 §5 六片全部立约。

| 叶子 | 父级例化点 | 契约 | 原始表项（桩口可见宽度） |
| --- | --- | --- | --- |
| `ub_mem_ptw_desc_dec` | `ub_mem_ptw`（TLB 回填 / 页表遍历） | [ub_mem_ptw_desc_dec.md](ub_mem_ptw_desc_dec.md) | 64（一次 8 B 描述符读） |
| `ub_mem_dec_ent_dec` | `ub_mem_decoder`（接 `ub_mem_dec_walk`；第一波 L0 在内存） | [ub_mem_dec_ent_dec.md](ub_mem_dec_ent_dec.md) | L0 大项 512；L1 **未知** |
| `ub_mem_tecte_dec` | `ub_mem_cfg_lkup`（CSR 写 TECT） | [ub_mem_tecte_dec.md](ub_mem_tecte_dec.md) | **未知** |
| `ub_mem_tcte_dec` | `ub_mem_ctx_lkup`（TCT 缓存填充） | [ub_mem_tcte_dec.md](ub_mem_tcte_dec.md) | 512（一次 64 B 读） |
| `ub_mem_l1tct_dec` | `ub_mem_ctx_lkup`（两级 TCT） | [ub_mem_l1tct_dec.md](ub_mem_l1tct_dec.md) | 64（一次 8 B 读） |
| `ub_mem_mapte_dec` | `ub_mem_perm_walk` / `ub_mem_plb` | [ub_mem_mapte_dec.md](ub_mem_mapte_dec.md) | 256（一次 32 B 读） |

结构叶子（`ub_mem_tlb`、`ub_mem_ptw`、`ub_mem_dec_walk` 等）只认本目录与 UARCH §5 的具名信号。

---

## 3. 共用非法原因符号

各叶子的 `*_ill_cause` 使用下表符号名。同一符号在不同叶子里的数值编码彼此独立，编码值 **未知**。

| 符号 | 含义 |
| --- | --- |
| `ILL_NONE` | 无非法；此时对应 `*_illegal=0` |
| `ILL_MAP_2MB` | 原始表项要求 2 MB 映射粒度（首轮，D20） |
| `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty（首轮，D20） |
| `ILL_RSVD` | 保留编码 |
| `ILL_PTR_OOB` | 指针高位越界 |
| `ILL_STALL` | Stall 配置（首轮） |
| `ILL_ENDIAN` | 首轮不支持的字节序 |
| `ILL_MAC` | MAC 模式（首轮） |
| `ILL_MAPT_MULTI_BLK` | 多块 MAPT（首轮） |
| `ILL_MAPT_OTHER_BLK` | 下一级在其他块（首轮） |
| `ILL_S2` | Stage 2 开启（首轮） |
| `ILL_UNSUP` | 其余首轮不支持、且已折成非法的合法编码 |

`ILL_MAP_2MB` 与 `ILL_HW_AD` 在每一片契约里都有效：原始表项一旦带上这两种配置，叶子必须拉高非法输出并给出对应符号。

---

## 4. 与上层文档的关系

- 具名信号束的字段名与位宽以 [UARCH.md](../UARCH.md) §5 为底稿；本目录补握手口、原始表项口、D20 要求的非法口，以及接口断言。
- 本目录冻结的是 **公开语义**。UARCH 仍标草案、端口未冻；改契约走新证明（§1 第 9 条）。
- 验证测试点见 `docs/VERIF_PLAN.md` §8.8（`TP-UNIT-MEM-072`–`079`、`TP-UNIT-DEC-017`–`018`）。结构叶子的 TB 只打本契约端口。
