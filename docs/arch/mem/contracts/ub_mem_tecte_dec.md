# 公开信号契约 — `ub_mem_tecte_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_tecte_dec` |
| 父级例化点 | `ub_mem_cfg_lkup`（CSR 写 TECT 通路；查找路径读已解码信号束） |
| 规范 | UB Base Spec Rev 2.0 §9.4.2.1 |
| 微架构 | [UARCH.md](../UARCH.md) §5.1 |
| 裁定 | D20 S-01 (b)；2 MB 映射与硬件 Access / Dirty 写回首轮报配置非法 |

配置表项解码叶子。写入时拆成 §5.1 信号束；查找路径读已解码字段。

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
| `in_valid` | in | 1 | CSR 侧原始 TECT 镜像本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始镜像 |
| `raw` | in | **未知** | 原始 TECT / CSR 规范格式镜像。内部字段位置只在私有叶子源 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | `ub_mem_cfg_lkup` 可写下位配置表 |
| `cfg_v` | out | 1 | 表项有效 |
| `cfg_abort` | out | 1 | 软件设成「终止、不记事件」的翻译模式 |
| `cfg_illegal` | out | 1 | 配置非法（含不支持的合法编码） |
| `cfg_ill_cause` | out | 3 | 非法原因，符号见 §4；数值编码 **未知** |
| `cfg_s1_en` | out | 1 | Stage 1 翻译开启 |
| `cfg_mem_attr` | out | 4 | 内存属性覆盖值 |
| `cfg_mem_attr_ovr` | out | 1 | 用覆盖值代替请求属性 |
| `cfg_sec_ovr_en` | out | 1 | 安全属性覆盖开关 |
| `cfg_sec_ovr_val` | out | 1 | 安全属性覆盖值 |
| `cfg_priv_ovr_en` | out | 1 | 特权属性覆盖开关 |
| `cfg_priv_ovr_val` | out | 1 | 特权属性覆盖值 |
| `cfg_inst_ovr_en` | out | 1 | 指令 / 数据属性覆盖开关 |
| `cfg_inst_ovr_val` | out | 1 | 指令 / 数据属性覆盖值 |
| `cfg_mapt_en` | out | 1 | 本 Entity 允许权限检查 |
| `cfg_em_en` | out | 1 | 事件合并开关（首轮接受、不合并） |
| `cfg_tct_num` | out | 5 | TCT 项数的以 2 为底的对数 |
| `cfg_tct_2lvl` | out | 1 | 两级 TCT |
| `cfg_tct_ptr` | out | 42 | TCT 基址（64 B 对齐后的地址） |
| `cfg_mtm_from_ctx` | out | 1 | MTM 标识取自 TCTE |
| `cfg_mtm_id` | out | 16 | 流量监测标识 |
| `cfg_mtm_gp` | out | 8 | 流量监测组 |

信号束合计 93 bit，等于 UARCH 登记的 TECT 存储宽度。Stage 2 相关字段首轮不出口；Stage 2 开启走 §4。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：寄存一拍。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时 `raw` 保持；`out_valid==1` 且 `out_ready==0` 时整束保持。

---

## 4. 非法 / 不支持配置

`cfg_illegal=1` 时 `cfg_ill_cause` 给出下表之一。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `cfg_illegal=0` |
| `ILL_MAP_2MB` | 原始表项要求 2 MB 映射粒度 |
| `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty |
| `ILL_S2` | Stage 2 开启 |
| `ILL_RSVD` | 保留编码 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，§2 全部 `cfg_*` 输出为 0（含 `cfg_illegal`、`cfg_ill_cause`）。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_TECTE_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`。 |
| `AP_TECTE_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`；未成交前 `raw` 保持。 |
| `AP_TECTE_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_TECTE_LAT1` | 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_TECTE_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束；未成交前整束保持。 |
| `AP_TECTE_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_TECTE_ILL_2MB` | 原始表项要求 2 MB 映射时，成交拍 `cfg_illegal=1` 且 `cfg_ill_cause=ILL_MAP_2MB`。 |
| `AP_TECTE_ILL_AD` | 原始表项要求硬件写回 Access / Dirty 时，成交拍 `cfg_illegal=1` 且 `cfg_ill_cause=ILL_HW_AD`。 |
| `AP_TECTE_ILL_S2` | Stage 2 开启时，成交拍 `cfg_illegal=1` 且 `cfg_ill_cause=ILL_S2`。 |
| `AP_TECTE_ILL_HOLD` | `cfg_illegal=1` 的成交拍，`cfg_ill_cause` 属于 §4 符号集。 |

---

## 7. 未知

- `raw` 口宽度（CSR 镜像与规范 TECT 项宽）。
- `cfg_ill_cause` 的数值编码（3 bit 空间如何分配）。
- `cfg_illegal=1` 时其余 `cfg_*` 是否清零。
- 复位撤销后 `in_ready` 的首拍值。
