#!/usr/bin/env bash
# Contract YAML + private stub hash + reports/private attest + role dirs + owned paths.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 -P "$GATE_DIR/contract_check.py"
