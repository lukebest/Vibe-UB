#!/usr/bin/env bash
# Run the RTL-free self-check on both TEST_HOOKS netlists.
# Icarus 12.0 is the pass/fail gate. Verilator is attempted when present.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TB="$ROOT/tb"
cd "$TB"

echo "=== model pytest ==="
python3 -m pytest

run_sim() {
  local sim="$1"
  echo "=== $sim TEST_HOOKS=0 and 1 ==="
  make selfcheck-both SIM="$sim"
}

run_sim icarus

if command -v verilator >/dev/null 2>&1; then
  if run_sim verilator; then
    echo "=== verilator line-coverage scaffold (HOOKS) ==="
    make cov-line || true
  else
    echo "NOTE: Verilator self-check failed; Icarus remains the gate (D7)."
  fi
else
  echo "NOTE: verilator not on PATH; skipped compare sim."
fi

python3 "$TB/scripts/summarize_tp.py"
echo "=== done ==="
