// ub_cmn_mem_1r1w_if_props — property/bind module (CODING_STYLE §10 / PR #20).
// Written-bit tracking lives HERE only (anyconst address, per segment).
// Never in product RTL. Bind on the leaf ports (core_clk; no reset —
// business name is rst_pyc). Yosys-compatible: clocked assert/cover.
//
// WMASK_W default WIDTH (whole-word). NSEG = WIDTH/WMASK_W. Architectural
// wmask[NSEG-1:0] exists only when NSEG>1; the bind pin is always present
// and is tied 1 when NSEG=1.

module ub_cmn_mem_1r1w_if_props #(
  parameter DEPTH = 5,
  parameter WIDTH = 8,
  parameter AW    = 3,
  parameter WMASK_W = WIDTH,
  parameter ASSERT_NO_UNINIT_READ = 1
) (
  input  wire             core_clk,
  input  wire             we,
  input  wire [AW-1:0]    waddr,
  input  wire [WIDTH-1:0] wdata,
  input  wire [WIDTH/WMASK_W-1:0] wmask,
  input  wire             re,
  input  wire [AW-1:0]    raddr,
  input  wire [WIDTH-1:0] rdata,
  // Formal helpers for the standalone harness (leave unconnected on bind).
  output wire [AW-1:0]    f_addr,
  output wire [WIDTH/WMASK_W-1:0] f_written
);

  localparam NSEG = WIDTH / WMASK_W;

  // One free address for the whole proof (converges at large DEPTH).
  (* anyconst *) wire [AW-1:0] f_watch;
  assign f_addr = f_watch;

  // NSEG=1: no architectural wmask; treat as all-1s.
  wire [NSEG-1:0] wmask_eff = (NSEG == 1) ? {NSEG{1'b1}} : wmask;

  always @(*) begin
    // Watch a legal entry. Non-pow2 DEPTH: extra AW encodings exist.
    a_f_addr_legal: assume (f_watch < DEPTH);

    // CODING_STYLE §10: RTL does not truncate; flag OOR.
    if (we)
      a_waddr_in_range: assert (waddr < DEPTH);
    if (re)
      a_raddr_in_range: assert (raddr < DEPTH);
  end

  reg [NSEG-1:0]  f_wr;
  reg [WIDTH-1:0] f_data;
  integer wi;
  initial f_wr = {NSEG{1'b0}};
  assign f_written = f_wr;

  always @(posedge core_clk) begin
    if (we && (waddr == f_watch) && (waddr < DEPTH)) begin
      for (wi = 0; wi < NSEG; wi = wi + 1) begin
        if (wmask_eff[wi]) begin
          f_wr[wi] <= 1'b1;
          f_data[wi*WMASK_W +: WMASK_W] <= wdata[wi*WMASK_W +: WMASK_W];
        end
      end
    end
  end

  reg f_past_ok;
  initial f_past_ok = 1'b0;
  always @(posedge core_clk)
    f_past_ok <= 1'b1;

  wire hit_r = re && (raddr == f_watch) && (raddr < DEPTH);
  wire hit_w = we && (waddr == f_watch) && (waddr < DEPTH);

  always @(posedge core_clk) begin
    // Default 1. A read where ANY segment is unwritten is a violation.
    // valid_outside instances elaborate 0; verification checks the
    // external valid bit instead.
    if (ASSERT_NO_UNINIT_READ && hit_r && (f_wr != {NSEG{1'b1}}))
      a_no_uninit_read: assert (1'b0);

    // Whole-word read-old when every segment is written (NSEG=1 path).
    if (f_past_ok && $past(hit_r && (f_wr == {NSEG{1'b1}})))
      a_rdata_read_old: assert (rdata == $past(f_data));

    // rdata holds when there is no read (registered output).
    if (f_past_ok && $past(!re))
      a_rdata_hold: assert (rdata == $past(rdata));

    c_write_watch:       cover (hit_w);
    c_read_watch:        cover (hit_r && (f_wr == {NSEG{1'b1}}));
    c_read_old_conflict: cover (hit_r && hit_w && (f_wr == {NSEG{1'b1}}));
    c_we_only:           cover (we && !re);
    c_re_only:           cover (re && !we && (f_wr == {NSEG{1'b1}}));
  end

  // Per-segment props. Yosys 0.33 does not uniquify assertion names
  // inside a for-generate, so each index is its own generate-if with
  // a unique label. Unrolled through 3 covers the d64w64m16 NSEG=4 job
  // (plus NSEG=1 whole-word).
  generate
    if (NSEG > 0) begin : g_seg0
      always @(posedge core_clk) begin
        if (f_past_ok && $past(hit_w && wmask_eff[0]))
          a_seg_masked_written_0: assert (f_wr[0]);
        if (f_past_ok && $past(hit_w && !wmask_eff[0])) begin
          a_seg_unmasked_wr_hold_0: assert (f_wr[0] == $past(f_wr[0]));
          a_seg_unmasked_data_hold_0: assert (
            f_data[0*WMASK_W +: WMASK_W] == $past(f_data[0*WMASK_W +: WMASK_W])
          );
        end
        if (f_past_ok && $past(hit_r && f_wr[0]))
          a_rdata_read_old_seg_0: assert (
            rdata[0*WMASK_W +: WMASK_W] == $past(f_data[0*WMASK_W +: WMASK_W])
          );
        if (ASSERT_NO_UNINIT_READ && hit_r && !f_wr[0])
          a_no_uninit_seg_0: assert (1'b0);
      end
    end
    if (NSEG > 1) begin : g_seg1
      always @(posedge core_clk) begin
        if (f_past_ok && $past(hit_w && wmask_eff[1]))
          a_seg_masked_written_1: assert (f_wr[1]);
        if (f_past_ok && $past(hit_w && !wmask_eff[1])) begin
          a_seg_unmasked_wr_hold_1: assert (f_wr[1] == $past(f_wr[1]));
          a_seg_unmasked_data_hold_1: assert (
            f_data[1*WMASK_W +: WMASK_W] == $past(f_data[1*WMASK_W +: WMASK_W])
          );
        end
        if (f_past_ok && $past(hit_r && f_wr[1]))
          a_rdata_read_old_seg_1: assert (
            rdata[1*WMASK_W +: WMASK_W] == $past(f_data[1*WMASK_W +: WMASK_W])
          );
        if (ASSERT_NO_UNINIT_READ && hit_r && !f_wr[1])
          a_no_uninit_seg_1: assert (1'b0);
      end
    end
    if (NSEG > 2) begin : g_seg2
      always @(posedge core_clk) begin
        if (f_past_ok && $past(hit_w && wmask_eff[2]))
          a_seg_masked_written_2: assert (f_wr[2]);
        if (f_past_ok && $past(hit_w && !wmask_eff[2])) begin
          a_seg_unmasked_wr_hold_2: assert (f_wr[2] == $past(f_wr[2]));
          a_seg_unmasked_data_hold_2: assert (
            f_data[2*WMASK_W +: WMASK_W] == $past(f_data[2*WMASK_W +: WMASK_W])
          );
        end
        if (f_past_ok && $past(hit_r && f_wr[2]))
          a_rdata_read_old_seg_2: assert (
            rdata[2*WMASK_W +: WMASK_W] == $past(f_data[2*WMASK_W +: WMASK_W])
          );
        if (ASSERT_NO_UNINIT_READ && hit_r && !f_wr[2])
          a_no_uninit_seg_2: assert (1'b0);
      end
    end
    if (NSEG > 3) begin : g_seg3
      always @(posedge core_clk) begin
        if (f_past_ok && $past(hit_w && wmask_eff[3]))
          a_seg_masked_written_3: assert (f_wr[3]);
        if (f_past_ok && $past(hit_w && !wmask_eff[3])) begin
          a_seg_unmasked_wr_hold_3: assert (f_wr[3] == $past(f_wr[3]));
          a_seg_unmasked_data_hold_3: assert (
            f_data[3*WMASK_W +: WMASK_W] == $past(f_data[3*WMASK_W +: WMASK_W])
          );
        end
        if (f_past_ok && $past(hit_r && f_wr[3]))
          a_rdata_read_old_seg_3: assert (
            rdata[3*WMASK_W +: WMASK_W] == $past(f_data[3*WMASK_W +: WMASK_W])
          );
        if (ASSERT_NO_UNINIT_READ && hit_r && !f_wr[3])
          a_no_uninit_seg_3: assert (1'b0);
      end
    end
  endgenerate

  generate
    if (NSEG > 1) begin : g_wmask_cover
      always @(posedge core_clk) begin
        c_wmask_single:   cover (hit_w && (wmask_eff == {{NSEG-1{1'b0}}, 1'b1}));
        c_wmask_adjacent: cover (hit_w && (wmask_eff == {{NSEG-2{1'b0}}, 2'b11}));
        c_wmask_all:      cover (hit_w && (wmask_eff == {NSEG{1'b1}}));
      end
    end
  endgenerate

endmodule
