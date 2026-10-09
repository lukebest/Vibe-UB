"""ub_pyc_rst_adapt — rst_n_sync → rst_pyc (SPEC §4.2, CODING_STYLE §2).

Generated logic (not whitelist SV). pyc4.0 ``pyc_reg`` is synchronous
active-high (``if (rst)`` in runtime/verilog/pyc_reg.v), so this leaf
is a single inverter. If a future library pin is already active-low,
this module degenerates to a wire (parameter ``PYC_RST_ACTIVE_HIGH``).

No TEST_HOOKS (SPEC §10 does not list this leaf). Combo, 0-cycle.
"""

from __future__ import annotations

MODULE = "ub_pyc_rst_adapt"


def emit_verilog(*, pyc_rst_active_high: int = 1) -> str:
    return f"""// GENERATED from pycircuit/common/ub_pyc_rst_adapt.py — do not edit.
// Reproduce: make emit
// SPEC §4.2 / CODING_STYLE §2. TEST_HOOKS=0 (no §10 hooks on this leaf).
// pyc_reg native polarity is active-high; invert rst_n_sync → rst_pyc.

module {MODULE} #(
  parameter integer PYC_RST_ACTIVE_HIGH = {int(pyc_rst_active_high)}
) (
  input  wire rst_n_sync,
  output wire rst_pyc
);

  generate
    if (PYC_RST_ACTIVE_HIGH != 0) begin : g_inv
      assign rst_pyc = ~rst_n_sync;
    end else begin : g_wire
      assign rst_pyc = rst_n_sync;
    end
  endgenerate

endmodule
"""


def build_pyc(m) -> None:
    """Optional pyc4.0 frontend body (combo invert)."""
    rst_n_sync = m.input("rst_n_sync", width=1)
    m.output("rst_pyc", ~rst_n_sync)
