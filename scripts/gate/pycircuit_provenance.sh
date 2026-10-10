#!/usr/bin/env bash
# Line A: pyCircuit provenance (AST static check + report-only pycc emit).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 "$GATE_DIR/pycircuit_provenance.py"
