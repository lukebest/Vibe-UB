// ub_csr_if_props — property-only CSR bus (SPEC §3.2.3, REGMAP bus / §2.4).
// Bind on ub_csr / ub_controller. No RTL logic. No csr_wstrb port (full-word).

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

  // SPEC §3.2.3: csr_ready is 1 every cycle (M1, no wait).
  a_csr_ready_hi: assert property (@(posedge core_clk) csr_ready == 1'b1);

  // SPEC §3.2.3 / §5: read response is the cycle after an accepted read.
  a_csr_read_1cycle: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (csr_req && csr_ready && !csr_wr) |=> csr_rvalid
  );

  // SPEC §3.2.3: write response has csr_rvalid=0 next cycle; csr_err is valid then.
  a_csr_write_no_rvalid: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (csr_req && csr_ready && csr_wr) |=> !csr_rvalid
  );

  // No request → no response the next cycle (fixed 1-cycle, no pipeline).
  a_csr_idle_no_resp: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    !(csr_req && csr_ready) |=> !csr_rvalid
  );

  // SPEC §3.2.3 / §7: unmapped (incl. unaligned) → csr_err next cycle.
  // TEST window is mapped even when quiet (err=0).
  a_csr_err_unmapped: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (csr_req && csr_ready && !is_mapped(csr_addr)) |=> csr_err
  );
  a_csr_err_mapped: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (csr_req && csr_ready && is_mapped(csr_addr)) |=> !csr_err
  );

  // SPEC §3.2.3: unmapped read returns 0.
  a_csr_unmap_rdata0: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (csr_req && csr_ready && !csr_wr && !is_mapped(csr_addr)) |=> (csr_rdata == 32'h0)
  );

  // SPEC §3.2.3 / §10.1 / §11 / REGMAP §2.4: TEST 0x0300–0x03FF is mapped.
  // Quiet (PRODUCT or tb_test_mode=0): read 0, write ignore, csr_err=0.
  a_csr_test_quiet_err0: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (csr_req && csr_ready && is_test_win(csr_addr) && test_quiet) |=> !csr_err
  );
  a_csr_test_quiet_rd0: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (csr_req && csr_ready && !csr_wr && is_test_win(csr_addr) && test_quiet)
    |=> (csr_rdata == 32'h0)
  );

  c_csr_read_mapped: cover property (
    @(posedge core_clk) rst_n && csr_req && !csr_wr && is_mapped(csr_addr)
  );
  c_csr_write_mapped: cover property (
    @(posedge core_clk) rst_n && csr_req && csr_wr && is_mapped(csr_addr)
  );
  c_csr_unmapped: cover property (
    @(posedge core_clk) rst_n && csr_req && !is_mapped(csr_addr)
  );
  c_csr_unaligned: cover property (
    @(posedge core_clk) rst_n && csr_req && !is_aligned(csr_addr)
  );
  c_csr_test_quiet: cover property (
    @(posedge core_clk) rst_n && csr_req && is_test_win(csr_addr) && test_quiet
  );

endmodule
