#!/usr/bin/env python3
"""Fail if results.xml records a failure, or if no testcase ran."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

path = Path("results.xml")
if not path.is_file():
    print("check_sim: missing results.xml")
    raise SystemExit(1)
root = ET.parse(path).getroot()
cases = list(root.iter("testcase"))
if not cases:
    print("check_sim: no testcase in results.xml")
    raise SystemExit(1)
fails = [c for c in cases if c.find("failure") is not None or c.find("error") is not None]
if fails:
    names = [c.attrib.get("name", "?") for c in fails]
    print(f"check_sim: FAIL {names}")
    raise SystemExit(1)
print(f"check_sim: PASS ({len(cases)} testcase(s))")
