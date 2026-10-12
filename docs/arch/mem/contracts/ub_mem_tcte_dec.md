# 公开信号契约 — `ub_mem_tcte_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_tcte_dec` |
| 父级例化点 | `ub_mem_ctx_lkup`（TCT 缓存填充通路） |
| 规范 | UB Base Spec Rev 2.0 §9.4.2.2.2 |
| 微架构 | [UARCH.md](../UARCH.md) §5.2 |
| 裁定 | D20 S-01 (b)；2 MB 映射与硬件 Access / Dirty 写回首轮报配置非法 |

上下文表项解码叶子。填充前拆成 §5.2 信号束，命中路径只读已解码字段。

---

## 1. 时钟与复位

| 端口 | 方向 | 宽度 | 含义 |
| --- | --- | --- | --- |
| `core_clk` | in | 1 | 单时钟，≈80.57 MHz |
| `rst_pyc` | in | 1 | `pyc_reg` 原生极性；业务寄存器同步复位（CODING_STYLE §2） |

---

## 2. 端口

| 端口 | 方向 | 宽度 | 含义 |
| --- | --- | --- | --- |
| `in_valid` | in | 1 | 原始 TCTE 本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始 TCTE |
| `raw` | in | 512 | 一次 64 B 表读的原始 TCTE。内部字段位置只在私有叶子源 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | `ub_mem_ctx_lkup` 可填缓存 |
| `ctx_v` | out | 1 | 表项有效 |
| `ctx_illegal` | out | 1 | 配置非法 |
| `ctx_ill_cause` | out | 4 | 非法原因，符号见 §4；数值编码 **未知** |
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
| `ctx_mapt_bb_sz` | out | 4 | MAPT 基块大小（以 4 KB 为单位的对数；2 MB 见 §4） |
| `ctx_mattr0` | out | 32 | 第一组属性字节，供页表属性索引选择 |
| `ctx_mattr1` | out | 32 | 第二组属性字节 |

信号束合计 203 bit。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：寄存一拍。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时 `raw` 保持；`out_valid==1` 且 `out_ready==0` 时整束保持。

---

## 4. 非法 / 不支持配置

`ctx_illegal=1` 时 `ctx_ill_cause` 给出下表之一。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `ctx_illegal=0` |
| `ILL_MAP_2MB` | 原始表项要求 2 MB 映射粒度（含 2 MB MAPT 基块） |
| `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty（硬件标志更新） |
| `ILL_ENDIAN` | 首轮不支持的字节序 |
| `ILL_STALL` | Stall |
| `ILL_MAC` | MAC 模式 |
| `ILL_MAPT_MULTI_BLK` | 多块 MAPT |
| `ILL_RSVD` | 保留编码 |
| `ILL_PTR_OOB` | 指针越界 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，§2 全部 `ctx_*` 输出为 0（含 `ctx_illegal`、`ctx_ill_cause`）。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_TCTE_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`。 |
| `AP_TCTE_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`；未成交前 `raw` 保持。 |
| `AP_TCTE_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_TCTE_LAT1` | 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_TCTE_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束；未成交前整束保持。 |
| `AP_TCTE_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_TCTE_ILL_2MB` | 原始表项要求 2 MB 映射时，成交拍 `ctx_illegal=1` 且 `ctx_ill_cause=ILL_MAP_2MB`。 |
| `AP_TCTE_ILL_AD` | 原始表项要求硬件写回 Access / Dirty 时，成交拍 `ctx_illegal=1` 且 `ctx_ill_cause=ILL_HW_AD`。 |
| `AP_TCTE_ILL_HOLD` | `ctx_illegal=1` 的成交拍，`ctx_ill_cause` 属于 §4 符号集。 |

---

## 7. 未知

- `ctx_ill_cause` 的数值编码（4 bit 空间如何分配）。
- `ctx_illegal=1` 时其余 `ctx_*` 是否清零。
- `ctx_mapt_bb_sz` 表示 2 MB 的具体对数值。
- 复位撤销后 `in_ready` 的首拍值。
