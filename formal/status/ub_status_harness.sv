// Legal STATUS / PARAM stub: only produces closed encodings. Not product RTL.

module ub_status_stub (
  input  wire       core_clk,
  input  wire       rst_n,
  input  wire [2:0] req_in,
  input  wire [1:0] ack_in,
  input  wire [3:0] ntx_in,
  input  wire [3:0] nrx_in,
  output reg  [2:0] retry_req_st,
  output reg  [1:0] retry_ack_st,
  output reg  [3:0] num_lanes_tx,
  output reg  [3:0] num_lanes_rx
);
  function automatic [3:0] clip_lanes(input [3:0] n);
    case (n)
      4'd1, 4'd2, 4'd4, 4'd8: clip_lanes = n;
      default: clip_lanes = 4'd1;
    endcase
  endfunction

  always @(posedge core_clk) begin
    if (!rst_n) begin
      retry_req_st <= 3'd0;
      retry_ack_st <= 2'd0;
      num_lanes_tx <= 4'd1;
      num_lanes_rx <= 4'd1;
    end else begin
      retry_req_st <= (req_in > 3'd4) ? 3'd0 : req_in;
      retry_ack_st <= (ack_in > 2'd1) ? 2'd0 : ack_in;
      num_lanes_tx <= clip_lanes(ntx_in);
      num_lanes_rx <= clip_lanes(nrx_in);
    end
  end
endmodule

module ub_status_harness (
  input wire       core_clk,
  input wire       rst_n,
  input wire [2:0] req_in,
  input wire [1:0] ack_in,
  input wire [3:0] ntx_in,
  input wire [3:0] nrx_in
);
  initial assume (rst_n == 1'b0);
  wire [2:0] retry_req_st;
  wire [1:0] retry_ack_st;
  wire [3:0] num_lanes_tx;
  wire [3:0] num_lanes_rx;

  ub_status_stub u_dut (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .req_in(req_in),
    .ack_in(ack_in),
    .ntx_in(ntx_in),
    .nrx_in(nrx_in),
    .retry_req_st(retry_req_st),
    .retry_ack_st(retry_ack_st),
    .num_lanes_tx(num_lanes_tx),
    .num_lanes_rx(num_lanes_rx)
  );

  ub_status_if_props u_props (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .retry_req_st(retry_req_st),
    .retry_ack_st(retry_ack_st),
    .num_lanes_tx(num_lanes_tx),
    .num_lanes_rx(num_lanes_rx)
  );
endmodule
