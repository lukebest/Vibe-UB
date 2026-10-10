"""Scoreboard base: subscribe monitors, compare against a Python golden (D8)."""

from __future__ import annotations

from uvm import UVMComponent, UVM_LOW, uvm_component_utils, uvm_error, uvm_info


def scoreboard_tally(n_compare: int, n_expect: int, n_mismatch: int) -> str | None:
    """Return an error string if the compare tally is not acceptable."""
    if n_compare <= 0:
        return "scoreboard compare count is 0"
    if n_compare != n_expect:
        return f"compares={n_compare} expected={n_expect}"
    if n_mismatch:
        return f"{n_mismatch} scoreboard mismatches"
    return None


class ScoreboardBase(UVMComponent):
    """Never force DUT internals (D13). Every DUT check goes through compare()."""

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.n_compare = 0
        self.n_expect = 0
        self.n_mismatch = 0
        self._finalized = False

    def expect(self, n: int = 1) -> None:
        """Declare how many compare() calls are about to be made."""
        if n < 1:
            raise ValueError("expect n >= 1")
        self.n_expect += n

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

    def check(self, expected, actual, ctx: str = "") -> bool:
        """One planned compare: expect(1) then compare()."""
        self.expect(1)
        return self.compare(expected, actual, ctx)

    def finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True
        msg = (
            f"compares={self.n_compare} expected={self.n_expect} "
            f"mismatches={self.n_mismatch}"
        )
        uvm_info(self.get_type_name(), msg, UVM_LOW)
        print(f"SCOREBOARD {msg}", flush=True)
        err = scoreboard_tally(self.n_compare, self.n_expect, self.n_mismatch)
        if err:
            uvm_error(self.get_type_name(), err)
            raise AssertionError(err)

    def check_phase(self, phase):
        super().check_phase(phase)
        try:
            self.finalize()
        except AssertionError:
            pass


uvm_component_utils(ScoreboardBase)
