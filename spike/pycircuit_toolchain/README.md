# pyCircuit pyc4.0 toolchain spike

See [REPORT.md](REPORT.md). Reproduce (after installing LLVM 19 + building `pycc`):

```bash
export PYC_TOOLCHAIN_ROOT=/tmp/spike/pyCircuit/.pycircuit_out/toolchain/install
export SPIKE_VENV=/tmp/spike/venv
bash spike/pycircuit_toolchain/emit_and_check.sh
```
