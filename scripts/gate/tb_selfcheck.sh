#!/usr/bin/env bash
# Auto-discover pytest + cocotb under tb/ and pytest under model/.
# Does not modify model/ or tb/models/. Icarus is the D7 pass/fail sim;
# Verilator (TOOLCHAIN.lock) is required so tb/cmn RTL sim cannot skip.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 -P "$GATE_DIR/tb_selfcheck.py"
