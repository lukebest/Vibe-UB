#!/usr/bin/env bash
# Regmap consistency. Architecture-confirmed knobs (Xia / design, 2026-10-10):
#   regenerate : python3 scripts/gen_regmap.py
#   check      : python3 scripts/gen_regmap.py --check
# Gate also checks docs/regmap/regmap.yaml variants: (PR #11 format):
#   product_* → PARAM_VARIANT.SCR_PLACEHOLDER reset must be 0
#   SCR_PLACEHOLDER=1 → non-PRODUCT tag only; lint/TB; report column
#   NUM_LANES / NUM_VL must match _xN / _vlN in the tag
# Missing generator / YAML → that half is skipped with a reason (do not fail).
#
# Re-confirm GEN_REGMAP / GEN_CMD with Xia before changing these.

set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

# --- architecture-owned knobs (confirm with Xia before editing) ---
GEN_REGMAP="scripts/gen_regmap.py"
REGMAP_YAML="docs/regmap/regmap.yaml"
GEN_CMD=(python3 -P "$GEN_REGMAP" --check)
# ------------------------------------------------------------------

echo "regmap knobs: GEN_REGMAP=$GEN_REGMAP REGMAP_YAML=$REGMAP_YAML GEN_CMD=${GEN_CMD[*]}"
exec python3 -P "$GATE_DIR/regmap_consistency.py"
