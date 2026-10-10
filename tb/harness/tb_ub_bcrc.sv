// TB-only wrapper. rst_n (low) inverted to rst_pyc (SPEC §4.2). No tb_* (SPEC §10 / Xia).
`timescale 1ns / 1ps

module tb_ub_bcrc (
  input  wire         core_clk,
  input  wire         rst_n,
  input  wire         start,
  input  wire         valid_in,
  input  wire [159:0] data_in,
  input  wire         last,
  output wire [31:0]  crc_word,
  output wire         done
);

  ub_dll_bcrc dut (
    .core_clk(core_clk),
    .rst_pyc(~rst_n),
    .start(start),
    .valid_in(valid_in),
    .data_in(data_in),
    .last(last),
    .crc_word(crc_word),
    .done(done)
  );

endmodule
