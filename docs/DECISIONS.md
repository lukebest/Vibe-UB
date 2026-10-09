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

D14 PHY / SerDes / DLL / process parameters: Xia proposes defaults, pending Luke's approval.

D15 Spec full text removed from the public repo (this PR); git history rewrite NOT done — pending Luke.

D16 Toolchain pins in D7 are recorded here; a TOOLCHAIN.lock will be added with the infrastructure PR.
