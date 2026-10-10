"""ub_pyc_rst_adapt — rst_n_sync to rst_pyc (SPEC §4.2).

Real pyCircuit API. Combo invert when PYC_RST_ACTIVE_HIGH != 0.
SPEC §10 lists no hooks: HOOKS ports match PRODUCT.
Single-config leaf: untagged name ub_pyc_rst_adapt.
"""

from __future__ import annotations

from pycircuit import Circuit, module

LEAF = "ub_pyc_rst_adapt"
VARIANTS: dict[str, dict] = {
    "": {"pyc_rst_active_high": 1},
}


def _adapt(m: Circuit, rst_n_sync, *, pyc_rst_active_high: int):
    if int(pyc_rst_active_high) != 0:
        return ~rst_n_sync
    return rst_n_sync


@module(name="ub_pyc_rst_adapt")
def build(
    m: Circuit,
    pyc_rst_active_high: int = 1,
    test_hooks: int = 0,
) -> None:
    _ = int(test_hooks)
    rst_n_sync = m.input("rst_n_sync", width=1)
    m.output(
        "rst_pyc",
        _adapt(m, rst_n_sync, pyc_rst_active_high=int(pyc_rst_active_high)),
    )


build.__pycircuit_name__ = "ub_pyc_rst_adapt"
