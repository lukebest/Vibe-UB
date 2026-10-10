#!/usr/bin/env python3
"""Roll up leaf-batch1 TCs by VERIF_PLAN TP id. No commit SHA in the report."""

from __future__ import annotations

import json
import re
from collections import defaultdict
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

COV_PREFIX = {
    "ub_rst_sync": "tp.rst_sync.",
    "ub_pyc_rst_adapt": "tp.rst_adapt.",
    "ub_pcs_lane_dist": "tp.lane.",
    "ub_pcs_lane_dedist": "tp.lane.",
    "ub_pcs_lane_collect": "tp.lane.",
    "ub_dll_bcrc": "tp.bcrc.",
    "ub_dll_bcrc_check": "tp.bcrc_chk.",
}

CASE_RE = re.compile(
    r"^(PASS|FAIL) (?P<name>\S+) TP=(?P<tp>\S+) SEED (?P<seed>\S+) "
    r"TEST_HOOKS=(?P<hooks>\S+)"
)
SUITE_RE = re.compile(r"^(PASS|FAIL) (?P<tb>\S+)_suite TEST_HOOKS=(?P<hooks>\S+)")


def _sim_roots() -> list[Path]:
    roots = []
    for name in ("icarus", "verilator"):
        p = REPORTS / "regress" / name
        if p.is_dir():
            roots.append(p)
    return roots


def _iter_json() -> list[dict]:
    rows = []
    for root in _sim_roots():
        for path in sorted(root.glob("**/*.json")):
            try:
                rec = json.loads(path.read_text())
            except json.JSONDecodeError:
                rec = {"tb": path.stem, "error": "invalid json", "tests": []}
            rec["_path"] = str(path.relative_to(REPORTS))
            rec["_sim"] = _sim_from_path(path)
            rows.append(rec)
    return rows


def _sim_from_path(path: Path) -> str:
    parts = path.parts
    if "icarus" in parts:
        return "icarus"
    if "verilator" in parts:
        return "verilator"
    return "unknown"


def _iter_log_cases() -> list[dict]:
    rows = []
    for root in _sim_roots():
        for path in sorted(root.glob("**/*.log")):
            sim = _sim_from_path(path)
            for line in path.read_text(errors="replace").splitlines():
                m = CASE_RE.match(line)
                if not m:
                    continue
                rows.append(
                    {
                        "status": m.group(1),
                        "test": m.group("name"),
                        "tp": [t for t in m.group("tp").split(",") if t],
                        "seed": m.group("seed"),
                        "test_hooks": m.group("hooks"),
                        "sim": sim,
                        "log": path.name,
                    }
                )
    return rows


def _tp_status(cases: list[dict]) -> dict[str, str]:
    acc = {tid: "SKIP" for tid, _, _ in TP_ROWS}
    for case in cases:
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


def _merge_cov_bins() -> dict[str, dict[str, dict[str, int]]]:
    """prefix -> cover item -> bin -> hits (summed across files)."""
    merged: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    cov = REPORTS / "cov_func"
    if not cov.exists():
        return merged
    for path in sorted(cov.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        for name, node in payload.items():
            if not isinstance(node, dict):
                continue
            detailed = node.get("detailed")
            if not isinstance(detailed, dict):
                continue
            if any(isinstance(v, dict) for v in detailed.values()):
                continue
            for prefix in set(COV_PREFIX.values()):
                if name.startswith(prefix):
                    for bin_name, hits in detailed.items():
                        if isinstance(hits, (int, float)):
                            merged[prefix][name][str(bin_name)] += int(hits)
    return merged


def _cov_line(item: str, bins: dict[str, int]) -> str:
    hit = sum(1 for v in bins.values() if v > 0)
    total = len(bins)
    pct = (100.0 * hit / total) if total else 0.0
    return f"  {item}: {hit}/{total} bins ({pct:.1f}%)"


def main() -> None:
    REPORTS.joinpath("regress").mkdir(parents=True, exist_ok=True)
    json_rows = _iter_json()
    log_cases = _iter_log_cases()
    json_cases = []
    for rec in json_rows:
        for case in rec.get("tests", []):
            case = dict(case)
            case["sim"] = rec.get("_sim", "unknown")
            case["tb"] = rec.get("tb")
            json_cases.append(case)

    cases = log_cases or json_cases
    tp = _tp_status(cases)

    n_pass = sum(1 for c in cases if c.get("status") == "PASS")
    n_fail = sum(1 for c in cases if c.get("status") == "FAIL")

    lines = [
        "Vibe-UB leaf batch 1 rollup",
        "",
        "TP                 spec                         status",
        "-" * 64,
    ]
    for tid, spec, desc in TP_ROWS:
        lines.append(f"{tid:<18} {spec:<28} {tp.get(tid, 'SKIP'):<8} {desc}")

    by_sim: dict[str, list[dict]] = defaultdict(list)
    for rec in json_rows:
        by_sim[rec.get("_sim", "unknown")].append(rec)

    if not json_rows and log_cases:
        by_sim["logs"] = []

    lines += ["", "Per-TB case results", "-" * 64]
    if json_rows:
        for rec in json_rows:
            tb = rec.get("tb", "?")
            hooks = rec.get("test_hooks", "?")
            seed = rec.get("seed", "?")
            tag = rec.get("tag") or ""
            sim = rec.get("_sim", "?")
            extra = f" tag={tag}" if tag else ""
            lines.append(
                f"{tb} sim={sim} TEST_HOOKS={hooks} SEED={seed}{extra} "
                f"pass={rec.get('pass', 0)} fail={rec.get('fail', 0)}"
            )
            for case in rec.get("tests", []):
                lines.append(
                    f"  {case.get('status')} {case.get('test')} "
                    f"TP={','.join(case.get('tp', []))}"
                )
    else:
        for case in log_cases:
            lines.append(
                f"  {case['status']} {case['test']} TP={','.join(case['tp'])} "
                f"sim={case['sim']} TEST_HOOKS={case['test_hooks']} "
                f"log={case['log']}"
            )

    lines += ["", f"case PASS={n_pass} FAIL={n_fail} (from {'logs' if log_cases else 'json'})"]

    merged = _merge_cov_bins()
    lines += ["", "functional coverage (relevant CoverPoint / CoverCross bins, merged)"]
    if not merged:
        lines.append("  (no cov_func JSON)")
    for tb, prefix in COV_PREFIX.items():
        items = merged.get(prefix)
        if not items:
            continue
        lines.append(f"{tb} ({prefix.rstrip('.')})")
        for name in sorted(items):
            lines.append(_cov_line(name, items[name]))

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
