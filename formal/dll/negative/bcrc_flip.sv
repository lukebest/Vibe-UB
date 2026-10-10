// Negative fixture only: SPEC CRC30 with crc_word[0] inverted.
// Used to prove scripts/gate/equiv_ref.sh returns non-zero.
// Not a reference. Not product RTL.
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

  localparam [29:0] POLY = 30'h15A94AD5;
  localparam [29:0] INIT = 30'h3FFF_FFFF;

  reg [29:0] crc;

  function automatic [29:0] crc30_absorb;
    input [29:0]  crc_i;
    input [159:0] data;
    input         is_last;
    integer       b, k;
    reg    [29:0] c;
    reg           mix;
    begin
      c = crc_i;
      for (b = 0; b < 20; b = b + 1) begin
        if (!is_last || (b < 16)) begin
          for (k = 7; k >= 0; k = k - 1) begin
            mix = c[29] ^ data[8 * b + k];
            c   = {c[28:0], 1'b0};
            if (mix)
              c = c ^ POLY;
          end
        end
      end
      crc30_absorb = c;
    end
  endfunction

  wire [29:0] nxt = crc30_absorb(crc, data_in, last);

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      crc      <= INIT;
      crc_word <= 32'b0;
      done     <= 1'b0;
    end else if (start) begin
      crc      <= INIT;
      done     <= 1'b0;
    end else if (valid_in) begin
      crc <= nxt;
      done <= 1'b0;
      if (last) begin
        crc_word <= {1'b0, 1'b0, nxt} ^ 32'h1;
        done     <= 1'b1;
      end
    end else begin
      done <= 1'b0;
    end
  end

endmodule
