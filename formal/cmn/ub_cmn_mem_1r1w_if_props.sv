// ub_cmn_mem_1r1w_if_props — property/bind module (CODING_STYLE §10 / PR #20).
// Written-bit tracking lives HERE only (anyconst address). Never in product RTL.
// Bind on the leaf ports (core_clk; no reset — business name is rst_pyc).
// Yosys-compatible: clocked assert/cover.

module ub_cmn_mem_1r1w_if_props #(
  parameter DEPTH = 5,
  parameter WIDTH = 8,
  parameter AW    = 3,
  parameter ASSERT_NO_UNINIT_READ = 1
) (
  input  wire             core_clk,
  input  wire             we,
  input  wire [AW-1:0]    waddr,
  input  wire [WIDTH-1:0] wdata,
  input  wire             re,
  input  wire [AW-1:0]    raddr,
  input  wire [WIDTH-1:0] rdata,
  // Formal helpers for the standalone harness (leave unconnected on bind).
  output wire [AW-1:0]    f_addr,
  output wire             f_written
);

  // One free address for the whole proof (converges at large DEPTH).
  (* anyconst *) wire [AW-1:0] f_watch;
  assign f_addr = f_watch;

  always @(*) begin
    // Watch a legal entry. Non-pow2 DEPTH: extra AW encodings exist.
    a_f_addr_legal: assume (f_watch < DEPTH);

    // CODING_STYLE §10: RTL does not truncate; flag OOR.
    if (we)
      a_waddr_in_range: assert (waddr < DEPTH);
    if (re)
      a_raddr_in_range: assert (raddr < DEPTH);
  end

  reg                f_wr;
  reg [WIDTH-1:0]    f_data;
  initial f_wr = 1'b0;
  assign f_written = f_wr;

  always @(posedge core_clk) begin
    if (we && (waddr == f_watch) && (waddr < DEPTH)) begin
      f_wr   <= 1'b1;
      f_data <= wdata;
    end
  end

  reg f_past_ok;
  initial f_past_ok = 1'b0;
  always @(posedge core_clk)
    f_past_ok <= 1'b1;

  wire hit_r = re && (raddr == f_watch) && (raddr < DEPTH);
  wire hit_w = we && (waddr == f_watch) && (waddr < DEPTH);

  always @(posedge core_clk) begin
    // Default 1. valid_outside instances elaborate 0; verification
    // checks the external valid bit instead.
    if (ASSERT_NO_UNINIT_READ && hit_r && !f_wr)
      a_no_uninit_read: assert (1'b0);

    // 1-cycle registered read; same-address same-cycle is read-old
    // ($past(f_data) is the value before this cycle's write update).
    if (f_past_ok && $past(hit_r && f_wr))
      a_rdata_read_old: assert (rdata == $past(f_data));

    // rdata holds when there is no read (registered output).
    if (f_past_ok && $past(!re))
      a_rdata_hold: assert (rdata == $past(rdata));

    c_write_watch:     cover (hit_w);
    c_read_watch:      cover (hit_r && f_wr);
    c_read_old_conflict: cover (hit_r && hit_w && f_wr);
    c_we_only:         cover (we && !re);
    c_re_only:         cover (re && !we && f_wr);
  end

endmodule
