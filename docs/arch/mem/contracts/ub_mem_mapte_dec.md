```yaml
leaf: ub_mem_mapte_dec
parent: ub_mem_perm_walk
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
  - {name: in_valid, dir: in, width: 1, desc: 原始 MAPTE 本拍有效}
  - {name: in_ready, dir: out, width: 1, desc: 本拍可收下原始 MAPTE}
  - {name: raw, dir: in, width: 256, desc: 一次 32 B 表读的原始 MAPTE；最终宽度见未知}
  - {name: mode_multi, dir: in, width: 1, desc: 1 为多级 MAPT}
  - {name: lvl, dir: in, width: 3, desc: 当前级别（0 起）；最终宽度见未知}
  - {name: out_valid, dir: out, width: 1, desc: 解码结果本拍有效}
  - {name: out_ready, dir: in, width: 1, desc: 下游可收下}
  - {name: mapte_v, dir: out, width: 1, desc: 表项有效}
  - {name: mapte_last, dir: out, width: 1, desc: 本项不再指向下一级}
  - {name: mapte_next_other_blk, dir: out, width: 1, desc: 下一级在其他块}
  - {name: mapte_e_bit, dir: out, width: 1, desc: 排他位}
  - {name: mapte_perm_w, dir: out, width: 1, desc: 写许可}
  - {name: mapte_perm_r, dir: out, width: 1, desc: 读许可}
  - {name: mapte_perm_a, dir: out, width: 1, desc: 原子许可}
  - {name: mapte_token_chk, dir: out, width: 1, desc: 需要比 TokenValue}
  - {name: mapte_base, dir: out, width: 48, desc: 范围起点（闭区间）}
  - {name: mapte_limit, dir: out, width: 48, desc: 范围终点（闭区间）}
  - {name: mapte_next_off, dir: out, width: 30, desc: 下一级相对块基址的字节偏移}
  - {name: mapte_next_idx, dir: out, width: 16, desc: 下一级所在块的块表下标}
  - {name: mapte_tv0, dir: out, width: 32, desc: 第一个 TokenValue}
  - {name: mapte_tv1, dir: out, width: 32, desc: 第二个 TokenValue}
  - {name: mapte_illegal, dir: out, width: 1, desc: 配置非法，等于 mapte_ill_cause != 0}
  - {name: mapte_ill_cause, dir: out, width: 4, desc: 共用非法原因码}
params: []
ill_cause_width: 4
status: draft
```

# 公开信号契约 — `ub_mem_mapte_dec`

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_mem_mapte_dec` |
| 父级例化点 | `ub_mem_perm_walk`（每读回一项解码一次）；填充结果也供 `ub_mem_plb` 使用 |
| 规范 | UB Base Spec Rev 2.0 §9.4.4.2.2、§9.4.4.2.3 |
| 微架构 | [UARCH.md](../UARCH.md) §5.4 |
| 裁定 | D20 S-01 (b)；接口补丁见 [README.md](README.md) §4（Xia 裁定 2026-10-12） |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；本叶子内部不做 CDC。**Xia 裁定 2026-10-12。** |

MAPT 表项解码叶子。单项与多级共用，多一个级别 / 模式选择输入。

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
| `in_valid` | in | 1 | 原始 MAPTE 本拍有效 |
| `in_ready` | out | 1 | 本拍可收下原始 MAPTE |
| `raw` | in | 256 | 一次 32 B 表读的原始 MAPTE。内部字段位置只在私有叶子源；最终宽度见 §7 |
| `mode_multi` | in | 1 | 1 = 多级 MAPT；0 = 单项 |
| `lvl` | in | 3 | 当前级别（0 起）。最终宽度与合法范围见 §7 |
| `out_valid` | out | 1 | 解码结果本拍有效 |
| `out_ready` | in | 1 | 遍历器 / PLB 可收下。第一波可以把本口 Tied 为 1。**Xia 裁定 2026-10-12。** |
| `mapte_v` | out | 1 | 表项有效 |
| `mapte_last` | out | 1 | 本项不再指向下一级（单项且 `mapte_illegal=0` 时恒为 1） |
| `mapte_next_other_blk` | out | 1 | 下一级在其他块（首轮视为非法，见 §4） |
| `mapte_e_bit` | out | 1 | 排他位 |
| `mapte_perm_w` | out | 1 | 写许可 |
| `mapte_perm_r` | out | 1 | 读许可 |
| `mapte_perm_a` | out | 1 | 原子许可 |
| `mapte_token_chk` | out | 1 | 需要比 TokenValue |
| `mapte_base` | out | 48 | 范围起点（按级零扩展；闭区间） |
| `mapte_limit` | out | 48 | 范围终点（闭区间） |
| `mapte_next_off` | out | 30 | 下一级相对块基址的字节偏移 |
| `mapte_next_idx` | out | 16 | 下一级所在块的块表下标（首轮不用） |
| `mapte_tv0` | out | 32 | 第一个 TokenValue |
| `mapte_tv1` | out | 32 | 第二个 TokenValue |
| `mapte_illegal` | out | 1 | 配置非法；`mapte_illegal == (mapte_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `mapte_ill_cause` | out | 4 | 非法原因，编码见 [README.md](README.md) §3 |

信号束合计 214 bit（UARCH §5.4 未含本契约补的 `mapte_illegal` / `mapte_ill_cause`）。

---

## 3. 握手与时序

- 输入、输出都是同时钟 valid/ready（SPEC §3.1）。
- 预算 **R**：寄存一拍。成交到 `out_valid` 为 **1** 拍，上界 **1** 拍。
- `in_valid==1` 且 `in_ready==0` 时 `raw` / `mode_multi` / `lvl` 保持。
- `out_valid==1` 且 `out_ready==0` 时，`out_valid` 与全部输出保持。叶子兑现反压。**Xia 裁定 2026-10-12。**
- `mode_multi=0` 且 `mapte_illegal=0` 时 `mapte_last` 恒为 1。
- 复位撤销后的 `in_ready`：SPEC §3.1「复位撤销后，`valid` 与 `ready` 的首拍值：**待定**（建议 `valid=0`，`ready` 在下游能收时为 1）。」该句未闭合。按 Xia 裁定 2026-10-12：撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。

---

## 4. 非法 / 不支持配置

原因码与数值见 [README.md](README.md) §3。本叶子会用到的符号：`ILL_NONE`、`ILL_MAP_2MB`、`ILL_HW_AD`、`ILL_MAPT_OTHER_BLK`、`ILL_MAPT_MULTI_BLK`、`ILL_PTR_OOB`、`ILL_RSVD`、`ILL_UNSUP`。

**Xia 裁定 2026-10-12：** `mapte_illegal=1` 的同一 `out_valid` 拍，其余解码输出为 0（含 `mapte_next_other_blk`）。该拍只有 `mapte_illegal` 与 `mapte_ill_cause` 携带信息。多个非法原因同时成立时，取最小非 0 码。

| 符号 | 何时拉起 |
| --- | --- |
| `ILL_NONE` | `mapte_illegal=0` |
| `ILL_MAP_2MB` | 原始表项要求 2 MB 映射粒度 |
| `ILL_HW_AD` | 原始表项要求硬件写回 Access / Dirty |
| `ILL_MAPT_OTHER_BLK` | 原始表项指示下一级在其他块（首轮） |
| `ILL_MAPT_MULTI_BLK` | 多块 MAPT |
| `ILL_PTR_OOB` | 指针 / 偏移越界 |
| `ILL_RSVD` | 保留编码 |
| `ILL_UNSUP` | 其余已折成非法的首轮不支持编码 |

结构叶子跟 `mapte_illegal` / `mapte_ill_cause`。

---

## 5. 复位值

`rst_pyc` 有效期间：`in_ready=0`，`out_valid=0`，§2 全部 `mapte_*` 输出为 0（含 `mapte_illegal`、`mapte_ill_cause`）。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_MAPTE_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_MAPTE_HS_IN` | `in_valid && in_ready` 的拍收下 `raw`、`mode_multi`、`lvl`；未成交前三者保持。 |
| `AP_MAPTE_RDY` | `in_ready` 不组合依赖本拍 `in_valid`。 |
| `AP_MAPTE_LAT1` | 成交后恰好 1 拍 `out_valid=1`；间隔 ≤ 1 拍。 |
| `AP_MAPTE_HS_OUT` | `out_valid && out_ready` 的拍下游收下整束。 |
| `AP_MAPTE_OUT_HOLD` | `out_valid && !out_ready` 期间，`out_valid` 与全部输出保持。**Xia 裁定 2026-10-12。** |
| `AP_MAPTE_IN_RDY_RST` | 复位撤销后第一拍 `in_ready` 可以为 0；从第二拍起，输出侧未停时 `in_ready=1`。**Xia 裁定 2026-10-12。** |
| `AP_MAPTE_RST` | `rst_pyc` 有效期间 §5 各输出为其复位值。 |
| `AP_MAPTE_SINGLE_LAST` | `mode_multi=0` 且 `mapte_illegal=0` 时，`mapte_last=1`。 |
| `AP_MAPTE_ILL_EQ` | `mapte_illegal == (mapte_ill_cause != 0)`。**Xia 裁定 2026-10-12。** |
| `AP_MAPTE_ILL_ZERO` | `mapte_illegal=1` 的 `out_valid` 拍，除 `mapte_illegal` / `mapte_ill_cause` 外解码输出为 0。**Xia 裁定 2026-10-12。** |
| `AP_MAPTE_ILL_PRI` | 多个非法原因同时成立时，`mapte_ill_cause` 取最小非 0 码。**Xia 裁定 2026-10-12。** |
| `AP_MAPTE_ILL_2MB` | 原始表项要求 2 MB 映射时，成交拍 `mapte_ill_cause=1`（`ILL_MAP_2MB`）。 |
| `AP_MAPTE_ILL_AD` | 原始表项要求硬件写回 Access / Dirty 时，成交拍 `mapte_ill_cause=2`（`ILL_HW_AD`）。 |
| `AP_MAPTE_ILL_OBLK` | 原始表项指示下一级在其他块时，成交拍 `mapte_ill_cause=9`（`ILL_MAPT_OTHER_BLK`）。 |

---

## 7. 未知

- `lvl` 的最终宽度与合法范围。
- 单项 / 多级原始 `raw` 是否永远 256 bit。
