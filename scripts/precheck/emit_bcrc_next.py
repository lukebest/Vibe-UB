#!/usr/bin/env python3
"""Emit a combo-only next-CRC pycc netlist for scripts/precheck/ (non-gating)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VENV_PY = Path(os.environ.get("UB_PYC_VENV", "/tmp/venv")) / "bin" / "python"


def _reexec() -> None:
    if VENV_PY.is_file() and Path(sys.executable).resolve() != VENV_PY.resolve():
        os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])


_reexec()
PYC = REPO / "pycircuit"
sys.path.insert(0, str(PYC))

os.environ.setdefault(
    "PYC_TOOLCHAIN_ROOT",
    "/tmp/pyCircuit/.pycircuit_out/toolchain/install",
)
os.environ["PATH"] = (
    f"{Path(os.environ['PYC_TOOLCHAIN_ROOT']) / 'bin'}:{os.environ.get('PATH', '')}"
)

from pycircuit import Circuit, module  # noqa: E402

from dll.lib import CRC_W, FLIT_W, next_crc_hw  # noqa: E402
from lib.pycc_emit import compile_to_verilog  # noqa: E402


@module(name="ub_dll_bcrc_next")
def build(m: Circuit, test_hooks: int = 0) -> None:
    _ = int(test_hooks)
    crc_q = m.input("crc_q", width=CRC_W)
    data_in = m.input("data_in", width=FLIT_W)
    last = m.input("last", width=1)
    m.output("nxt", next_crc_hw(m, crc_q, data_in, last))


build.__pycircuit_name__ = "ub_dll_bcrc_next"


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/ub-ev/ub_dll_bcrc_next.v")
    out.parent.mkdir(parents=True, exist_ok=True)
    body = compile_to_verilog(
        build, name="ub_dll_bcrc_next", params={}, test_hooks=False
    )
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out} ({len(body)} bytes)")


if __name__ == "__main__":
    main()
