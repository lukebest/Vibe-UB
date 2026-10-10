// Legal PMA↔PCS stub. TX follows SPEC §3.1 hold-until-ready.
// RX is valid-only (no pma_rx_ready). Not product RTL.

module ub_pma_pcs_stub #(
  parameter NUM_LANES_TX = 1,
  parameter NUM_LANES_RX = 1,
  parameter PMA_W        = 32
) (
  input  wire                       core_clk,
  input  wire                       rst_n,
  input  wire                       tx_go,
  input  wire [NUM_LANES_TX*PMA_W-1:0] tx_data_next,
  input  wire                       pma_tx_ready,
  input  wire [NUM_LANES_TX-1:0]    elec_idle_next,
  input  wire                       rx_go,
  input  wire [NUM_LANES_RX*PMA_W-1:0] rx_data_next,
  output reg  [NUM_LANES_TX*PMA_W-1:0] pma_tx_data,
  output reg                        pma_tx_valid,
  output reg  [NUM_LANES_TX-1:0]    pma_tx_elec_idle,
  output reg  [NUM_LANES_RX*PMA_W-1:0] pma_rx_data,
  output reg                        pma_rx_valid
);
  always @(posedge core_clk) begin
    if (!rst_n) begin
      pma_tx_valid     <= 1'b0;
      pma_tx_data      <= {NUM_LANES_TX*PMA_W{1'b0}};
      pma_tx_elec_idle <= {NUM_LANES_TX{1'b0}};
      pma_rx_valid     <= 1'b0;
      pma_rx_data      <= {NUM_LANES_RX*PMA_W{1'b0}};
    end else begin
      if (pma_tx_valid && !pma_tx_ready) begin
        // SPEC §3.1: hold.
      end else if (tx_go) begin
        pma_tx_valid     <= 1'b1;
        pma_tx_data      <= tx_data_next;
        pma_tx_elec_idle <= elec_idle_next;
      end else begin
        pma_tx_valid <= 1'b0;
      end
      // SPEC §3.1 valid-only RX: source may assert any cycle; sink must take it.
      pma_rx_valid <= rx_go;
      if (rx_go)
        pma_rx_data <= rx_data_next;
    end
  end
endmodule

module ub_pma_pcs_harness #(
  parameter NUM_LANES_TX = 1,
  parameter NUM_LANES_RX = 1,
  parameter PMA_W        = 32
) (
  input wire                       core_clk,
  input wire                       rst_n,
  input wire                       tx_go,
  input wire [NUM_LANES_TX*PMA_W-1:0] tx_data_next,
  input wire                       pma_tx_ready,
  input wire [NUM_LANES_TX-1:0]    elec_idle_next,
  input wire                       rx_go,
  input wire [NUM_LANES_RX*PMA_W-1:0] rx_data_next
);
  initial assume (rst_n == 1'b0);
  wire [NUM_LANES_TX*PMA_W-1:0] pma_tx_data;
  wire                       pma_tx_valid;
  wire [NUM_LANES_TX-1:0]    pma_tx_elec_idle;
  wire [NUM_LANES_RX*PMA_W-1:0] pma_rx_data;
  wire                       pma_rx_valid;

  ub_pma_pcs_stub #(
    .NUM_LANES_TX(NUM_LANES_TX),
    .NUM_LANES_RX(NUM_LANES_RX),
    .PMA_W(PMA_W)
  ) u_dut (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .tx_go(tx_go),
    .tx_data_next(tx_data_next),
    .pma_tx_ready(pma_tx_ready),
    .elec_idle_next(elec_idle_next),
    .rx_go(rx_go),
    .rx_data_next(rx_data_next),
    .pma_tx_data(pma_tx_data),
    .pma_tx_valid(pma_tx_valid),
    .pma_tx_elec_idle(pma_tx_elec_idle),
    .pma_rx_data(pma_rx_data),
    .pma_rx_valid(pma_rx_valid)
  );

  ub_pma_pcs_if_props #(
    .NUM_LANES_TX(NUM_LANES_TX),
    .NUM_LANES_RX(NUM_LANES_RX),
    .PMA_W(PMA_W)
  ) u_props (
    .core_clk(core_clk),
    .rst_n(rst_n),
    .pma_tx_data(pma_tx_data),
    .pma_tx_valid(pma_tx_valid),
    .pma_tx_ready(pma_tx_ready),
    .pma_tx_elec_idle(pma_tx_elec_idle),
    .pma_rx_data(pma_rx_data),
    .pma_rx_valid(pma_rx_valid)
  );
endmodule
