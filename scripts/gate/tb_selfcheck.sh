#!/usr/bin/env bash
# Auto-discover pytest + cocotb under tb/ and pytest under model/.
# Does not modify model/ or tb/models/. Icarus is the D7 pass/fail sim;
# Verilator (TOOLCHAIN.lock) is required so tb/cmn RTL sim cannot skip.
set -euo pipefail
# shellcheck disable=SC1091
source "$(cd "$(dirname "$0")" && pwd)/lib.sh"
# lib.sh activates .pycircuit-venv for pycc jobs. That venv has no pytest /
# cocotb; after `make gate` runs provenance, tb-selfcheck would then fail.
# TB deps are the runner / repo .venv (tb/requirements.txt).
if [[ "${VIRTUAL_ENV:-}" == *".pycircuit-venv"* ]]; then
  if type deactivate >/dev/null 2>&1; then
    deactivate || true
  fi
  _new=""
  IFS=':' read -r -a _parts <<< "${PATH:-}"
  for _p in "${_parts[@]}"; do
    [[ "$_p" == *".pycircuit-venv"* ]] && continue
    _new="${_new:+$_new:}$_p"
  done
  export PATH="$_new"
  unset VIRTUAL_ENV _new _parts _p
  if [[ -d "$REPO_ROOT/.venv" ]]; then
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.venv/bin/activate"
  fi
fi
exec python3 -P "$GATE_DIR/tb_selfcheck.py"
