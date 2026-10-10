# Spike: real pyCircuit pyc4.0 / pycc flow on this cloud VM

**Verdict: the toolchain installs and runs.** A combinational `ub_pcs_lane_dist` was authored with the pyCircuit Python API (no f-string Verilog) and emitted by `pycc` for `NUM_LANES=4` and `8`.

No PR. Branch: `cursor/spike-pycircuit-toolchain`. Existing PR branches were not checked out or modified.

## Success / fail

| Step | Result |
|---|---|
| Prebuilt `pycircuit-hisi==0.1.0` wheel / PyPI | **FAIL** — no matching distribution. No GitHub releases on `lukebest/pyCircuit` or `LinxISA/pyCircuit`. Built from pinned source. |
| Clone `lukebest/pyCircuit` @ `43cc5918` | **PASS** |
| Install LLVM/MLIR 19 + ninja + Verilator + Yosys | **PASS** (after `apt-get update`; universe already enabled) |
| First `flows/scripts/pyc build` | **FAIL** — missing `libstdc++` |
| Second `pyc build` | **FAIL** — LLVM CMake wants `zstd::libzstd_shared` |
| Third `pyc build` after `libzstd-dev` | **PASS** — `pycc` staged |
| `python3 -m pip install -e` (system) | **FAIL** — PEP 668 externally-managed |
| venv + editable frontend | **PASS** (`pycircuit-hisi==0.1.0`) |
| Smoke: official `counter` → pycc Verilog | **PASS** |
| Author `ub_pcs_lane_dist` via API + pycc N=4,8 | **PASS** (after JIT workarounds; see blockers) |
| Verilator `--lint-only -Wall` N=4,8 | **PASS** (no warnings) |
| Yosys `read_verilog -sv; hierarchy -check -top; proc; opt; stat` + no latches | **PASS** (0 cells after opt — pure wiring) |
| Yosys equiv vs PR `cursor/rtl-m1-leaf-batch1-e5bb` RTL | **FAIL** — mapping mismatch (not a pycc bug) |
| Yosys equiv vs spec-gold (UB-PHY formula) | **PASS** (128/128 and 256/256 bits) |
| Bit-exact vs `tb/models` `UbPcsLaneDist` on `origin/main` | **PASS** |
| `eqy` | **not installed**; no apt package on noble. Used `equiv_make/simple/induct/status -assert`. |

## Versions

| Component | Version |
|---|---|
| Host | Ubuntu 24.04.4 LTS, x86_64, 4 CPU, 15 GiB |
| Python | 3.12.3 (`/usr/bin/python3`; venv `/tmp/spike/venv`) |
| pyCircuit | `43cc5918e3d09ecc0c814cabef6c1384cb9980ae` (pyc4.0 / package `pycircuit-hisi` 0.1.0) |
| pycc metadata | `pyc_version=0.0.0`, `llvm_version=19.1.1`, git sha above |
| `pycc --version` | prints **Ubuntu LLVM version 19.1.1** (LLVM’s printer, not a pyCircuit semver) |
| LLVM / MLIR | 19.1.1 (`1:19.1.1-1ubuntu1~24.04.2`, `llvm-config-19`) |
| cmake / ninja | 3.28.3 / 1.11.1 |
| Host clang used to compile pycc | 18.1.3 (`/usr/bin/c++`) |
| g++ (libstdc++) | 13.3.0 |
| Verilator | 5.020 (Debian). D7 pin is 5.032 — lint-only only here. |
| Yosys | 0.33 (`2584903a060`, package `0.33-5build2`) |

## Exact install commands and wall-clock

Times from this VM. Clone of pyCircuit: **1.6 s**.

```bash
# 0. clone pin (1.6s + 0.2s checkout)
git clone --filter=blob:none https://github.com/lukebest/pyCircuit.git /tmp/spike/pyCircuit
git -C /tmp/spike/pyCircuit checkout 43cc5918e3d09ecc0c814cabef6c1384cb9980ae

# 1. apt update (3s)
sudo apt-get update -y

# 2. LLVM 19 + MLIR + EDA (35s)
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  llvm-19 llvm-19-dev llvm-19-tools libmlir-19-dev mlir-19-tools \
  ninja-build build-essential python3-pip python3-venv verilator yosys

# 3. first pyc build FAILED (verbatim):
# /usr/bin/ld: cannot find -lstdc++: No such file or directory
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y g++ libstdc++-14-dev   # 3s

# 4. second pyc build FAILED (verbatim):
# CMake Error at /usr/lib/llvm-19/lib/cmake/llvm/LLVMExports.cmake:73
#   The link interface of target "LLVMSupport" contains:
#     zstd::libzstd_shared
#   but the target was not found.
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y libzstd-dev            # 3s

# 5. pycc build (31s)
cd /tmp/spike/pyCircuit
bash flows/scripts/pyc build
# stages: /tmp/spike/pyCircuit/.pycircuit_out/toolchain/install/bin/pycc
# pyc-opt skipped: "MLIRRegisterAllPasses not found; skipping pyc-opt (pycc only)"

# 6. frontend (system pip FAIL: externally-managed-environment)
python3 -m venv /tmp/spike/venv
/tmp/spike/venv/bin/pip install -e /tmp/spike/pyCircuit                       # 6s

# 7. emit + pycc (typical <0.3s per variant)
export PYC_TOOLCHAIN_ROOT=/tmp/spike/pyCircuit/.pycircuit_out/toolchain/install
export PATH="$PYC_TOOLCHAIN_ROOT/bin:$PATH"
/tmp/spike/venv/bin/python -m pycircuit.cli emit \
  spike/pycircuit_toolchain/ub_pcs_lane_dist.py \
  -o /tmp/out.mlir --project-root spike/pycircuit_toolchain \
  --param num_lanes=4 --param pma_w=32 --param sym_w=8 --param test_hooks=0
pycc /tmp/out.mlir --emit=verilog --include-primitives=0 -o /tmp/out.v
```

**Preferred wheel path was not available.** `python3 -m pip index versions pycircuit-hisi` → `No matching distribution found for pycircuit-hisi`. TOOLCHAIN.lock on the leaf-batch PR documents that wheel as “when published”.

**Total (successful path, excluding failed cmake retries ~8 s):** ~3+35+3+3+31+6 ≈ **81 s** apt+build+venv, plus 1.6 s clone. Leaf emit+lint+yosys+equiv+model: **0.58 s**.

Reproduce locally after the toolchain is staged:

```bash
export PYC_TOOLCHAIN_ROOT=/tmp/spike/pyCircuit/.pycircuit_out/toolchain/install
export SPIKE_VENV=/tmp/spike/venv
bash spike/pycircuit_toolchain/emit_and_check.sh
```

## Generated files

| Path | What |
|---|---|
| `spike/pycircuit_toolchain/ub_pcs_lane_dist.py` | Real `@module` leaf |
| `spike/pycircuit_toolchain/gen/n4/ub_pcs_lane_dist.v` | pycc Verilog, 128-bit IO |
| `spike/pycircuit_toolchain/gen/n8/ub_pcs_lane_dist.v` | pycc Verilog, 256-bit IO |
| `spike/pycircuit_toolchain/ref/ub_pcs_lane_dist_pr_e5bb.v` | PR-branch f-string RTL |
| `spike/pycircuit_toolchain/ref/ub_pcs_lane_dist_spec.v` | Spec-gold (Yosys only) |
| `spike/pycircuit_toolchain/gen/yosys_n{4,8}.log` | hierarchy/proc/opt/stat |
| `spike/pycircuit_toolchain/gen/equiv_n{4,8}_vs_pr.log` | equiv vs PR RTL |
| `spike/pycircuit_toolchain/gen/equiv_n{4,8}_vs_spec.log` | equiv vs spec-gold |

pycc default emit prepends unused `` `include "pyc_reg.v" `` etc. This leaf used `--include-primitives=0`.

## Lint / Yosys / equivalence

**Verilator** `verilator --lint-only -Wall` on both `.v`: clean (empty logs).

**Yosys stat** (`read_verilog -sv; hierarchy -check -top ub_pcs_lane_dist; proc; opt; stat`):

- N=4: wires 21 / wire bits 768 / cells **0** / processes 0
- N=8: wires 37 / wire bits 1536 / cells **0** / processes 0
- `select -assert-none t:$dlatch t:$adff t:$adffe t:$dlatchsr` — **no latches**

0 cells is expected: the leaf is a static byte permute; `opt` folds `extract`/`concat` to wires.

**Equiv vs PR e5bb** (`chparam NUM_LANES=4/8`, then `equiv_make/simple/induct/status -assert`):

```
ERROR: Found 128 unproven $equiv cells in 'equiv_status -assert'.   # N=4
ERROR: Found 256 unproven $equiv cells in 'equiv_status -assert'.   # N=8
```

PR RTL maps `Lane<j,i> = CA<i*NUM_LANES + j>` (forward stripe). Spec / `tb/models` / this leaf map `Lane<j,i> = CA<(NSYM-1) - i*NUM_LANES - j>`.

**Equiv vs spec-gold:** `Equivalence successfully proven!` (128 bits N=4, 256 bits N=8).

**`tb/models` (origin/main):** `UbPcsLaneDist` with `n_symbols = NUM_LANES * 4` matches the leaf mapping (64 random + identity CA). Sample vs PR mapping: `match=False`.

## How pyCircuit expresses the four migration concerns

### 1. Sync active-high reset registers

```python
clk = m.clock("clk")
rst = m.reset("rst")          # !pyc.reset, Verilog port name = argument
q = m.out("count_q", clk=clk, rst=rst, width=8, init=u(8, 0))
q.set(next, when=en)
m.output("count", q.out())
```

`pycc` instantiates `runtime/verilog/pyc_reg.v`:

```verilog
always @(posedge clk) begin
  if (rst) q <= init;
  else if (en) q <= d;
end
```

Sync, **active-high**. D6 product `rst_n` async-low still needs the handwritten whitelist (`ub_rst_sync` / adapter). Switch’s `vibe_bcrc` documents the same: pyCircuit `rst` is finished to async-low `rst_n` by hand. `m.reset_active(rst)` is the i1 “asserted” view.

### 2. Module parameters

JIT / CLI `--param name=value` (Python literal). Widths are **elaborated constants**. Emitted Verilog is a **fixed variant**, not `parameter integer NUM_LANES`.

`@module(value_params={"gain": "i8"})` is a **runtime value port**, not a Verilog parameter.

Migrating 10 leaves: emit N=4 and N=8 as two files (this spike) **or** keep a thin parameterized SV wrapper around a pycc-fixed core. pycc will not recreate the PR-style `#(parameter NUM_LANES=4)`.

### 3. TEST_HOOKS-style generate-time switch

A JIT int + Python `if` elaborates two netlists (`--param test_hooks=0` vs `1`). There is **no** Verilog `parameter TEST_HOOKS` / `generate`.

Pinned JIT bugs to avoid **inside** `@module def build` (see blockers). Put loops / `m.cat(*list)` in a plain helper (Switch style). Compare `test_hooks != 0`, do not use `x in ...`.

`--param test_hooks=1` on this leaf (no hook ports) failed JIT with:

```
design compile failed: .../ub_pcs_lane_dist.py:55:5: [PYC520] bool() takes no keyword arguments
stage=jit
```

(`raise ValueError(...)` on the taken branch). A real hooks variant should add ports in that `if`, not raise.

### 4. Port naming

The string to `m.input` / `m.output` / `m.clock` / `m.reset` **is** the Verilog port name (`data_in`, `data_out`). Module name: `build.__pycircuit_name__ = "ub_pcs_lane_dist"` (CLI top). `@module(name=...)` is the hierarchy symbol. Without `__pycircuit_name__`, CLI CamelCases the filename (`UbPcsLaneDist`). Internal nets are mangled (`data_in__ub_pcs_lane_dist__L61`).

## Blockers / JIT errors (verbatim)

These did **not** stop the spike; they matter for the 10-leaf port.

1. **No wheel**
   ```
   ERROR: No matching distribution found for pycircuit-hisi
   ```

2. **Missing libstdc++** (first cmake)
   ```
   /usr/bin/ld: cannot find -lstdc++: No such file or directory
   c++: error: linker command failed with exit code 1
   ```

3. **Missing zstd CMake target** (second cmake)
   ```
   CMake Error at /usr/lib/llvm-19/lib/cmake/llvm/LLVMExports.cmake:73 (set_target_properties):
     The link interface of target "LLVMSupport" contains:
       zstd::libzstd_shared
     but the target was not found.
   ```

4. **`in` / `not in` inside `@module`** — pinned `compiler/frontend/pycircuit/jit.py:1157` names undefined `Vec`:
   ```
   design compile failed: .../ub_pcs_lane_dist.py:37:5: [PYC520] name 'Vec' is not defined
   stage=jit
   ```

5. **`range(hi, -1, -1)` inside `@module`**
   ```
   [PYC520] range() step must be > 0
   ```

6. **`m.cat(*pieces)` inside `@module`**
   ```
   [PYC520] unsupported expression: Starred(value=Name(id='pieces', ctx=Load()), ctx=Load())
   ```

7. **`eqy`** not on PATH / not in noble apt. Yosys 0.33 `equiv_*` is enough for this leaf.

## Migration note

`origin/cursor/rtl-m1-leaf-batch1-e5bb` `pycircuit/pcs/ub_pcs_lane_dist.py` is an f-string Verilog emitter (`make emit` does not require LLVM). That is **not** the D5 flow. The PR RTL is also **not** bit-equivalent to `tb/models` / UB-PHY §3.2.2.3.

This spike is the real flow: `@module` + `pycc`. It runs on this VM in ~1.5 minutes from a clean package cache once `libstdc++` and `libzstd-dev` are present.
