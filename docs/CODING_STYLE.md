# Vibe-UB 编码约定（M1）

产品数字逻辑 **全部** 由 pyCircuit（pyc4.0，fork `lukebest/pyCircuit`，见 [DECISIONS.md](DECISIONS.md) D5）生成可综合 Verilog。禁止手写产品 SystemVerilog。

配套：[SPEC.md](SPEC.md)、[REGMAP.md](REGMAP.md)。

---

## 1. 生成与网表

- 源码是 Python（pyCircuit）。提交的产品 `.v` 必须能从当前 Python **再现**。
- `TEST_HOOKS` 在 **Python 生成期** 展开，产出两套 Verilog。规则见 [SPEC.md](SPEC.md) **§11**，此处不重复例外：
  - **PRODUCT**（`TEST_HOOKS=0`）：无 `tb_*` 端口；lint / CDC / 综合 / 实现 / FPGA **只认这一套**。
  - **HOOKS**（`TEST_HOOKS=1`）：须过 lint 与 CDC，**不得**实现。回归与行覆盖率在此网上跑（`tb_test_mode` 为 0 与 1）；覆盖率分母含钩子 mux，钩子代码不另开 waiver。
  - PRODUCT 另跑与钩子无关的 smoke。
  - 形式等价（Yosys eqy 或同等开源工具）：PRODUCT vs HOOKS（`tb_test_mode=0` 且全部 `tb_inj_*` 接复位值）必须等价，否则阻断交付。
- 禁止在生成 Verilog 里再用 `` `ifdef TEST_HOOKS `` 做第二套分叉。

---

## 2. 复位与 CDC

- 业务寄存器只用 `pyc_reg`（**同步复位**，D6）。敏感表只有时钟。
- 顶层 `rst_n`：低有效，**异步置位、同步释放**，只经白名单 `ub_rst_sync`（**2 级**触发器）→ `rst_n_sync`。
- 封装 `ub_pyc_rst_adapt` 把 `rst_n_sync` 转到 `pyc_reg` **原生极性**（`rst_pyc`）。业务模块只接 `rst_pyc`。若库原生已是低有效，封装为连线。见 SPEC §4.2。
- M1 **单时钟** `core_clk` ≈ 80.57 MHz，无 `pma_clk`（`USE_PMA_CLK=0` 已定）。产品通路无 CDC。
- 跨时钟原语（后续阶段才用）：
  - 1-bit 电平：`pyc_cdc_sync`（**仅 1 bit**）。
  - 多 bit：`pyc_async_fifo`。
  - **没有** pulse / req-ack 同步原语 → 接口不得依赖跨时钟脉冲。

---

## 3. 允许手写的 SV（白名单）

仅下列单元可以手写 SystemVerilog，且必须单独成文件、接口稳定、有评审记录：

| 单元 | 用途 |
| --- | --- |
| `ub_rst_sync` | 2 级；异步置位 / 同步释放：`rst_n` → `rst_n_sync` |
| CDC 原语封装 | 若需把 `pyc_cdc_sync` / `pyc_async_fifo`  generater 接到库单元；不得发明 pulse 同步器 |

白名单之外的手写 SV（含「只改一拍」的修补）禁止进入产品路径。现有 `rtl/*.v` 手写实现按 D10 迁 `legacy/`，不作为风格样板。

---

## 4. 验证不得碰内部信号

- TB **不得** `force` 或 `deposit` 内部信号（D13）。
- 注入与观察 **只允许**：
  1. 顶层功能端口；
  2. [SPEC.md](SPEC.md) §10 列出的 `tb_inj_*` / `tb_obs_*`（且 `TEST_HOOKS=1` 与 `tb_test_mode` 门控）；
  3. [REGMAP.md](REGMAP.md) 寄存器（测试窗仅 `tb_test_mode=1` 生效）。
- 禁止 force / deposit FSM 当前态或非法态。默认分支用 **具名 waiver** 覆盖（见 §7）。到达 `Link_Active` 必须走真实转移，用 `LMSM_TMR_SCALE` 缩短超时。
- 叶子内部（CRC / FEC / deskew / 缓冲）走叶子端口或 wrapper 共仿真，不加产品钩子。
- PCS RX unpack `n==0 && have`：**待定**（验证确认端口可达性，否则删分支或 waiver）。

---

## 5. 命名与文件

| 对象 | 约定 |
| --- | --- |
| 模块 / Python 生成单元 | `ub_<层>_<功能>`，小写+下划线。例：`ub_dll`、`ub_pcs`、`ub_lmsm`、`ub_csr` |
| 一个模块一个文件 | 生成后放 `rtl/`（按层分子目录：`rtl/dll/`、`rtl/pcs/`、`rtl/lmsm/`、`rtl/csr/`） |
| 时钟 | `core_clk`（M1 唯一时钟） |
| 复位 | 顶层 `rst_n`（低有效，异步置位）；`rst_n_sync`；业务 `rst_pyc`（`pyc_reg` 原生极性，见 SPEC §4.2） |
| 数据流 | `valid` / `ready`；源到宿前缀如 `dll2pcs_*`、`pcs2dll_*` |
| 测试钩子 | 仅 `tb_inj_*`、`tb_obs_*`、`tb_test_mode` |
| 参数 | `UPPER_SNAKE`，与 SPEC §9 标识符一致 |
| 常量 / 枚举 | `UPPER_SNAKE` |
| 禁止 | 与验证旧名 `vibe_*` 混用产品模块名（映射见 SPEC §10） |

---

## 6. 禁止出现在产品 RTL 中的结构

- `$display`、`$monitor`、`$strobe`、`$write` 及类似系统任务。
- `force` / `release`。
- 对内部层次的层次路径引用（`tb.dut.u_foo.bar`）写在产品模块里。
- 异步复位的业务 `always`（`or negedge rst_n`）。
- 手写的非白名单门控时钟、脉冲同步、双沿寄存器。
- X 传播依赖（用 X 当逻辑）。

仿真打印放在 TB（uvm-python / cocotb），不放生成 RTL。

---

## 7. Lint 与 waiver

- 门禁：`verilator --lint-only` 对 **PRODUCT** 与 **HOOKS** 两套网表均为 **0 error**。
- warning 不得默默留下：每条 warning 要么改代码消除，要么写 **具名 waiver**（文件+行或规则 ID+理由+批准人）。
- FSM 默认分支、不可达臂：用命名 waiver 覆盖，**不要**靠 force 非法态来「测到」。
- 钩子 mux 代码（HOOKS 网表）**不**单独开覆盖率 waiver（SPEC §11 (b)）。
- 信用下溢 `CRD_UF` 计数与 irq 分支：具名 waiver `WAIVER_CRD_UF_CNT`、`WAIVER_CRD_UF_IRQ`（SPEC §13.4）。禁止 force 下溢来打覆盖率。
- toggle 覆盖不计入接收（D12）。行覆盖 + 功能覆盖（测试点矩阵）= 100%（计具名 waiver）。

---

## 8. 接口可表达性（pyc4.0）

设计接口时只使用下列原语能表达的东西：

- `pyc_reg`：同步复位寄存器。
- `pyc_cdc_sync`：1-bit。
- `pyc_async_fifo`：多 bit 跨时钟。
- 同时钟 `valid`/`ready` 或 CSR `req`/`ready`。

不要引入「跨时钟单拍 req-ack」再回头找原语。

---

## 9. 与现有树的关系

`rtl/`、`tb/` 下现存手写 Verilog 不是本约定的范本（异步复位、2-bit 分 lane、PCS 内 Gray）。重写以 SPEC §12 为准。
