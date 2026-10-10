#!/usr/bin/env bash
# Local + CI entry: Yosys synth per PRODUCT module (pass/fail, no QoR).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
python3 "$GATE_DIR/synth_selftest.py"
exec python3 "$GATE_DIR/synth_check.py"
