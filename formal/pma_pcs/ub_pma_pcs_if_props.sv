// ub_pma_pcs_if_props — property-only PMA↔PCS interface (SPEC §3.1, §3.2.4, §3.3).
// Bind/instantiate on ub_controller or the PCS–PMA boundary. No RTL logic.
//
// RX is valid-only: this module has no pma_rx_ready port (SPEC §3.1 / §3.2.4).
// Per-lane pack: lane 0 at the bus LSB (SPEC §3.2.4 / §3.3). PMA_W=32 (SPEC §9).

module ub_pma_pcs_if_props #(
  parameter NUM_LANES_TX = 1,
  parameter NUM_LANES_RX = 1,
  parameter PMA_W        = 32
) (
  input wire                       core_clk,
  input wire                       rst_n,
  input wire [NUM_LANES_TX*PMA_W-1:0] pma_tx_data,
  input wire                       pma_tx_valid,
  input wire                       pma_tx_ready,
  input wire [NUM_LANES_TX-1:0]    pma_tx_elec_idle,
  input wire [NUM_LANES_RX*PMA_W-1:0] pma_rx_data,
  input wire                       pma_rx_valid
);

  // SPEC §9 / REGMAP §2.2: NUM_LANES_* legal set is {1,2,4,8}; PMA_W M1 = 32.
  always @(*) begin
    a_pma_w_m1: assert (PMA_W == 32);
    a_nlanes_tx_legal: assert (
      NUM_LANES_TX == 1 || NUM_LANES_TX == 2 ||
      NUM_LANES_TX == 4 || NUM_LANES_TX == 8
    );
    a_nlanes_rx_legal: assert (
      NUM_LANES_RX == 1 || NUM_LANES_RX == 2 ||
      NUM_LANES_RX == 4 || NUM_LANES_RX == 8
    );
  end

  // SPEC §3.1 valid/ready (TX only): hold valid and data until ready.
  a_pma_tx_hold: assert property (
    @(posedge core_clk) disable iff (!rst_n)
    (pma_tx_valid && !pma_tx_ready) |=> (pma_tx_valid && $stable(pma_tx_data))
  );

  // SPEC §3.2.4: RX has no ready — every pma_rx_valid beat is a transfer.
  // Documented by the absence of pma_rx_ready on this module.
  c_pma_rx_valid_beat: cover property (
    @(posedge core_clk) rst_n && pma_rx_valid
  );
  c_pma_tx_handshake: cover property (
    @(posedge core_clk) rst_n && pma_tx_valid && pma_tx_ready
  );
  c_pma_tx_backpressure: cover property (
    @(posedge core_clk) rst_n && pma_tx_valid && !pma_tx_ready
  );

  // SPEC §3.2.4 / §3.3: lane 0 occupies the LSB PMA_W bits.
  wire [PMA_W-1:0] tx_lane0 = pma_tx_data[PMA_W-1:0];
  wire [PMA_W-1:0] rx_lane0 = pma_rx_data[PMA_W-1:0];
  c_tx_lane0_nonzero: cover property (@(posedge core_clk) rst_n && pma_tx_valid && (tx_lane0 != {PMA_W{1'b0}}));
  c_rx_lane0_nonzero: cover property (@(posedge core_clk) rst_n && pma_rx_valid && (rx_lane0 != {PMA_W{1'b0}}));

  // Keep elec_idle visible so the per-lane sideband is part of the bind.
  c_tx_elec_idle: cover property (@(posedge core_clk) rst_n && (|pma_tx_elec_idle));

endmodule
