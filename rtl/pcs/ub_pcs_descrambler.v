// GENERATED from pycircuit/pcs/ub_pcs_descrambler.py — do not edit.
// Reproduce: make emit
// SPEC §2.4 / UB-PHY §3.2.2.4 / §3.2.6 / §3.3 / §3.4.3.6 / §3.4.3.7.
// TEST_HOOKS=0. pyc_reg: posedge core_clk, sync active-high rst_pyc.
// PRECODE_EN=0 (PMA; SPEC §9) — this leaf does not precode.
//
// Fibonacci LFSR: output = MSB; feedback = XOR of s[k]&SCR_TAPS[k];
// next = {s[SCR_W-2:0], fb}. data[0] gets the first output bit (LSB-first).
//
// SPEC §2.4 reseed (TX/RX same). Leaf pin is seed_load; parent decodes:
//   seed_load = amctl_edf & ~lmsm_in_Send_NullBlock_or_Link_Active;
//   SDF while in those two LMSM states → seed_load must stay 0.
//
// OPEN per SPEC §13, not authoritative — parent / selfcheck MUST pass:
//   SCR_TAPS, SEED_MAP, LFSR_INIT
// No product default (no Switch g(x), no invented LID map).

module ub_pcs_descrambler #(
  parameter integer DATA_W        = 32,
  parameter integer SCR_W         = 23,
  parameter integer AMCTL_LID_W   = 4,
  parameter integer SEED_MAP_SLOTS = 9,
  parameter integer SEED_MAP_W    = SCR_W * SEED_MAP_SLOTS,
  // OPEN per SPEC §13, not authoritative. Parent / selfcheck must override.
  parameter [SCR_W-1:0]      SCR_TAPS  = {SCR_W{1'b0}},
  parameter [SCR_W-1:0]      LFSR_INIT = {SCR_W{1'b0}},
  parameter [SEED_MAP_W-1:0] SEED_MAP  = {SEED_MAP_W{1'b0}}
) (
  input  wire                   core_clk,
  input  wire                   rst_pyc,
  input  wire [AMCTL_LID_W-1:0] amctl_lid,
  input  wire                   seed_load,
  input  wire                   en,
  input  wire                   valid_in,
  input  wire [DATA_W-1:0]      data_in,
  output wire                   valid_out,
  output wire [DATA_W-1:0]      data_out
);

  reg  [SCR_W-1:0]  lfsr_q;
  reg               valid_q;
  reg  [DATA_W-1:0] data_q;

  reg  [DATA_W-1:0] xmask;
  reg  [SCR_W-1:0]  t_mask;
  reg  [SCR_W-1:0]  t_adv;
  integer           i;

  function automatic [SCR_W-1:0] lfsr_step;
    input [SCR_W-1:0] s;
    reg               fb;
    integer           tk;
    begin
      fb = 1'b0;
      for (tk = 0; tk < SCR_W; tk = tk + 1)
        fb = fb ^ (s[tk] & SCR_TAPS[tk]);
      lfsr_step = {s[SCR_W-2:0], fb};
    end
  endfunction

  function automatic [SCR_W-1:0] seed_from_lid;
    input [AMCTL_LID_W-1:0] lid;
    begin
      if (lid <= 4'd8)
        seed_from_lid = SEED_MAP[lid*SCR_W +: SCR_W];
      else
        seed_from_lid = {SCR_W{1'b0}};
    end
  endfunction

  always @* begin
    xmask  = {DATA_W{1'b0}};
    t_mask = lfsr_q;
    for (i = 0; i < DATA_W; i = i + 1) begin
      xmask[i] = t_mask[SCR_W-1];
      t_mask   = lfsr_step(t_mask);
    end
    t_adv = lfsr_q;
    for (i = 0; i < DATA_W; i = i + 1)
      t_adv = lfsr_step(t_adv);
  end

  wire [SCR_W-1:0] seed_now = seed_from_lid(amctl_lid);
  // SPEC §2.4 EDF reseed (seed_load) wins over a same-cycle step.
  wire             lfsr_en  = seed_load | (valid_in & en);
  wire [SCR_W-1:0] lfsr_d   = seed_load ? seed_now : t_adv;

  always @(posedge core_clk) begin
    if (rst_pyc)
      lfsr_q <= LFSR_INIT;
    else if (lfsr_en)
      lfsr_q <= lfsr_d;
  end

  always @(posedge core_clk) begin
    if (rst_pyc)
      valid_q <= 1'b0;
    else
      valid_q <= valid_in;
  end

  always @(posedge core_clk) begin
    if (rst_pyc)
      data_q <= {DATA_W{1'b0}};
    else if (valid_in)
      data_q <= en ? (data_in ^ xmask) : data_in;
  end

  assign valid_out = valid_q;
  assign data_out  = data_q;

endmodule
