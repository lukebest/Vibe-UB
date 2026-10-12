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
  - {name: desc_lvl, dir: in, width: 2, desc: 当前遍历级，0=L0 … 3=L3，与 in_valid 同拍采样}
  - {name: out_valid, dir: out, width: 1, desc: 解码结果本拍有效}
  - {name: out_ready, dir: in, width: 1, desc: 下游可收下结果}
  - {name: desc_v, dir: out, width: 1, desc: 描述符有效}
  - {name: desc_kind, dir: out, width: 2, desc: "页粒度类别：0 invalid，1 table，2 block，3 page"}
  - {name: desc_addr, dir: out, width: 36, desc: 下一级表基址、块基址或 4 KB 页基址（4 KB 对齐）；块描述符只给块基址}
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
| 父级例化点 | `ub_mem_ptw`（UMMU 页表遍历器）。块描述符由遍历器按 §8 合成 4 KB 页地址，交给 `ub_mem_tlb` 的 `fill_*` 口（PR #27） |
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
| `desc_lvl` | in | 2 | 当前遍历级。编码：0 = L0，1 = L1，2 = L2，3 = L3。由 `ub_mem_ptw` 驱动，与 `in_valid` 同拍采样。**Xia 裁定 2026-10-12。** |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | 下游（`ub_mem_ptw`）可收下结果。第一波遍历器可以把本口 Tied 为 1。**Xia 裁定 2026-10-12。** |
| `desc_v` | out | 1 | 描述符有效 |
| `desc_kind` | out | 2 | 页粒度类别。编码（Xia 裁定 2026-10-12）：0 = invalid，1 = table，2 = block，3 = page |
| `desc_addr` | out | 36 | 下一级表基址、块基址或 4 KB 页基址（4 KB 对齐）。块描述符只给出块基址；块内偏移由父级按请求 VA 计算（§8）。**Xia 裁定 2026-10-12。** |
| `desc_attr_idx` | out | 3 | 属性 / 内存类型索引；遍历器在填 TLB 前用 `ctx_mattr0/1` 换成 8 bit 属性字节 |
| `desc_ap` | out | 2 | 访问许可 |
| `desc_uxn` | out | 1 | 用户执行禁止（按 §9.4.3 适配第 3 条使用） |
| `desc_pxn` | out | 1 | 特权执行禁止（同上） |
| `desc_af` | out | 1 | 访问标志（已置位的观测值；硬件写回见 §4） |
| `desc_illegal` | out | 1 | 配置非法；`desc_illegal == (desc_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `desc_ill_cause` | out | 4 | 非法原因，编码见 [README.md](README.md) §3 |

`desc_kind` 承担页粒度类别。输入按编码类与 `desc_lvl` 交叉，见 §3。块描述符只给出块基址 `desc_addr`。按 Q-A11，每个块拆成 4 KB TLB 项，合成规则见 §8。UB-MEM 第 9 章未定义 MATT 页表描述符格式与块大小；TCTE.TGS 字段注记写明其位含义跟随体系结构。**Xia 裁定 2026-10-12。**

---

## 3. 各级允许的描述符类型

按输入编码类（只写符号，公开面不写位值）与 `desc_lvl[1:0]` 交叉，共 12 格。依据 TCTE.TGS 注记，描述符格式跟随体系结构；语义取 VMSAv8-64 4 KB 粒度。验证按 `desc_lvl` × 编码类交叉。**Xia 裁定 2026-10-12。**

输入编码类：

| 符号 | 含义 |
| --- | --- |
| `ENC_INVALID` | 无效编码 |
| `ENC_TBL_PG` | L0–L2 表示 table，L3 表示 page |
| `ENC_BLOCK` | 块编码 |

输出列定义：table → `desc_kind=1`；block → `desc_kind=2`；page → `desc_kind=3`。翻译故障 → `desc_v=0`，`desc_kind=0`（invalid），`desc_illegal=0`，`desc_ill_cause=ILL_NONE`。

| 级 | `ENC_INVALID` | `ENC_TBL_PG` | `ENC_BLOCK` |
| --- | --- | --- | --- |
| L0 | 翻译故障 | table | 翻译故障（保留编码） |
| L1 | 翻译故障 | table | block 1 GB |
| L2 | 翻译故障 | table | block 2 MB |
| L3 | 翻译故障 | page 4 KB | 翻译故障（保留编码） |

L1 的 1 GB 块与 L2 的 2 MB 块：`desc_kind=2`，`desc_illegal=0`。本条取代此前对 1 GB 块报 `ILL_UNSUP` 的行，也取代此前对 L0 块 / L3 table 报 `ILL_RSVD` 的行。`ILL_MAP_2MB` 只对应 TCTE 范围表颗粒度，只出现在 `ub_mem_tcte_dec`。

---

## 4. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：解码结果寄存一拍。从 `in_valid && in_ready` 成交到 `out_valid` 拉高为 **1** 拍；延迟上界 **1** 拍。
- 下游看到的是已寄存的字段。
- `in_valid==1` 且 `in_ready==0` 时，`raw` 与 `desc_lvl` 保持。
- `out_valid==1` 且 `out_ready==0` 时，`out_valid` 与全部输出保持。叶子兑现反压；第一波 `ub_mem_ptw` 可以把 `out_ready` Tied 为 1。**Xia 裁定 2026-10-12。**
- 同时最多一笔未决解码（与 `ub_mem_ptw` 首轮单未决表读一致）。
- 复位撤销后的 `in_ready`：SPEC §3.1「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。按 Xia 裁定 2026-10-12：撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。

---

## 5. 非法 / 不支持配置

原因码与数值见 [README.md](README.md) §3。本叶子会用到的符号：`ILL_NONE`、`ILL_HW_AD`、`ILL_RSVD`、`ILL_UNSUP`。`ILL_MAP_2MB` 只对应 TCTE 范围表颗粒度选取 2 MB，只出现在 `ub_mem_tcte_dec`。2 MB 页表块描述符是另一件事，合法（L2）。**Xia 裁定 2026-10-12。**

**Xia 裁定 2026-10-12：**

- `desc_illegal=1` 的同一 `out_valid` 拍，其余解码输出（`desc_v` / `desc_kind` / `desc_addr` / `desc_attr_idx` / `desc_ap` / `desc_uxn` / `desc_pxn` / `desc_af`）为 0。该拍只有 `desc_illegal` 与 `desc_ill_cause` 携带信息。
- 配置非法（`ILL_HW_AD`）先于翻译故障（例如 AF=0）报告。多个非法原因同时成立时，取最小非 0 码。
- 描述符 `AF=0` 且需要硬件写回 Access / Dirty → `desc_ill_cause=ILL_HW_AD`。
- 描述符 `AF=0` 且不要求硬件写回 → `desc_illegal=0`，`desc_af=0`，由遍历器按普通 AF 故障处理。
- §3 标「翻译故障」的格子（含任意级 `ENC_INVALID`、L0 / L3 的 `ENC_BLOCK`）：`desc_v=0`，`desc_kind=0`，`desc_illegal=0`，`desc_ill_cause=ILL_NONE`。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `desc_illegal=0`（含 §3 合法格与全部翻译故障格） |
| `ILL_HW_AD` | 原始描述符要求硬件写回 Access / Dirty（含「AF=0 且必须写回才能继续」） |
| `ILL_RSVD` | 其余保留编码 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

---

## 6. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，`desc_v=0`，`desc_kind=0`，`desc_addr=0`，`desc_attr_idx=0`，`desc_ap=0`，`desc_uxn=0`，`desc_pxn=0`，`desc_af=0`，`desc_illegal=0`，`desc_ill_cause=0`。

---

## 7. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_PTW_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_PTW_HS_IN` | `in_valid && in_ready` 的拍收下 `raw` 与 `desc_lvl`；该拍之前二者保持。 |
| `AP_PTW_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_PTW_LAT1` | 成交后恰好 1 拍 `out_valid=1`；从不成交到 `out_valid` 的间隔 ≤ 1 拍。 |
| `AP_PTW_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束解码信号。 |
| `AP_PTW_OUT_HOLD` | `out_valid && !out_ready` 期间，`out_valid` 与全部输出保持。**Xia 裁定 2026-10-12。** |
| `AP_PTW_IN_RDY_RST` | 复位撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_RST` | `rst_pyc` 有效期间 §6 各输出为其复位值。 |
| `AP_PTW_ILL_EQ` | `desc_illegal == (desc_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_ILL_ZERO` | `desc_illegal=1` 的 `out_valid` 拍，除 `desc_illegal` / `desc_ill_cause` 外解码输出为 0。**Xia 裁定 2026-10-12。** |
| `AP_PTW_ILL_PRI` | 多个非法原因同时成立时，`desc_ill_cause` 取最小非 0 码。**Xia 裁定 2026-10-12。** |
| `AP_PTW_ILL_AD` | 原始描述符要求硬件写回 Access / Dirty 时，`out_valid` 拍 `desc_ill_cause=2`（`ILL_HW_AD`）。 |
| `AP_PTW_AF` | `AF=0` 且不要求硬件写回时，`desc_illegal=0` 且 `desc_af=0`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_KIND` | `desc_illegal=0` 时 `desc_kind` ∈ {0, 1, 2, 3}，分别 invalid / table / block / page。**Xia 裁定 2026-10-12。** |
| `AP_PTW_LVL` | `desc_lvl` ∈ {0, 1, 2, 3}，对应 L0..L3。**Xia 裁定 2026-10-12。** |
| `AP_PTW_XCLASS` | 成交拍按 `desc_lvl` × {`ENC_INVALID`, `ENC_TBL_PG`, `ENC_BLOCK`} 落入 §3 十二格之一。**Xia 裁定 2026-10-12。** |
| `AP_PTW_KIND_LVL` | `ENC_TBL_PG`：L0/L1/L2 给出 `desc_kind=1`（table）；L3 给出 `desc_kind=3`（page）。`ENC_BLOCK`：L1 给出 1 GB 块、L2 给出 2 MB 块，`desc_kind=2`。上述格子 `desc_v=1` 且 `desc_illegal=0`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_FAULT` | §3 翻译故障格（任意级 `ENC_INVALID`；L0 / L3 的 `ENC_BLOCK`）：`desc_v=0`，`desc_kind=0`，`desc_illegal=0`，`desc_ill_cause=ILL_NONE`。**Xia 裁定 2026-10-12。** |
| `AP_PTW_BLOCK` | L1 的 1 GB 块与 L2 的 2 MB 块：`desc_kind=2`（block），`desc_illegal=0`，`desc_addr` 为块基址。`ILL_MAP_2MB` 只出现在 `ub_mem_tcte_dec`。**Xia 裁定 2026-10-12。** |

---

## 8. 父级义务

父级 `ub_mem_ptw` 兑现下列规则。**Xia 裁定 2026-10-12**（按 Q-A11；本条取代此前对 1 GB 块报 `ILL_UNSUP` 的行）：

- 驱动 `desc_lvl` 为当前遍历级，与 `in_valid` 同拍采样。
- 页表用 4 KB 粒度，每个块拆成 4 KB TLB 项。
- 本叶子只给出块基址 `desc_addr` 与 `desc_kind`；块内偏移由父级按请求 VA 计算。
- 父级把块基址与请求 VA 的块内偏移合成 4 KB 对齐 PA，交给 `ub_mem_tlb`。
- `fill_*`（`fill_pfn` / `fill_attr` / `fill_ap` / `fill_uxn` / `fill_pxn` / `fill_af`）只携带该 4 KB 页地址与页属性。块偏移在合成 PA 时用掉。
- 遍历器观测口走 SPEC §10。
