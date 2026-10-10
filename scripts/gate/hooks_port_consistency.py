#!/usr/bin/env python3
"""Independent HOOKS vs PRODUCT port check (Xia ruling, SPEC §11 (f)).

Leaves not in scripts/gate/hooks_ports.yml: HOOKS ports == PRODUCT ports
(no tb_test_mode). Listed modules: HOOKS = PRODUCT + extra_ports.
Failure is blocking.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import (
    REPO_ROOT,
    Finding,
    discover_layers,
    discover_leaf_pairs,
    emit_report,
    hooks_extra_for,
    is_handwritten_path,
    is_legacy_path,
    is_listed_hook_style,
    is_tb_obs_port,
    is_tb_port,
    load_hooks_ports,
    parse_port_decls,
    packed_width,
    print_tool_versions,
    rel,
)


def compare_ports(
    module: str,
    product: Path,
    hooks: Path,
    allowed_extra: list[str] | None,
    incdirs: list[Path] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    prod_full = parse_port_decls(product, incdirs=incdirs, module=module)
    hook_full = parse_port_decls(hooks, incdirs=incdirs, module=module)
    prod = [(d, n) for d, n, _p in prod_full]
    hook = [(d, n) for d, n, _p in hook_full]
    prod_names = [n for _d, n in prod]
    hook_names = [n for _d, n in hook]
    prod_dir = {n: d for d, n in prod}
    hook_dir = {n: d for d, n in hook}
    prod_w = {n: packed_width(p) for _d, n, p in prod_full}
    hook_w = {n: packed_width(p) for _d, n, p in hook_full}
    extra = list(allowed_extra or [])

    prod_tb = [n for n in prod_names if is_tb_port(n)]
    if prod_tb:
        findings.append(
            Finding(
                check="hooks_ports",
                module=module,
                file=rel(product),
                rule="HOOKS_PORT_ON_PRODUCT",
                message=(
                    f"tb_* ports {prod_tb} must only appear on HOOKS "
                    "(gated by tb_test_mode; SPEC §10 / §11 (f))"
                ),
            )
        )

    if allowed_extra is None:
        if hook_names != prod_names:
            findings.append(
                Finding(
                    check="hooks_ports",
                    module=module,
                    file=rel(hooks),
                    rule="HOOKS_PORT_MISMATCH",
                    message=(
                        "leaf is not on scripts/gate/hooks_ports.yml; HOOKS ports "
                        f"must match PRODUCT exactly (product={prod_names} "
                        f"hooks={hook_names})"
                    ),
                )
            )
        else:
            for name in prod_names:
                if prod_dir.get(name) != hook_dir.get(name):
                    findings.append(
                        Finding(
                            check="hooks_ports",
                            module=module,
                            file=rel(hooks),
                            rule="HOOKS_PORT_DIR",
                            message=(
                                f"port {name} direction PRODUCT="
                                f"{prod_dir.get(name)} HOOKS={hook_dir.get(name)}"
                            ),
                        )
                    )
                if prod_w.get(name) != hook_w.get(name):
                    findings.append(
                        Finding(
                            check="hooks_ports",
                            module=module,
                            file=rel(hooks),
                            rule="HOOKS_PORT_WIDTH",
                            message=(
                                f"port {name} width PRODUCT={prod_w.get(name)} "
                                f"HOOKS={hook_w.get(name)}"
                            ),
                        )
                    )
        forbidden = [n for n in hook_names if is_tb_port(n)]
        if forbidden:
            findings.append(
                Finding(
                    check="hooks_ports",
                    module=module,
                    file=rel(hooks),
                    rule="HOOKS_PORT_UNEXPECTED",
                    message=(
                        f"tb_* {forbidden} not on scripts/gate/hooks_ports.yml "
                        "(SPEC §10 list; Xia: tb_<inst>_bd_* / tb_<inst>_bd_vld_*)"
                    ),
                )
            )
        return findings

    bad_style = [n for n in extra if is_tb_port(n) and not is_listed_hook_style(n)]
    if bad_style:
        findings.append(
            Finding(
                check="hooks_ports",
                module=module,
                file=rel(hooks),
                rule="HOOKS_PORT_BAD_NAME",
                message=(
                    f"listed extras {bad_style} are not tb_test_mode / tb_inj_* / "
                    f"tb_obs_* / tb_<inst>_obs_* / tb_<inst>_bd_* / tb_<inst>_bd_vld_*"
                ),
            )
        )
    expected = prod_names + extra
    missing_prod = [n for n in prod_names if n not in hook_dir]
    missing_extra = [n for n in extra if n not in hook_dir]
    unexpected = [n for n in hook_names if n not in expected]
    unexpected_tb = [n for n in unexpected if is_tb_port(n)]
    if unexpected_tb:
        findings.append(
            Finding(
                check="hooks_ports",
                module=module,
                file=rel(hooks),
                rule="HOOKS_PORT_UNEXPECTED",
                message=(
                    f"tb_* {unexpected_tb} not on the SPEC §10 list "
                    "(hooks_ports.yml) for this module"
                ),
            )
        )
    if missing_prod or missing_extra or unexpected:
        findings.append(
            Finding(
                check="hooks_ports",
                module=module,
                file=rel(hooks),
                rule="HOOKS_PORT_MISMATCH",
                message=(
                    "HOOKS must be PRODUCT + scripts/gate/hooks_ports.yml extras; "
                    f"missing_product={missing_prod} missing_extra={missing_extra} "
                    f"unexpected={unexpected}"
                ),
            )
        )
    for name in prod_names:
        if name in hook_dir and prod_dir.get(name) != hook_dir.get(name):
            findings.append(
                Finding(
                    check="hooks_ports",
                    module=module,
                    file=rel(hooks),
                    rule="HOOKS_PORT_DIR",
                    message=(
                        f"port {name} direction PRODUCT="
                        f"{prod_dir.get(name)} HOOKS={hook_dir.get(name)}"
                    ),
                )
            )
        if name in hook_w and prod_w.get(name) != hook_w.get(name):
            findings.append(
                Finding(
                    check="hooks_ports",
                    module=module,
                    file=rel(hooks),
                    rule="HOOKS_PORT_WIDTH",
                    message=(
                        f"port {name} width PRODUCT={prod_w.get(name)} "
                        f"HOOKS={hook_w.get(name)}"
                    ),
                )
            )
    for name in hook_names:
        if is_tb_obs_port(name) and hook_dir.get(name) != "output":
            findings.append(
                Finding(
                    check="hooks_ports",
                    module=module,
                    file=rel(hooks),
                    rule="HOOKS_PORT_DIR",
                    message=(
                        f"{name} is tb_obs_* / tb_<inst>_obs_* and must be "
                        f"a read-only output (HOOKS has {hook_dir.get(name)})"
                    ),
                )
            )
    return findings


def main() -> int:
    print_tool_versions(["python", "yosys"])
    table = load_hooks_ports()
    print(
        f"hooks_ports table: {len(table)} approved module(s): "
        f"{sorted(table) or '[]'}"
    )
    print(
        f"discovered layers: pycircuit={discover_layers(REPO_ROOT / 'pycircuit') or []} "
        f"rtl={discover_layers(REPO_ROOT / 'rtl') or []}"
    )
    findings: list[Finding] = []
    for leaf in discover_leaf_pairs():
        product = REPO_ROOT / leaf["product"]
        hooks = REPO_ROOT / leaf["hooks"]
        module = leaf["module"]
        if leaf.get("placeholder"):
            print(f"hooks-ports skip {module}: _placeholder (lint/TB only)")
            continue
        if not product.is_file():
            continue
        if is_handwritten_path(product):
            print(f"hooks-ports skip {module}: handwritten whitelist")
            continue
        if is_legacy_path(product):
            continue
        if not hooks.is_file():
            findings.append(
                Finding(
                    check="hooks_ports",
                    module=module,
                    file=leaf["product"],
                    rule="HOOKS_MISSING",
                    message=f"non-legacy leaf missing hooks netlist {leaf['hooks']}",
                )
            )
            continue
        extra = hooks_extra_for(module, leaf.get("leaf"))
        findings.extend(compare_ports(module, product, hooks, extra))
    return emit_report("hooks_ports", findings)


if __name__ == "__main__":
    raise SystemExit(main())
