#!/usr/bin/env bash
# Auto-discover pytest + cocotb under tb/ and pytest under model/.
# Does not modify model/ or tb/models/. Icarus is the pass/fail sim (D7).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 -P "$GATE_DIR/tb_selfcheck.py"
