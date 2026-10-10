#!/usr/bin/env python3
"""Large-netlist manifest: variants over the impl_quick_synth bit threshold.

rtl/<layer>/manifest.yml lists each over-threshold variant (name, params,
pycc version, PRODUCT/HOOKS sha256). Gate regenerates when emit_rtl.py +
pycc are available and checks sha256 + ports + PRODUCT≡HOOKS except module
name. A committed .v over the threshold fails. A listed variant that the
isolated emit did not produce fails.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    Finding,
    LAYER_SKIP,
    RTL_SOURCE_SUFFIXES,
    cmn_mem_bits,
    cmn_mem_is_large,
    cmn_mem_tag_of,
    is_cmn_mem_module,
    is_handwritten_path,
    load_yaml,
    parse_cmn_mem_tag,
    read_cmn_mem_threshold_bits,
    rel,
    sha256_file,
    verilog_equal_except_module_name,
)
from hooks_port_consistency import compare_ports


def _layer_dirs(rtl_root: Path) -> list[Path]:
    if not rtl_root.is_dir():
        return []
    out: list[Path] = []
    for child in sorted(rtl_root.iterdir()):
        if child.is_dir() and child.name not in LAYER_SKIP and child.name != "gen":
            out.append(child)
    return out


def parse_manifest_entries(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = data.get("variants") or data.get("entries") or []
    else:
        return []
    entries: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(
            item.get("name") or item.get("variant") or item.get("module") or ""
        ).strip()
        params = item.get("params") or item.get("parameters") or {}
        if not isinstance(params, dict):
            params = {}
        pycc = str(
            item.get("pycc")
            or item.get("pycc_version")
            or item.get("pycc_lock")
            or ""
        ).strip()
        product_sha = str(
            item.get("product_sha256") or item.get("PRODUCT_sha256") or ""
        ).strip()
        hooks_sha = str(
            item.get("hooks_sha256") or item.get("HOOKS_sha256") or ""
        ).strip()
        entries.append(
            {
                "name": name,
                "params": params,
                "pycc": pycc,
                "product_sha256": product_sha,
                "hooks_sha256": hooks_sha,
            }
        )
    return entries


def _entry_bits(entry: dict[str, Any]) -> int | None:
    params = dict(entry.get("params") or {})
    tag = cmn_mem_tag_of(entry.get("name") or "")
    parsed = parse_cmn_mem_tag(tag or "")
    extra = dict(params)
    if parsed:
        extra.update(parsed)
        extra["module"] = entry.get("name")
    return cmn_mem_bits(None, extra)


def collect_committed_large_v(rtl_root: Path, thresh: int) -> list[Path]:
    hits: list[Path] = []
    if not rtl_root.is_dir():
        return hits
    for path in sorted(rtl_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in RTL_SOURCE_SUFFIXES:
            continue
        if "hooks" in {p.lower() for p in path.parts}:
            continue
        if "pyc_lib" in {p.lower() for p in path.parts}:
            continue
        if is_handwritten_path(path):
            continue
        extra = parse_cmn_mem_tag(cmn_mem_tag_of(path.stem) or "") or {
            "module": path.stem
        }
        if is_cmn_mem_module(path.stem) and cmn_mem_is_large(
            path, extra, thresh=thresh
        ):
            hits.append(path)
    return hits


def check_large_mem_manifest(
    rtl_root: Path,
    generated_rtl: Path | None = None,
    emit_available: bool = False,
    pycc_ready: bool = False,
    skip_reason: str = "",
    thresh: int | None = None,
    check: str = "emit",
) -> list[Finding]:
    """Return findings for committed large .v and manifest rows."""
    findings: list[Finding] = []
    limit = thresh if thresh is not None else read_cmn_mem_threshold_bits()
    for path in collect_committed_large_v(rtl_root, limit):
        bits = cmn_mem_bits(path, parse_cmn_mem_tag(cmn_mem_tag_of(path.stem) or ""))
        findings.append(
            Finding(
                check=check,
                module=path.stem,
                file=rel(path),
                rule="LARGE_V_COMMITTED",
                message=(
                    f"variant is {bits} bits > {limit}; over-threshold netlists "
                    "must be listed in rtl/<layer>/manifest.yml, not committed as .v"
                ),
            )
        )

    can_verify = bool(emit_available and pycc_ready and generated_rtl is not None)
    if not can_verify:
        reason = skip_reason or (
            "emit_rtl.py or pycc unavailable; manifest sha256 not regenerated"
        )
        print(f"manifest sha256/ports: skip ({reason})")

    for layer_dir in _layer_dirs(rtl_root):
        man = layer_dir / "manifest.yml"
        if not man.is_file():
            continue
        try:
            data = load_yaml(man)
        except SystemExit:
            findings.append(
                Finding(
                    check=check,
                    module="*",
                    file=rel(man),
                    rule="MANIFEST_UNREADABLE",
                    message=f"cannot parse {rel(man)}",
                )
            )
            continue
        entries = parse_manifest_entries(data)
        if not entries:
            findings.append(
                Finding(
                    check=check,
                    module="*",
                    file=rel(man),
                    rule="MANIFEST_EMPTY",
                    message=f"{rel(man)} has no variants",
                )
            )
            continue
        for entry in entries:
            name = entry["name"]
            missing_fields = [
                k
                for k, ok in (
                    ("name", bool(name)),
                    ("params", bool(entry["params"])),
                    ("pycc", bool(entry["pycc"])),
                    ("product_sha256", bool(entry["product_sha256"])),
                    ("hooks_sha256", bool(entry["hooks_sha256"])),
                )
                if not ok
            ]
            if missing_fields:
                findings.append(
                    Finding(
                        check=check,
                        module=name or "*",
                        file=rel(man),
                        rule="MANIFEST_FIELDS",
                        message=(
                            f"{rel(man)} entry missing {missing_fields} "
                            "(need variant name, params, pycc, PRODUCT/HOOKS sha256)"
                        ),
                    )
                )
            if not name:
                continue
            if not can_verify:
                findings.append(
                    Finding(
                        check=check,
                        module=name,
                        file=rel(man),
                        rule="MANIFEST_SKIP",
                        message=(
                            f"listed {name}: sha256/ports not regenerated "
                            f"({skip_reason or 'emit_rtl.py / pycc unavailable'})"
                        ),
                        bucket="report",
                    )
                )
                continue
            assert generated_rtl is not None
            product = generated_rtl / layer_dir.name / f"{name}.v"
            hooks = generated_rtl / layer_dir.name / "hooks" / f"{name}.v"
            if not product.is_file() or not hooks.is_file():
                findings.append(
                    Finding(
                        check=check,
                        module=name,
                        file=rel(man),
                        rule="MANIFEST_UNPRODUCIBLE",
                        message=(
                            f"manifest lists {name} but isolated emit_rtl.py "
                            f"did not produce PRODUCT ({product.is_file()}) "
                            f"and HOOKS ({hooks.is_file()})"
                        ),
                    )
                )
                continue
            got_p = sha256_file(product)
            got_h = sha256_file(hooks)
            if entry["product_sha256"] and got_p != entry["product_sha256"]:
                findings.append(
                    Finding(
                        check=check,
                        module=name,
                        file=rel(man),
                        rule="MANIFEST_SHA",
                        message=(
                            f"PRODUCT sha256 mismatch for {name}: "
                            f"manifest={entry['product_sha256']} generated={got_p}"
                        ),
                    )
                )
            if entry["hooks_sha256"] and got_h != entry["hooks_sha256"]:
                findings.append(
                    Finding(
                        check=check,
                        module=name,
                        file=rel(man),
                        rule="MANIFEST_SHA",
                        message=(
                            f"HOOKS sha256 mismatch for {name}: "
                            f"manifest={entry['hooks_sha256']} generated={got_h}"
                        ),
                    )
                )
            if not verilog_equal_except_module_name(product, hooks):
                findings.append(
                    Finding(
                        check=check,
                        module=name,
                        file=rel(man),
                        rule="CMN_MEM_BODY_DIFF",
                        message=(
                            f"large variant {name}: PRODUCT vs HOOKS must match "
                            "byte-for-byte except module name"
                        ),
                    )
                )
            extra = None
            port_hits = compare_ports(name, product, hooks, extra)
            for hit in port_hits:
                hit.check = check
            findings.extend(port_hits)
    return findings
