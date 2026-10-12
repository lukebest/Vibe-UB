# contract_sha256: 646c76d8c254cedafe0b1dbb2a9e826205e4e84d7692cdd62b0f3bc8f314eb1d
# generated-by: scripts/gate/gen_private_stub.py
"""Public port-only stub for ub_pcs_amctl_cw_dec. Bit layout is private (S-01(b))."""

from __future__ import annotations

from pycircuit import Circuit, module, u


@module(name="ub_pcs_amctl_cw_dec")
def build(m: Circuit) -> None:
    clk = m.clock('core_clk')
    rst = m.reset('rst_pyc')
    _ = (clk, rst)
    m.input('word', width=32)
    m.input('word_vld', width=1)
    m.output('end_hit', u(1, 0))
    m.output('amctl_vld', u(1, 0))
    m.output('end_ok', u(1, 0))
    m.output('lid', u(4, 0))
    m.output('lid_ok', u(1, 0))
    m.output('ctrl_type', u(3, 0))
    m.output('ctrl_type_ok', u(1, 0))
    m.output('ctrl_detail', u(4, 0))
    m.output('ctrl_detail_ok', u(1, 0))

build.__pycircuit_name__ = 'ub_pcs_amctl_cw_dec'
