#!/usr/bin/env bash
# Common paths for the gate wrappers. CI and `make gate` source this.
# Do not `set -e` here: run_all.sh sources this and must continue after a job fails.

GATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$GATE_DIR/../.." && pwd)"
export GATE_DIR REPO_ROOT
export PYTHONPATH="$GATE_DIR${PYTHONPATH:+:$PYTHONPATH}"
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
