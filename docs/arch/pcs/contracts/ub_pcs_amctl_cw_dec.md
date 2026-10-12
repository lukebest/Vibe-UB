```yaml
leaf: ub_pcs_amctl_cw_dec
parent: ub_pcs_amctl_rx
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
  - {name: word, dir: in, width: 32, desc: 本 lane 经 amctl_rx 滑窗后的 32-bit 字}
  - {name: word_vld, dir: in, width: 1, desc: 本拍字有效；来自共享 pma_rx_valid}
  - {name: end_hit, dir: out, width: 1, desc: 本字 END 经 eBCH-16 纠正后匹配；供 amctl_rx 锁定/滑窗}
  - {name: amctl_vld, dir: out, width: 1, desc: 1 拍脉冲；AMCTL 末符号所在字的下一拍}
  - {name: end_ok, dir: out, width: 1, desc: 本窗 END 有效；仅 amctl_vld 时有意义}
  - {name: lid, dir: out, width: 4, desc: 已纠正 LID；空身份公开称 LID_NULL}
  - {name: lid_ok, dir: out, width: 1, desc: 两半 LID 一致}
  - {name: ctrl_type, dir: out, width: 3, desc: 项目枚举 FEC_CTRL/LW_SWITCH/EI/PERIOD_CTRL/REMOTE_LW_SWITCH/RSVD/NO_CMD}
  - {name: ctrl_type_ok, dir: out, width: 1, desc: 任一半合法；两半不同合法码字则 0}
  - {name: ctrl_detail, dir: out, width: 4, desc: 项目枚举 X0/X1/X2/X4/X8/EEI/PERIOD0/PERIOD1/OPEN_FEC/CLOSE_FEC/RSVD/NO_CMD}
  - {name: ctrl_detail_ok, dir: out, width: 1, desc: 与 ctrl_type_ok 同一半场规则}
params: []
ill_cause_width: 4
status: draft
```

# 公开信号契约 — `ub_pcs_amctl_cw_dec`

YAML 机读头按 [docs/arch/mem/contracts/README.md](../../mem/contracts/README.md) §8 的固定键写（`leaf` / `parent` / `clock` / `latency` / `ports` / `params` / `ill_cause_width` / `status`）。寄存叶子不写 `comb_budget_ns`。该 README 现于 PR #43，尚未合入 main；本 PR 不把它并进来。schema 源就是那一份，本文件不另立键。

| 项 | 值 |
| --- | --- |
| 叶子 | `ub_pcs_amctl_cw_dec` |
| 父级例化点 | `ub_pcs_amctl_rx`。每硬件 lane **一份**单 lane 实例；父叶静态例化 `NUM_LANES_RX` 份（`PARAM_PHY.NUM_LANES_RX` 同参数族）。编号 ≥ `pma_rx_width` 的实例由 `amctl_rx` 忽略。面积按**单实例**证明 |
| 规范 | UB-PHY §3.2.4.2 / 表 3-7..3-10 / 「AMCTL Identification Mechanism」/ §3.2.4.4。公开只写语义与节/表号 |
| 清单 | [MODULE_INVENTORY.md](../../MODULE_INVENTORY.md) `ub_pcs_amctl_rx` / `ub_pcs_amctl_cw_dec` |
| 裁定 | 船长确认走 C 线 S-01(b)。Xia 裁定 2026-10-12 |
| 私有源 | `lukebest/Vibe-UB-private`（公开叙述称独立私有仓库）。码字表不进公开 SPEC |
| 时钟域 | 单一 `core_clk`，同步复位 `rst_pyc`，目标周期 12.412 ns（`F_CORE` 80.57 MHz，SPEC §4.1），时序估计走 Sky130 代理；本叶子内部不做 CDC。**Xia 裁定 2026-10-12。** |

本叶内部持有 AMCTL 窗口（40 符号）及全部场/符号位置；公开契约不列下标。父叶只认具名口。

---

## 1. 时钟与复位

| 端口 | 方向 | 宽度 | 含义 |
| --- | --- | --- | --- |
| `core_clk` | in | 1 | 单时钟，≈80.57 MHz，目标周期 12.412 ns（SPEC §4.1） |
| `rst_pyc` | in | 1 | `pyc_reg` 原生极性；业务寄存器同步复位（CODING_STYLE §2） |

`clock` / `rst_pyc` 同时列入 YAML `ports`（schema §8）。

---

## 2. 端口

| 端口 | 方向 | 宽度 | 含义 |
| --- | --- | --- | --- |
| `word` | in | 32 | 本 lane 经 `amctl_rx` 滑窗之后的 32-bit 字 |
| `word_vld` | in | 1 | 本拍字有效。来自共享 `pma_rx_valid` |
| `end_hit` | out | 1 | 本字 END 经 eBCH-16 纠正后匹配。`amctl_rx` 锁定/滑窗 FSM 用。**不受** `amctl_vld` 限定 |
| `amctl_vld` | out | 1 | **1 拍脉冲**。出现在携带 AMCTL **末符号**的那一字之后 1 拍 |
| `end_ok` | out | 1 | 本窗 END 有效。仅 `amctl_vld=1` 时有意义 |
| `lid` | out | 4 | 已纠正 LID。lane 0..7 或 `LID_NULL`（`LID_NULL` 线码是本叶私有细节） |
| `lid_ok` | out | 1 | 两半 LID 一致 |
| `ctrl_type` | out | 3 | 项目枚举，见 §4 |
| `ctrl_type_ok` | out | 1 | 任一半解出合法码字为 1；两半解出**不同**合法码字则为 0 |
| `ctrl_detail` | out | 4 | 项目枚举，见 §4 |
| `ctrl_detail_ok` | out | 1 | 与 `ctrl_type_ok` 同一半场规则 |

`end_ok` / `lid` / `lid_ok` / `ctrl_type` / `ctrl_type_ok` / `ctrl_detail` / `ctrl_detail_ok` 受 `amctl_vld` 限定。`desc` 只写解码后语义。

---

## 3. 握手与时序

- 本叶是 **valid-only**（SPEC §3.2.4 / §13 A-05）：输入 `word_vld`，无 `ready`。不套 schema README §1 第 4 条的 valid/ready 成交（那条写的是 C 线表项解码）。
- `latency.kind = registered`，`cycles = 1`，`max_cycles = 1`。不写 `comb_budget_ns`（schema §8：寄存叶子不得带该键）。
- `word` / `word_vld` 在 **t** → 输出在 **t+1**。
- `pcs_rx_sdf_seen` 的 t / t+1 / t+2 在父叶，见 [MODULE_INVENTORY.md](../../MODULE_INVENTORY.md)。

---

## 4. 项目枚举（不是规范码字）与 `ill_cause_width`

下列取值是本项目枚举，**不是** UB-PHY 码字。

`ctrl_type[2:0]`：

| 值 | 符号 |
| --- | --- |
| 0 | `FEC_CTRL` |
| 1 | `LW_SWITCH` |
| 2 | `EI` |
| 3 | `PERIOD_CTRL` |
| 4 | `REMOTE_LW_SWITCH` |
| 5 | `RSVD` |
| 6 | `NO_CMD` |

`ctrl_detail[3:0]`：

| 值 | 符号 |
| --- | --- |
| 0 | `X0` |
| 1 | `X1` |
| 2 | `X2` |
| 3 | `X4` |
| 4 | `X8` |
| 5 | `EEI` |
| 6 | `PERIOD0` |
| 7 | `PERIOD1` |
| 8 | `OPEN_FEC` |
| 9 | `CLOSE_FEC` |
| 10 | `RSVD` |
| 11 | `NO_CMD` |

`LID_NULL`：公开只称此名。

`ill_cause_width: 4` 按 schema 固定键填写。本叶**不**产 `*_illegal` / `*_ill_cause` 口，也不引用 C 线 §3 非法码表。

---

## 5. 复位值

寄存输出在 `rst_pyc` 有效期间为 0：`end_hit`、`amctl_vld`、`end_ok`、`lid`、`lid_ok`、`ctrl_type`、`ctrl_type_ok`、`ctrl_detail`、`ctrl_detail_ok`。

---

## 6. 接口断言（桩与私有叶子共同满足）

| 名字 | 性质 |
| --- | --- |
| `AP_CWDEC_CLK` | 只存在 `core_clk` 与同步 `rst_pyc`；叶子内部不做 CDC。 |
| `AP_CWDEC_LAT1` | `word_vld` 在 t 的字，对应输出在 t+1。 |
| `AP_CWDEC_AMCTL_VLD` | `amctl_vld` 是 1 拍脉冲，出现在末符号字之后 1 拍。 |
| `AP_CWDEC_QUAL_ZERO` | `amctl_vld=0` 时，除 `end_hit` 外全部输出为 0。 |
| `AP_CWDEC_OK_WITH_VLD` | `lid_ok` / `ctrl_type_ok` / `ctrl_detail_ok` / `end_ok` 只在 `amctl_vld=1` 时可为 1。 |
| `AP_CWDEC_LID_OK` | `amctl_vld=1` 时，`lid_ok=1` 当且仅当两半 LID 一致。 |
| `AP_CWDEC_CTRL_OK` | `amctl_vld=1` 时：任一半合法则对应 `*_ok` 可为 1；两半解出不同合法码字则 `*_ok=0`。 |
| `AP_CWDEC_RST` | `rst_pyc` 有效期间 §5 各输出为 0。 |

---

## 7. 未知

无。公开面已由 Xia 裁定 2026-10-12 闭合。码字表与符号下标按 S-01(b) 留在私有源，不是未知。
