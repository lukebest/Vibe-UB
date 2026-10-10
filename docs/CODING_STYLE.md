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
  - 形式等价：规范工具是 Yosys **`equiv`**（版本见 `TOOLCHAIN.lock`）；eqy 可安装后可作为可选补充。只比 PRODUCT 已有端口（`tb_<inst>_obs_*` 不参加）。HOOKS 侧 `tb_test_mode=0`，全部 `tb_*` 钩子输入接低（含 `tb_inj_*` 复位值与 §10 点名存储的 `tb_<inst>_bd_*` / `tb_<inst>_bd_vld_*`）。必须等价，否则阻断交付。见 SPEC §11 (d)。
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
  3. [REGMAP.md](REGMAP.md) 寄存器（测试窗仅 `tb_test_mode=1` 生效）；
  4. **例外（backdoor）：** SPEC §10 **点名**的存储阵列，HOOKS 网表上的 `tb_<inst>_bd_*`（阵列 we/addr/wdata/re/rdata + 原语外 valid flop 的 `tb_<inst>_bd_vld_*`；`tb_test_mode` 门控）。PRODUCT 无这些口。等价检查：`tb_test_mode=0` 且全部 `tb_<inst>_bd_*` 输入接低。
  5. **例外（叶子只读观察）：** SPEC §10 **按叶子登记**的 `tb_<inst>_obs_*`。仅 HOOKS；只出不进；**不受** `tb_test_mode` 门控；不回灌功能。等价检查只比 PRODUCT 已有端口，观察口不参加。PRODUCT 与 quick-synth 不受影响。禁止用 keep 类属性钉内部名。未在 §10 登记的 `tb_*` 门禁拒绝。
- 禁止 force / deposit FSM 当前态或非法态。默认分支用 **具名 waiver** 覆盖（见 §7）。到达 `Link_Active` 必须走真实转移，用 `LMSM_TMR_SCALE` 缩短超时。
- 叶子内部（CRC / FEC / deskew / 缓冲）走叶子端口或 wrapper 共仿真，不加产品钩子。**除此例外外，不得**再给叶子内部缓冲加钩子。
- PCS RX unpack `n==0 && have`：**待定**（验证确认端口可达性，否则删分支或 waiver）。

---

## 5. 命名与文件

| 对象 | 约定 |
| --- | --- |
| 模块 / Python 生成单元 | `ub_<层>_<功能>`，小写+下划线。例：`ub_dll`、`ub_pcs`、`ub_lmsm`、`ub_csr`。公共存储原语：`ub_cmn_mem_1r1w`（§10） |
| 一个模块一个文件 | 生成后放 `rtl/`（按层分子目录：`rtl/dll/`、`rtl/pcs/`、`rtl/lmsm/`、`rtl/csr/`） |
| 时钟 | `core_clk`（M1 唯一时钟） |
| 复位 | 顶层 `rst_n`（低有效，异步置位）；`rst_n_sync`；业务 `rst_pyc`（`pyc_reg` 原生极性，见 SPEC §4.2） |
| 数据流 | `valid` / `ready`；源到宿前缀如 `dll2pcs_*`、`pcs2dll_*` |
| 测试钩子 | `tb_inj_*`、`tb_obs_*`、`tb_test_mode`；§10 点名存储 `tb_<inst>_bd_*`（含 `bd_vld_*`）；§10 按叶子登记的 `tb_<inst>_obs_*`（仅 HOOKS，只出） |
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
- 大缓冲 / 大表：`ub_cmn_mem_1r1w`（§10）。不得另发明第二套阵列口。

不要引入「跨时钟单拍 req-ack」再回头找原语。

---

## 9. 与现有树的关系

`rtl/`、`tb/` 下现存手写 Verilog 不是本约定的范本（异步复位、2-bit 分 lane、PCS 内 Gray）。重写以 SPEC §12 为准。

---

## 10. 统一存储原语（`ub_cmn_mem_1r1w`）

大缓冲与大表 **必须** 例化本原语，不得各写一套阵列。命名 `ub_<层>_<功能>`：层 = `cmn`，功能 = `mem_1r1w`。

**时序默认（Xia 架构提案；规范未裁定 / spec silent）：** 读 1 拍寄存、同址同拍 read-old。规范若另给时序，以规范为准并改本口说明。

| 项 | 约定 |
| --- | --- |
| 参数 | `DEPTH`、`WIDTH`（`UPPER_SNAKE`） |
| 时钟 | `core_clk`（与现有叶子同名；**不是** `clk`） |
| 复位 | **阵列无复位口**（无 `rst_n` / `rst_pyc`）；内容上电后保持，不清零。有效位在原语外，用 `rst_pyc` 同步复位 flop（与现有叶子业务寄存器相同） |
| 写口 | `we`、`waddr`、`wdata` |
| 读口 | `re`、`raddr`、`rdata` |
| 读时序 | `rdata` **寄存输出**，读延迟 **1 拍** |
| 同址同拍 | 同一拍对同一地址既读又写：读出口返回 **旧数据**（read-old） |
| 端口形态 | 1R1W（独立读写口） |

**实现：** pyCircuit **行为模型**，用 pyCircuit API 搭建，经 **pycc** 生成 Verilog。列入门禁 **stub 名单**（验证维护，与 `waivers/` 并列）。随后可换成 SRAM 宏，**不改端口、不改测试**。本原语不是手写 SV，不进 §3 白名单。

**必须例化本原语的阵列：**

| 线 | 阵列 |
| --- | --- |
| B | RTP 重传缓冲、重排（reorder）缓冲、TA 未决表 |
| C | UMMU TLB way `mem_tlb_w0`…`mem_tlb_w3`；decoder bank `mem_dec_b0`…`mem_dec_b7`；`mem_dec_tlb`。页表与 MAPT 在系统内存，不例化本原语；PLB 为 FF，不列 |

其它标 SRAM / 行为 stub 的大缓冲（如线 A `ub_dll_retry`）**应当**用同一原语，避免第二套 stub 口。

HOOKS 上的 backdoor 只允许 SPEC §10 点名的阵列，口名 `tb_<inst>_bd_*`（阵列口 + `tb_<inst>_bd_vld_*`）与门控见 SPEC §10.5 与上文 §4。PRODUCT 无 `tb_*`。

**实现路径（本 PR，接在 #20 §10 正文之后，不改写上表）：**

| 路径 | 谁 | 做什么 |
| --- | --- | --- |
| `pycircuit/cmn/` → `rtl/cmn/`（+HOOKS 时的 `tb_<inst>_bd_*`） | 设计-B | pycc 生成的**普通叶子**。走 emit-consistency + Yosys `equiv`。 |
| 门禁 stub / black box 名单 | 验证维护 | **没有**单独的 primitive 种类。本原语就是普通 pycc 叶子；**仅当**换成 SRAM 宏时才登记为 stub。换宏不改端口、不改测试。`valid_outside: true` 表示 valid 位在阵列外的复位 flop（如线 C UMMU/TLB）。 |
| `formal/cmn/` | 架构 | formal-only 可综合行为模型 + `ub_cmn_mem_1r1w_if_props`。**不是**产品 RTL。用 `$anyconst` 盯一个地址（`NSEG` bit `written` + 该地址数据），大 `DEPTH` 也能收敛。written 跟踪只在 property/bind 模块，**不进产品 RTL**。 |
| `model/ub_cmn_mem_1r1w.py` | 架构 | scoreboard 参考。 |
| `tb/cmn/` | 验证-B | cocotb + Verilator；PRODUCT 与 HOOKS。 |

**`rdata` 何时有效：** `rdata` 寄存器和阵列都**不复位**。`rdata` **只**在完成一次「已写入地址 / 段」的读之后才有效。模型 `rdata_valid` 是 **`NSEG` bit 段掩码**（`NSEG=1` 时仍是 1 bit，行为与整字写兼容）。未定义段的 `rdata` 为 None / unspecified；检查器和 scoreboard **只**比较 valid 段（整字比较仅当 `is_defined`，即全部段有效）。

**分段写使能 `WMASK_W`（默认 `WIDTH`）：** `WIDTH` 必须是 `WMASK_W` 的整数倍；`NSEG = WIDTH/WMASK_W`。`NSEG=1`（整字写）端口表不变。仅当 `NSEG>1` 时多一个输入 `wmask[NSEG-1:0]`：bit i=1 写第 i 段（`[i*WMASK_W +: WMASK_W]`），其余段保持旧值。同址同拍 **按段 read-old**。

**变体命名：** `ub_cmn_mem_1r1w_d<DEPTH>w<WIDTH>`；`NSEG>1` 时追加 `m<WMASK_W>`。例：C 线 `ub_cmn_mem_1r1w_d512w512m64`；门禁 / formal 小配置 `ub_cmn_mem_1r1w_d64w64m16`。

**`ASSERT_NO_UNINIT_READ`（默认 1）：** written **按段**跟踪。`=1`：读时该字**任一**段自复位以来未写过即违规。`=0`：不报违规（未写段的 `rdata` 未定义，由所有者屏蔽）。Python 构造参数 `assert_no_uninit_read`；形式化模块参数 `ASSERT_NO_UNINIT_READ`。门禁名单 `valid_outside: true` 的实例（valid 在阵列外）设 **0**。复位之后阵列内容同样未定义。

**formal：** `$anyconst` 盯一个地址。性质：未掩码段不变、掩码段写入、按段 read-old、按段未初始化检查。覆盖：单段写、相邻段写、全段写。跑现有整字小配置 + `d64w64m16`。

**越界：** RTL **不截断**地址。`we`/`re` 时 `waddr`/`raddr >= DEPTH` 由断言标出（非 2 幂 `DEPTH` 时 `AW` 多出的编码会走到这里）。
