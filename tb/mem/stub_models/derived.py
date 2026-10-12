"""Regenerate lockfile data derived from the contract YAML headers.

When a new contract head lands the YAML SHA-256 changes. Rewrite
``_derived/yaml_digests.json`` from the live headers and the parsed
PTW ``desc_lvl`` × ENC_* cross (no raw-bit encodings). Digests use
``contract_sha256`` (canonical JSON of the YAML object, all fields).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contract_encodings import load_enc_class_table
from .contract_hash import contract_sha256
from .contract_yaml import (
    extract_yaml_header,
    find_contracts_dir,
    list_leaf_contract_paths,
    load_contract_document,
)

DERIVED_DIR = Path(__file__).resolve().parent / "_derived"
DIGESTS_NAME = "yaml_digests.json"


def digests_path() -> Path:
    return DERIVED_DIR / DIGESTS_NAME


# #43 head the lockfile was last regenerated against.
SOURCE_HEAD = "3d08513a7e334d7deb3b3279b203b05277faf713"


def collect_live() -> dict[str, Any]:
    root = find_contracts_dir()
    yaml_digests: dict[str, str] = {}
    for path in list_leaf_contract_paths(root):
        yaml_digests[path.name] = contract_sha256(path)

    ptw = load_contract_document(root / "ub_mem_ptw_desc_dec.md")
    table = load_enc_class_table(ptw.header, body=ptw.body, yaml_digest=ptw.yaml_digest)
    if table is None:
        raise ValueError("ub_mem_ptw_desc_dec has no ENC_* cross to derive")
    return {
        "final": True,
        "source_head": SOURCE_HEAD,
        "yaml_digests": yaml_digests,
        "ptw_yaml_digest": ptw.yaml_digest,
        "ptw_enc_cross": table.as_nested(),
        "ptw_enc_classes": list(table.classes),
        "ptw_source": table.source,
    }


def write_derived(path: Path | None = None) -> Path:
    dest = path or digests_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = collect_live()
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def load_derived(path: Path | None = None) -> dict[str, Any]:
    dest = path or digests_path()
    return json.loads(dest.read_text(encoding="utf-8"))


def live_matches_derived(path: Path | None = None) -> tuple[bool, str]:
    recorded = load_derived(path)
    live = collect_live()
    if live["yaml_digests"] != recorded.get("yaml_digests"):
        return False, "contract YAML hashes changed; regenerate _derived/yaml_digests.json"
    if live["ptw_enc_cross"] != recorded.get("ptw_enc_cross"):
        return False, "PTW ENC_* cross changed; regenerate _derived/yaml_digests.json"
    return True, "ok"


# extract_yaml_header stays imported so regen and tests share one parser.
__all__ = [
    "DERIVED_DIR",
    "SOURCE_HEAD",
    "collect_live",
    "digests_path",
    "extract_yaml_header",
    "live_matches_derived",
    "load_derived",
    "write_derived",
]
