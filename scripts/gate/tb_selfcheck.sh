#!/usr/bin/env bash
# pytest model/ (if present) + tb/models/tests + Icarus TEST_HOOKS=0/1.
# Does not modify model/ or tb/models/. Icarus is the pass/fail sim (D7).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

python3 - <<'PY'
from gatelib import print_tool_versions
print_tool_versions(["python", "icarus"])
PY

if ! command -v iverilog >/dev/null 2>&1; then
  echo "ERROR: iverilog is not on PATH; Icarus is the tb-selfcheck gate (D7)"
  exit 1
fi

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

if [[ -d "$REPO_ROOT/model" ]]; then
  echo "=== pytest model/ ==="
  python3 -m pytest "$REPO_ROOT/model" -q
else
  echo "NOTE: model/ not present; skip top-level golden pytest (architecture will move goldens here)"
fi

if [[ -d "$REPO_ROOT/tb/models/tests" ]]; then
  echo "=== pytest tb/models/tests ==="
  python3 -m pytest "$REPO_ROOT/tb/models/tests" -q
else
  echo "NOTE: tb/models/tests not present; skip"
fi

if [[ ! -f "$REPO_ROOT/tb/Makefile" ]]; then
  echo "ERROR: tb/Makefile missing; cannot run Icarus TEST_HOOKS self-check"
  exit 1
fi

echo "=== Icarus TEST_HOOKS=0 and 1 (tb/Makefile selfcheck-both) ==="
make -C "$REPO_ROOT/tb" selfcheck-both SIM=icarus

echo "tb-selfcheck: PASS"
exit 0
