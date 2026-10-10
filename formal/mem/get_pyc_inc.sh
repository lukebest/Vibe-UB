#!/usr/bin/env bash
# Resolve pyc_reg.v the same way as scripts/check_mem.sh / tb/mem/run_smoke.sh:
#   * rtl/pyc_lib/pyc_reg.v if present (PR #21 already on this tree)
#   * else fetch origin/cursor/cmn-mem-1r1w-5d26:rtl/pyc_lib/pyc_reg.v
# Writes formal/mem/inc/pyc_reg.v for ub_mem_tlb.sby (`include / -I).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DEST="$HERE/inc/pyc_reg.v"
PR21_REF="${PR21_REF:-origin/cursor/cmn-mem-1r1w-5d26}"

mkdir -p "$HERE/inc"
if [[ -f "$ROOT/rtl/pyc_lib/pyc_reg.v" ]]; then
  cp "$ROOT/rtl/pyc_lib/pyc_reg.v" "$DEST"
  echo "pyc_reg.v from rtl/pyc_lib"
else
  git -C "$ROOT" cat-file -e "${PR21_REF}:rtl/pyc_lib/pyc_reg.v" 2>/dev/null \
    || git -C "$ROOT" fetch origin cursor/cmn-mem-1r1w-5d26
  git -C "$ROOT" show "${PR21_REF}:rtl/pyc_lib/pyc_reg.v" > "$DEST"
  echo "pyc_reg.v from $PR21_REF"
fi

if [[ ! -s "$DEST" ]]; then
  echo "FAIL: pyc_reg.v not found (need #21 rtl/pyc_lib or fetch $PR21_REF)"
  exit 1
fi
