"""Blackbox set for every PRODUCT≡HOOKS / regpair / emit-consistency flatten.

Set = scripts/gate/blackbox.yml modules ∪ docs/arch/*/contracts/ leaves.
Applied as Yosys `blackbox <name>` after hierarchy, before flatten.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import REPO_ROOT, load_yaml, stub_modules
from private_leaves import discover_contract_files, parse_contract_file


def contract_leaf_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in discover_contract_files(root):
        data, _errs = parse_contract_file(path, root)
        if data and data.get("leaf"):
            names.add(str(data["leaf"]).strip())
    return {n for n in names if n}


def yml_blackbox_modules(root: Path) -> set[str]:
    path = root / "scripts" / "gate" / "blackbox.yml"
    names: set[str] = set()
    if path.is_file():
        data = load_yaml(path)
        rows = data.get("entries") if isinstance(data, dict) else None
        for entry in rows or []:
            if not isinstance(entry, dict):
                continue
            for key in ("module", "name"):
                mod = str(entry.get(key) or "").strip()
                if mod:
                    names.add(mod)
            pat = str(entry.get("file") or "").strip()
            if pat:
                names.add(Path(pat).stem)
    names |= stub_modules()
    return {n for n in names if n}


def equiv_blackbox_set(root: Path) -> list[str]:
    return sorted(yml_blackbox_modules(root) | contract_leaf_names(root))


def ys_blackbox_cmds(names: list[str] | None = None, root: Path | None = None) -> list[str]:
    mods = list(names) if names is not None else equiv_blackbox_set(root or REPO_ROOT)
    return [f"blackbox {name}" for name in mods]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ys", action="store_true", help="print Yosys blackbox lines")
    args = parser.parse_args()
    names = equiv_blackbox_set(REPO_ROOT)
    if args.ys:
        for line in ys_blackbox_cmds(names):
            print(line)
        return 0
    print(f"equiv blackbox set ({len(names)}): {', '.join(names) or '(empty)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
