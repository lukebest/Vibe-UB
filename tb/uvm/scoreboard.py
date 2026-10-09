"""Scoreboard base: subscribe monitors, compare against a Python golden (D8)."""

from __future__ import annotations

from uvm.base.uvm_component import UVMComponent
from uvm.base.uvm_globals import uvm_error, uvm_info
from uvm.base.uvm_object_globals import UVM_LOW
from uvm.macros import uvm_component_utils


class ScoreboardBase(UVMComponent):
    """Subclass and implement compare(). Never force DUT internals (D13)."""

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.n_compare = 0
        self.n_mismatch = 0

    def compare(self, expected, actual, ctx: str = "") -> bool:
        self.n_compare += 1
        if expected == actual:
            return True
        self.n_mismatch += 1
        uvm_error(
            self.get_type_name(),
            f"mismatch {ctx}: expected={expected!r} actual={actual!r}",
        )
        return False

    def check_phase(self, phase):
        super().check_phase(phase)
        uvm_info(
            self.get_type_name(),
            f"compares={self.n_compare} mismatches={self.n_mismatch}",
            UVM_LOW,
        )
        if self.n_mismatch:
            uvm_error(self.get_type_name(), f"{self.n_mismatch} scoreboard mismatches")


uvm_component_utils(ScoreboardBase)
