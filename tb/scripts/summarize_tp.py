#!/usr/bin/env python3
"""Roll up self-check / later TCs by VERIF_PLAN TP id.

Scaffold only: this PR has no product DUT, so TPs stay SKIP / skeleton.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "tb" / "reports"
OUT = REPORTS / "regress" / "summary.txt"

# Placeholder rows — full matrix is docs/VERIF_PLAN.md on PR #3.
SKELETON_TPS = (
    ("TP-UNIT-PCS-003", "UB-PHY §3.2.2.4", "scrambler model pytest", "models"),
    ("TP-UNIT-PCS-004", "UB-PHY §3.2.3.2", "descrambler inverse pytest", "models"),
    ("TP-UNIT-PCS-006", "UB-PHY §3.2.2.3", "lane dist x4 pytest", "models"),
    ("TP-UNIT-PCS-007", "UB-PHY §3.2.2.3", "lane dist x1/x8 pytest", "models"),
    ("TP-UNIT-PCS-008", "UB-PHY §3.2.2.3", "dedist inverse pytest", "models"),
    ("TP-UNIT-DLL-001", "UB-DL §4.3.2.2.4 / §4.7.2", "BCRC generate pytest", "models"),
    ("TP-UNIT-DLL-002", "UB-DL §4.7.2", "BCRC check pytest", "models"),
    ("TP-TB-SELF-001", "SPEC §3.1 / §3.2.3 / §10 / §11", "passthrough skeleton", "sim"),
)


def _load_func() -> dict:
    acc = {}
    cov = REPORTS / "cov_func"
    if not cov.exists():
        return acc
    for path in sorted(cov.glob("*.json")):
        try:
            acc[path.name] = json.loads(path.read_text())
        except json.JSONDecodeError:
            acc[path.name] = {"error": "invalid json"}
    return acc


def main() -> None:
    REPORTS.joinpath("regress").mkdir(parents=True, exist_ok=True)
    func = _load_func()
    lines = [
        "Vibe-UB TB rollup (scaffold)",
        "",
        "TP                 spec                              status     via",
        "-" * 78,
    ]
    for tid, spec, desc, via in SKELETON_TPS:
        status = "PASS" if via == "models" else "SKELETON"
        if via == "sim" and func:
            status = "PASS" if any(func.values()) else "SKELETON"
        lines.append(f"{tid:<18} {spec:<33} {status:<10} {desc}")
    lines.append("")
    lines.append(f"functional JSON files: {len(func)}")
    for name in func:
        lines.append(f"  - {name}")
    lines.append("")
    lines.append("Line coverage: tb/reports/cov_line/ (Verilator --coverage, HOOKS stand-in).")
    lines.append("Icarus is the pass/fail gate and does not produce line coverage (D7).")
    OUT.write_text("\n".join(lines) + "\n")
    print(OUT.read_text())


if __name__ == "__main__":
    main()
