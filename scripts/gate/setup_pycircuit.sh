#!/usr/bin/env bash
# Install pyc4.0 / pycc / LLVM 19 using the design-proven recipe
# (spike/pycircuit_toolchain/REPORT.md on cursor/spike-pycircuit-toolchain).
# Versions come ONLY from TOOLCHAIN.lock — do not duplicate pins here.
#
# Layout (CI-cacheable):
#   .pycircuit-src          clone of lukebest/pyCircuit @ lock commit
#   .pycircuit_out/...      flows/scripts/pyc build install prefix
#   .pycircuit-venv         editable frontend (pycircuit-hisi)
set -u
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

LOG="$GATE_DIR/out/pycircuit_setup.log"
mkdir -p "$GATE_DIR/out"
: >"$LOG"
note() { echo "$*" | tee -a "$LOG"; }

lock_get() {
  python3 - <<PY
import sys
sys.path.insert(0, "$GATE_DIR")
from gatelib import parse_lock
print(parse_lock().get("$1", ""))
PY
}

REPO_URL="$(lock_get pycircuit_repo)"
COMMIT="$(lock_get pycircuit_commit)"
PKG="$(lock_get pycircuit_package)"
PKG_VER="$(lock_get pycircuit_package_version)"
RELEASE="$(lock_get pycircuit_release)"
[[ -n "$REPO_URL" ]] || REPO_URL="https://github.com/lukebest/pyCircuit"
[[ -n "$COMMIT" ]] || COMMIT="43cc5918e3d09ecc0c814cabef6c1384cb9980ae"
[[ -n "$PKG" ]] || PKG="pycircuit-hisi"
[[ -n "$RELEASE" ]] || RELEASE="pyc4.0"

SRC="${PYCIRCUIT_SRC:-$REPO_ROOT/.pycircuit-src}"
OUT="${PYC_TOOLCHAIN_ROOT:-$REPO_ROOT/.pycircuit_out/toolchain/install}"
VENV="${PYCIRCUIT_VENV:-$REPO_ROOT/.pycircuit-venv}"
# pyc build stages under the clone by default; keep a stable cache path.
export PYC_INSTALL_PREFIX="$OUT"

note "=== setup_pycircuit (design spike recipe) ==="
note "TOOLCHAIN.lock: repo=$REPO_URL commit=$COMMIT release=$RELEASE package=$PKG==${PKG_VER:-0.1.0}"
note "SRC=$SRC OUT=$OUT VENV=$VENV"

already_ok() {
  [[ -x "$OUT/bin/pycc" ]] || return 1
  [[ -x "$VENV/bin/python" ]] || return 1
  "$VENV/bin/python" -c "import pycircuit" >/dev/null 2>&1 || return 1
  return 0
}

if already_ok; then
  export PATH="$OUT/bin:$PATH"
  export PYC_TOOLCHAIN_ROOT="$OUT"
  note "cache hit: $($OUT/bin/pycc --version 2>&1 | head -1)"
  note "venv import pycircuit: ok"
  note "SETUP_OK=1"
  exit 0
fi

note "--- apt (LLVM/MLIR 19, ninja, verilator, yosys, libstdc++, zstd) ---"
if command -v sudo >/dev/null 2>&1; then
  sudo apt-get update -y >>"$LOG" 2>&1 || note "apt-get update failed (continuing)"
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    llvm-19 llvm-19-dev llvm-19-tools \
    libmlir-19-dev mlir-19-tools \
    ninja-build \
    verilator yosys \
    python3-venv \
    g++ libstdc++-14-dev libzstd-dev \
    build-essential cmake \
    >>"$LOG" 2>&1 || note "BLOCKER: apt install failed"
else
  note "BLOCKER: no sudo; cannot apt install LLVM 19 / build deps"
fi

if command -v llvm-config-19 >/dev/null 2>&1; then
  note "llvm-config-19: $(llvm-config-19 --version)"
else
  note "BLOCKER: llvm-config-19 missing after apt"
  note "SETUP_OK=0"
  exit 0
fi

note "--- git clone $REPO_URL @ $COMMIT ---"
if [[ ! -d "$SRC/.git" ]]; then
  rm -rf "$SRC"
  if ! git clone --filter=blob:none "$REPO_URL" "$SRC" >>"$LOG" 2>&1; then
    note "BLOCKER: git clone failed"
    note "SETUP_OK=0"
    exit 0
  fi
fi
git -C "$SRC" fetch --depth 1 origin "$COMMIT" >>"$LOG" 2>&1 || \
  git -C "$SRC" fetch origin "$COMMIT" >>"$LOG" 2>&1 || true
if ! git -C "$SRC" checkout --detach "$COMMIT" >>"$LOG" 2>&1; then
  note "BLOCKER: git checkout $COMMIT failed"
  note "SETUP_OK=0"
  exit 0
fi
note "checked out $(git -C "$SRC" rev-parse HEAD)"

if [[ ! -x "$SRC/flows/scripts/pyc" ]]; then
  note "BLOCKER: $SRC/flows/scripts/pyc not found at this pin"
  note "SETUP_OK=0"
  exit 0
fi

note "--- bash flows/scripts/pyc build ---"
export LLVM_CONFIG="$(command -v llvm-config-19)"
if ! (cd "$SRC" && bash flows/scripts/pyc build) >>"$LOG" 2>&1; then
  note "BLOCKER: pyc build failed (see log)"
  tail -n 80 "$LOG" | sed 's/^/  /'
  note "SETUP_OK=0"
  exit 0
fi

# pyc stages under the clone; copy/link into the cache prefix if needed.
if [[ ! -x "$OUT/bin/pycc" ]]; then
  staged="$SRC/.pycircuit_out/toolchain/install"
  if [[ -x "$staged/bin/pycc" ]]; then
    mkdir -p "$(dirname "$OUT")"
    rm -rf "$OUT"
    ln -s "$staged" "$OUT" || cp -a "$staged" "$OUT"
  fi
fi
if [[ ! -x "$OUT/bin/pycc" ]]; then
  note "BLOCKER: pycc missing after pyc build"
  note "SETUP_OK=0"
  exit 0
fi
note "pycc: $($OUT/bin/pycc --version 2>&1 | head -1)"

note "--- venv + pip install -e pyCircuit ---"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" >>"$LOG" 2>&1 || {
    note "BLOCKER: python3 -m venv failed"
    note "SETUP_OK=0"
    exit 0
  }
fi
if ! "$VENV/bin/pip" install -e "$SRC" >>"$LOG" 2>&1; then
  note "BLOCKER: pip install -e pyCircuit failed"
  tail -n 40 "$LOG" | sed 's/^/  /'
  note "SETUP_OK=0"
  exit 0
fi
if ! "$VENV/bin/python" -c "import pycircuit" 2>/dev/null; then
  note "BLOCKER: venv cannot import pycircuit"
  note "SETUP_OK=0"
  exit 0
fi

export PATH="$OUT/bin:$PATH"
export PYC_TOOLCHAIN_ROOT="$OUT"
note "SETUP_OK=1"
note "ok: pycc + $PKG editable frontend"
exit 0
