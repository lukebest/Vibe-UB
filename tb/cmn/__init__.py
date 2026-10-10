"""Unit TB for ``ub_cmn_mem_1r1w`` (CODING_STYLE §10 / PR #20).

Scoreboard reference is ``model.ub_cmn_mem_1r1w``. Product leaf lives in
``rtl/cmn/`` (design-B). This package must import without cocotb / uvm so
the Python self-check stays green when the simulator stack is absent.
"""
