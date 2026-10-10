#!/usr/bin/env bash
# `make gate` — run every gate job locally in the same order CI can use.
# Continues after a failure so the two-column report is complete.
set -u
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

jobs=(
  rtl-emit-consistency
  equiv
  pycircuit-provenance
  hooks-port-consistency
  lint
  synth-check
  cdc-rdc
  formal
  regmap-consistency
  tb-selfcheck
)

declare -A rc
fail=0
for job in "${jobs[@]}"; do
  script="$GATE_DIR/${job//-/_}.sh"
  echo
  echo "########## gate job: $job ##########"
  if [[ -x "$script" ]]; then
    if "$script"; then
      rc[$job]=0
    else
      rc[$job]=$?
      fail=1
    fi
  else
    echo "ERROR: missing $script"
    rc[$job]=127
    fail=1
  fi
done

echo
echo "=== make gate summary ==="
for job in "${jobs[@]}"; do
  if [[ ${rc[$job]} -eq 0 ]]; then
    echo "  PASS  $job"
  else
    echo "  FAIL  $job  (exit ${rc[$job]})"
  fi
done

if [[ "$fail" -ne 0 ]]; then
  echo "gate: FAIL"
  exit 1
fi
echo "gate: PASS"
exit 0
