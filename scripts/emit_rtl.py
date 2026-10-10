#!/usr/bin/env python3
"""Emit PRODUCT + HOOKS for every registered leaf.

    python3 scripts/emit_rtl.py

Re-execs the pyCircuit venv so `import pycircuit` is the toolchain
package (pycircuit-hisi) and local leaves load from pycircuit/.

Layout (SPEC §2.2 / CODING_STYLE §5):

    PRODUCT  rtl/<block>/<leaf>[_<tag>].v
    HOOKS    rtl/<block>/hooks/<leaf>[_<tag>].v

STEP 1 leaves (rst_adapt, lane _x4/_x8, BCRC gen/check) are compiled
with pycircuit + pycc. Scrambler / descrambler stay on leftover
f-string emitters until STEP 2.

Whitelist ``rtl/common/ub_rst_sync.sv`` is handwritten and is not
copied into ``hooks/`` (CODING_STYLE §3).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENV_PY = Path(os.environ.get("UB_PYC_VENV", "/tmp/venv")) / "bin" / "python"


def _reexec_venv() -> None:
    if not VENV_PY.is_file():
        return
    if Path(sys.executable).resolve() == VENV_PY.resolve():
        return
    os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])


_reexec_venv()

os.environ.setdefault(
    "PYC_TOOLCHAIN_ROOT",
    "/tmp/pyCircuit/.pycircuit_out/toolchain/install",
)
_root = Path(os.environ["PYC_TOOLCHAIN_ROOT"])
os.environ["PATH"] = f"{_root / 'bin'}:{os.environ.get('PATH', '')}"

PYC = REPO / "pycircuit"
if str(PYC) not in sys.path:
    sys.path.insert(0, str(PYC))

from emit import emit_all, register_batch1, try_pycc  # noqa: E402
from lib.registry import register  # noqa: E402, F401


def main() -> int:
    register_batch1()
    paths = emit_all()
    print(try_pycc())
    for p in paths:
        print(f"wrote {p.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
