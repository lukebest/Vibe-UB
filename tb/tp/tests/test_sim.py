"""cocotb + Verilator against PRODUCT and HOOKS ``ub_tp_bypass``.

RTL lives at ``rtl/tp/`` (merged #65). Missing netlist or tools is a
failure, not a skip — the gate treats skip as fail.
"""

from __future__ import annotations

import shutil

import pytest

from tb.cmn.discover import require_pyc_runtime
from tb.tp.ports import HOOKS, PRODUCT

SEED = 1


def _require_sim(netlist: str):
    # Do not import cocotb here: tb-selfcheck skips any test_*.py that
    # mentions `import cocotb`, and skip is a gate fail.
    require_pyc_runtime()
    path = HOOKS if netlist == "hooks" else PRODUCT
    if not path.is_file():
        raise AssertionError(f"missing {path}; merge the #65 DUT before RTL sim")
    if shutil.which("verilator") is None:
        raise AssertionError("Verilator not on PATH; cannot run the scoreboard")
    return path


@pytest.mark.sim
@pytest.mark.parametrize("netlist", ["product", "hooks"])
def test_rtl_scoreboard_all(netlist):
    _require_sim(netlist)
    from tb.tp.sim_runner import run_sim

    print(f"SEED {SEED}", flush=True)
    run_sim(netlist, case="all", seed=SEED)
