// GENERATED from pycircuit/dll/ub_dll_bcrc.py — do not edit.
// Reproduce: make emit
// SPEC §2.6 / UB-DL §4.3.2.2.4 / §4.7.2 / §7. TEST_HOOKS=0
// (SPEC §10 lists no hook ports on this leaf).
// BCRC generator. Registers: posedge core_clk, sync active-high rst_pyc.
// Poly/init/no-invert/MSB-first-per-byte/packing from SPEC (not Switch).
// TX ERROR_FLAG hardwired 0 (SPEC §7).

module ub_dll_bcrc #(
  parameter integer FLIT_W  = 160,
  parameter integer CRC_W   = 30,
  parameter integer WORD_W  = 32,
  parameter [CRC_W-1:0] POLY = 30'h15A94AD5
) (
  input  wire                 core_clk,
  input  wire                 rst_pyc,
  input  wire                 start,
  input  wire                 valid_in,
  input  wire [FLIT_W-1:0]    data_in,
  input  wire                 last,
  output wire [WORD_W-1:0]    crc_word,
  output wire                 done
);

  localparam [CRC_W-1:0] CRC_INIT    = {CRC_W{1'b1}};
  localparam integer     NBYTE       = FLIT_W / 8;
  localparam integer     BCRC_BYTES  = WORD_W / 8;

  reg  [CRC_W-1:0]  crc_q;
  reg  [WORD_W-1:0] word_q;
  reg               done_q;

  integer by;
  integer bi;

  function automatic [CRC_W-1:0] crc_step;
    input [CRC_W-1:0] c;
    input             b;
    reg               fb;
    begin
      fb       = c[CRC_W-1] ^ b;
      crc_step = {c[CRC_W-2:0], 1'b0} ^ ({CRC_W{fb}} & POLY);
    end
  endfunction

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      crc_q     <= CRC_INIT;
      word_q    <= {WORD_W{1'b0}};
      done_q    <= 1'b0;
    end else begin
      done_q <= 1'b0;
      if (start) begin
        crc_q <= CRC_INIT;
      end else if (valid_in) begin
        begin : eat
          reg [CRC_W-1:0] t;
          t = crc_q;
          // SPEC §2.6: cover data before the CRC30 field. Last flit's
          // trailing WORD_W/8 bytes are the BCRC word — do not CRC them.
          for (by = 0; by < NBYTE; by = by + 1)
            if (!(last && (by >= (NBYTE - BCRC_BYTES))))
              for (bi = 7; bi >= 0; bi = bi - 1)
                t = crc_step(t, data_in[by*8 + bi]);
          crc_q <= t;
          if (last) begin
            word_q <= {1'b0, 1'b0, t};
            done_q <= 1'b1;
          end
        end
      end
    end
  end

  assign crc_word = word_q;
  assign done     = done_q;

endmodule
