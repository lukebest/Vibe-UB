#!/usr/bin/env bash
# Run every formal/<iface>/*.sby. Each interface ships its own stub so the
# job does not need product RTL. Empty tree → success + "no assertions yet".
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

python3 - <<'PY'
from gatelib import print_tool_versions
print_tool_versions(["sby", "yosys", "python"])
PY

mapfile -t SBY_FILES < <(find "$REPO_ROOT/formal" -mindepth 2 -maxdepth 2 -type f -name '*.sby' 2>/dev/null | sort || true)

if [[ ${#SBY_FILES[@]} -eq 0 ]]; then
  echo "no assertions yet"
  echo "formal: PASS (no formal/<iface>/*.sby; Xia will add interface assertions)"
  exit 0
fi

if ! command -v sby >/dev/null 2>&1; then
  echo "ERROR: formal/<iface>/*.sby present but sby is not on PATH"
  echo "TOOL sby: locked=(not in TOOLCHAIN.lock) actual=MISSING — cannot pretend"
  exit 1
fi

fail=0
for sby in "${SBY_FILES[@]}"; do
  echo "=== sby -f ${sby#"$REPO_ROOT/"} ==="
  if ! sby -f "$sby"; then
    echo "formal FAIL: $sby"
    fail=1
  fi
done

if [[ "$fail" -ne 0 ]]; then
  echo "formal: FAIL (one or more .sby jobs failed)"
  exit 1
fi
echo "formal: PASS"
exit 0
