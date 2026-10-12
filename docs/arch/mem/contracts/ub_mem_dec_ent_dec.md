# 公开信号契约 — `ub_mem_dec_ent_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_dec_ent_dec` |
| 父级例化点 | `ub_mem_decoder`。第一波 L0 表在内存（D20 第 5 条），本叶子接 `ub_mem_dec_walk` 读回的原始大项；完整方案下同一叶子也接 L1 读回 |
| 规范 | UB Base Spec Rev 2.0 §9.5.1；译码器表项格式由项目自定（D20 第 8 条） |
| 微架构 | [UARCH.md](../UARCH.md) §5.5、§6.4 |
| 裁定 | D20 S-01 (b)；L0 第一波在内存；2 MB 映射与硬件 Access / Dirty 写回首轮报配置非法 |

User 侧译码器表项解码叶子。L0 PTE、L0 范围项、L1 PTE 共用。

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
| `in_valid` | in | 1 | 原始大项本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始大项 |
| `raw` | in | 512 | L0 原始大项（64 B）。L1 原始宽度 **未知**；L1 使用本口低位、高位由上游填 0，或另开变体，见 §7 |
| `src_l1` | in | 1 | 1 = 本拍是 L1 表项；0 = L0 大项 |
| `pte_sel` | in | 3 | 在 L0 页表项大项里选中第几条页表项 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | 下游结构逻辑可收下结果 |
| `dent_is_range` | out | 1 | 本大项是范围项。为 0 时按页表项组处理 |
| `dent_pte_v` | out | 1 | 选中的页表项有效 |
| `dent_rng_v` | out | 1 | 范围项有效 |
| `dent_rng_base` | out | 15 | 范围起点（与主机 PA 的范围键比较，比较可在下游） |
| `dent_rng_limit` | out | 15 | 范围终点（闭区间，UARCH Q-A14 口径） |
| `dent_rng_last` | out | 1 | 范围项本身是最后一级（Xia 提案，D-05） |
| `dent_l1_base` | out | 36 | L1 表基址（4 KB 对齐后的地址；UARCH 标「待」） |
| `dent_eid` | out | `EID_W` | 目标 EID。第一波 `EID_W=20` |
| `dent_token_id` | out | 20 | TokenID |
| `dent_token_value` | out | 32 | TokenValue |
| `dent_uba_base` | out | 52 | UBA 基值（§9.5.2；与 PA 低位相加在 `ub_mem_dec_uba`） |
| `dent_attr` | out | 8 | 其它相关属性 / 内存类型（UARCH 标「待」） |
| `dent_illegal` | out | 1 | 配置非法（含首轮不支持的合法编码、非法大项） |
| `dent_ill_cause` | out | 4 | 非法原因，符号见 §4；数值编码 **未知** |

`dent_eid` + `dent_token_id` + `dent_token_value` + `dent_uba_base` + `dent_attr` 组成译码结果束。第一波 `EID_W=20` 时结果束 132 bit。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- **L0（`src_l1=0`）预算 C：** 现场组合解码，延迟 **0** 拍，上界 **0** 拍。组合深度目标 ≤ 周期的 30%（UARCH §5.5）。`out_valid` 随 `in_valid` 同拍；`in_ready` 跟随 `out_ready`。
- **L1（`src_l1=1`）预算 R：** 读回后先寄存，延迟 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时，`raw` / `src_l1` / `pte_sel` 保持。
- `out_valid==1` 且 `out_ready==0` 时，全部解码输出保持。

---

## 4. 非法 / 不支持配置

`dent_illegal=1` 时 `dent_ill_cause` 给出下表之一。结构叶子只看这两根信号。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `dent_illegal=0` |
| `ILL_MAP_2MB` | 原始表项要求 2 MB 映射粒度 |
| `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty |
| `ILL_RSVD` | 保留 / 非法大项编码 |
| `ILL_PTR_OOB` | L1 基址等指针越界 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

项目自定格式能否编码 2 MB 或 Access / Dirty **未知**；一旦原始表项带上这两种配置，本表仍然适用。

---

## 5. 复位值

`rst_pyc` 有效期间寄存输出：`in_ready=0`，`out_valid=0`，`dent_is_range=0`，`dent_pte_v=0`，`dent_rng_v=0`，`dent_rng_base=0`，`dent_rng_limit=0`，`dent_rng_last=0`，`dent_l1_base=0`，`dent_eid=0`，`dent_token_id=0`，`dent_token_value=0`，`dent_uba_base=0`，`dent_attr=0`，`dent_illegal=0`，`dent_ill_cause=0`。

L0 组合路径随输入。上游在复位期间保持 `in_valid=0`、`raw=0` 时，组合解码输出为 0。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_DENT_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`。 |
| `AP_DENT_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`、`src_l1`、`pte_sel`；未成交前三者保持。 |
| `AP_DENT_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_DENT_LAT_L0` | `src_l1=0` 时，`out_valid` 与 `in_valid` 同拍，延迟为 0。 |
| `AP_DENT_LAT_L1` | `src_l1=1` 且成交后，恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_DENT_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束；未成交前整束保持。 |
| `AP_DENT_RST` | `rst_pyc` 有效期间 §5 各寄存输出为其复位值。 |
| `AP_DENT_ILL_2MB` | 原始表项要求 2 MB 映射时，结果成交拍 `dent_illegal=1` 且 `dent_ill_cause=ILL_MAP_2MB`。 |
| `AP_DENT_ILL_AD` | 原始表项要求硬件写回 Access / Dirty 时，结果成交拍 `dent_illegal=1` 且 `dent_ill_cause=ILL_HW_AD`。 |
| `AP_DENT_ILL_HOLD` | `dent_illegal=1` 的成交拍，`dent_ill_cause` 属于 §4 符号集。 |
| `AP_DENT_SEL` | `src_l1=0` 且 `dent_is_range=0` 时，`dent_pte_v` 对应 `pte_sel` 选中的那一条页表项。 |
| `AP_DENT_EID_W` | 第一波 `dent_eid` 宽 20。 |

---

## 7. 未知

- 译码器 L0 PTE / L0 范围项 / L1 PTE 的项目格式（D-05），含 `dent_rng_last` 是否写入格式。
- L1 原始表项宽度，以及是否与 L0 共用 512 bit `raw` 口。
- `dent_l1_base`、`dent_attr` 的最终宽度（UARCH 标「待」）。
- `dent_ill_cause` 的数值编码。
- 范围比较是本叶子输入主机 PA 范围键，还是下游用 `dent_rng_base` / `dent_rng_limit` 自己比。
- `_eid128` 变体是否出、何时出（D-06）。
- `dent_illegal=1` 时结果束各字段是否清零。
- 复位撤销后 `in_ready` 的首拍值。
