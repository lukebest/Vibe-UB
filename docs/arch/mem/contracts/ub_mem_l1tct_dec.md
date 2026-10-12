```yaml
leaf: ub_mem_l1tct_dec
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
  - {name: in_valid, dir: in, width: 1, desc: 原始 L1 TCT 描述符本拍有效}
  - {name: in_ready, dir: out, width: 1, desc: 本拍可收下原始描述符}
  - {name: raw, dir: in, width: 64, desc: 一次 8 B 表读的原始描述符}
  - {name: out_valid, dir: out, width: 1, desc: 解码结果本拍有效}
  - {name: out_ready, dir: in, width: 1, desc: 下游可继续读 L2}
  - {name: l1tct_v, dir: out, width: 1, desc: 描述符有效}
  - {name: l1tct_illegal, dir: out, width: 1, desc: 配置非法，等于 l1tct_ill_cause != 0}
  - {name: l1tct_ill_cause, dir: out, width: 4, desc: 共用非法原因码}
  - {name: l1tct_l2_ptr, dir: out, width: 36, desc: L2 TCT 基址（4 KB 对齐）}
params: []
ill_cause_width: 4
assertions:
  - AP_L1TCT_CLK
  - AP_L1TCT_HS_IN
  - AP_L1TCT_HS_OUT
  - AP_L1TCT_ILL_2MB
  - AP_L1TCT_ILL_AD
  - AP_L1TCT_ILL_EQ
  - AP_L1TCT_ILL_PRI
  - AP_L1TCT_ILL_ZERO
  - AP_L1TCT_IN_RDY_RST
  - AP_L1TCT_LAT1
  - AP_L1TCT_OUT_HOLD
  - AP_L1TCT_RDY
  - AP_L1TCT_RST
status: draft
```

# 公开信号契约 — `ub_mem_l1tct_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_l1tct_dec` |
| 父级例化点 | `ub_mem_ctx_lkup`（两级 TCT：先读 L1 描述符，再读 L2 TCTE） |
| 规范 | UB Base Spec Rev 2.0 §9.4.2.2.3 |
| 微架构 | [UARCH.md](../UARCH.md) §5.3 |
| 裁定 | D20 S-01 (b)；接口补丁见 [README.md](README.md) §4（Xia 裁定 2026-10-12） |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；本叶子内部不做 CDC。**Xia 裁定 2026-10-12。** |

L1 TCT 描述符解码叶子。

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
| `in_valid` | in | 1 | 原始 L1 TCT 描述符本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始描述符 |
| `raw` | in | 64 | 一次 8 B 表读的原始描述符。内部字段位置只在私有叶子源 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | `ub_mem_ctx_lkup` 可继续读 L2。第一波可以把本口 Tied 为 1。**Xia 裁定 2026-10-12。** |
| `l1tct_v` | out | 1 | 描述符有效 |
| `l1tct_illegal` | out | 1 | 配置非法；`l1tct_illegal == (l1tct_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `l1tct_ill_cause` | out | 4 | 非法原因，编码见 [README.md](README.md) §3 |
| `l1tct_l2_ptr` | out | 36 | L2 TCT 基址（4 KB 对齐后的地址） |

UARCH §5.3 只列了 `l1tct_illegal`（指针越界）。本契约按 D20 与 Xia 裁定 2026-10-12 给出 4 bit `l1tct_ill_cause`。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：寄存一拍。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时 `raw` 保持。
- `out_valid==1` 且 `out_ready==0` 时，`out_valid` 与全部输出保持。叶子兑现反压。**Xia 裁定 2026-10-12。**
- 复位撤销后的 `in_ready`：SPEC §3.1「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。按 Xia 裁定 2026-10-12：撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。

---

## 4. 非法 / 不支持配置

原因码与数值见 [README.md](README.md) §3。本叶子会用到的符号：`ILL_NONE`、`ILL_MAP_2MB`、`ILL_HW_AD`、`ILL_PTR_OOB`、`ILL_RSVD`、`ILL_UNSUP`。

**Xia 裁定 2026-10-12：** `l1tct_illegal=1` 的同一 `out_valid` 拍，其余解码输出为 0。该拍只有 `l1tct_illegal` 与 `l1tct_ill_cause` 携带信息。多个非法原因同时成立时，取最小非 0 码。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `l1tct_illegal=0` |
| `ILL_MAP_2MB` | 原始描述符要求 2 MB 映射粒度 |
| `ILL_HW_AD` | 原始描述符要求硬件写回 Access / Dirty |
| `ILL_PTR_OOB` | L2 指针越界 |
| `ILL_RSVD` | 保留编码 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

L1 描述符格式能否编码 2 MB 或 Access / Dirty 见 §7 暂缓；一旦原始表项带上这两种配置，本表仍然适用。

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，`l1tct_v=0`，`l1tct_illegal=0`，`l1tct_ill_cause=0`，`l1tct_l2_ptr=0`。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_L1TCT_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_L1TCT_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`；未成交前 `raw` 保持。 |
| `AP_L1TCT_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_L1TCT_LAT1` | 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_L1TCT_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束。 |
| `AP_L1TCT_OUT_HOLD` | `out_valid && !out_ready` 期间，`out_valid` 与全部输出保持。**Xia 裁定 2026-10-12。** |
| `AP_L1TCT_IN_RDY_RST` | 复位撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。**Xia 裁定 2026-10-12。** |
| `AP_L1TCT_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_L1TCT_ILL_EQ` | `l1tct_illegal == (l1tct_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `AP_L1TCT_ILL_ZERO` | `l1tct_illegal=1` 的 `out_valid` 拍，除 `l1tct_illegal` / `l1tct_ill_cause` 外解码输出为 0。**Xia 裁定 2026-10-12。** |
| `AP_L1TCT_ILL_PRI` | 多个非法原因同时成立时，`l1tct_ill_cause` 取最小非 0 码。**Xia 裁定 2026-10-12。** |
| `AP_L1TCT_ILL_2MB` | 原始描述符要求 2 MB 映射时，成交拍 `l1tct_ill_cause=1`（`ILL_MAP_2MB`）。 |
| `AP_L1TCT_ILL_AD` | 原始描述符要求硬件写回 Access / Dirty 时，成交拍 `l1tct_ill_cause=2`（`ILL_HW_AD`）。 |

---

## 7. 暂缓：随 D-05 译码器表项格式 PR 关闭

总表见 [README.md](README.md) §5。本叶子：

| 项 | 状态 |
| --- | --- |
| L1 TCT 格式能否编码 2 MB 映射 | 暂缓：随 D-05 译码器表项格式 PR 关闭 |
