#!/usr/bin/env bash
# Replaceable pyc4.0 / pycc / LLVM 19 install entry.
#
# Versions are maintained ONLY in TOOLCHAIN.lock — do not duplicate pins here.
# Design will drop the real install recipe into this file (group message).
# Until that recipe lands, this script records the lock pins and exits 0
# so the provenance job can stay report-only on the emit path.
set -u
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

LOG="$GATE_DIR/out/pycircuit_setup.log"
mkdir -p "$GATE_DIR/out"
: >"$LOG"
note() { echo "$*" | tee -a "$LOG"; }

lock_get() {
  python3 - <<PY
from pathlib import Path
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
LLVM="$(lock_get llvm_lock)"
PYCC="$(lock_get pycc_lock)"

note "=== setup_pycircuit (replaceable entry) ==="
note "TOOLCHAIN.lock pins (single source of truth):"
note "  pycircuit_repo=$REPO_URL"
note "  pycircuit_commit=$COMMIT"
note "  pycircuit_release=$RELEASE"
note "  pycircuit_package=$PKG==${PKG_VER:-unspecified}"
note "  llvm_lock=${LLVM:-}"
note "  pycc_lock=${PYCC:-}"
note "BLOCKER: install recipe not yet provided by design."
note "Replace the body of scripts/gate/setup_pycircuit.sh with the group recipe."
note "Do not add version numbers in this script; read them from TOOLCHAIN.lock."

if command -v pycc >/dev/null 2>&1 && python3 -c "import pycircuit" 2>/dev/null; then
  note "already present on PATH: $(pycc --version 2>&1 | head -1)"
  note "python import pycircuit: ok"
  exit 0
fi

exit 0
