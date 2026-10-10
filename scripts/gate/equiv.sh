#!/usr/bin/env bash
# Visible PRODUCT≡HOOKS job (eqy primary; Yosys equiv_* fallback).
# Same checker as rtl-emit-consistency; this wrapper is --equiv-only so
# C-line can see the eqy job without re-running emit.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 "$GATE_DIR/rtl_emit_consistency.py" --equiv-only
