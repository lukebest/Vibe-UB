// ub_csr_if_props — property-only CSR bus (SPEC §3.2.3, REGMAP bus / §2.4).
// Bind on ub_csr / ub_controller. No RTL datapath. No csr_wstrb port (full-word).

module ub_csr_if_props #(
  parameter TEST_HOOKS = 1
) (
  input wire        core_clk,
  input wire        rst_n,
  input wire        csr_req,
  input wire        csr_wr,
  input wire [15:0] csr_addr,
  input wire [31:0] csr_wdata,
  input wire        csr_ready,
  input wire        csr_rvalid,
  input wire [31:0] csr_rdata,
  input wire        csr_err,
  input wire        tb_test_mode
);

  // SPEC §3.2.3 / REGMAP §1: mapped 32-bit windows used by the checker.
  function automatic is_aligned(input [15:0] addr);
    is_aligned = (addr[1:0] == 2'b00);
  endfunction

  function automatic is_test_win(input [15:0] addr);
    is_test_win = (addr >= 16'h0300) && (addr <= 16'h03FF) && is_aligned(addr);
  endfunction

  function automatic is_mapped(input [15:0] addr);
    if (!is_aligned(addr))
      is_mapped = 1'b0;
    else if (is_test_win(addr))
      is_mapped = 1'b1;
    else begin
      case (addr)
        16'h0000, 16'h0004, 16'h0008, 16'h000C, 16'h0010,
        16'h0100, 16'h0104, 16'h0108, 16'h010C, 16'h0110, 16'h0114, 16'h0118,
        16'h0200, 16'h0204, 16'h0208, 16'h020C, 16'h0210, 16'h0214,
        16'h0218, 16'h021C, 16'h0220, 16'h0224,
        16'h1000, 16'h1100, 16'h1200, 16'h1E00, 16'h1F00:
          is_mapped = 1'b1;
        default:
          is_mapped = 1'b0;
      endcase
    end
  endfunction

  wire test_quiet = (TEST_HOOKS == 0) || !tb_test_mode;
  wire mapped_now  = is_mapped(csr_addr);
  wire test_now    = is_test_win(csr_addr);
  wire aligned_now = is_aligned(csr_addr);

  // SPEC §3.2.3: csr_ready is 1 every cycle (M1, no wait).
  always @(*) begin
    a_csr_ready_hi: assert (csr_ready == 1'b1);
  end

  // Formal helpers only. Sample 1-bit decode so Yosys does not put the
  // 16-bit address case inside $past (z3 BMC timeout).
  reg f_past_ok, f_rst, f_req, f_wr, f_rdy, f_mapped, f_test, f_quiet;
  initial begin
    f_past_ok = 1'b0;
    f_rst     = 1'b0;
    f_req     = 1'b0;
    f_wr      = 1'b0;
    f_rdy     = 1'b0;
    f_mapped  = 1'b0;
    f_test    = 1'b0;
    f_quiet   = 1'b0;
  end
  always @(posedge core_clk) begin
    f_past_ok <= 1'b1;
    f_rst     <= rst_n;
    f_req     <= csr_req;
    f_wr      <= csr_wr;
    f_rdy     <= csr_ready;
    f_mapped  <= mapped_now;
    f_test    <= test_now;
    f_quiet   <= test_quiet;
  end

  always @(posedge core_clk) begin
    if (rst_n && f_past_ok) begin
      // SPEC §3.2.3 / §5: read response is the cycle after an accepted read.
      if (f_rst && f_req && f_rdy && !f_wr)
        a_csr_read_1cycle: assert (csr_rvalid);

      // SPEC §3.2.3: write response has csr_rvalid=0 next cycle.
      if (f_rst && f_req && f_rdy && f_wr)
        a_csr_write_no_rvalid: assert (!csr_rvalid);

      // No request → no response the next cycle (fixed 1-cycle, no pipeline).
      if (f_rst && !(f_req && f_rdy))
        a_csr_idle_no_resp: assert (!csr_rvalid);

      // SPEC §3.2.3 / §7: unmapped (incl. unaligned) → csr_err next cycle.
      if (f_rst && f_req && f_rdy && !f_mapped)
        a_csr_err_unmapped: assert (csr_err);
      if (f_rst && f_req && f_rdy && f_mapped)
        a_csr_err_mapped: assert (!csr_err);

      // SPEC §3.2.3: unmapped read returns 0.
      if (f_rst && f_req && f_rdy && !f_wr && !f_mapped)
        a_csr_unmap_rdata0: assert (csr_rdata == 32'h0);

      // SPEC §3.2.3 / §10.1 / §11 / REGMAP §2.4: TEST window mapped; quiet ⇒
      // read 0, write ignore, csr_err=0.
      if (f_rst && f_req && f_rdy && f_test && f_quiet)
        a_csr_test_quiet_err0: assert (!csr_err);
      if (f_rst && f_req && f_rdy && !f_wr && f_test && f_quiet)
        a_csr_test_quiet_rd0: assert (csr_rdata == 32'h0);

      c_csr_read_mapped:  cover (csr_req && !csr_wr && mapped_now);
      c_csr_write_mapped: cover (csr_req && csr_wr && mapped_now);
      c_csr_unmapped:     cover (csr_req && !mapped_now);
      c_csr_unaligned:    cover (csr_req && !aligned_now);
      c_csr_test_quiet:   cover (csr_req && test_now && test_quiet);
    end
  end

endmodule
