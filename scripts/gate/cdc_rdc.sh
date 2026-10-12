#!/usr/bin/env bash
# Local + CI entry: structural CDC / RDC (single core_clk, rst via ub_rst_sync).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 -P "$GATE_DIR/cdc_rdc.py"
