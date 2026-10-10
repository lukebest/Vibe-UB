# Changelog

## Unreleased

### Added

- `scripts/impl/buffer_fanout.py`：Yosys JSON 上确定性 `buf_4`/`buf_8` 扇出树（quick-synth 默认在 abc 之后调用）。
- 工具守门 CI：`.github/workflows/gate.yml` + `scripts/gate/` + `make gate`（emit / 端口一致性 / lint / CDC / formal / synth-check / regmap `--check` / tb-selfcheck）。名单在 `gate/`（legacy / handwritten / stubs / hooks_ports），豁免在 `waivers/`，批准规则相同。等价主工具 eqy（`TOOLCHAIN.lock` `eqy_lock`），不可用则回退 Yosys `equiv_*` 并注明工具。规则分册 `docs/rules/verif_gate.md`。CODEOWNERS 将 `waivers/`、`gate/`、gate workflow 指给 `lukebest`。不改 `rtl/`、`tb/models/`、`model/`。SPEC §11 仅补 Xia 端口裁定 (f)。
- `docs/VERIF_PLAN.md` §8.8：轨道 C 内存管理（UMMU + 译码器）测试点（docs-only；公共 §8.7 / §13 / §14 / §15 另 PR 并入）。
- `scripts/impl/quick_synth.sh`：合入前叶子快速综合（Yosys flatten + Sky130 hd tt proxy + OpenSTA 最差建立路径）。Informational；不进验证门禁。规则见 `docs/rules/impl_quick_synth.md`。
- `TOOLCHAIN.lock` + `tb/` uvm-python 骨架、golden-model 接口、双网表自检入口（叠在 M1 SPEC 上；不改 `rtl/` / SPEC 类文档）。
- TB 模型按 CODING_STYLE §5 命名：`ub_dll_bcrc` 已按 SPEC §2.6 写全；`ub_pcs_scrambler` 已按已定项实现，抽头与 `AMCTL.LID`→种子为必填参数（SPEC §13，无默认）；`ub_pcs_lane_dist` 已实现。无 LMB/LTB golden。
- `tb/vibe_uvm/ub_csr_map.py` + harness：`CNT_CLR` `0x0224` bit0–8（含 `CNT_CRD_UF`）；`APPD_LMSM_ST` `0x1E00`；`APPD_PORT_ERR` `0x1F00`；TEST 窗按 SPEC §3.2.3 / §10 / §11、REGMAP §2.4。`CTRL.LMSM_START`、`RETRY_*_ST` 与 `NUM_LANES_*` 合法编码及保留值 TB assert。
- `docs/SPEC.md`：M1 功能规格（范围、模块划分、接口、时钟复位、状态机、异常、参数、测试钩子、两套 `TEST_HOOKS` 网表）。
- `docs/REGMAP.md`：M1 寄存器表（CTRL/STATUS/PARAM/ERR/TEST + App. D 端口子集镜像）。
- `docs/CODING_STYLE.md`：pyc4.0 生成、同步复位、白名单单元、禁止 force/deposit、lint/waiver、两套网表门禁。
- `docs/TEAM.md`：角色表、所有权、角色接口、工具守门与豁免、人工评审重点（D17）。
- `docs/PROCESS.md`：每模块节拍、工具流水线、REGMAP 单一来源、规则库每周版本、每周复盘指标、PHY 先行、过渡安排（D17）。
- `docs/rules/`：architect / design / verification / backend 规则库骨架（v0.1）。
- `docs/DECISIONS.md` D17：团队分工与流程（Luke Liu via Firstmate，2026-10-10 16:48 Asia/Shanghai）。
- `docs/DECISIONS.md` D18：全层级范围，作为完整 UB 控制器（Luke Liu via Firstmate，2026-10-10 17:04 Asia/Shanghai）；D18 取代 D2 的分阶段范围。
- `docs/DECISIONS.md` D19：三线并行与新增角色（Luke Liu via Firstmate，2026-10-10 17:22 Asia/Shanghai）。
- `docs/arch/mem/UARCH.md`：线 C 第 9 章内存管理微架构草案（UMMU + 译码器结构；解码叶子与结构叶子分开；不冻结端口）。

### Changed

- SPEC §2.2：pyCircuit 源码目录与导入（已定）——叶子 `pycircuit/<层>/<leaf>.py`，门禁只扫该层 `*.py`（跳过 `lib/` 与 `__init__.py`）；同层 helper 在 `pycircuit/<层>/lib/` 不出网表；导入根 `pycircuit/`（`from <层>.lib import ...`），门禁 / `emit_rtl.py` / tb 把 `pycircuit/` 置于 `PYTHONPATH` 最前；仓库根目录不进 `sys.path`；工具按脚本路径调用。门禁细则见 `docs/rules/verif_gate.md`（PR #33）。架构 Xia 与守门人验证 2026-10-10 共同定。
- `docs/rules/verif_gate.md` v0.6：导入根统一为 `<repo>/pycircuit`（`PYTHONPATH` 最前，叶子 `from <层>.lib import ...`）；仓库根不得进 `sys.path`（与已安装 pyCircuit 库同名会遮蔽；#27 的 `pycircuit is not importable` / `No module named 'mem'`）。叶子只扫 `pycircuit/<层>/*.py`，跳过 `lib/` 与 `__init__.py`；`lib/` 不生成网表，仍跑禁止拼接 Verilog 文本。调用用脚本路径 + `python -P`，不用 `python -m`。与 SPEC §2.2 对齐。
- `docs/rules/verif_gate.md` v0.5：`COMBO_DEPTH` 只数逻辑门；与实现快速综合对照时用 #31 已合入的 `logic depth` 列（等于 `--no-buffer` 级数；`depth incl. buf` 是含缓冲级数），slack / 面积用带缓冲器版本。emit 按 `TOOLCHAIN.lock` 装 pycc，装不上或无 `emit_rtl.py` 则跳过并写原因。大网表 `rtl/<层>/manifest.yml`。`rtl/pyc_lib/` 有则逐字节、无则跳过（等 #21）。`tb_<inst>_obs_*` 与 `ub_mem_tlb` §10 口。sby bind 信号必须存在。D10/迁移名册缺文件标「已删除」并扣总数，不删文件。synth-check 模块超时 180s、job 25 min，报告最慢 3 个模块。
- SPEC §2.6：BCRC 流式接口拍位（已定）：`start`/`valid_in` 同拍计入首 flit；`start`/`valid_in`/`last` 同拍只算末 4 字节 BCRC 之前的 16 字节并 1 拍给出 `crc_word`；`start==1 && valid_in==0` 只复位全 1；未见 `last` 再 `start` 以新块初值重算。与 `tb/models/ub_dll_bcrc.py` 的 `start()`/`eat()` 一致。架构 Xia 2026-10-10 裁定。
- `scripts/impl/quick_synth.*` + `docs/rules/impl_quick_synth.md` v0.5：每叶子拆两列深度——`logic depth` 不计 `buf_*`/`clkbuf_*`/`qs_fbuf_*`（与 `--no-buffer`、COMBO_DEPTH、日后 pycc `--logic-depth` 同口径）；`depth incl. buf` 为含缓冲级数。slack/area 仍来自缓冲后网表。
- `scripts/impl/quick_synth.*` + `docs/rules/impl_quick_synth.md` v0.4：abc 映射后默认插确定性 Sky130 `buf_4`/`buf_8` 扇出树（max fanout 16；`--no-buffer` / `--max-fanout`；每叶子报 max fanout）。OpenROAD `repair_design` 未作为本 proxy 路径（VM 无 OpenROAD、且无 floorplan）。`sta -version` 探测版本，避免 `sta -no_init -exit` 无脚本挂起。
- `docs/rules/verif_gate.md` v0.4：后门命名 `tb_<inst>_bd_*` / `tb_<inst>_bd_vld_*`（HOOKS only，§10 登记，eqy 拉低）；`ub_cmn_mem_1r1w` 时钟口 `core_clk`；存储变体 `d<DEPTH>w<WIDTH>[m<WMASK_W>]`；大变体 PRODUCT/HOOKS 除模块名外逐字节 + 端口，不跑完整 equiv。emit 只调用 `scripts/emit_rtl.py` 重生成到临时目录后逐字节比对（脚本不在则 skip）。`TOOLCHAIN.lock` 只认仓库根，第二份报冲突。regmap `variants:`（PR #11 格式）`product_` 的 `SCR_PLACEHOLDER` 必须为 0，`=1` 非 PRODUCT 只 lint/TB，`NUM_VL`/`NUM_LANES` 与变体名一致。GATE-TB-SB-001：分段比对按段计次数。
- `docs/rules/verif_gate.md` v0.3：§8.0.1 / §11 增补 GATE-TB-SB-001（记分板须统计实际比对次数，结束时断言次数 `> 0` 且等于预期；审查清单，不自动拦截）。
- `docs/TEAM.md` §4、`docs/PROCESS.md` §2：豁免清单从 `docs/WAIVERS.md` 改为 `waivers/`。
- `scripts/impl/quick_synth.*` + `docs/rules/impl_quick_synth.md` v0.3：Yosys 默认 `-I rtl/pyc_lib`（pycc `pyc_reg.v` 等；未落地时回退 `rtl/common` 并 WARN）；`--incdir` / `QS_INCDIRS` 为额外路径；`pyc_*` 不作报告 top；`ub_dll_crc32` / `ub_dll_crc_check` / `ub_controller_tx` / `ub_controller_rx` 只报「待删除 / to be deleted」，不进合计、不对 baseline。
- SPEC §2.2 + CODING_STYLE §1 / §5：pycc 运行库原语（`pyc_reg.v` 等运行时发出的 `pyc_*`）只放 `rtl/pyc_lib/`，从 `TOOLCHAIN.lock` 钉死版本原样拷贝、不得改；其它 `rtl/<layer>/` 与 `hooks/` 不得含 `pyc_*`；filelist 引用该目录；`` `include `` 用 `-I rtl/pyc_lib`。门禁细则见 `docs/rules/verif_gate.md`。
- `docs/VERIF_PLAN.md`：公共 §8.7 / §13 / §14 / §15 并入轨道 C 内存管理计数与追溯（§8.8 正文不动）。
- `scripts/impl/quick_synth.*` + `docs/rules/impl_quick_synth.md` v0.2：按 SPEC §2.2 每文件一个 top（无必经 `chparam`）；`_placeholder` 单独表且不计入 PRODUCT 面积；`--baseline-map` / `--baseline-report` 对照旧模块+参数；QoR（cells / area / depth / slack）相对 baseline 超 10% 标旗；`ub_cmn_mem_1r1w`（及 `scripts/gate/blackbox.yml`）超过可配 4096-bit 阈值作黑盒并报 SRAM 估算列，小实例仍综合为 flop；STA 按 1 拍 registered read。
- `docs/SPEC.md` §2.2：pycc 按参数集展开固定网表（`<leaf>_<tag>` 命名；占位变体 `_placeholder`）。
- 架构关闭若干待定项：M1 单时钟 80.57 MHz、`rst_n` 封装、CSR 整字/1 拍/未映射 `csr_err`、非法 VL 丢包、信用下溢计数+irq（TB assert）、`irq` 高有效默认全屏蔽、预编码默认关、信用钩子仅 VL0、`tb_obs_lmsm_st` 仅顶层编码。
- LTB/CLTB 字段口（SPEC §3.3.4）；去掉 `pma_rx_ready` / `pcs2dll_ready`（RX valid-only）；计数 RO + `CNT_CLR`；`PORT_RST` 16 拍脉冲及复位范围；`tb_inj_crd_cells` 每拍 mux；TEST 窗 `tb_test_mode=0` 时已映射且 `csr_err=0`；`ub_rst_sync` 2 级；`CRD_UF` 具名 waiver。
- App. D 镜像迁址：`APPD_LMSM_ST` `0x2400`→`0x1E00`；`APPD_PORT_ERR` `0x2500`→`0x1F00`。
- 关闭 Q4 剩余项：TX Lane_ID 由 PCS 按 `lmsm2pcs_lane_id_mode` / `lmsm2pcs_lane_id_base` / `lmsm2pcs_lane_id_map` 逐 lane 填写后再算 CRC；LMB 字段在每帧 LMB 起始锁存，无多拍 valid 稳定要求。
- `lmsm2pcs_lane_id_mode` 编码 3 为保留：LMSM 不驱动（TB assert）；PCS 与 2（NULL）同分支解码，无需 waiver。
- 关闭加扰/BCRC/`ERROR_FLAG`：种子源为 `AMCTL.LID`（叶子口 `amctl_lid[3:0]`）；PRBS23 状态 23 bit、每 lane 32-bit 通路（抽头与 LID→种子映射仍待定）；BCRC CRC30 `30'h15A94AD5`、初值全 1、余数不取反、每字节 MSB 先、`{rsvd, ERROR_FLAG, CRC30}`；TX `ERROR_FLAG` 恒 0（无 ECC、无 `nw_tx_err`），RX 用 `nw_rx_err`；PMA 字符号 0 在 LSB。
- 模块名对齐 CODING_STYLE §5：`pcs_fec_enc`→`ub_pcs_fec_enc`，`pcs_fec_dec`→`ub_pcs_fec_dec`，`pcs_scrambler`→`ub_pcs_scrambler`，`pcs_descrambler`→`ub_pcs_descrambler`，`pcs_lane_dist`→`ub_pcs_lane_dist`，`pcs_lane_dedist`→`ub_pcs_lane_dedist`，`pcs_amctl_tx`→`ub_pcs_amctl_tx`，`pcs_amctl_rx`→`ub_pcs_amctl_rx`，`pcs_deskew`→`ub_pcs_deskew`，`segmenter`→`ub_dll_segmenter`，`reassembler`→`ub_dll_reassembler`，BCRC TX/RX→`ub_dll_bcrc` / `ub_dll_bcrc_check`，credit/VL/retry→`ub_dll_credit` / `ub_dll_vl` / `ub_dll_retry`。
- `LMSM_CTRL.START` 更名为 `CTRL.LMSM_START`（REGMAP `0x0000` bit1）。关闭 `STATUS.RETRY_REQ_ST` / `RETRY_ACK_ST` 与 `PARAM_PHY.NUM_LANES_{TX,RX}` 编码（二进制 1/2/4/8）；保留值 RTL 不产出、TB assert。
- `docs/TEAM.md`、`docs/PROCESS.md`：按 D18 写全层级范围；PROCESS §6 为「全层级推进」。
- `docs/TEAM.md`、`docs/PROCESS.md`：按 D19 写入三条轨道、轨道所有权，以及「设计-B」/「验证-B」、「设计-C」/「验证-C」新角色。
- `docs/CODING_STYLE.md` §10：统一存储原语 `ub_cmn_mem_1r1w`（`DEPTH`/`WIDTH`；时钟口 `core_clk`；阵列无复位；1R1W `we/waddr/wdata` + `re/raddr/rdata`；读 1 拍寄存、同址 read-old — Xia 提案，规范未裁定）。pyCircuit 行为模型、pycc 生成、门禁 stub 名单；换宏不改口。线 B RTP 重传/重排、TA 未决与线 C `mem_tlb_w0`…`w3` / `mem_dec_b0`…`b7` / `mem_dec_tlb` 必须例化。页表与 MAPT 在系统内存；PLB 为 FF。
- SPEC §10.5 + CODING_STYLE §4：§10 点名存储允许 HOOKS-only `tb_<inst>_bd_*`（阵列 we/addr/wdata/re/rdata + 原语外 valid flop 伴随口 `tb_<inst>_bd_vld_*`），`tb_test_mode` 门控；等价检查接低。其它叶子内部缓冲不得加钩子。不改 TEAM/PROCESS/DECISIONS；不改 `regmap.yaml`。
- SPEC §11 (d) / §10.5 / CODING_STYLE：PRODUCT vs HOOKS 形式等价的规范工具改为 Yosys **`equiv`**（版本见 `TOOLCHAIN.lock`）；eqy 可安装后作可选补充。规则不变：`tb_test_mode=0`，全部 `tb_*` 钩子**输入**（含 `tb_<inst>_bd_*` / `tb_<inst>_bd_vld_*`）接低；只比 PRODUCT 已有端口。
- SPEC §10 / §10.5 / §11 + CODING_STYLE §4：增加叶子只读观察口 `tb_<inst>_obs_*`（与 `tb_<inst>_bd_*` 并列）。仅 HOOKS、只出、不受 `tb_test_mode`、不回灌；未登记 `tb_*` 门禁拒绝；不用 keep 钉内部名。首个叶子 `ub_mem_tlb`：`tb_mem_tlb_obs_lkup_v`、`obs_hit[3:0]`、`obs_vld[3:0]`、`obs_tag_w0`…`w3`（各 60）；四口对齐查找请求下一拍（原语寄存 `rdata` 比较拍）。断言仅 `lkup_v=1`。`formal/mem/` 经 HOOKS bind。PRODUCT / quick-synth 不受影响。
- SPEC §2.2 / §11 (f) + CODING_STYLE §1：PM（对齐验证）— 超过 `impl_quick_synth.md` 黑盒阈值（默认 4096 bit）的变体不提交 `.v`。每层 `rtl/<layer>/manifest.yml`，每变体一条：变体名、参数、pycc 版本、PRODUCT/HOOKS sha256。门禁按 `TOOLCHAIN.lock` 装 pycc，`emit_rtl.py` 再生并核 sha256/端口；PRODUCT 与 HOOKS 除模块名外字节相同。超阈值 `.v` 或 manifest 再生失败均拒绝。细则见 `docs/rules/verif_gate.md`。其余生成 `.v` 仍提交。
