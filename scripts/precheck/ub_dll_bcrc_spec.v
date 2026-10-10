// Independent bit-serial BCRC generator from SPEC §2.6 / UB-DL §4.3.2.2.4 / §4.7.2.
// Local pre-check only (non-gating). Not generated from pycircuit.
// Poly 30'h15A94AD5 (x^30 implicit), init all-ones,
// Byte0-up MSB-first, last-beat trailing 4 bytes excluded, pack {1'b0, 1'b0, crc}.
// 1-cycle registered crc_word / done. Sync active-high rst_pyc.
module ub_dll_bcrc_spec (
  input         core_clk,
  input         rst_pyc,
  input         start,
  input         valid_in,
  input [159:0] data_in,
  input         last,
  output [31:0] crc_word,
  output        done
);
  localparam [29:0] POLY = 30'h15A94AD5;
  localparam [29:0] INIT = 30'h3FFFFFFF;

  reg [29:0] crc_q;
  reg [31:0] word_q;
  reg        done_q;

  function automatic [29:0] crc_step;
    input [29:0] c;
    input        b;
    reg          fb;
    begin
      fb       = c[29] ^ b;
      crc_step = {c[28:0], 1'b0} ^ ({30{fb}} & POLY);
    end
  endfunction

  function automatic [29:0] crc_eat;
    input [29:0]  c;
    input [159:0] d;
    input         last_i;
    integer       by, bi;
    begin
      crc_eat = c;
      for (by = 0; by < 20; by = by + 1)
        if (!(last_i && (by >= 16)))
          for (bi = 7; bi >= 0; bi = bi - 1)
            crc_eat = crc_step(crc_eat, d[by*8 + bi]);
    end
  endfunction

  wire [29:0] nxt = crc_eat(crc_q, data_in, last);

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      crc_q  <= INIT;
      word_q <= 32'b0;
      done_q <= 1'b0;
    end else begin
      done_q <= 1'b0;
      if (start) begin
        crc_q <= INIT;
      end else if (valid_in) begin
        crc_q <= nxt;
        if (last) begin
          word_q <= {1'b0, 1'b0, nxt};
          done_q <= 1'b1;
        end
      end
    end
  end

  assign crc_word = word_q;
  assign done     = done_q;
endmodule
