// Verification formula reference. Not product RTL.
// SPEC §2.6: same CRC30 as ub_dll_bcrc; compare crc_recv[29:0] only.
// error_flag_rx = crc_recv[30] (passthrough; not in the CRC). rsvd ignored.
// Result appears 1 cycle after last (SPEC §7) and holds until the next last.
// Bit-serial loop (not an XOR matrix). Do not copy pycircuit/ or rtl/.
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
  reg        ok_q;
  reg        fail_q;
  reg        eflag_q;

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

  wire cmp_ok   = (crc_word[29:0] == recv_q[29:0]);
  wire cmp_fail = (crc_word[29:0] != recv_q[29:0]);
  wire cmp_ef   = recv_q[30];

  // Capture on the done cycle (old done in this block); hold otherwise.
  always @(posedge core_clk) begin
    if (rst_pyc) begin
      ok_q    <= 1'b0;
      fail_q  <= 1'b0;
      eflag_q <= 1'b0;
    end else if (done) begin
      ok_q    <= cmp_ok;
      fail_q  <= cmp_fail;
      eflag_q <= cmp_ef;
    end
  end

  assign crc_ok        = done ? cmp_ok : ok_q;
  assign crc_fail      = done ? cmp_fail : fail_q;
  assign error_flag_rx = done ? cmp_ef : eflag_q;

endmodule
