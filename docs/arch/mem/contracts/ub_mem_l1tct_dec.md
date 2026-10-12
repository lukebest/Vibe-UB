# 公开信号契约 — `ub_mem_l1tct_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_l1tct_dec` |
| 父级例化点 | `ub_mem_ctx_lkup`（两级 TCT：先读 L1 描述符，再读 L2 TCTE） |
| 规范 | UB Base Spec Rev 2.0 §9.4.2.2.3 |
| 微架构 | [UARCH.md](../UARCH.md) §5.3 |
| 裁定 | D20 S-01 (b)；2 MB 映射与硬件 Access / Dirty 写回首轮报配置非法 |

L1 TCT 描述符解码叶子。

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
| `in_valid` | in | 1 | 原始 L1 TCT 描述符本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始描述符 |
| `raw` | in | 64 | 一次 8 B 表读的原始描述符。内部字段位置只在私有叶子源 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | `ub_mem_ctx_lkup` 可继续读 L2 |
| `l1tct_v` | out | 1 | 描述符有效 |
| `l1tct_illegal` | out | 1 | 配置非法（含指针越界与 §4 首轮不支持项） |
| `l1tct_ill_cause` | out | 3 | 非法原因，符号见 §4；数值编码 **未知** |
| `l1tct_l2_ptr` | out | 36 | L2 TCT 基址（4 KB 对齐后的地址） |

UARCH §5.3 只列了 `l1tct_illegal`（指针越界）。本契约按 D20 补 `l1tct_ill_cause`，让 2 MB / Access-Dirty 与越界共用同一非法口。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：寄存一拍。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时 `raw` 保持；`out_valid==1` 且 `out_ready==0` 时整束保持。

---

## 4. 非法 / 不支持配置

`l1tct_illegal=1` 时 `l1tct_ill_cause` 给出下表之一。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `l1tct_illegal=0` |
| `ILL_MAP_2MB` | 原始描述符要求 2 MB 映射粒度 |
| `ILL_HW_AD` | 原始描述符要求硬件写回 Access / Dirty |
| `ILL_PTR_OOB` | L2 指针越界 |
| `ILL_RSVD` | 保留编码 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

L1 描述符格式能否编码 2 MB 或 Access / Dirty **未知**；一旦原始表项带上这两种配置，本表仍然适用。

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，`l1tct_v=0`，`l1tct_illegal=0`，`l1tct_ill_cause=0`，`l1tct_l2_ptr=0`。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_L1TCT_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`。 |
| `AP_L1TCT_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`；未成交前 `raw` 保持。 |
| `AP_L1TCT_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_L1TCT_LAT1` | 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_L1TCT_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束；未成交前整束保持。 |
| `AP_L1TCT_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_L1TCT_ILL_2MB` | 原始描述符要求 2 MB 映射时，成交拍 `l1tct_illegal=1` 且 `l1tct_ill_cause=ILL_MAP_2MB`。 |
| `AP_L1TCT_ILL_AD` | 原始描述符要求硬件写回 Access / Dirty 时，成交拍 `l1tct_illegal=1` 且 `l1tct_ill_cause=ILL_HW_AD`。 |
| `AP_L1TCT_ILL_HOLD` | `l1tct_illegal=1` 的成交拍，`l1tct_ill_cause` 属于 §4 符号集。 |

---

## 7. 未知

- `l1tct_ill_cause` 宽度的最终值（本契约暂按 3）与数值编码。
- L1 描述符能否携带 2 MB / Access-Dirty。
- `l1tct_illegal=1` 时 `l1tct_v` / `l1tct_l2_ptr` 是否清零。
- 复位撤销后 `in_ready` 的首拍值。
