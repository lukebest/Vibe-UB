# M0 decisions — Luke Liu via Firstmate, 2026-10-09 11:40 (Asia/Shanghai)

D1 Spec baseline: UB Base Specification Rev 2.0 (2025-12-31). Rev 2.1 (2026-09-18) known, not adopted.

D2 Phased scope: phase 1 = PHY/PCS + DLL + LMSM + registers/CDC. NW / TP / TA deferred to later phases.

D3 SerDes/PMA analog: behavioral model at the PCS-PMA boundary (not in RTL scope).

D4 No optional spec features in phase 1 (mandatory behaviour only).

D5 All RTL authored in pyCircuit, pinned to the pyc4.0 fork lukebest/pyCircuit, generating synthesizable Verilog.

D6 Reset (decision 15A): business logic uses synchronous reset; a whitelist of handwritten SV cells is allowed (async reset synchronizer, CDC primitives) — nothing else handwritten.

D7 Verification ONLY in uvm-python (tpoikela/uvm-python, via fork lukebest/uvm-python) on top of cocotb. No SV-UVM, no unstructured bare cocotb tests. Toolchain pins:

- cocotb 1.9.2 (constraint >=1.9.2,<2 — uvm-python cannot run on cocotb 2.x)
- uvm-python: git+https://github.com/lukebest/uvm-python@96a06eee7dda1edae2013154b3d3756b040c71ad (fork of upstream 0.4.0)
- cocotb-coverage 1.2.0 (must stay <2.0; 2.0 requires cocotb>=2)
- cocotb-bus and regex: frozen from Vibe-UB-Switch's passing venv (pip freeze) when the TB is imported in M2
- Python 3.11-3.13
- Simulators: Icarus Verilog 12.0 primary (pass/fail gate); Verilator 5.032 compare and source of line coverage (cocotb 1.9.2 documents Verilator >=5.022; do not move to >=5.036 without re-qualifying)

D8 Random/coverage: directed tests + Python golden models (as in Vibe-UB-Switch); functional coverage = test-point matrix (each VERIF_PLAN TP mapped to passing TCs); constrained-random via uvm-python's built-in randomize() (cocotb-coverage crv) where useful, seed logged per run; cocotb-coverage CoverPoint/CoverCross allowed to back TPs. No pyvsc.

D9 Reuse: copy and adapt Vibe-UB-Switch pyCircuit modules and its uvm-python TB (tb/vibe/pyuvm, which is uvm-python).

D10 Existing handwritten Verilog (rtl/, tb/) moves to legacy/ later (separate PR).

D11 No FPGA prototype in phase 1.

D12 Coverage acceptance = line + functional, 100% counting named waivers; toggle excluded.

D13 TB never forces internal signals; stimulus/error injection via ports or explicit test hooks only.

D14 PHY / SerDes / DLL / process parameters: confirmed by Luke on 2026-10-09. RTT = 2 µs. ASIC scope = digital PCS + DLL only; PMA is a behavioral model (not in ASIC). ASIC process node unspecified (open item).

D15 Spec full text removed from the public repo (this PR); git history rewrite NOT done — pending Luke.

D16 Toolchain pins in D7 are recorded here; a TOOLCHAIN.lock will be added with the infrastructure PR.

# 2026-10-10 decisions — Luke Liu via Firstmate, 16:48 (Asia/Shanghai)

D17 Team roles and process adopted (see docs/TEAM.md, docs/PROCESS.md):

1. Architect Xia owns SPEC, REGMAP, plus Python golden reference models and interface assertions — RTL-independent shared answers. Verification wires those models into the scoreboard and adds end-to-end test points.
2. Design and verification work in isolated AI sessions and share SPEC, interface contracts, and assertions. Spec questions go to Xia; answers are written back to SPEC.
3. Tool gatekeeper (temporarily the verification lead) runs lint, CDC, formal, and quick synthesis on every commit. Waivers need written gatekeeper approval and a waiver-list entry (ID / 检查项 / 模块 / 理由 / 批准人 / 日期). docs/WAIVERS.md is future.
4. REGMAP is the single source that auto-generates (a) pyCircuit register R/W logic, (b) cocotb/uvm-python register models, and (c) firmware drivers; firmware and verification share the generated code. Backend runs quick synthesis before each module merge and feeds area/timing trends to design.
5. Rule libraries are split (Xia: protocol/interface; design: coding/reset/pyCircuit; verification: test specs; backend: constraints/synthesis). PM versions weekly from v0.1. Each late-bug retro yields at least one rule. Human review focuses on spec changes, interface contracts, test-point lists, CDC, reset, clock gating, timing constraints, and waivers.
6. Weekly metrics: first-pass rate and iteration count by module type; spec Q&A count by module; late bugs as 规格缺陷 / 设计错误 / 验证漏测 (back to architect/design/verification rule libraries); AI-written vs human-written escape bugs. Roll out covers every layer of the UB Base Specification (Physical through Security, plus management functions).

# 2026-10-10 decisions — Luke Liu via Firstmate, 17:04 (Asia/Shanghai)

D18 Full-layer scope: Vibe-UB implements all layers of the UB Base Specification as a complete UB controller — Physical (ch3), Data Link (ch4), Network (ch5), Transport (ch6), Transaction (ch7), Function (ch8), Memory Management (ch9), Resource Management including virtualization/RAS (ch10), Security (ch11), plus the management functions defined by the spec. The team's private spec copy is authoritative. PHY (ch3) and DLL (ch4) are the first batch; the remaining layers follow in sequence or in parallel. The D17 process covers every layer. D18 supersedes D2 (phased scope). Layer priority order after DLL, optional-feature policy (D4 currently: mandatory only in phase 1), and parallelism remain pending Luke and will be recorded as later decisions. Module list and milestone dates live in docs/SPEC.md (owned by Xia).

# 2026-10-10 decisions — Luke Liu via Firstmate, 17:22 (Asia/Shanghai)

D19 三线并行与新增角色（见 docs/TEAM.md、docs/PROCESS.md）：

1. 三条并行轨道：轨道 A = Physical（ch3）→ Data Link（ch4）→ Network（ch5）；轨道 B = Transport（ch6）→ Transaction（ch7）→ Function 层（ch8）；轨道 C = Memory Management（ch9）→ Resource Management（含虚拟化 / RAS，ch10）→ Security（ch11）。为轨道 B、C 各增设一对设计 / 验证。
2. DLL 之后的推进顺序：先打通端到端数据通路（Network → Transport → Transaction → ch8 Load/Store），随后 URMA/URPC（ch8）、memory、resource、security。轨道争用共享资源（Xia 的时间、守门、评审）时，端到端数据通路优先。
3. 可选功能：各层先实现 mandatory 功能，optional 功能集中在最后一轮。本条把 D4 扩展到全部层级。
4. 附录功能（Ethernet interworking、device hot-plug、network management over UB links）放入 M10 全栈集成之后的扩展里程碑。
5. D1（规格 Rev 2.0）与 D3（PMA 行为模型）继续有效。
