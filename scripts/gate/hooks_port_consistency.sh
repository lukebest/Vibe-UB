#!/usr/bin/env bash
# Independent HOOKS vs PRODUCT port check (SPEC §11 (f)).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 -P "$GATE_DIR/hooks_port_consistency.py"
