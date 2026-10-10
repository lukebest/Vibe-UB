# Tool-gate scripts

CI (`.github/workflows/gate.yml`) and `make gate` call the same wrappers.
Do not put extra logic only in the workflow.

Lists live in this directory (`legacy.txt`, `handwritten.yml`, `blackbox.yml`,
`hooks_ports.yml`, `pycircuit_migrate.txt`).

| Script | Job |
| --- | --- |
| `rtl_emit_consistency.sh` | Line A: emit + `git diff rtl/` + hooks + PRODUCT≡HOOKS |
| `equiv.sh` | Visible eqy job (`--equiv-only`; Yosys `equiv_*` fallback) |
| `pycircuit_provenance.sh` | AST provenance (blocking) + pycc emit (report-only) |
| `setup_pycircuit.sh` | Replaceable pyc4.0/pycc/LLVM 19 entry (pins in `TOOLCHAIN.lock`) |
| `hooks_port_consistency.sh` | Independent HOOKS vs PRODUCT ports |
| `lint.sh` | Verilator `--lint-only -Wall` + unlisted stub/macro |
| `synth_check.sh` | Yosys synth, latch / multi-drive / combo-loop; `-lib` for blackbox.yml; combo depth report |
| `cdc_rdc.sh` | Structural CDC / RDC (`cdc_rules.yml`; `valid_outside` for unreset arrays) |
| `formal.sh` | `formal/<iface>/*.sby` (includes `formal/cmn/`) |
| `regmap_consistency.sh` | `python3 scripts/gen_regmap.py --check` |
| `tb_selfcheck.sh` | Auto-discover pytest + cocotb under `tb/` and `model/` |

Three lines, every hierarchy level auto-discovered (`pycircuit/*/`, `rtl/*/`, `formal/*/`; `cmn` always enumerated; no hard-coded `pcs`/`dll`/`lmsm`/`csr`):

- **A** emit / hooks / ports / eqy / provenance
- **B** lint / synth-check / cdc-rdc on `rtl/<layer>/` (+ `hooks/`)
- **C** `formal/<iface>/*.sby`

Xia: `ub_cmn_mem_1r1w` is a normal leaf (`pycircuit/cmn/` → `rtl/cmn/`).
`blackbox.yml` `kind` is `stub` | `macro` only.

Rules, fail criteria, and the waiver flow:
[docs/rules/verif_gate.md](../../docs/rules/verif_gate.md).
