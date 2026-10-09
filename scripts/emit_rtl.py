#!/usr/bin/env python3
"""Repo-root wrapper: python3 scripts/emit_rtl.py → rtl/gen/."""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[1] / "pycircuit" / "emit.py"), run_name="__main__")
