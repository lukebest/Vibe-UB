#!/usr/bin/env bash
# Deliberate-fail fixtures for each new gate check.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 "$GATE_DIR/selftest.py"
