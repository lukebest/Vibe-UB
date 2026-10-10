#!/usr/bin/env bash
# Common paths for the gate wrappers. CI and `make gate` source this.
# Do not `set -e` here: run_all.sh sources this and must continue after a job fails.

GATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$GATE_DIR/../.." && pwd)"
export GATE_DIR REPO_ROOT
# Layer import root first so leaves can `from <layer>.lib import ...`.
# Never put the repo root on PYTHONPATH: ./pycircuit shadows the install.
_filtered=""
if [[ -n "${PYTHONPATH:-}" ]]; then
  IFS=':' read -r -a _pp <<< "$PYTHONPATH"
  for _p in "${_pp[@]}"; do
    [[ -z "$_p" || "$_p" == "." ]] && continue
    _abs="$(cd "$_p" 2>/dev/null && pwd || echo "$_p")"
    [[ "$_abs" == "$REPO_ROOT" ]] && continue
    _filtered="${_filtered:+$_filtered:}$_p"
  done
fi
export PYTHONPATH="$REPO_ROOT/pycircuit:$GATE_DIR${_filtered:+:$_filtered}"
export PYTHONSAFEPATH=1
unset _filtered _pp _p _abs
cd "$REPO_ROOT"

if [[ -d "$REPO_ROOT/.pycircuit-venv" ]]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.pycircuit-venv/bin/activate"
  if [[ -d "$REPO_ROOT/.pycircuit_out/toolchain/install/bin" ]]; then
    export PATH="$REPO_ROOT/.pycircuit_out/toolchain/install/bin:$PATH"
    export PYC_TOOLCHAIN_ROOT="$REPO_ROOT/.pycircuit_out/toolchain/install"
  fi
elif [[ -d "$REPO_ROOT/.venv" ]]; then
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.venv/bin/activate"
fi
