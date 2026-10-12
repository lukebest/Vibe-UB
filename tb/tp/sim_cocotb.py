"""cocotb port + 1-flit handshake check for ub_tp_bypass. No model/tp/."""

from __future__ import annotations

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

from tb.tp.ports import CLK_PORT, PORTS, RST_PORT


def _require_ports(dut) -> None:
    missing = [n for n in PORTS if not hasattr(dut, n)]
    extra_tb = [n for n in dir(dut) if n.startswith("tb_")]
    if missing:
        raise AssertionError(f"DUT missing ports {missing}")
    if extra_tb:
        raise AssertionError(f"DUT has tb_* ports {extra_tb}; SPEC §10 lists none")


async def _reset(dut) -> None:
    getattr(dut, RST_PORT).value = 1
    dut.nw_link_up.value = 1
    dut.nw2tp_flush.value = 0
    dut.tp2nw_ready.value = 1
    dut.tp2ta_ready.value = 1
    dut.ta2tp_valid.value = 0
    dut.ta2tp_op_valid.value = 0
    dut.nw2tp_valid.value = 0
    dut.ta2tp_data.value = 0
    dut.ta2tp_sop.value = 0
    dut.ta2tp_eop.value = 0
    dut.ta2tp_bypass.value = 1
    dut.ta2tp_dcna.value = 0
    dut.nw2tp_data.value = 0
    dut.nw2tp_sop.value = 0
    dut.nw2tp_eop.value = 0
    dut.nw2tp_err.value = 0
    for _ in range(3):
        await RisingEdge(getattr(dut, CLK_PORT))
    getattr(dut, RST_PORT).value = 0
    await RisingEdge(getattr(dut, CLK_PORT))


@cocotb.test()
async def test_ports_and_one_flit(dut):
    seed = int(os.environ.get("TP_SEED", "1"), 0)
    print(f"SEED {seed}", flush=True)
    _require_ports(dut)
    clock = Clock(getattr(dut, CLK_PORT), 2, units="ns")
    cocotb.start_soon(clock.start())
    await _reset(dut)

    assert int(dut.tp2nw_valid.value) == 0
    assert int(dut.tp2ta_valid.value) == 0

    dut.ta2tp_op_valid.value = 1
    dut.ta2tp_bypass.value = 1
    dut.ta2tp_dcna.value = 0x1234
    dut.ta2tp_valid.value = 1
    dut.ta2tp_sop.value = 1
    dut.ta2tp_eop.value = 1
    dut.ta2tp_data.value = 0xA5A5
    await RisingEdge(getattr(dut, CLK_PORT))
    # Same-cycle op+data accepted; registered output next beat.
    dut.ta2tp_op_valid.value = 0
    dut.ta2tp_valid.value = 0
    await RisingEdge(getattr(dut, CLK_PORT))
    timeout = 8
    while int(dut.tp2nw_valid.value) != 1 and timeout:
        await RisingEdge(getattr(dut, CLK_PORT))
        timeout -= 1
    assert timeout, "TX flit never presented"
    assert int(dut.tp2nw_data.value) == 0xA5A5
    assert int(dut.tp2nw_sop.value) == 1
    assert int(dut.tp2nw_eop.value) == 1
    assert int(dut.tp2nw_bypass.value) == 1
    assert int(dut.tp2nw_dcna.value) == 0x1234
    assert int(dut.tp2nw_sl.value) == 0
    assert int(dut.tp2nw_cci.value) == 0

    dut.nw2tp_valid.value = 1
    dut.nw2tp_sop.value = 1
    dut.nw2tp_eop.value = 1
    dut.nw2tp_err.value = 1
    dut.nw2tp_data.value = 0x5A5A
    await RisingEdge(getattr(dut, CLK_PORT))
    dut.nw2tp_valid.value = 0
    await RisingEdge(getattr(dut, CLK_PORT))
    timeout = 8
    while int(dut.tp2ta_valid.value) != 1 and timeout:
        await RisingEdge(getattr(dut, CLK_PORT))
        timeout -= 1
    assert timeout, "RX flit never presented"
    assert int(dut.tp2ta_data.value) == 0x5A5A
    assert int(dut.tp2ta_err.value) == 1
    print("PASS ub_tp_bypass ports + 1-flit", flush=True)
