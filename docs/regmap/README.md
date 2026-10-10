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
| `rtl/csr/ub_csr_regs.py` | pyCircuit CSR leaf (`ub_csr`); SPEC §2.2 |
| `rtl/csr/ub_csr.v` | PRODUCT netlist (`TEST_HOOKS=0`) |
| `rtl/csr/hooks/ub_csr.v` | HOOKS netlist (`TEST_HOOKS=1`) |
| `tb/ral/ub_regmodel.py` | uvm-python register model |
| `sw/include/ub_regs.h` | Firmware address / mask / shift macros + inline field accessors |
| `sw/hal/ub_regs_access.h` | HAL declarations |
| `sw/hal/ub_regs_access.c` | HAL register access layer |
| `model/regs.py` | Python constants shared by verification |

RAL lives at `tb/ral/ub_regmodel.py` (PR #6 `tb/` is on main). `gen/tb_ral/` is removed.

Generator: `python3` + PyYAML only. Product `.v` is reproduced by `emit_verilog`
(same style as PR #7 `ub_lmsm.py`). `elaborate(0)` / `elaborate(1)` call
`pycircuit.compile()` when the frontend is installed.

## YAML-driven CSR semantics

`rtl/csr/ub_csr_regs.py` walks YAML attributes (not per-register handwritten logic):

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

Do not put that fanout inside `ub_csr_regs.py`.

## pyCircuit / uvm-python assumptions

- In-repo pyc4.0 style (PR #7 `ub_lmsm.py`): Python emits Verilog; `pyc_reg` =
  sync flop on `core_clk` / `rst_pyc`. `elaborate(0/1)` uses
  `from pycircuit import Circuit, compile, module, u` (`lukebest/pyCircuit`
  @ `43cc5918`, see `pycircuit/TOOLCHAIN.lock`). `compile()` produces frontend
  MLIR. `pycc` (Circuit→Verilog, LLVM 19) is **not** required to regenerate
  PRODUCT `.v`. Lint: `make -C rtl/csr lint`.
- uvm-python RAL: `UVMReg` / `UVMRegField.configure(parent, size, lsb_pos, access,
  volatile, reset, has_reset, is_rand, individually_accessible)` from
  `lukebest/uvm-python`. The generated model imports uvm-python when present and
  otherwise uses a tiny fallback so the file still imports.
