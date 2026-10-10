#!/usr/bin/env bash
# Line A: emit + git diff rtl/ + hooks present + PRODUCT↔hooks eqy.
# Skip (print reason) when scripts/emit_rtl.py is missing.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 "$GATE_DIR/rtl_emit_consistency.py"
