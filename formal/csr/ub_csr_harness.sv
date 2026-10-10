// Legal CSR stub: full-word, 1-cycle read, unmapped err, TEST quiet rules.
// Sync reset on rst_n (stands in for rst_n_sync / rst_pyc). Not product RTL.

module ub_csr_stub (
  input  wire        core_clk,
  input  wire        rst_n,
  input  wire        csr_req,
  input  wire        csr_wr,
  input  wire [15:0] csr_addr,
  input  wire [31:0] csr_wdata,
  input  wire        tb_test_mode,
  output wire        csr_ready,
  output reg         csr_rvalid,
  output reg  [31:0] csr_rdata,
  output reg         csr_err
);
  assign csr_ready = 1'b1;

  reg [31:0] port_cna;
  reg [31:0] test_scale;

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

  function automatic [31:0] read_data(input [15:0] addr);
    if (is_test_win(addr) && !tb_test_mode)
      read_data = 32'h0;
    else if (addr == 16'h0010)
      read_data = port_cna;
    else if (addr == 16'h0300 && tb_test_mode)
      read_data = test_scale;
    else
      read_data = 32'h0;
  endfunction

  always @(posedge core_clk) begin
    if (!rst_n) begin
      csr_rvalid <= 1'b0;
      csr_rdata  <= 32'h0;
      csr_err    <= 1'b0;
      port_cna   <= 32'h0;
      test_scale <= 32'h0;
    end else if (csr_req) begin
      csr_rvalid <= !csr_wr;
      csr_err    <= !is_mapped(csr_addr);
      csr_rdata  <= (!csr_wr) ? read_data(csr_addr) : 32'h0;
      if (csr_wr && is_mapped(csr_addr)) begin
        if (csr_addr == 16'h0010)
          port_cna <= csr_wdata;
        if (is_test_win(csr_addr) && tb_test_mode && csr_addr == 16'h0300)
          test_scale <= csr_wdata;
      end
    end else begin
      csr_rvalid <= 1'b0;
      csr_rdata  <= 32'h0;
      csr_err    <= 1'b0;
    end
  end
endmodule

module ub_csr_harness (
  input wire        core_clk,
  input wire        rst_n,
  input wire        csr_req,
  input wire        csr_wr,
  input wire [15:0] csr_addr,
  input wire [31:0] csr_wdata,
  input wire        tb_test_mode
);
  wire        csr_ready;
  wire        csr_rvalid;
  wire [31:0] csr_rdata;
  wire        csr_err;

  ub_csr_stub u_dut (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .csr_req(csr_req),
    .csr_wr(csr_wr),
    .csr_addr(csr_addr),
    .csr_wdata(csr_wdata),
    .tb_test_mode(tb_test_mode),
    .csr_ready(csr_ready),
    .csr_rvalid(csr_rvalid),
    .csr_rdata(csr_rdata),
    .csr_err(csr_err)
  );

  ub_csr_if_props #(.TEST_HOOKS(1)) u_props (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .csr_req(csr_req),
    .csr_wr(csr_wr),
    .csr_addr(csr_addr),
    .csr_wdata(csr_wdata),
    .csr_ready(csr_ready),
    .csr_rvalid(csr_rvalid),
    .csr_rdata(csr_rdata),
    .csr_err(csr_err),
    .tb_test_mode(tb_test_mode)
  );
endmodule
