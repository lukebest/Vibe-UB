// Leaves in this batch have no SPEC §10 hooks. HOOKS=1 wrapper keeps
// obs at 0 and does not mux inj into the DUT (SPEC §10 / §11).
`ifdef TB_TEST_HOOKS
  assign tb_obs_link_ready    = 1'b0;
  assign tb_obs_link_up       = 1'b0;
  assign tb_obs_lmsm_st       = 5'd0;
  assign tb_obs_crd_cells     = 16'd0;
  assign tb_obs_crd_pend      = 16'd0;
  assign tb_obs_crd_low       = 1'b0;
  assign tb_obs_crd_bp        = 1'b0;
  assign tb_obs_crd_to        = 11'd0;
  assign tb_obs_dll_sm_st     = 2'd0;
  assign tb_obs_consume_flits = 10'd0;
`endif
