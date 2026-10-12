```yaml
leaf: ub_mem_tecte_dec
parent: ub_mem_cfg_lkup
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
  - {name: in_valid, dir: in, width: 1, desc: CSR 侧原始 TECT 镜像本拍有效}
  - {name: in_ready, dir: out, width: 1, desc: 本拍可收下原始镜像}
  - {name: raw, dir: in, width: 512, desc: 原始 TECTE，64 B}
  - {name: out_valid, dir: out, width: 1, desc: 解码结果本拍有效}
  - {name: out_ready, dir: in, width: 1, desc: 下游可写下位配置表}
  - {name: cfg_v, dir: out, width: 1, desc: 表项有效}
  - {name: cfg_abort, dir: out, width: 1, desc: 终止且不记事件的翻译模式}
  - {name: cfg_illegal, dir: out, width: 1, desc: 配置非法，等于 cfg_ill_cause != 0}
  - {name: cfg_ill_cause, dir: out, width: 4, desc: 共用非法原因码}
  - {name: cfg_s1_en, dir: out, width: 1, desc: Stage 1 翻译开启}
  - {name: cfg_mem_attr, dir: out, width: 4, desc: 内存属性覆盖值}
  - {name: cfg_mem_attr_ovr, dir: out, width: 1, desc: 用覆盖值代替请求属性}
  - {name: cfg_sec_ovr_en, dir: out, width: 1, desc: 安全属性覆盖开关}
  - {name: cfg_sec_ovr_val, dir: out, width: 1, desc: 安全属性覆盖值}
  - {name: cfg_priv_ovr_en, dir: out, width: 1, desc: 特权属性覆盖开关}
  - {name: cfg_priv_ovr_val, dir: out, width: 1, desc: 特权属性覆盖值}
  - {name: cfg_inst_ovr_en, dir: out, width: 1, desc: 指令 / 数据属性覆盖开关}
  - {name: cfg_inst_ovr_val, dir: out, width: 1, desc: 指令 / 数据属性覆盖值}
  - {name: cfg_mapt_en, dir: out, width: 1, desc: 本 Entity 允许权限检查}
  - {name: cfg_em_en, dir: out, width: 1, desc: 事件合并开关}
  - {name: cfg_tct_num, dir: out, width: 5, desc: TCT 项数以 2 为底的对数}
  - {name: cfg_tct_2lvl, dir: out, width: 1, desc: 两级 TCT}
  - {name: cfg_tct_ptr, dir: out, width: 42, desc: TCT 基址（64 B 对齐）}
  - {name: cfg_mtm_from_ctx, dir: out, width: 1, desc: MTM 标识取自 TCTE}
  - {name: cfg_mtm_id, dir: out, width: 16, desc: 流量监测标识}
  - {name: cfg_mtm_gp, dir: out, width: 8, desc: 流量监测组}
params: []
ill_cause_width: 4
status: draft
```

# 公开信号契约 — `ub_mem_tecte_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_tecte_dec` |
| 父级例化点 | `ub_mem_cfg_lkup`（CSR 写 TECT 通路；查找路径读已解码信号束） |
| 规范 | UB Base Spec Rev 2.0 §9.4.2.1 |
| 微架构 | [UARCH.md](../UARCH.md) §5.1 |
| 裁定 | D20 S-01 (b)；接口补丁见 [README.md](README.md) §4（Xia 裁定 2026-10-12） |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；本叶子内部不做 CDC。**Xia 裁定 2026-10-12。** |

配置表项解码叶子。写入时拆成 §5.1 信号束；查找路径读已解码字段。

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
| `in_valid` | in | 1 | CSR 侧原始 TECT 镜像本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始镜像 |
| `raw` | in | 512 | 原始 TECTE（64 B）。内部字段位置只在私有叶子源。**Xia 裁定 2026-10-12，依据 UB-MEM 第 9 章条目尺寸。** |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | `ub_mem_cfg_lkup` 可写下位配置表。第一波可以把本口 Tied 为 1。**Xia 裁定 2026-10-12。** |
| `cfg_v` | out | 1 | 表项有效 |
| `cfg_abort` | out | 1 | 软件设成「终止、不记事件」的翻译模式 |
| `cfg_illegal` | out | 1 | 配置非法；`cfg_illegal == (cfg_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `cfg_ill_cause` | out | 4 | 非法原因，编码见 [README.md](README.md) §3 |
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

信号束随 `cfg_ill_cause` 加宽到 4 bit 计为 94 bit。Stage 2 相关字段首轮不出口；Stage 2 开启走 §4。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：寄存一拍。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时 `raw` 保持。
- `out_valid==1` 且 `out_ready==0` 时，`out_valid` 与全部输出保持。叶子兑现反压。**Xia 裁定 2026-10-12。**
- 复位撤销后的 `in_ready`：SPEC §3.1「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。按 Xia 裁定 2026-10-12：撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。

---

## 4. 非法 / 不支持配置

原因码与数值见 [README.md](README.md) §3。本叶子会用到的符号：`ILL_NONE`、`ILL_MAP_2MB`、`ILL_HW_AD`、`ILL_S2`、`ILL_RSVD`、`ILL_UNSUP`。

**Xia 裁定 2026-10-12：** `cfg_illegal=1` 的同一 `out_valid` 拍，其余解码输出为 0。该拍只有 `cfg_illegal` 与 `cfg_ill_cause` 携带信息。多个非法原因同时成立时，取最小非 0 码。

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
| `AP_TECTE_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_TECTE_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`；未成交前 `raw` 保持。 |
| `AP_TECTE_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_TECTE_LAT1` | 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_TECTE_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束。 |
| `AP_TECTE_OUT_HOLD` | `out_valid && !out_ready` 期间，`out_valid` 与全部输出保持。**Xia 裁定 2026-10-12。** |
| `AP_TECTE_IN_RDY_RST` | 复位撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。**Xia 裁定 2026-10-12。** |
| `AP_TECTE_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_TECTE_ILL_EQ` | `cfg_illegal == (cfg_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `AP_TECTE_ILL_ZERO` | `cfg_illegal=1` 的 `out_valid` 拍，除 `cfg_illegal` / `cfg_ill_cause` 外解码输出为 0。**Xia 裁定 2026-10-12。** |
| `AP_TECTE_ILL_PRI` | 多个非法原因同时成立时，`cfg_ill_cause` 取最小非 0 码。**Xia 裁定 2026-10-12。** |
| `AP_TECTE_ILL_2MB` | 原始表项要求 2 MB 映射时，成交拍 `cfg_ill_cause=1`（`ILL_MAP_2MB`）。 |
| `AP_TECTE_ILL_AD` | 原始表项要求硬件写回 Access / Dirty 时，成交拍 `cfg_ill_cause=2`（`ILL_HW_AD`）。 |
| `AP_TECTE_ILL_S2` | Stage 2 开启时，成交拍 `cfg_ill_cause=10`（`ILL_S2`）。 |

---

