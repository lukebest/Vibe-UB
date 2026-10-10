#!/usr/bin/env bash
# Regmap consistency. Architecture-confirmed knobs (Xia / design, 2026-10-10):
#   regenerate : python3 scripts/gen_regmap.py
#   check      : python3 scripts/gen_regmap.py --check
# Gate calls --check. Missing generator → skip with reason (do not fail).
#
# When the generator lands, --check is the source of truth for drift.
# Re-confirm GEN_REGMAP / GEN_CMD with Xia before changing these.

set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

# --- architecture-owned knobs (confirm with Xia before editing) ---
GEN_REGMAP="scripts/gen_regmap.py"
REGMAP_YAML="docs/regmap/regmap.yaml"
GEN_CMD=(python3 "$GEN_REGMAP" --check)
# ------------------------------------------------------------------

python3 - <<'PY'
from gatelib import print_tool_versions
print_tool_versions(["python"])
PY

echo "regmap knobs: GEN_REGMAP=$GEN_REGMAP REGMAP_YAML=$REGMAP_YAML GEN_CMD=${GEN_CMD[*]}"

if [[ ! -f "$REPO_ROOT/$GEN_REGMAP" ]]; then
  echo "skip: $GEN_REGMAP does not exist (architecture generator not on this branch)"
  echo "regmap-consistency: PASS (skip)"
  exit 0
fi

if [[ ! -f "$REPO_ROOT/$REGMAP_YAML" ]]; then
  echo "skip: $REGMAP_YAML does not exist (no machine-readable map to check yet)"
  echo "regmap-consistency: PASS (skip)"
  exit 0
fi

echo "=== ${GEN_CMD[*]} ==="
exec "${GEN_CMD[@]}"
