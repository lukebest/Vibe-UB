// Negative fixture only: same formula as the reference except crc resets
// to 0 instead of INIT (all-1s). Used to prove EQUIV_METHODS=regpair
// fails the dedicated reset-value check. Not a reference. Not product RTL.
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

  wire [29:0] seed = start ? INIT : crc;
  wire [29:0] nxt  = crc30_absorb(seed, data_in, last);
  // Deliberately wrong reset value for crc (0, not INIT). last still reloads INIT.
  wire [29:0] crc_n  = rst_pyc ? 30'b0 :
                       ((valid_in && last) ? INIT :
                        (valid_in ? nxt : (start ? INIT : crc)));
  wire [31:0] word_n = rst_pyc ? 32'b0 :
                       ((valid_in && last) ? {2'b00, nxt} : crc_word);
  wire        done_n = rst_pyc ? 1'b0 : (valid_in && last);

  always @(posedge core_clk) begin
    crc      <= crc_n;
    crc_word <= word_n;
    done     <= done_n;
  end

endmodule
