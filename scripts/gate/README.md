# Tool-gate scripts

CI (`.github/workflows/gate.yml`) and `make gate` call the same wrappers.
Do not put extra logic only in the workflow.

| Script | Job |
| --- | --- |
| `lint.sh` | Verilator `--lint-only -Wall` |
| `synth_check.sh` | Yosys synth, latch / multi-drive / combo-loop |
| `cdc_rdc.sh` | Structural CDC / RDC (`cdc_rules.yml`) |
| `formal.sh` | `formal/<iface>/*.sby` |
| `regmap_consistency.sh` | `python3 scripts/gen_regmap.py --check` |
| `tb_selfcheck.sh` | `model/` pytest + `tb/models/tests` + Icarus hooks |
| `legacy.txt` | D10 leftover list (report-only) |

Rules, fail criteria, and the waiver flow:
[docs/rules/verif_gate.md](../../docs/rules/verif_gate.md).
