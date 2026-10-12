```yaml
leaf: ub_mem_dec_ent_dec
parent: ub_mem_dec_walk
clock:
  name: core_clk
  period_ns: 12.412
  reset: rst_pyc
  reset_type: sync
latency:
  kind: registered
  cycles: 1
  max_cycles: 1
ports:
  - {name: core_clk, dir: in, width: 1, desc: 单时钟}
  - {name: rst_pyc, dir: in, width: 1, desc: 同步复位，pyc_reg 原生极性}
  - {name: in_valid, dir: in, width: 1, desc: 原始大项本拍有效}
  - {name: in_ready, dir: out, width: 1, desc: 本拍可收下原始大项}
  - {name: raw, dir: in, width: 512, desc: L0 原始大项 64 B；L1 宽度见暂缓}
  - {name: src_l1, dir: in, width: 1, desc: 1 为本拍 L1 表项}
  - {name: pte_sel, dir: in, width: 3, desc: L0 页表项大项内选中下标}
  - {name: out_valid, dir: out, width: 1, desc: 解码结果本拍有效}
  - {name: out_ready, dir: in, width: 1, desc: 下游可收下结果}
  - {name: dent_is_range, dir: out, width: 1, desc: 本大项是范围项}
  - {name: dent_pte_v, dir: out, width: 1, desc: 选中的页表项有效}
  - {name: dent_rng_v, dir: out, width: 1, desc: 范围项有效}
  - {name: dent_rng_base, dir: out, width: 15, desc: 范围起点}
  - {name: dent_rng_limit, dir: out, width: 15, desc: 范围终点（闭区间）}
  - {name: dent_rng_last, dir: out, width: 1, desc: 范围项本身是最后一级}
  - {name: dent_l1_base, dir: out, width: 36, desc: L1 表基址（4 KB 对齐；最终宽度暂缓）}
  - {name: dent_eid, dir: out, width: EID_W, desc: 目标 EID}
  - {name: dent_token_id, dir: out, width: 20, desc: TokenID}
  - {name: dent_token_value, dir: out, width: 32, desc: TokenValue}
  - {name: dent_uba_base, dir: out, width: 52, desc: UBA 基值}
  - {name: dent_attr, dir: out, width: 8, desc: 其它相关属性 / 内存类型（最终宽度暂缓）}
  - {name: dent_illegal, dir: out, width: 1, desc: 配置非法，等于 dent_ill_cause != 0}
  - {name: dent_ill_cause, dir: out, width: 4, desc: 共用非法原因码}
params:
  - {name: EID_W, default: 20}
ill_cause_width: 4
status: draft
```

# 公开信号契约 — `ub_mem_dec_ent_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_dec_ent_dec` |
| 父级例化点 | `ub_mem_dec_walk`（C-D1：L0 表在内存，片上 `ub_mem_dec_l0` 已撤）。输入为遍历器已寄存的存储器读回；L0 与 L1 共用 |
| 规范 | UB Base Spec Rev 2.0 §9.5.1；译码器表项格式由项目自定（D20 第 8 条） |
| 微架构 | [UARCH.md](../UARCH.md) §5.5、§6.4 |
| 裁定 | D20 S-01 (b)；接口补丁见 [README.md](README.md) §4（Xia 裁定 2026-10-12） |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；本叶子内部不做 CDC。**Xia 裁定 2026-10-12。** |

User 侧译码器表项解码叶子。L0 PTE、L0 范围项、L1 PTE 共用。C-D1 之后 L0 与 L1 都是寄存 1 拍；输入为 `ub_mem_dec_walk` 已寄存的存储器读回。**Xia 裁定 2026-10-12。**

---

## 1. 时钟与复位

| 端口 | 方向 | 宽度 | 含义 |
| --- | --- | --- | --- |
| `core_clk` | in | 1 | 单时钟，≈80.57 MHz，目标周期 12.412 ns（SPEC §4.1） |
| `rst_pyc` | in | 1 | `pyc_reg` 原生极性；业务寄存器同步复位（CODING_STYLE §2） |

---

## 2. 端口

| 端口 | 方向 | 宽度 | 含义 |
| --- | --- | --- | --- |
| `in_valid` | in | 1 | 原始大项本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始大项 |
| `raw` | in | 512 | L0 原始大项（64 B）。L1 原始宽度见 §7 暂缓 |
| `src_l1` | in | 1 | 1 = 本拍是 L1 表项；0 = L0 大项 |
| `pte_sel` | in | 3 | 在 L0 页表项大项里选中第几条页表项 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | 下游结构逻辑可收下结果。第一波可以把本口 Tied 为 1。**Xia 裁定 2026-10-12。** |
| `dent_is_range` | out | 1 | 本大项是范围项。为 0 时按页表项组处理 |
| `dent_pte_v` | out | 1 | 选中的页表项有效 |
| `dent_rng_v` | out | 1 | 范围项有效 |
| `dent_rng_base` | out | 15 | 范围起点（与主机 PA 的范围键比较，比较位置见 §7 暂缓） |
| `dent_rng_limit` | out | 15 | 范围终点（闭区间，UARCH Q-A14 口径） |
| `dent_rng_last` | out | 1 | 范围项本身是最后一级（Xia 提案，D-05） |
| `dent_l1_base` | out | 36 | L1 表基址（4 KB 对齐后的地址；最终宽度见 §7 暂缓） |
| `dent_eid` | out | `EID_W` | 目标 EID。第一波 `EID_W=20` |
| `dent_token_id` | out | 20 | TokenID |
| `dent_token_value` | out | 32 | TokenValue |
| `dent_uba_base` | out | 52 | UBA 基值（§9.5.2；与 PA 低位相加在 `ub_mem_dec_uba`） |
| `dent_attr` | out | 8 | 其它相关属性 / 内存类型（最终宽度见 §7 暂缓） |
| `dent_illegal` | out | 1 | 配置非法；`dent_illegal == (dent_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `dent_ill_cause` | out | 4 | 非法原因，编码见 [README.md](README.md) §3 |

`dent_eid` + `dent_token_id` + `dent_token_value` + `dent_uba_base` + `dent_attr` 组成译码结果束。第一波 `EID_W=20` 时结果束 132 bit。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- L0 与 L1 预算 **R**：输入为遍历器已寄存的存储器读回。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。与其余五片解码叶子相同。**Xia 裁定 2026-10-12（C-D1）。**
- `in_valid==1` 且 `in_ready==0` 时，`raw` / `src_l1` / `pte_sel` 保持。
- `out_valid==1` 且 `out_ready==0` 时，`out_valid` 与全部输出保持。叶子兑现反压。**Xia 裁定 2026-10-12。**
- 复位撤销后的 `in_ready`：SPEC §3.1「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。按 Xia 裁定 2026-10-12：撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。

---

## 4. 非法 / 不支持配置

原因码与数值见 [README.md](README.md) §3。本叶子会用到的符号：`ILL_NONE`、`ILL_MAP_2MB`、`ILL_HW_AD`、`ILL_RSVD`、`ILL_PTR_OOB`、`ILL_UNSUP`。

**Xia 裁定 2026-10-12：** `dent_illegal=1` 的同一 `out_valid` 拍，其余解码输出为 0。该拍只有 `dent_illegal` 与 `dent_ill_cause` 携带信息。多个非法原因同时成立时，取最小非 0 码。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `dent_illegal=0` |
| `ILL_MAP_2MB` | 原始表项要求 2 MB 映射粒度 |
| `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty |
| `ILL_RSVD` | 保留 / 非法大项编码 |
| `ILL_PTR_OOB` | L1 基址等指针越界 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

译码器格式能否编码 2 MB 或 Access / Dirty 见 §7 暂缓；一旦原始表项带上这两种配置，本表仍然适用。

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，`dent_is_range=0`，`dent_pte_v=0`，`dent_rng_v=0`，`dent_rng_base=0`，`dent_rng_limit=0`，`dent_rng_last=0`，`dent_l1_base=0`，`dent_eid=0`，`dent_token_id=0`，`dent_token_value=0`，`dent_uba_base=0`，`dent_attr=0`，`dent_illegal=0`，`dent_ill_cause=0`。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_DENT_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_DENT_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`、`src_l1`、`pte_sel`；未成交前三者保持。 |
| `AP_DENT_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_DENT_LAT1` | L0 与 L1 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。**Xia 裁定 2026-10-12（C-D1）。** |
| `AP_DENT_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束。 |
| `AP_DENT_OUT_HOLD` | `out_valid && !out_ready` 期间，`out_valid` 与全部输出保持。**Xia 裁定 2026-10-12。** |
| `AP_DENT_IN_RDY_RST` | 复位撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。**Xia 裁定 2026-10-12。** |
| `AP_DENT_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_DENT_ILL_EQ` | `dent_illegal == (dent_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `AP_DENT_ILL_ZERO` | `dent_illegal=1` 的 `out_valid` 拍，除 `dent_illegal` / `dent_ill_cause` 外解码输出为 0。**Xia 裁定 2026-10-12。** |
| `AP_DENT_ILL_PRI` | 多个非法原因同时成立时，`dent_ill_cause` 取最小非 0 码。**Xia 裁定 2026-10-12。** |
| `AP_DENT_ILL_2MB` | 原始表项要求 2 MB 映射时，结果拍 `dent_ill_cause=1`（`ILL_MAP_2MB`）。 |
| `AP_DENT_ILL_AD` | 原始表项要求硬件写回 Access / Dirty 时，结果拍 `dent_ill_cause=2`（`ILL_HW_AD`）。 |
| `AP_DENT_SEL` | `src_l1=0` 且 `dent_is_range=0` 且 `dent_illegal=0` 时，`dent_pte_v` 对应 `pte_sel` 选中的那一条页表项。 |
| `AP_DENT_EID_W` | 第一波 `dent_eid` 宽 20。 |

---

## 7. 暂缓：随 D-05 译码器表项格式 PR 关闭

总表见 [README.md](README.md) §5。本叶子：

| 项 | 状态 |
| --- | --- |
| 译码器 L0 PTE / L0 范围项 / L1 PTE 的项目格式（含 `dent_rng_last` 是否写入格式） | 暂缓：随 D-05 译码器表项格式 PR 关闭 |
| L1 原始表项宽度，以及是否与 L0 共用 512 bit `raw` 口 | 暂缓：随 D-05 译码器表项格式 PR 关闭 |
| `dent_l1_base`、`dent_attr` 的最终宽度 | 暂缓：随 D-05 译码器表项格式 PR 关闭 |
| `_eid128` 变体是否出、何时出（D-06） | 暂缓：随 D-05 译码器表项格式 PR 关闭 |
| 范围比较放在本叶子还是下游结构叶子 | 暂缓：随 D-05 译码器表项格式 PR 关闭 |
| 译码器格式能否编码 2 MB 映射 | 暂缓：随 D-05 译码器表项格式 PR 关闭 |
