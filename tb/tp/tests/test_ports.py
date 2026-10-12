"""Port-only self-check for ub_tp_bypass (no cocotb, no model/)."""

from __future__ import annotations

from tb.tp.ports import HOOKS, PRODUCT, check_ports


def _parse_names(path):
    from tb.cmn.ports import parse_module_ports as _p

    return _p(path.read_text(encoding="utf-8"), "ub_tp_bypass")


def test_product_ports():
    assert PRODUCT.is_file(), f"missing {PRODUCT}"
    check_ports(PRODUCT.read_text(encoding="utf-8"))


def test_hooks_ports_match_product():
    assert HOOKS.is_file(), f"missing {HOOKS}"
    check_ports(HOOKS.read_text(encoding="utf-8"))
    assert _parse_names(PRODUCT) == _parse_names(HOOKS)


def test_no_unknown_width_ports():
    from tb.tp.ports import UNKNOWN_OMITTED

    names = set(_parse_names(PRODUCT))
    for port in UNKNOWN_OMITTED:
        assert port not in names
