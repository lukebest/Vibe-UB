`ifdef TB_TEST_HOOKS
  ,
  input  wire        tb_test_mode,
  input  wire [3:0]  tb_inj_am_lock,
  input  wire        tb_inj_lid_bad,
  input  wire [15:0] tb_inj_crd_cells,
  output wire        tb_obs_link_ready,
  output wire        tb_obs_link_up,
  output wire [4:0]  tb_obs_lmsm_st,
  output wire [15:0] tb_obs_crd_cells,
  output wire [15:0] tb_obs_crd_pend,
  output wire        tb_obs_crd_low,
  output wire        tb_obs_crd_bp,
  output wire [10:0] tb_obs_crd_to,
  output wire [1:0]  tb_obs_dll_sm_st,
  output wire [9:0]  tb_obs_consume_flits
`endif
