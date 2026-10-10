#!/usr/bin/env python3
"""Audit fake netlists: every FAIL must come from a real compare conclusion.

No filename / source-constant / compile-ok greps. Prints a Markdown table:
Fake × Method × Failure source (raw conclusion line).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EQUIV = ROOT / "scripts/gate/equiv_ref.sh"

FAKES = [
    ("forward_lane_dist", "ub_pcs_lane_dist", ROOT / "formal/pcs/negative/forward_lane_dist.sv"),
    ("forward_lane_dedist", "ub_pcs_lane_dedist", ROOT / "formal/pcs/negative/forward_lane_dedist.sv"),
    ("forward_lane_collect", "ub_pcs_lane_collect", ROOT / "formal/pcs/negative/forward_lane_collect.sv"),
    ("bcrc_flip", "ub_dll_bcrc", ROOT / "formal/dll/negative/bcrc_flip.sv"),
    ("bcrc_drop_start", "ub_dll_bcrc", ROOT / "formal/dll/negative/bcrc_drop_start_flit.sv"),
    ("bcrc_wrong_reset", "ub_dll_bcrc", ROOT / "formal/dll/negative/bcrc_wrong_reset.sv"),
    ("bcrc_extra_reg", "ub_dll_bcrc", ROOT / "formal/dll/negative/bcrc_extra_reg.sv"),
    ("bcrc_carry_after_last", "ub_dll_bcrc", ROOT / "formal/dll/negative/bcrc_carry_after_last.sv"),
    ("rst_adapt_wrong_pol", "ub_pyc_rst_adapt", ROOT / "formal/common/negative/rst_adapt_wrong_pol.sv"),
]

# Real compare conclusions only — not filenames or source constants.
REAL = re.compile(
    r"NOT EQUIVALENT|Verification failed|Assert failed|SAT proof finished - model found|"
    r"SAT Model|unmatched|ports=FAIL|reset=FAIL|regpair=FAIL|"
    r"INCONCLUSIVE\(state-encoding\)|未证完|ERROR:.*equiv|"
    r"Found [0-9]+ unproven|equiv_ref FAIL|scoreboard|MISMATCH",
    re.I,
)
GREP_SMELL = re.compile(r"grep .*INIT|filename match|compile.?ok", re.I)


def conclusion(log: str) -> str:
    for line in log.splitlines():
        if REAL.search(line):
            return line.strip()
    tail = [ln.strip() for ln in log.splitlines() if ln.strip()]
    return tail[-1] if tail else "(no conclusion)"


def run_one(leaf: str, net: Path, methods: str, extra_env: dict[str, str] | None = None) -> tuple[int, str]:
    env = {**os.environ, "EQUIV_METHODS": methods, "EQUIV_TMO": os.environ.get("EQUIV_TMO", "40")}
    if extra_env:
        env.update(extra_env)
    if "lane" in leaf:
        env.setdefault("NUM_LANES", "4")
    proc = subprocess.run(
        [str(EQUIV), leaf, str(net)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )
    return proc.returncode, proc.stdout or ""


def main() -> int:
    rows: list[tuple[str, str, str]] = []
    covered: dict[str, str] = {}
    wanted = ["equiv", "sat", "dsec", "&cec", "regpair"]
    specs = [
        ("equiv", "equiv", {}),
        ("sat", "sat", {}),
        ("dsec", "abc", {"EQUIV_ABC_STAGE": "dsec"}),
        ("&cec", "abc", {"EQUIV_ABC_STAGE": "cec"}),
        ("regpair", "regpair", {}),
        ("seq", "seq", {"EQUIV_SEQ_DEPTH": "8"}),
    ]
    # Keep the matrix readable: one method family per fake (plus seq on BCRC fakes).
    plan = [
        ("forward_lane_dist", [("equiv",), ("dsec",), ("&cec",)]),
        ("forward_lane_dedist", [("equiv",), ("&cec",)]),
        ("forward_lane_collect", [("equiv",), ("sat",)]),
        ("bcrc_flip", [("sat",), ("dsec",), ("regpair",), ("seq",)]),
        ("bcrc_drop_start", [("sat",), ("regpair",), ("seq",)]),
        ("bcrc_wrong_reset", [("regpair",), ("seq",)]),
        ("bcrc_extra_reg", [("regpair",)]),
        ("bcrc_carry_after_last", [("regpair",), ("seq",), ("&cec",)]),
        ("rst_adapt_wrong_pol", [("equiv",), ("&cec",), ("sat",)]),
    ]
    by_name = {n: (leaf, path) for n, leaf, path in FAKES}
    fail = 0
    for name, methods in plan:
        leaf, path = by_name[name]
        if not path.is_file():
            print(f"AUDIT SKIP missing {path}")
            fail += 1
            continue
        for (meth,) in methods:
            _label, family, extra = next(s for s in specs if s[0] == meth)
            rc, log = run_one(leaf, path, family, extra)
            line = conclusion(log)
            real = bool(REAL.search(log)) and rc != 0
            smell = bool(GREP_SMELL.search(log))
            src = line if real and not smell else f"NOT-REAL rc={rc} {line}"
            rows.append((name, meth, src))
            if real and not smell:
                covered[meth] = name
                print(f"AUDIT OK {name} × {meth}: {line}")
            else:
                fail += 1
                print(f"AUDIT BAD {name} × {meth} rc={rc}: {line}")
                print(log[-800:])

    print("\n## Fake netlist × Method × Failure source\n")
    print("| Fake | Method | Failure source (raw conclusion line) |")
    print("| --- | --- | --- |")
    for fake, meth, src in rows:
        print(f"| `{fake}` | `{meth}` | `{src.replace('|', '/').replace('`', '')}` |")

    missing = [m for m in wanted if m not in covered]
    if missing:
        print(f"\nAUDIT FAIL methods without a real FAIL: {missing}")
        fail += 1
    else:
        print("\nAUDIT OK every method family has ≥1 real FAIL")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
