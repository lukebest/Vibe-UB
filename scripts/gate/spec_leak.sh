#!/usr/bin/env bash
# Private spec must not land in the public repo.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
exec python3 -P "$GATE_DIR/spec_leak.py"
