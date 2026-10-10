#!/usr/bin/env bash
# Regenerate into a temp dir and fail on drift vs committed outputs.
# Official CSR Python: pycircuit/csr/ub_csr.py  RAL: tb/ral/ub_regmodel.py
# Prefer: python3 scripts/gen_regmap.py --check
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 scripts/gen_regmap.py --check
