#!/usr/bin/env bash
# Regenerate into a temp dir and fail on drift vs committed outputs.
# Prefer: python3 scripts/gen_regmap.py --check
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 scripts/gen_regmap.py --check
