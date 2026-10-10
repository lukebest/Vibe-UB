#!/usr/bin/env python3
"""Roll up leaf-batch1 TCs by VERIF_PLAN TP id. No commit SHA in the report."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "tb" / "reports"
OUT = REPORTS / "regress" / "summary.txt"

TP_ROWS = (
    ("TP-UNIT-RST-001", "SPEC §4.2", "ub_rst_sync 2-stage"),
    ("TP-UNIT-CDC-001", "SPEC §4.2", "ub_rst_sync leaf"),
    ("TP-UNIT-RST-002", "SPEC §4.2", "ub_pyc_rst_adapt polarity"),
    ("TP-UNIT-PCS-006", "UB-PHY §3.2.2.3", "lane dist x4"),
    ("TP-UNIT-PCS-007", "UB-PHY §3.2.5", "lane dist x1/x2/x8"),
    ("TP-UNIT-PCS-008", "UB-PHY §3.2.3.3", "dedist / collect"),
    ("TP-UNIT-DLL-001", "SPEC §2.6", "BCRC generate"),
    ("TP-UNIT-DLL-002", "SPEC §2.6", "BCRC check"),
)


def _load_json(folder: Path) -> list[dict]:
    rows = []
    if not folder.exists():
        return rows
    for path in sorted(folder.glob("*.json")):
        try:
            rows.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            rows.append({"tb": path.stem, "error": "invalid json"})
    return rows


def _tp_status(rows: list[dict]) -> dict[str, str]:
    acc = {tid: "SKIP" for tid, _, _ in TP_ROWS}
    for rec in rows:
        for case in rec.get("tests", []):
            status = case.get("status", "FAIL")
            for tid in case.get("tp", []):
                if tid not in acc:
                    acc[tid] = status
                    continue
                if acc[tid] == "FAIL" or status == "FAIL":
                    acc[tid] = "FAIL"
                elif status == "PASS":
                    acc[tid] = "PASS"
    return acc


def _cov_files() -> dict:
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


def _cov_pct(payload: dict) -> str:
    vals = []
    for node in payload.values():
        if not isinstance(node, dict):
            continue
        c = node.get("coverage")
        if isinstance(c, (int, float)):
            vals.append(float(c))
    if not vals:
        return "n/a"
    return f"{sum(vals) / len(vals):.1f}%"


def main() -> None:
    REPORTS.joinpath("regress").mkdir(parents=True, exist_ok=True)
    hooks0 = _load_json(REPORTS / "regress" / "hooks0")
    hooks1 = _load_json(REPORTS / "regress" / "hooks1")
    all_rows = hooks0 + hooks1
    tp = _tp_status(all_rows)
    func = _cov_files()

    n_pass = n_fail = 0
    lines = [
        "Vibe-UB leaf batch 1 rollup",
        "",
        "TP                 spec                         status",
        "-" * 64,
    ]
    for tid, spec, desc in TP_ROWS:
        lines.append(f"{tid:<18} {spec:<28} {tp.get(tid, 'SKIP'):<8} {desc}")

    lines += ["", "Per-TB case results", "-" * 64]
    for rec in all_rows:
        tb = rec.get("tb", "?")
        hooks = rec.get("test_hooks", "?")
        seed = rec.get("seed", "?")
        lines.append(
            f"{tb} TEST_HOOKS={hooks} SEED={seed} "
            f"pass={rec.get('pass', 0)} fail={rec.get('fail', 0)}"
        )
        for case in rec.get("tests", []):
            st = case.get("status")
            if st == "PASS":
                n_pass += 1
            elif st == "FAIL":
                n_fail += 1
            lines.append(
                f"  {st} {case.get('test')} TP={','.join(case.get('tp', []))}"
            )

    lines += ["", f"case PASS={n_pass} FAIL={n_fail}", "", "functional coverage JSON"]
    for name, payload in func.items():
        lines.append(f"  {name}: {_cov_pct(payload)}")

    lines += [
        "",
        "Line coverage: tb/reports/cov_line/ (Verilator --coverage, HOOKS denominator).",
        "Icarus is the pass/fail gate and does not produce line coverage (D7).",
        "Scrambler / descrambler leaf TBs are out of this batch (SPEC §13).",
    ]
    OUT.write_text("\n".join(lines) + "\n")
    print(OUT.read_text())


if __name__ == "__main__":
    main()
