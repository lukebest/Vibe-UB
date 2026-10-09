"""ub_dll_bcrc — DLL block CRC generator (SPEC §2.6; UB-DL §4.3.2.2 / §4.7.2).

Streaming CRC over 160-bit flits. Default CRC30 / poly / init / packing
are parameters (not closed in-repo SPEC text); defaults match
Vibe-UB-Switch ``vibe_bcrc`` (D9):
  poly 30'h15A94AD5, init all-1s, no invert, LSB-first,
  last word {{1'b0, error_flag, crc[29:0]}}.

``start`` reloads init and wins over ``valid_in``.
``error_flag`` is a port (SPEC §7 TX ERROR_FLAG is 待定) — packed on last,
not mixed into the CRC remainder.

Registers: pyc_reg semantics (sync ``rst_pyc``). 1-cycle latency to
``done`` / ``crc_word``. No TEST_HOOKS (SPEC §10 / CODING_STYLE §4).
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
    if check:
        extra_ports = f"""
  input  wire [WORD_W-1:0]    crc_recv,"""
        extra_outs = """,
  output wire                 crc_ok,
  output wire                 crc_fail"""
        extra_regs = """
  reg               ok_q;
  reg               fail_q;"""
        extra_rst = """
      ok_q      <= 1'b0;
      fail_q    <= 1'b0;"""
        extra_last = """
          ok_q   <= ({1'b0, error_flag, t} == crc_recv);
          fail_q <= ({1'b0, error_flag, t} != crc_recv);"""
        extra_assign = """
  assign crc_ok   = ok_q;
  assign crc_fail = fail_q;"""
    role = "checker" if check else "generator"
    return f"""// GENERATED from pycircuit/dll/{name}.py — do not edit.
// Reproduce: make emit
// SPEC §2.6 / UB-DL §4.3.2.2 / §4.7.2. TEST_HOOKS=0.
// BCRC {role}. Registers: posedge core_clk, sync active-high rst_pyc.
// Polynomial / width / packing are parameters (Open questions for Xia).

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
  input  wire                 last,
  input  wire                 error_flag,{extra_ports}
  output wire [WORD_W-1:0]    crc_word,
  output wire                 done{extra_outs}
);

  localparam [CRC_W-1:0] CRC_INIT = {{CRC_W{{1'b1}}}};

  reg  [CRC_W-1:0]  crc_q;
  reg  [WORD_W-1:0] word_q;
  reg               done_q;{extra_regs}

  integer i;

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
          for (i = 0; i < FLIT_W; i = i + 1)
            t = crc_step(t, data_in[i]);
          crc_q <= t;
          if (last) begin
            word_q <= {{1'b0, error_flag, t}};
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
