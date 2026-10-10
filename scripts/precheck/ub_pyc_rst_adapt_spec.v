// SPEC §4.2 local pre-check (not pycc; non-gating). pyc_reg native rst is sync active-high,
// so rst_pyc = ~rst_n_sync. Combo, 0-cycle.
module ub_pyc_rst_adapt_spec (
  input  rst_n_sync,
  output rst_pyc
);
  assign rst_pyc = ~rst_n_sync;
endmodule
