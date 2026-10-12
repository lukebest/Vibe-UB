```yaml
leaf: ub_mem_ptw_desc_dec
parent: ub_mem_ptw
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
  - {name: in_valid, dir: in, width: 1, desc: 原始描述符本拍有效}
  - {name: in_ready, dir: out, width: 1, desc: 本拍可收下原始描述符}
  - {name: raw, dir: in, width: 64, desc: 一次 8 B 表读的原始描述符}
  - {name: out_valid, dir: out, width: 1, desc: 解码结果本拍有效}
  - {name: out_ready, dir: in, width: 1, desc: 下游可收下结果}
  - {name: desc_v, dir: out, width: 1, desc: 描述符有效}
  - {name: desc_kind, dir: out, width: 2, desc: "页粒度类别：0 invalid，1 table，2 block，3 page"}
  - {name: desc_addr, dir: out, width: 36, desc: 下一级表基址或输出页基址（4 KB 对齐）}
  - {name: desc_attr_idx, dir: out, width: 3, desc: 属性 / 内存类型索引}
  - {name: desc_ap, dir: out, width: 2, desc: 访问许可}
  - {name: desc_uxn, dir: out, width: 1, desc: 用户执行禁止}
  - {name: desc_pxn, dir: out, width: 1, desc: 特权执行禁止}
  - {name: desc_af, dir: out, width: 1, desc: 访问标志观测值}
  - {name: desc_illegal, dir: out, width: 1, desc: 配置非法，等于 desc_ill_cause != 0}
  - {name: desc_ill_cause, dir: out, width: 4, desc: 共用非法原因码}
params: []
ill_cause_width: 4
status: draft
```

# 公开信号契约 — `ub_mem_ptw_desc_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_ptw_desc_dec` |
| 父级例化点 | `ub_mem_ptw`（UMMU 页表遍历器）。解码结果经遍历器拆成 4 KB 项，交给 `ub_mem_tlb` 的 `fill_*` 口（PR #27） |
| 规范 | UB Base Spec Rev 2.0 §9.4.3 |
| 微架构 | [UARCH.md](../UARCH.md) §5.6、§6.2 |
| 裁定 | D20 S-01 (b)；接口补丁见 [README.md](README.md) §4（Xia 裁定 2026-10-12） |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；本叶子内部不做 CDC。**Xia 裁定 2026-10-12。** |

TLB 回填路径上的页表描述符解码叶子。输入一根原始描述符总线，输出字段级翻译语义。

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
| `in_valid` | in | 1 | 原始描述符本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始描述符 |
| `raw` | in | 64 | 一次 8 B 表读的原始描述符。内部字段位置只在私有叶子源 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | 下游（`ub_mem_ptw`）可收下结果。第一波遍历器可以把本口 Tied 为 1。**Xia 裁定 2026-10-12。** |
| `desc_v` | out | 1 | 描述符有效 |
| `desc_kind` | out | 2 | 页粒度类别。编码（Xia 裁定 2026-10-12）：0 = invalid，1 = table，2 = block，3 = page |
| `desc_addr` | out | 36 | 下一级表基址或输出页基址（4 KB 对齐后的地址） |
| `desc_attr_idx` | out | 3 | 属性 / 内存类型索引；遍历器在填 TLB 前用 `ctx_mattr0/1` 换成 8 bit 属性字节 |
| `desc_ap` | out | 2 | 访问许可 |
| `desc_uxn` | out | 1 | 用户执行禁止（按 §9.4.3 适配第 3 条使用） |
| `desc_pxn` | out | 1 | 特权执行禁止（同上） |
| `desc_af` | out | 1 | 访问标志（已置位的观测值；硬件写回见 §4） |
| `desc_illegal` | out | 1 | 配置非法；`desc_illegal == (desc_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `desc_ill_cause` | out | 4 | 非法原因，编码见 [README.md](README.md) §3 |

`desc_kind` 承担页粒度类别。4 KB 页与「拆成 4 KB 项的块」都经 `desc_addr` 给出页基址；2 MB 粒度走 §4 非法路径。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：解码结果寄存一拍。从 `in_valid && in_ready` 成交到 `out_valid` 拉高为 **1** 拍；延迟上界 **1** 拍。
- 下游看到的是已寄存的字段。
- `in_valid==1` 且 `in_ready==0` 时，`raw` 保持。
- `out_valid==1` 且 `out_ready==0` 时，`out_valid` 与全部输出保持。叶子兑现反压；第一波 `ub_mem_ptw` 可以把 `out_ready` Tied 为 1。**Xia 裁定 2026-10-12。**
- 同时最多一笔未决解码（与 `ub_mem_ptw` 首轮单未决表读一致）。
- 复位撤销后的 `in_ready`：SPEC §3.1「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。按 Xia 裁定 2026-10-12：撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。

---

## 4. 非法 / 不支持配置

原因码与数值见 [README.md](README.md) §3。本叶子会用到的符号：`ILL_NONE`、`ILL_MAP_2MB`、`ILL_HW_AD`、`ILL_RSVD`、`ILL_UNSUP`。

**Xia 裁定 2026-10-12：**

- `desc_illegal=1` 的同一 `out_valid` 拍，其余解码输出（`desc_v` / `desc_kind` / `desc_addr` / `desc_attr_idx` / `desc_ap` / `desc_uxn` / `desc_pxn` / `desc_af`）为 0。该拍只有 `desc_illegal` 与 `desc_ill_cause` 携带信息。
- 配置非法（`ILL_MAP_2MB`、`ILL_HW_AD`）先于翻译故障（例如 AF=0）报告。多个非法原因同时成立时，取最小非 0 码。
- 描述符 `AF=0` 且需要硬件写回 Access / Dirty → `desc_ill_cause=ILL_HW_AD`。
- 描述符 `AF=0` 且不要求硬件写回 → `desc_illegal=0`，`desc_af=0`，由遍历器按普通 AF 故障处理。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `desc_illegal=0` |
| `ILL_MAP_2MB` | 原始描述符要求 2 MB 映射粒度 |
| `ILL_HW_AD` | 原始描述符要求硬件写回 Access / Dirty（含「AF=0 且必须写回才能继续」） |
| `ILL_RSVD` | 保留编码 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，`desc_v=0`，`desc_kind=0`，`desc_addr=0`，`desc_attr_idx=0`，`desc_ap=0`，`desc_uxn=0`，`desc_pxn=0`，`desc_af=0`，`desc_illegal=0`，`desc_ill_cause=0`。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_PTW_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_PTW_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`；该拍之前 `raw` 保持。 |
| `AP_PTW_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_PTW_LAT1` | 成交后恰好 1 拍 `out_valid=1`；从不成交到 `out_valid` 的间隔 ≤ 1 拍。 |
| `AP_PTW_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束解码信号。 |
| `AP_PTW_OUT_HOLD` | `out_valid && !out_ready` 期间，`out_valid` 与全部输出保持。**Xia 裁定 2026-10-12。** |
| `AP_PTW_IN_RDY_RST` | 复位撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_PTW_ILL_EQ` | `desc_illegal == (desc_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_ILL_ZERO` | `desc_illegal=1` 的 `out_valid` 拍，除 `desc_illegal` / `desc_ill_cause` 外解码输出为 0。**Xia 裁定 2026-10-12。** |
| `AP_PTW_ILL_PRI` | 多个非法原因同时成立时，`desc_ill_cause` 取最小非 0 码。**Xia 裁定 2026-10-12。** |
| `AP_PTW_ILL_2MB` | 原始描述符要求 2 MB 映射时，`out_valid` 拍 `desc_ill_cause=1`（`ILL_MAP_2MB`）。 |
| `AP_PTW_ILL_AD` | 原始描述符要求硬件写回 Access / Dirty 时，`out_valid` 拍 `desc_ill_cause=2`（`ILL_HW_AD`）。 |
| `AP_PTW_AF` | `AF=0` 且不要求硬件写回时，`desc_illegal=0` 且 `desc_af=0`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_KIND` | `desc_illegal=0` 时 `desc_kind` ∈ {0, 1, 2, 3}，分别 invalid / table / block / page。**Xia 裁定 2026-10-12。** |

---

## 7. 未知

- 1 GB 块描述符是否出现、出现时的原因码。
