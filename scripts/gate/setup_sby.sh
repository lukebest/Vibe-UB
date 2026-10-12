#!/usr/bin/env bash
# ubuntu-24.04 apt has yosys 0.33 but no sby package. `apt-get install sby || true`
# leaves PATH empty, then formal.sh dies once formal/**/*.sby exists (#21).
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"

SBY_REPO="${SBY_REPO:-https://github.com/YosysHQ/sby}"
SBY_REF="${SBY_REF:-v0.69}"
SBY_SRC="${SBY_SRC:-$REPO_ROOT/.sby-src}"
SBY_BIN="${SBY_BIN:-$REPO_ROOT/.sby-src/sby}"

if command -v sby >/dev/null 2>&1; then
  echo "sby already on PATH: $(command -v sby)"
  sby --help >/dev/null
  exit 0
fi

if [[ ! -d "$SBY_SRC/.git" ]]; then
  git clone --depth 1 --branch "$SBY_REF" "$SBY_REPO" "$SBY_SRC"
fi
# Wrapper so `sby` finds sbysrc/*.py (click is in scripts/gate/requirements.txt).
cat > "$SBY_BIN" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$SBY_SRC/sbysrc\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 "$SBY_SRC/sbysrc/sby.py" "\$@"
EOF
chmod +x "$SBY_BIN"
export PATH="$(dirname "$SBY_BIN"):$PATH"
if ! command -v z3 >/dev/null 2>&1; then
  echo "ERROR: z3 is not on PATH (cmn.sby uses smtbmc z3)"
  exit 1
fi
sby --help >/dev/null
echo "sby installed: $SBY_BIN (ref $SBY_REF)"
