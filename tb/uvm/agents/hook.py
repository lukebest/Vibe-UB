"""Hook agent: only SPEC §10 tb_inj_* / tb_obs_*, gated by tb_test_mode (D13)."""

from __future__ import annotations

from dataclasses import dataclass

from cocotb.triggers import RisingEdge
from uvm.base.uvm_component import UVMComponent
from uvm.macros import uvm_component_utils

# SPEC §10.2 — exhaustive list. Do not add ports here.
INJ_PORTS = ("tb_inj_am_lock", "tb_inj_lid_bad", "tb_inj_crd_cells")
OBS_PORTS = (
    "tb_obs_link_ready",
    "tb_obs_link_up",
    "tb_obs_lmsm_st",
    "tb_obs_crd_cells",
    "tb_obs_crd_pend",
    "tb_obs_crd_low",
    "tb_obs_crd_bp",
    "tb_obs_crd_to",
    "tb_obs_dll_sm_st",
    "tb_obs_consume_flits",
)
GATE_PORT = "tb_test_mode"


@dataclass
class HookBundle:
    present: bool
    test_mode: int = 0
    inj: dict[str, int] | None = None
    obs: dict[str, int] | None = None


class HookAgent(UVMComponent):
    """Drive/sample the §10 hook bundle. Absent when TEST_HOOKS=0 (no ports)."""

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.dut = None
        self.present = False

    def bind(self, dut) -> None:
        self.dut = dut
        self.present = hasattr(dut, GATE_PORT)
        if self.present:
            for name in INJ_PORTS + OBS_PORTS:
                if not hasattr(dut, name):
                    raise AttributeError(f"TEST_HOOKS=1 netlist missing {name} (SPEC §10.2)")

    async def set_test_mode(self, value: int) -> None:
        if not self.present:
            return
        self.dut.tb_test_mode.value = 1 if value else 0
        await RisingEdge(self.dut.core_clk)

    async def drive_inj(self, **fields: int) -> None:
        if not self.present:
            return
        unknown = set(fields) - set(INJ_PORTS)
        if unknown:
            raise KeyError(f"not a SPEC §10 inj port: {unknown}")
        for name, val in fields.items():
            getattr(self.dut, name).value = val
        await RisingEdge(self.dut.core_clk)

    def sample_obs(self) -> HookBundle:
        if not self.present:
            return HookBundle(present=False)
        obs = {name: int(getattr(self.dut, name).value) for name in OBS_PORTS}
        inj = {name: int(getattr(self.dut, name).value) for name in INJ_PORTS}
        return HookBundle(
            present=True,
            test_mode=int(self.dut.tb_test_mode.value),
            inj=inj,
            obs=obs,
        )

    async def idle_inj(self) -> None:
        """Reset-equivalent: injectors at 0 (SPEC §10.1 复位值 = 不介入)."""
        if not self.present:
            return
        self.dut.tb_test_mode.value = 0
        self.dut.tb_inj_am_lock.value = 0
        self.dut.tb_inj_lid_bad.value = 0
        self.dut.tb_inj_crd_cells.value = 0
        await RisingEdge(self.dut.core_clk)


uvm_component_utils(HookAgent)
