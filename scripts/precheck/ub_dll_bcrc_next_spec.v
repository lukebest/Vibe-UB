// Combinational bit-serial CRC30 next-state (SPEC §2.6). Local pre-check (non-gating).
// Byte0-up, MSB-first per byte; last beat drops trailing 4 bytes.
module ub_dll_bcrc_next_spec (
  input  [29:0]  crc_q,
  input  [159:0] data_in,
  input          last,
  output [29:0]  nxt
);
  localparam [29:0] POLY = 30'h15A94AD5;

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

  assign nxt = crc_eat(crc_q, data_in, last);
endmodule
