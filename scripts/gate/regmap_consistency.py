#!/usr/bin/env python3
"""regmap-consistency: variants: table (PR #11 format) + optional gen --check.

When docs/regmap/regmap.yaml exists (format from PR #11 head b2e57475):

  variants:
    default: product_x4_vl2
    product_x4_vl2:
      NUM_LANES: 4
      NUM_VL: 2
      SCR_PLACEHOLDER: 0

Rules (blocking unless noted):
  - tag starting with product_ → PARAM_VARIANT.SCR_PLACEHOLDER reset must be 0
  - SCR_PLACEHOLDER=1 only on non-PRODUCT tags (Xia); lint/TB only; report column
  - NUM_LANES / NUM_VL must match `_xN` / `_vlN` in the tag

If scripts/gen_regmap.py exists, also run `python3 scripts/gen_regmap.py --check`.
Missing YAML / generator → skip that half and print the reason.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (  # noqa: E402
    Finding,
    REPO_ROOT,
    emit_report,
    load_yaml,
    print_tool_versions,
    run_cmd,
)

REGMAP_YAML = REPO_ROOT / "docs" / "regmap" / "regmap.yaml"
GEN_REGMAP = REPO_ROOT / "scripts" / "gen_regmap.py"

_X_RE = re.compile(r"_x(\d+)(?:_|$)")
_VL_RE = re.compile(r"_vl(\d+)(?:_|$)")


def _as_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("0x", "0X")):
            return int(text, 16)
        return int(text, 0)
    return None


def variant_tags(data: dict) -> dict[str, dict[str, int]]:
    raw = data.get("variants") or {}
    if not isinstance(raw, dict):
        return {}
    tags: dict[str, dict[str, int]] = {}
    for key, val in raw.items():
        if key == "default" or not isinstance(val, dict):
            continue
        parsed: dict[str, int] = {}
        for name, item in val.items():
            num = _as_int(item)
            if num is not None:
                parsed[str(name)] = num
        tags[str(key)] = parsed
    return tags


def collect_variant_findings(data: dict, yaml_rel: str) -> list[Finding]:
    findings: list[Finding] = []
    tags = variant_tags(data)
    if not tags:
        findings.append(
            Finding(
                check="regmap",
                module="variants",
                file=yaml_rel,
                rule="REGMAP_VARIANTS_MISSING",
                message="variants: table required (PR #11 format; SPEC §2.2)",
            )
        )
        return findings

    print("## regmap variants (PARAM_VARIANT)")
    print("| tag | PRODUCT | NUM_LANES | NUM_VL | SCR_PLACEHOLDER | lint/TB only |")
    print("| --- | --- | --- | --- | --- | --- |")

    scr1: list[str] = []
    for tag, params in tags.items():
        is_product = tag.startswith("product_")
        scr = params.get("SCR_PLACEHOLDER")
        lanes = params.get("NUM_LANES")
        nvl = params.get("NUM_VL")
        lint_tb = scr == 1
        if lint_tb:
            scr1.append(tag)
        print(
            f"| {tag} | {'yes' if is_product else 'no'} | {lanes} | {nvl} | "
            f"{scr} | {'yes' if lint_tb else 'no'} |"
        )

        if is_product and scr != 0:
            findings.append(
                Finding(
                    check="regmap",
                    module=tag,
                    file=yaml_rel,
                    rule="REGMAP_PRODUCT_SCR_PLACEHOLDER",
                    message=(
                        f"variants.{tag}: PARAM_VARIANT.SCR_PLACEHOLDER reset "
                        f"must be 0 for product_* (got {scr!r})"
                    ),
                )
            )
        if scr == 1 and is_product:
            # already blocked above; keep a single finding
            pass
        elif scr == 1:
            findings.append(
                Finding(
                    check="regmap",
                    module=tag,
                    file=yaml_rel,
                    rule="REGMAP_SCR_PLACEHOLDER",
                    message=(
                        f"variants.{tag}: SCR_PLACEHOLDER=1 is a non-PRODUCT "
                        "tag (Xia); lint/TB only, not synth/equiv/PRODUCT"
                    ),
                    bucket="report",
                )
            )
        elif scr not in (0, 1, None):
            findings.append(
                Finding(
                    check="regmap",
                    module=tag,
                    file=yaml_rel,
                    rule="REGMAP_SCR_PLACEHOLDER_VALUE",
                    message=f"variants.{tag}: SCR_PLACEHOLDER={scr!r} must be 0 or 1",
                )
            )

        name_lanes = _X_RE.search(tag)
        name_vl = _VL_RE.search(tag)
        if name_lanes is not None and lanes is not None and lanes != int(name_lanes.group(1)):
            findings.append(
                Finding(
                    check="regmap",
                    module=tag,
                    file=yaml_rel,
                    rule="REGMAP_VARIANT_LANES",
                    message=(
                        f"variants.{tag}: NUM_LANES={lanes} does not match "
                        f"_x{name_lanes.group(1)} in the tag"
                    ),
                )
            )
        if name_vl is not None and nvl is not None and nvl != int(name_vl.group(1)):
            findings.append(
                Finding(
                    check="regmap",
                    module=tag,
                    file=yaml_rel,
                    rule="REGMAP_VARIANT_VL",
                    message=(
                        f"variants.{tag}: NUM_VL={nvl} does not match "
                        f"_vl{name_vl.group(1)} in the tag"
                    ),
                )
            )
        if name_lanes is not None and lanes is None:
            findings.append(
                Finding(
                    check="regmap",
                    module=tag,
                    file=yaml_rel,
                    rule="REGMAP_VARIANT_LANES",
                    message=f"variants.{tag}: NUM_LANES missing (tag has _x{name_lanes.group(1)})",
                )
            )
        if name_vl is not None and nvl is None:
            findings.append(
                Finding(
                    check="regmap",
                    module=tag,
                    file=yaml_rel,
                    rule="REGMAP_VARIANT_VL",
                    message=f"variants.{tag}: NUM_VL missing (tag has _vl{name_vl.group(1)})",
                )
            )

    if scr1:
        print()
        print("## SCR_PLACEHOLDER=1 (lint/TB only; not PRODUCT)")
        for tag in scr1:
            print(f"  - {tag}")
    return findings


def main() -> int:
    print_tool_versions(["python"])
    findings: list[Finding] = []
    yaml_rel = "docs/regmap/regmap.yaml"

    if not REGMAP_YAML.is_file():
        print(f"skip variants: {yaml_rel} does not exist (no machine-readable map yet)")
    else:
        data = load_yaml(REGMAP_YAML)
        if not isinstance(data, dict):
            findings.append(
                Finding(
                    check="regmap",
                    module="variants",
                    file=yaml_rel,
                    rule="REGMAP_YAML_INVALID",
                    message="regmap.yaml root must be a mapping",
                )
            )
        else:
            findings.extend(collect_variant_findings(data, yaml_rel))

    if GEN_REGMAP.is_file():
        print("=== python3 scripts/gen_regmap.py --check ===")
        proc = run_cmd(
            [sys.executable, str(GEN_REGMAP), "--check"],
            cwd=REPO_ROOT,
            timeout=120,
        )
        print((proc.stdout or "").rstrip())
        if proc.returncode != 0:
            findings.append(
                Finding(
                    check="regmap",
                    module="gen_regmap",
                    file="scripts/gen_regmap.py",
                    rule="REGMAP_GEN_CHECK",
                    message=(
                        f"scripts/gen_regmap.py --check failed "
                        f"(exit {proc.returncode})"
                    ),
                )
            )
    else:
        print("skip gen --check: scripts/gen_regmap.py does not exist")

    return emit_report("regmap", findings)


if __name__ == "__main__":
    raise SystemExit(main())
