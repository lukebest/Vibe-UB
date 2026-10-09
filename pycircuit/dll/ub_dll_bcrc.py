"""ub_dll_bcrc — DLL BCRC generator (SPEC §2.6; UB-DL §4.3.2.2.4 / §4.7.2).

Closed by SPEC:
  - CRC30 poly ``x^30+x^28+…+1``, tap mask ``30'h15A94AD5`` (x^30 implicit)
  - init all-ones; remainder not inverted and not reordered
  - input order: Byte 0 of the DLLDB upward; **MSB first inside each byte**
  - covers all data **before** the CRC30 field
  - pack ``{1'b0, ERROR_FLAG, crc[29:0]}``; bit31 reserved 0
  - TX ERROR_FLAG is **always 0** (SPEC §7: no ECC, no nw_tx_err)
  - FLIT_W=160 streaming; 1-cycle to crc_word / done (SPEC §5)
  - sync rst_pyc; no TEST_HOOKS (§10)
"""

from __future__ import annotations

from lib import params as P

MODULE = "ub_dll_bcrc"


def emit_verilog(
    *,
    flit_w: int = P.FLIT_W,
    crc_w: int = P.BCRC_W,
    poly: int = P.BCRC_POLY,
    word_w: int = P.BCRC_WORD_W,
) -> str:
    return _emit_bcrc(
        MODULE,
        check=False,
        flit_w=flit_w,
        crc_w=crc_w,
        poly=poly,
        word_w=word_w,
    )


def _emit_bcrc(
    name: str,
    *,
    check: bool,
    flit_w: int,
    crc_w: int,
    poly: int,
    word_w: int,
) -> str:
    extra_ports = ""
    extra_outs = ""
    extra_regs = ""
    extra_rst = ""
    extra_last = ""
    extra_assign = ""
    tx_flag = "1'b0"
    if check:
        extra_ports = """
  input  wire [WORD_W-1:0]    crc_recv,"""
        extra_outs = """,
  output wire                 crc_ok,
  output wire                 crc_fail,
  output wire                 error_flag_rx"""
        extra_regs = """
  reg               ok_q;
  reg               fail_q;
  reg               eflag_q;"""
        extra_rst = """
      ok_q      <= 1'b0;
      fail_q    <= 1'b0;
      eflag_q   <= 1'b0;"""
        extra_last = """
          ok_q    <= (t == crc_recv[CRC_W-1:0]) & ~(crc_recv[WORD_W-1] & 1'b0);
          fail_q  <= (t != crc_recv[CRC_W-1:0]);
          eflag_q <= crc_recv[WORD_W-2];"""
        extra_assign = """
  assign crc_ok        = ok_q;
  assign crc_fail      = fail_q;
  assign error_flag_rx = eflag_q;"""
        tx_flag = "1'b0"
    role = "checker" if check else "generator"
    check_note = (
        "Check compares CRC30 only (SPEC §2.6); bit31 ignored; "
        "error_flag_rx = crc_recv[30] for parent nw_rx_err (SPEC §7)."
        if check
        else "TX ERROR_FLAG hardwired 0 (SPEC §7)."
    )
    return f"""// GENERATED from pycircuit/dll/{name}.py — do not edit.
// Reproduce: make emit
// SPEC §2.6 / UB-DL §4.3.2.2.4 / §4.7.2 / §7. TEST_HOOKS=0.
// BCRC {role}. Registers: posedge core_clk, sync active-high rst_pyc.
// Poly/init/no-invert/MSB-first-per-byte/packing from SPEC (not Switch).
// {check_note}

module {name} #(
  parameter integer FLIT_W  = {flit_w},
  parameter integer CRC_W   = {crc_w},
  parameter integer WORD_W  = {word_w},
  parameter [CRC_W-1:0] POLY = {crc_w}'h{poly:X}
) (
  input  wire                 core_clk,
  input  wire                 rst_pyc,
  input  wire                 start,
  input  wire                 valid_in,
  input  wire [FLIT_W-1:0]    data_in,
  input  wire                 last,{extra_ports}
  output wire [WORD_W-1:0]    crc_word,
  output wire                 done{extra_outs}
);

  localparam [CRC_W-1:0] CRC_INIT    = {{CRC_W{{1'b1}}}};
  localparam integer     NBYTE       = FLIT_W / 8;
  localparam integer     BCRC_BYTES  = WORD_W / 8;

  reg  [CRC_W-1:0]  crc_q;
  reg  [WORD_W-1:0] word_q;
  reg               done_q;{extra_regs}

  integer by;
  integer bi;

  function automatic [CRC_W-1:0] crc_step;
    input [CRC_W-1:0] c;
    input             b;
    reg               fb;
    begin
      fb       = c[CRC_W-1] ^ b;
      crc_step = {{c[CRC_W-2:0], 1'b0}} ^ ({{CRC_W{{fb}}}} & POLY);
    end
  endfunction

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      crc_q     <= CRC_INIT;
      word_q    <= {{WORD_W{{1'b0}}}};
      done_q    <= 1'b0;{extra_rst}
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
            word_q <= {{1'b0, {tx_flag}, t}};
            done_q <= 1'b1;{extra_last}
          end
        end
      end
    end
  end

  assign crc_word = word_q;
  assign done     = done_q;{extra_assign}

endmodule
"""
