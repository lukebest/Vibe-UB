// Verification formula reference. Not product RTL.
// SPEC §2.6: same CRC30 as ub_dll_bcrc; compare crc_recv[29:0] only.
// error_flag_rx = crc_recv[30] (passthrough; not in the CRC). rsvd ignored.
// Bit-serial loop (not an XOR matrix). 1-cycle to done / crc_ok.
// Do not copy pycircuit/ or rtl/.
`timescale 1ns / 1ps

module ub_dll_bcrc_check (
  input  wire         core_clk,
  input  wire         rst_pyc,
  input  wire         start,
  input  wire         valid_in,
  input  wire [159:0] data_in,
  input  wire         last,
  input  wire [31:0]  crc_recv,
  output wire [31:0]  crc_word,
  output wire         done,
  output wire         crc_ok,
  output wire         crc_fail,
  output wire         error_flag_rx
);

  reg [31:0] recv_q;

  ub_dll_bcrc u_crc (
    .core_clk(core_clk),
    .rst_pyc(rst_pyc),
    .start(start),
    .valid_in(valid_in),
    .data_in(data_in),
    .last(last),
    .crc_word(crc_word),
    .done(done)
  );

  always @(posedge core_clk) begin
    if (rst_pyc)
      recv_q <= 32'b0;
    else if (valid_in && last)
      recv_q <= crc_recv;
  end

  assign crc_ok        = done & (crc_word[29:0] == recv_q[29:0]);
  assign crc_fail      = done & (crc_word[29:0] != recv_q[29:0]);
  assign error_flag_rx = done & recv_q[30];

endmodule
