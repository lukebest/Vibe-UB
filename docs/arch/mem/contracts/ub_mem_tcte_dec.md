```yaml
leaf: ub_mem_tcte_dec
parent: ub_mem_ctx_lkup
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
  - {name: in_valid, dir: in, width: 1, desc: 原始 TCTE 本拍有效}
  - {name: in_ready, dir: out, width: 1, desc: 本拍可收下原始 TCTE}
  - {name: raw, dir: in, width: 512, desc: 一次 64 B 表读的原始 TCTE}
  - {name: out_valid, dir: out, width: 1, desc: 解码结果本拍有效}
  - {name: out_ready, dir: in, width: 1, desc: 下游可填缓存}
  - {name: ctx_v, dir: out, width: 1, desc: 表项有效}
  - {name: ctx_illegal, dir: out, width: 1, desc: 配置非法，等于 ctx_ill_cause != 0}
  - {name: ctx_ill_cause, dir: out, width: 4, desc: 共用非法原因码}
  - {name: ctx_oa_w, dir: out, width: 6, desc: 输出地址有效位数}
  - {name: ctx_ia_w, dir: out, width: 6, desc: UBA 有效位数}
  - {name: ctx_affd, dir: out, width: 1, desc: AF 故障不报}
  - {name: ctx_fbr, dir: out, width: 1, desc: 翻译故障要记录}
  - {name: ctx_mapt_en, dir: out, width: 1, desc: 本上下文做权限检查}
  - {name: ctx_mapt_multi, dir: out, width: 1, desc: 多级 MAPT}
  - {name: ctx_e_bit, dir: out, width: 1, desc: 上下文排他位}
  - {name: ctx_matt_wd, dir: out, width: 1, desc: 不遍历页表}
  - {name: ctx_mtm_id, dir: out, width: 16, desc: 流量监测标识}
  - {name: ctx_mtm_gp, dir: out, width: 8, desc: 流量监测组}
  - {name: ctx_matt_ba, dir: out, width: 44, desc: 页表基址（16 B 对齐）}
  - {name: ctx_mapt_bba, dir: out, width: 43, desc: MAPT 基块地址（32 B 对齐）}
  - {name: ctx_mapt_bb_sz, dir: out, width: 4, desc: MAPT 基块大小指数，4 KB × 2^n，合法 0..9}
  - {name: ctx_mattr0, dir: out, width: 32, desc: 第一组属性字节}
  - {name: ctx_mattr1, dir: out, width: 32, desc: 第二组属性字节}
params: []
ill_cause_width: 4
status: draft
```

# 公开信号契约 — `ub_mem_tcte_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_tcte_dec` |
| 父级例化点 | `ub_mem_ctx_lkup`（TCT 缓存填充通路） |
| 规范 | UB Base Spec Rev 2.0 §9.4.2.2.2 |
| 微架构 | [UARCH.md](../UARCH.md) §5.2 |
| 裁定 | D20 S-01 (b)；接口补丁见 [README.md](README.md) §4（Xia 裁定 2026-10-12） |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；本叶子内部不做 CDC。**Xia 裁定 2026-10-12。** |

上下文表项解码叶子。填充前拆成 §5.2 信号束，命中路径只读已解码字段。

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
| `in_valid` | in | 1 | 原始 TCTE 本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始 TCTE |
| `raw` | in | 512 | 一次 64 B 表读的原始 TCTE。内部字段位置只在私有叶子源 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | `ub_mem_ctx_lkup` 可填缓存。第一波可以把本口 Tied 为 1。**Xia 裁定 2026-10-12。** |
| `ctx_v` | out | 1 | 表项有效 |
| `ctx_illegal` | out | 1 | 配置非法；`ctx_illegal == (ctx_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `ctx_ill_cause` | out | 4 | 非法原因，编码见 [README.md](README.md) §3 |
| `ctx_oa_w` | out | 6 | 输出地址有效位数 |
| `ctx_ia_w` | out | 6 | UBA 有效位数（由规范大小字段换算） |
| `ctx_affd` | out | 1 | AF 故障不报 |
| `ctx_fbr` | out | 1 | 翻译故障要记录 |
| `ctx_mapt_en` | out | 1 | 本上下文做权限检查 |
| `ctx_mapt_multi` | out | 1 | 多级 MAPT（0 = 单项） |
| `ctx_e_bit` | out | 1 | 上下文排他位 |
| `ctx_matt_wd` | out | 1 | 不遍历页表，TLB 缺失即记事件 |
| `ctx_mtm_id` | out | 16 | 流量监测标识 |
| `ctx_mtm_gp` | out | 8 | 流量监测组 |
| `ctx_matt_ba` | out | 44 | 页表基址（16 B 对齐后的地址） |
| `ctx_mapt_bba` | out | 43 | MAPT 基块地址（32 B 对齐后的地址） |
| `ctx_mapt_bb_sz` | out | 4 | MAPT 基块大小指数（4 KB × 2^n）。合法 0..9（9 = 2 MB 基块）；10..15 报 `ILL_RSVD`。**Xia 裁定 2026-10-12，依据 UB-MEM 第 9 章条目尺寸。** |
| `ctx_mattr0` | out | 32 | 第一组属性字节，供页表属性索引选择 |
| `ctx_mattr1` | out | 32 | 第二组属性字节 |

信号束合计 203 bit。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：寄存一拍。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时 `raw` 保持。
- `out_valid==1` 且 `out_ready==0` 时，`out_valid` 与全部输出保持。叶子兑现反压。**Xia 裁定 2026-10-12。**
- 复位撤销后的 `in_ready`：SPEC §3.1「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。按 Xia 裁定 2026-10-12：撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。

---

## 4. 非法 / 不支持配置

原因码与数值见 [README.md](README.md) §3。本叶子会用到的符号：`ILL_NONE`、`ILL_MAP_2MB`、`ILL_HW_AD`、`ILL_ENDIAN`、`ILL_STALL`、`ILL_MAC`、`ILL_MAPT_MULTI_BLK`、`ILL_RSVD`、`ILL_PTR_OOB`、`ILL_UNSUP`。

**Xia 裁定 2026-10-12：** `ctx_illegal=1` 的同一 `out_valid` 拍，其余解码输出为 0。该拍只有 `ctx_illegal` 与 `ctx_ill_cause` 携带信息。多个非法原因同时成立时，取最小非 0 码。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `ctx_illegal=0` |
| `ILL_MAP_2MB` | TCTE 范围表颗粒度选取 2 MB（延后的「2 MB 映射粒度」）。2 MB 页表块描述符是另一件事，在 `ub_mem_ptw_desc_dec` 合法 |
| `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty（硬件标志更新） |
| `ILL_ENDIAN` | 首轮不支持的字节序 |
| `ILL_STALL` | Stall |
| `ILL_MAC` | MAC 模式 |
| `ILL_MAPT_MULTI_BLK` | 多块 MAPT |
| `ILL_RSVD` | 保留编码，含 `ctx_mapt_bb_sz` 取值 10..15 |
| `ILL_PTR_OOB` | 指针越界 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，§2 全部 `ctx_*` 输出为 0（含 `ctx_illegal`、`ctx_ill_cause`）。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_TCTE_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_TCTE_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`；未成交前 `raw` 保持。 |
| `AP_TCTE_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_TCTE_LAT1` | 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_TCTE_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束。 |
| `AP_TCTE_OUT_HOLD` | `out_valid && !out_ready` 期间，`out_valid` 与全部输出保持。**Xia 裁定 2026-10-12。** |
| `AP_TCTE_IN_RDY_RST` | 复位撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。**Xia 裁定 2026-10-12。** |
| `AP_TCTE_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_TCTE_ILL_EQ` | `ctx_illegal == (ctx_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `AP_TCTE_ILL_ZERO` | `ctx_illegal=1` 的 `out_valid` 拍，除 `ctx_illegal` / `ctx_ill_cause` 外解码输出为 0。**Xia 裁定 2026-10-12。** |
| `AP_TCTE_ILL_PRI` | 多个非法原因同时成立时，`ctx_ill_cause` 取最小非 0 码。**Xia 裁定 2026-10-12。** |
| `AP_TCTE_ILL_2MB` | TCTE 范围表颗粒度选取 2 MB 时，成交拍 `ctx_ill_cause=1`（`ILL_MAP_2MB`）。**Xia 裁定 2026-10-12，依据 UB-MEM 第 9 章条目尺寸。** |
| `AP_TCTE_ILL_AD` | 原始表项要求硬件写回 Access / Dirty 时，成交拍 `ctx_ill_cause=2`（`ILL_HW_AD`）。 |
| `AP_TCTE_BB_SZ` | `ctx_illegal=0` 时 `ctx_mapt_bb_sz` ∈ 0..9。`ctx_mapt_bb_sz` ∈ 10..15 时 `ctx_ill_cause=3`（`ILL_RSVD`）。**Xia 裁定 2026-10-12，依据 UB-MEM 第 9 章条目尺寸。** |
