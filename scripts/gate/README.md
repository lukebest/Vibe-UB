# Tool-gate scripts

CI (`.github/workflows/gate.yml`) and `make gate` call the same wrappers.
Do not put extra logic only in the workflow.

Lists live in [`gate/`](../../gate/README.md) (legacy / handwritten / stubs / hooks ports).
Do not keep a second copy under `scripts/gate/`.

| Script | Job |
| --- | --- |
| `rtl_emit_consistency.sh` | Line A: emit + `git diff rtl/` + hooks + PRODUCT≡HOOKS |
| `hooks_port_consistency.sh` | Independent HOOKS vs PRODUCT ports (`gate/hooks_ports.yml`) |
| `lint.sh` | Verilator `--lint-only -Wall` + unlisted stub/blackbox |
| `synth_check.sh` | Yosys synth, latch / multi-drive / combo-loop |
| `cdc_rdc.sh` | Structural CDC / RDC (`cdc_rules.yml`) |
| `formal.sh` | `formal/<iface>/*.sby` |
| `regmap_consistency.sh` | `python3 scripts/gen_regmap.py --check` |
| `tb_selfcheck.sh` | Auto-discover pytest + cocotb under `tb/` and `model/` |

Three lines, every hierarchy level auto-discovered (`pycircuit/*/`, `rtl/*/`, `formal/*/`; no hard-coded layer names):

- **A** emit / hooks / ports / eqy (eqy primary; Yosys `equiv_*` fallback)
- **B** lint / synth-check / cdc-rdc on `rtl/<layer>/` (+ `hooks/`)
- **C** `formal/<iface>/*.sby`

Rules, fail criteria, and the waiver flow:
[docs/rules/verif_gate.md](../../docs/rules/verif_gate.md).
