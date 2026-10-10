#!/usr/bin/env bash
# Line A: call scripts/emit_rtl.py only (no homemade pycc argv),
# regen to an isolated tree, byte-compare rtl/<layer>/ and hooks/.
# Skip (report-only) when scripts/emit_rtl.py is missing.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 "$GATE_DIR/rtl_emit_consistency.py"
