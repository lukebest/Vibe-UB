"""ub_pcs_scrambler — additive PCS scrambler (SPEC §2.4; UB-PHY §3.2.2.4).

Per-lane LFSR, valid-only, sync ``rst_pyc``. Default polynomial / seed
are parameters (not closed in-repo SPEC text); defaults match
Vibe-UB-Switch ``vibe_pcs_scramble`` (D9): PRBS23 ``x^23+x^18+1``,
seed ``{{prefix=1, lane_id, 2'b01}}``, LSB-first window.

``en=0`` passes data and does not step the LFSR (AMCTL/EEIB later).
``seed_load`` reloads the lane seed. If ``seed_load`` and ``valid_in && en``
are both 1, the advance from the *current* LFSR wins (Switch NBA last-wins).

Precoding is PMA, ``PRECODE_EN=0`` (SPEC §9) — this leaf does not precode.
No TEST_HOOKS (SPEC §10 / CODING_STYLE §4).
"""

from __future__ import annotations

from lib import params as P

MODULE = "ub_pcs_scrambler"


def emit_verilog(
    *,
    data_w: int = P.DATA_W_SCR,
    scr_w: int = P.SCR_W,
    scr_tap: int = P.SCR_TAP,
    lane_id_w: int = P.LANE_ID_W,
) -> str:
    return _emit_scramble_module(
        MODULE, data_w=data_w, scr_w=scr_w, scr_tap=scr_tap, lane_id_w=lane_id_w
    )


def _emit_scramble_module(
    name: str,
    *,
    data_w: int,
    scr_w: int,
    scr_tap: int,
    lane_id_w: int,
) -> str:
    seed_prefix_w = scr_w - lane_id_w - 2
    if seed_prefix_w < 1:
        raise ValueError("SCR_W must be > LANE_ID_W + 2")
    return f"""// GENERATED from pycircuit/pcs/{name}.py — do not edit.
// Reproduce: make emit
// SPEC §2.4 / UB-PHY §3.2.2.4. TEST_HOOKS=0 (no §10 hooks on this leaf).
// Registers are pyc_reg semantics: posedge core_clk, sync active-high rst_pyc.
// Polynomial / seed are parameters (Open questions for Xia). PRECODE_EN=0.

module {name} #(
  parameter integer DATA_W     = {data_w},
  parameter integer SCR_W      = {scr_w},
  parameter integer SCR_TAP    = {scr_tap},
  parameter integer LANE_ID_W  = {lane_id_w}
) (
  input  wire                 core_clk,
  input  wire                 rst_pyc,
  input  wire [LANE_ID_W-1:0] lane_id,
  input  wire                 seed_load,
  input  wire                 en,
  input  wire                 valid_in,
  input  wire [DATA_W-1:0]    data_in,
  output wire                 valid_out,
  output wire [DATA_W-1:0]    data_out
);

  localparam integer SEED_PREFIX_W = SCR_W - LANE_ID_W - 2;

  reg  [SCR_W-1:0]  lfsr_q;
  reg               valid_q;
  reg  [DATA_W-1:0] data_q;

  wire [SCR_W-1:0] seed;
  wire [SCR_W-1:0] rst_seed;
  assign seed     = {{ {{SEED_PREFIX_W-1{{1'b0}}}}, 1'b1, lane_id, 2'b01 }};
  assign rst_seed = {{ {{SCR_W-2{{1'b0}}}}, 2'b01 }};

  reg  [DATA_W-1:0] xmask;
  reg  [SCR_W-1:0]  t_mask;
  reg  [SCR_W-1:0]  t_adv;
  integer           i;

  function automatic [SCR_W-1:0] lfsr_step;
    input [SCR_W-1:0] s;
    begin
      lfsr_step = {{s[SCR_W-2:0], s[SCR_W-1] ^ s[SCR_TAP]}};
    end
  endfunction

  always @* begin
    xmask  = {{DATA_W{{1'b0}}}};
    t_mask = lfsr_q;
    for (i = 0; i < DATA_W; i = i + 1) begin
      xmask[i] = t_mask[0];
      t_mask   = lfsr_step(t_mask);
    end
    t_adv = lfsr_q;
    for (i = 0; i < DATA_W; i = i + 1) begin
      t_adv = lfsr_step(t_adv);
    end
  end

  wire        lfsr_en = seed_load | (valid_in & en);
  wire [SCR_W-1:0] lfsr_d = (valid_in & en) ? t_adv : seed;

  // pyc_reg #(.WIDTH(SCR_W)) expansion
  always @(posedge core_clk) begin
    if (rst_pyc)
      lfsr_q <= rst_seed;
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
