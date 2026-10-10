#!/usr/bin/env bash
# Install pinned pyCircuit pyc4.0 + pycc from the root TOOLCHAIN.lock [pycircuit] section.
# Proven by spike cursor/spike-pycircuit-toolchain @ 6c48cb7.
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd -- "${HERE}/.." && pwd)"
LOCK="${REPO}/TOOLCHAIN.lock"

lock_get() {
  local key="$1"
  awk -F= -v key="${key}" '
    BEGIN { sect = 0 }
    /^[[:space:]]*\[pycircuit\]/ { sect = 1; next }
    /^[[:space:]]*\[/ { sect = 0; next }
    sect && $1 ~ "^[[:space:]]*" key "[[:space:]]*$" {
      val = $0
      sub(/^[^=]*=[[:space:]]*/, "", val)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
      gsub(/^"|"$/, "", val)
      print val
      exit
    }
  ' "${LOCK}"
}

PIN="$(lock_get commit)"
GIT_URL="$(lock_get repo)"
RELEASE="$(lock_get release)"
LLVM_VER="$(lock_get llvm_lock)"
MLIR_VER="$(lock_get mlir_lock)"
if [[ -z "${PIN}" || -z "${GIT_URL}" ]]; then
  echo "setup_pycircuit.sh: missing repo/commit in ${LOCK} [pycircuit]" >&2
  exit 1
fi
if [[ -z "${LLVM_VER}" || -z "${MLIR_VER}" ]]; then
  echo "setup_pycircuit.sh: missing llvm_lock/mlir_lock in ${LOCK} [pycircuit]" >&2
  exit 1
fi

SRC="${PYCIRCUIT_SRC:-/tmp/pyCircuit}"
VENV="${UB_PYC_VENV:-/tmp/venv}"

echo "TOOLCHAIN.lock [pycircuit]: ${RELEASE} ${GIT_URL} @ ${PIN}"
echo "LLVM ${LLVM_VER} / MLIR ${MLIR_VER}"

if [[ ! -d "${SRC}/.git" ]]; then
  git clone "${GIT_URL}" "${SRC}"
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
echo "cmake: $(cmake --version | head -1)"
echo "ninja: $(ninja --version)"
echo "frontend: $("${VENV}/bin/python" -c 'import pycircuit; print(pycircuit.__file__)')"
