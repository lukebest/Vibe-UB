#!/usr/bin/env python3
"""Test double of scripts/gate/contract_hash.py (PR #47).

Production attest mode imports the gate module. This copy exists so
scripts/impl/tests can build a fake repo before #47 lands on main.
The digest must stay: yaml.safe_load → json.dumps(sort_keys=True,
separators=(',', ':'), ensure_ascii=False) → UTF-8 → sha256.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)",
    re.S,
)
FENCE_RE = re.compile(
    r"\A```ya?ml[ \t]*\n(.*?)```",
    re.S,
)


def extract_contract_yaml(text: str) -> str | None:
    m = FRONT_MATTER_RE.match(text)
    if m:
        return m.group(1)
    m = FENCE_RE.match(text)
    if m:
        return m.group(1)
    return None


def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    return str(obj)


def canonical_contract_bytes(obj: Any) -> bytes:
    return json.dumps(
        _jsonable(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def contract_sha256(path: Path | str) -> str:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    body = extract_contract_yaml(text)
    if body is None:
        raise ValueError(f"{p}: no leading YAML segment (--- … ---)")
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise ValueError("PyYAML is required for contract_sha256") from exc
    obj = yaml.safe_load(body)
    if not isinstance(obj, dict):
        raise ValueError(f"{p}: contract YAML must be a mapping")
    return hashlib.sha256(canonical_contract_bytes(obj)).hexdigest()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print("usage: contract_hash.py <contract.md>")
        return 0 if args and args[0] in {"-h", "--help"} else 2
    print(contract_sha256(Path(args[0])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
