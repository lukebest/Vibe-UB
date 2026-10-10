// ub_lmsm_pcs_if_props — property-only LMSM→PCS control (SPEC §3.3.4).
// Bind on LMSM outputs + the PCS latched copies. No RTL datapath.
//
// lmb_start is the PCS "LMB about to start" strobe (not a SPEC top-level pin;
// design and TB bind it to the insertion-boundary pulse).

module ub_lmsm_pcs_if_props (
  input wire       core_clk,
  input wire       rst_n,
  input wire       lmb_start,
  input wire [1:0] lmsm2pcs_pattern,
  input wire [1:0] lmsm2pcs_lane_id_mode,
  input wire       lmsm2pcs_ltb_valid,
  input wire [7:0] lmsm2pcs_ltb_type,
  input wire [1:0] latched_pattern,
  input wire [1:0] latched_lane_id_mode,
  input wire       latched_ltb_valid,
  input wire [7:0] latched_ltb_type
);

  // SPEC §3.3.4: lmsm2pcs_pattern[1:0] encodings 0..3 are all legal
  // (0 idle, 1 EEIB, 2 LTB, 3 DLL). A 2-bit net is always 0..3.
  always @(*) begin
    a_pattern_in_0_3: assert (lmsm2pcs_pattern <= 2'd3);
  end

  reg f_past_ok;
  initial f_past_ok = 1'b0;
  always @(posedge core_clk)
    f_past_ok <= 1'b1;

  always @(posedge core_clk) begin
    if (rst_n && f_past_ok) begin
      // SPEC §3.3.4: lane_id_mode 0=PHYS, 1=ASCEND, 2=NULL; 3=RESERVED.
      // LMSM never drives 3 (TB assert).
      a_lane_id_mode_ne3: assert (lmsm2pcs_lane_id_mode != 2'd3);

      c_pattern_idle: cover (lmsm2pcs_pattern == 2'd0);
      c_pattern_eeib: cover (lmsm2pcs_pattern == 2'd1);
      c_pattern_ltb:  cover (lmsm2pcs_pattern == 2'd2);
      c_pattern_dll:  cover (lmsm2pcs_pattern == 2'd3);
      c_mode_phys:    cover (lmsm2pcs_lane_id_mode == 2'd0);
      c_mode_ascend:  cover (lmsm2pcs_lane_id_mode == 2'd1);
      c_mode_null:    cover (lmsm2pcs_lane_id_mode == 2'd2);
      c_lmb_start:         cover (lmb_start);
      c_ltb_valid_pulse:   cover (lmsm2pcs_ltb_valid && !$past(lmsm2pcs_ltb_valid));
      c_change_before_lmb: cover (!lmb_start && (lmsm2pcs_pattern != $past(lmsm2pcs_pattern)));
    end

    // SPEC §3.3.4 / §5: latch at LMB start; hold between starts.
    // One enclosing if per group so Yosys uses the whole guard as enable.
    // start at T ⇒ latched_{T+1} == live_T. Current rst_n must stay 1
    // (a later assert clears the copies).
    if (rst_n && f_past_ok && $past(rst_n && lmb_start)) begin
      a_latch_pattern:   assert (latched_pattern == $past(lmsm2pcs_pattern));
      a_latch_mode:      assert (latched_lane_id_mode == $past(lmsm2pcs_lane_id_mode));
      a_latch_ltb_valid: assert (latched_ltb_valid == $past(lmsm2pcs_ltb_valid));
      a_latch_ltb_type:  assert (latched_ltb_type == $past(lmsm2pcs_ltb_type));
    end
    // No start at T ⇒ latched_{T+1} == latched_T.
    if (rst_n && f_past_ok && $past(rst_n && !lmb_start)) begin
      a_hold_pattern: assert (latched_pattern == $past(latched_pattern));
      a_hold_mode:    assert (latched_lane_id_mode == $past(latched_lane_id_mode));
    end
  end

endmodule
