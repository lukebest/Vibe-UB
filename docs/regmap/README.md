# Register map — single source

`docs/regmap/regmap.yaml` is the **single machine-readable source** for the M1 CSR map.
Do not hand-edit generated files.

The human table `docs/REGMAP.md` is regenerated from the YAML. A JSON Schema lives at
`docs/regmap/schema.json`; `scripts/regmap_lib.py` is the documented Python validator
(overlap, 32-bit fit, unique aligned addresses, reset/enum width).

UB Base Spec body text is **not** copied here — cite section numbers only.

## Commands

```bash
# regenerate all outputs
python3 scripts/gen_regmap.py

# consistency check (temp dir + diff; non-zero on drift)
python3 scripts/gen_regmap.py --check

# schema / semantic validation only
python3 scripts/gen_regmap.py --validate-only

# pytest
pytest scripts/tests
```

`scripts/check_regmap_gen.sh` is a wrapper around `--check`.

## Generated paths

| Path | Role |
| --- | --- |
| `docs/REGMAP.md` | Human table (header: `GENERATED — edit docs/regmap/regmap.yaml`) |
| `pycircuit/csr/ub_csr.py` | pyCircuit CSR leaf (`ub_csr_<tag>` per `variants:`); SPEC §2.2 |
| `tb/ral/ub_regmodel.py` | uvm-python register model |
| `sw/include/ub_regs.h` | Firmware address / mask / shift macros + inline field accessors |
| `sw/hal/ub_regs_access.h` | HAL declarations |
| `sw/hal/ub_regs_access.c` | HAL register access layer |
| `model/regs.py` | Python constants shared by verification |

Directory convention (PM): pyCircuit sources live in `pycircuit/<layer>/`.
`scripts/emit_rtl.py` (design PR #5) writes generated Verilog into `rtl/` only.
`rtl/` must not hold Python sources.

RAL lives at `tb/ral/ub_regmodel.py`. `gen/tb_ral/` is removed.

Generator: `python3` + PyYAML only. The CSR leaf imports
`from pycircuit import Circuit, compile, module, u` and builds one fixed
`ub_csr_<tag>` netlist per `variants:` row (SPEC §2.2). `elaborate(0, variant=)` /
`elaborate(1, variant=)` call `pycircuit.compile()`.
`emit_verilog(False/True, variant=)` writes the compile() MLIR and runs
`pycc <file.pyc> --emit=verilog --logic-depth=64 -o <out.v>` (LLVM 19). Verilog is not
string-templated. GitHub CI has the frontend only; verilator lint runs when
`pycc` is on `PATH` (all tags). Reset fields marked `reset_from: variant` are
filled from the table; they are not handwritten.

### Verilog emit

`scripts/emit_rtl.py` writes the 8 committed netlists from
`pycircuit/csr/ub_csr.py` (`compile()` + `pycc --emit=verilog --logic-depth=64`):

| Netlist | Path |
| --- | --- |
| PRODUCT | `rtl/csr/ub_csr_<tag>.v` |
| HOOKS | `rtl/csr/hooks/ub_csr_<tag>.v` |

`python3 scripts/gen_regmap.py --check` regenerates via the same `emit_verilog()`
and fails on a byte mismatch (skipped only when `pycc` is not on PATH; the
committed files must still exist). Do not hand-write `.v`.

Netlists `` `include "pyc_reg.v" `` and do **not** copy `pyc_*` runtime files
into `rtl/csr/` or `rtl/csr/hooks/` (SPEC §2.2). Lint / synth / gate use
`-I rtl/pyc_lib`. That single-copy directory is **not on main yet**; until it
lands, `scripts/lint_csr.sh` falls back to `PYC_TOOLCHAIN_ROOT` / pycc
`include/verilog` and prints a NOTE.

`PARAM_VARIANT` (`0x011C`) is the RO capability word for a single driver:
`NUM_VL[3:0]`, `SCR_PLACEHOLDER[4]`, `RSVD[31:5]`. Lane count is
`PARAM_PHY.NUM_LANES_TX` / `NUM_LANES_RX` (not duplicated).
`product_*` tags are PRODUCT (`SCR_PLACEHOLDER=0`) and never instantiate a
`_placeholder` scrambler. `x4_vl2_placeholder` / `x8_vl2_placeholder` are
lint/TB only and are deleted once SPEC §13 closes and the scrambler has a
PRODUCT netlist. `--check` rejects `product_*` with `SCR_PLACEHOLDER!=0`,
`SCR_PLACEHOLDER=1` unless the name ends `_placeholder`, and lane/VL counts
that do not match `xN_vlM` in the tag.

## YAML-driven CSR semantics

`pycircuit/csr/ub_csr.py` walks YAML attributes (not per-register handwritten logic):

| Attribute | Behavior |
| --- | --- |
| `access: W1C` | Sticky bit; `event_port` is a 1-cycle set; write-1-clears |
| `saturating: true` | RO counter, saturate to all-1; `increment_port` input |
| `clear_target` on `CNT_CLR` (`0x0224`, WO, bits 0–8) | Self-clearing write-1 pulse clears that counter |
| `self_clearing: true` + `access: WO` | Reads 0; no sticky storage |
| `pulse_cycles: 16` + `pulse_output: port_rst_pulse` | WO self-clear bit stretched to a 16-cycle pulse |
| `irq` map | `irq = IRQ_EN & OR(IRQ_STATUS & ~IRQ_MASK)`; MASK bit 1 = block; reset all masked; active-high |
| TEST window (`test_gated`) | `tb_test_mode=0` or `TEST_HOOKS=0`: mapped, read 0, write ignore, `csr_err=0` |
| unmapped / unaligned | read 0 + `csr_err=1`; write ignore + `csr_err=1` |
| bus | full-word writes only (no `csr_wstrb`); 1-cycle read; write next-cycle `csr_rvalid=0` (SPEC §3.2.3) |

`TEST_HOOKS` is a Python generation-time split: PRODUCT has no `tb_*` port;
HOOKS adds `tb_test_mode`. `emit_verilog(False)` / `emit_verilog(True)`.

### Ports on `ub_csr`

- **Bus:** `csr_req`, `csr_wr`, `csr_addr[15:0]`, `csr_wdata[31:0]`, `csr_ready`,
  `csr_rvalid`, `csr_rdata[31:0]`, `csr_err`
- **Event inputs (W1C):** `ev_fec_uncorr` … `ev_crd_uf`
- **Increment inputs (counters):** `inc_fec_uncorr` … `inc_crd_uf`
- **Live STATUS:** `hw_link_up`, `hw_link_ready`, `hw_dll_status_up`, `hw_lmsm_st`,
  `hw_dll_sm_st`, `hw_retry_req_st`, `hw_retry_ack_st`
- **Config outputs:** `csr_lmsm_start`, `csr_irq_en`, `csr_irq_mask`, `csr_port_cna`,
  `csr_tmr_scale`, `csr_crd_to_dis`, `csr_am_ivl_scale`
- **`port_rst_pulse`:** 16-cycle pulse from `CTRL.PORT_RST`
- **`irq`:** active-high aggregate

### What stays handwritten (outside this module)

The generated leaf only implements the register file. The **parent** (`ub_controller` /
block wrappers) stays handwritten for:

1. Wiring block event sources into `ev_*` and `inc_*`
2. Fanning `port_rst_pulse` out to PCS / LMSM / DLL / credit

Do not put that fanout inside `ub_csr.py`.

## pyCircuit / uvm-python assumptions

- In-repo pyc4.0 style: Python under `pycircuit/<layer>/` emits Verilog into
  `rtl/`. `pyc_reg` = sync flop on `core_clk` / `rst_pyc`. `elaborate(0/1)` uses
  `from pycircuit import Circuit, compile, module, u` (`lukebest/pyCircuit`
  @ `43cc5918`, see `TOOLCHAIN.lock`). `compile()` produces frontend
  MLIR. PRODUCT `.v` is `pycc --emit=verilog` (LLVM 19). Do not put the
  repo root on `PYTHONPATH` (shadows the toolchain package named `pycircuit`).

### Install pyc4.0 + pycc (timed on this environment)

```bash
# 1) Frontend wheel/sdist (~6 s)
python3 -m pip install git+https://github.com/lukebest/pyCircuit@43cc5918e3d09ecc0c814cabef6c1384cb9980ae

# 2) LLVM 19 + build deps (~29 s apt)
sudo apt-get install -y ninja-build llvm-19 llvm-19-dev llvm-19-tools \
  libmlir-19-dev mlir-19-tools clang-19 g++ libstdc++-13-dev \
  libzstd-dev libedit-dev libcurl4-openssl-dev
# llvm-config-19 --version → 19.1.1

# 3) Clone pin + build pycc (~34 s with CC=gcc CXX=g++)
git clone https://github.com/lukebest/pyCircuit /tmp/pyCircuit
git -C /tmp/pyCircuit checkout 43cc5918e3d09ecc0c814cabef6c1384cb9980ae
export LLVM_DIR=/usr/lib/llvm-19/lib/cmake/llvm
export MLIR_DIR=/usr/lib/llvm-19/lib/cmake/mlir
export CC=gcc CXX=g++
bash /tmp/pyCircuit/flows/scripts/pyc build
export PATH=/tmp/pyCircuit/.pycircuit_out/toolchain/install/bin:$PATH
export PYC_TOOLCHAIN_ROOT=/tmp/pyCircuit/.pycircuit_out/toolchain/install
# pycc lives at $PYC_TOOLCHAIN_ROOT/bin/pycc
# primitives: $PYC_TOOLCHAIN_ROOT/include/verilog  (or /tmp/pyCircuit/runtime/verilog)
```

Clean-path wall time is about 70 s (pip 6 + apt 29 + pyc build 34). Clang 18
without libstdc++ and a missing `zstd` CMake target each fail configure; use
`CC=gcc CXX=g++` and `libzstd-dev`. `pyc-opt` may be skipped if
`MLIRRegisterAllPasses` is absent — `pycc --emit=verilog` is enough.

Verilator lint of the pycc netlist needs `-I` to those primitives (`pyc_reg.v`).
- uvm-python RAL: `UVMReg` / `UVMRegField.configure(parent, size, lsb_pos, access,
  volatile, reset, has_reset, is_rand, individually_accessible)` from
  `lukebest/uvm-python`. The generated model imports uvm-python when present and
  otherwise uses a tiny fallback so the file still imports.
