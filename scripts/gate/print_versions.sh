#!/usr/bin/env bash
# Print locked vs actual tool versions. Never pretend a lock is installed.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
python3 - <<'PY'
from gatelib import print_tool_versions
print_tool_versions(["python", "icarus", "verilator", "yosys", "eqy", "sby"])
PY
