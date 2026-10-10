"""ub_pcs_scrambler — per-lane additive PRBS23 (SPEC §2.4; UB-PHY §3.2.2.4 / §3.2.6).

Closed by SPEC:
  - one instance per physical lane; DATA_W = PMA_W = 32 (§2.4, §9)
  - 23-bit state SCR_W (§2.4, §9)
  - seed source is AMCTL.LID (port ``amctl_lid[3:0]``), not physical
    lane index and not LTB.Lane_ID (§2.4)
  - LID encoding: 0–7 = Lane0–Lane7, 8 = NULL, 9–15 reserved (§2.4, §3.2.4.2)
  - each scrambled symbol LSB first; data[0] is the first bit of the beat (§2.4, §3.3)
  - en=0: bypass, LFSR does not step (AMCTL / EEIB)
  - seed_load: load SEED_MAP[amctl_lid]. This **is** the SPEC §2.4 /
    §3.2.2.4 / §3.4.3.6 / §3.4.3.7 reseed. Parent must drive it as:
      seed_load = amctl_edf & ~lmsm_in_Send_NullBlock_or_Link_Active
    SDF while LMSM is in those two states must keep seed_load=0 (do not
    reseed). Same-cycle seed_load wins over LFSR advance (AMCTL beat has
    en=0). Leaf does not invent EDF/SDF ports — SPEC §2.4 leaf table.
  - 1-cycle latency (§5)
  - sync rst_pyc; SPEC §10 lists no hook ports (HOOKS netlist identical)

OPEN per SPEC §13.2 (no product default, not authoritative):
  - PRBS23 tap mask ``SCR_TAPS`` (bit k = include s[k] in Fibonacci XOR;
    degree d ↔ bit d-1, matching the TB model convention)
  - AMCTL.LID → 23-bit seed map ``SEED_MAP`` (slots 0..8)
  - power-on LFSR init before first seed_load ``LFSR_INIT``

Parent / selfcheck / lint **must** pass those three. Emit does not bake
Switch or any guessed g(x).
"""

from __future__ import annotations

from lib import params as P

MODULE = "ub_pcs_scrambler"


def emit_verilog(
    test_hooks: bool = False,
    *,
    data_w: int = P.DATA_W_SCR,
    scr_w: int = P.SCR_W,
    amctl_lid_w: int = P.AMCTL_LID_W,
    seed_slots: int = P.SEED_MAP_SLOTS,
) -> str:
    return _emit_scramble_module(
        MODULE,
        test_hooks=test_hooks,
        data_w=data_w,
        scr_w=scr_w,
        amctl_lid_w=amctl_lid_w,
        seed_slots=seed_slots,
    )


def _emit_scramble_module(
    name: str,
    *,
    test_hooks: bool = False,
    data_w: int,
    scr_w: int,
    amctl_lid_w: int,
    seed_slots: int,
) -> str:
    seed_map_w = scr_w * seed_slots
    th = 1 if test_hooks else 0
    return f"""// GENERATED from pycircuit/pcs/{name}.py — do not edit.
// Reproduce: make emit
// SPEC §2.4 / UB-PHY §3.2.2.4 / §3.2.6 / §3.3 / §3.4.3.6 / §3.4.3.7.
// TEST_HOOKS={th} (SPEC §10 lists no hook ports on this leaf).
// pyc_reg: posedge core_clk, sync active-high rst_pyc.
// PRECODE_EN=0 (PMA; SPEC §9) — this leaf does not precode.
//
// Fibonacci LFSR: output = MSB; feedback = XOR of s[k]&SCR_TAPS[k];
// next = {{s[SCR_W-2:0], fb}}. data[0] gets the first output bit (LSB-first).
//
// SPEC §2.4 reseed (TX/RX same). Leaf pin is seed_load; parent decodes:
//   seed_load = amctl_edf & ~lmsm_in_Send_NullBlock_or_Link_Active;
//   SDF while in those two LMSM states → seed_load must stay 0.
//
// OPEN per SPEC §13, not authoritative — parent / selfcheck MUST pass:
//   SCR_TAPS, SEED_MAP, LFSR_INIT
// No product default (no Switch g(x), no invented LID map).

module {name} #(
  parameter integer DATA_W        = {data_w},
  parameter integer SCR_W         = {scr_w},
  parameter integer AMCTL_LID_W   = {amctl_lid_w},
  parameter integer SEED_MAP_SLOTS = {seed_slots},
  parameter integer SEED_MAP_W    = SCR_W * SEED_MAP_SLOTS,
  // OPEN per SPEC §13, not authoritative. Parent / selfcheck must override.
  parameter [SCR_W-1:0]      SCR_TAPS  = {{SCR_W{{1'b0}}}},
  parameter [SCR_W-1:0]      LFSR_INIT = {{SCR_W{{1'b0}}}},
  parameter [SEED_MAP_W-1:0] SEED_MAP  = {{SEED_MAP_W{{1'b0}}}}
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
      lfsr_step = {{s[SCR_W-2:0], fb}};
    end
  endfunction

  function automatic [SCR_W-1:0] seed_from_lid;
    input [AMCTL_LID_W-1:0] lid;
    begin
      if (lid <= 4'd8)
        seed_from_lid = SEED_MAP[lid*SCR_W +: SCR_W];
      else
        seed_from_lid = {{SCR_W{{1'b0}}}};
    end
  endfunction

  always @* begin
    xmask  = {{DATA_W{{1'b0}}}};
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
      data_q <= {{DATA_W{{1'b0}}}};
    else if (valid_in)
      data_q <= en ? (data_in ^ xmask) : data_in;
  end

  assign valid_out = valid_q;
  assign data_out  = data_q;

endmodule
"""
