#!/usr/bin/env bash
# Deliberate-fail fixtures: async-reset FF vs real latch / combo loop.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 "$GATE_DIR/synth_selftest.py"
