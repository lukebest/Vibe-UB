#!/usr/bin/env bash
# Local + CI entry: Verilator lint-only over every RTL top and leaf.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 -P "$GATE_DIR/lint.py"
