#!/usr/bin/env bash
# Bind-existence first (formal/**/*.sby + referenced assertions).
# Then run every formal/<iface>/*.sby (cmn included). Each interface ships
# its own stub so the job does not need product RTL. Empty tree → success +
# "no assertions yet".
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

python3 -P "$GATE_DIR/formal_bind.py"

# formal/<iface>/*.sby only (GATE-FOR-002); PRIVATE_SKIP on stderr.
mapfile -t SBY_FILES < <(python3 -P "$GATE_DIR/private_leaves.py" --list-sby)

if [[ ${#SBY_FILES[@]} -eq 0 ]]; then
  echo "no assertions yet"
  echo "formal: PASS (no formal/**/*.sby; Xia will add interface assertions)"
  exit 0
fi

if ! command -v sby >/dev/null 2>&1; then
  echo "ERROR: formal/**/*.sby present but sby is not on PATH"
  echo "TOOL sby: locked=(not in TOOLCHAIN.lock) actual=MISSING — cannot pretend"
  exit 1
fi

fail=0
for sby in "${SBY_FILES[@]}"; do
  sby_dir=$(dirname "$sby")
  sby_base=$(basename "$sby")
  rel_sby=${sby#"$REPO_ROOT/"}
  echo "=== sby -f ${rel_sby} (cwd ${sby_dir#"$REPO_ROOT/"}) ==="
  # [files] tokens are sibling-relative, same as `make -C formal` (`cd iface && sby`).
  if ! (cd "$sby_dir" && sby -f --sequential "$sby_base"); then
    echo "formal FAIL: $sby"
    fail=1
  fi
done

# GATE-FORMAL-DEPTH (3): bmc >= deepest cover + 6. Report-only.
python3 -P "$GATE_DIR/formal_depth.py"
# GATE-PRIVATE-PARENT-FREE: default tasks must not assume private leaf outputs.
if ! python3 -P "$GATE_DIR/formal_parent_free.py"; then
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  echo "formal: FAIL (one or more .sby jobs failed)"
  exit 1
fi
echo "formal: PASS"
exit 0
