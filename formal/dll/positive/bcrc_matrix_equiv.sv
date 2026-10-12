// Functionally equivalent rewrite of formal/dll/ref/ub_dll_bcrc.sv.
// Same SPEC §2.6 formula (POLY / INIT / byte-0 = data_in[7:0] MSB-first /
// last flit bytes 0..15 / last reloads INIT). Structure is a generate XOR
// chain with every internal wire renamed — not the gold bit-serial function.
// Used only to prove regpair CEC is not fooled by a property-AIGER &cec.
// Not product RTL.
`timescale 1ns / 1ps

module ub_dll_bcrc (
  input  wire         core_clk,
  input  wire         rst_pyc,
  input  wire         start,
  input  wire         valid_in,
  input  wire [159:0] data_in,
  input  wire         last,
  output reg  [31:0]  crc_word,
  output reg          done
);

  localparam [29:0] POLY_M = 30'h15A94AD5;
  localparam [29:0] ALL_ONES = 30'h3FFF_FFFF;

  reg [29:0] crc;

  wire [29:0] rem_base = start ? ALL_ONES : crc;

  // 160-bit absorb as a generate XOR-shift chain (matrix-style unrolling).
  // Stream order matches gold: byte b, bit k=7..0 of data_in[8*b+k].
  // Last flit absorbs only the first 128 bits (bytes 0..15).
  wire [29:0] stage [0:160];
  assign stage[0] = rem_base;

  genvar gi;
  generate
    for (gi = 0; gi < 160; gi = gi + 1) begin : g_xor_col
      localparam integer BYTE_I = gi / 8;
      localparam integer BIT_I  = 7 - (gi % 8);
      wire take_bit = !last || (BYTE_I < 16);
      wire data_bit = data_in[8 * BYTE_I + BIT_I];
      wire mix_bit  = stage[gi][29] ^ data_bit;
      wire [29:0] shifted = {stage[gi][28:0], 1'b0};
      wire [29:0] xored   = shifted ^ POLY_M;
      assign stage[gi + 1] = take_bit ? (mix_bit ? xored : shifted) : stage[gi];
    end
  endgenerate

  wire [29:0] folded   = stage[160];
  wire [29:0] rem_next = rst_pyc ? ALL_ONES :
                         ((valid_in && last) ? ALL_ONES :
                          (valid_in ? folded : (start ? ALL_ONES : crc)));
  wire [31:0] emit_next = rst_pyc ? 32'b0 :
                          ((valid_in && last) ? {2'b00, folded} : crc_word);
  wire        flag_next = rst_pyc ? 1'b0 : (valid_in && last);

  always @(posedge core_clk) begin
    crc      <= rem_next;
    crc_word <= emit_next;
    done     <= flag_next;
  end

endmodule
