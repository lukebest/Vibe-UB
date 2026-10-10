#!/usr/bin/env bash
# Install pinned pyCircuit pyc4.0 + pycc (LLVM 19) for M1 leaf emit.
# Proven by spike cursor/spike-pycircuit-toolchain @ 6c48cb7.
set -euo pipefail

PIN=43cc5918e3d09ecc0c814cabef6c1384cb9980ae
SRC="${PYCIRCUIT_SRC:-/tmp/pyCircuit}"
VENV="${UB_PYC_VENV:-/tmp/venv}"

if [[ ! -d "${SRC}/.git" ]]; then
  git clone https://github.com/lukebest/pyCircuit.git "${SRC}"
fi
git -C "${SRC}" fetch --depth 1 origin "${PIN}" || true
git -C "${SRC}" checkout "${PIN}"

sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  llvm-19 llvm-19-dev llvm-19-tools libmlir-19-dev mlir-19-tools \
  ninja-build verilator yosys python3-venv g++ libstdc++-14-dev libzstd-dev

( cd "${SRC}" && bash flows/scripts/pyc build )

python3 -m venv "${VENV}"
"${VENV}/bin/pip" install -e "${SRC}"

export PYC_TOOLCHAIN_ROOT="${SRC}/.pycircuit_out/toolchain/install"
export PATH="${PYC_TOOLCHAIN_ROOT}/bin:${PATH}"
echo "pycc: $(command -v pycc)"
pycc --version || true
echo "llvm: $(llvm-config-19 --version)"
echo "frontend: $("${VENV}/bin/python" -c 'import pycircuit; print(pycircuit.__file__)')"
