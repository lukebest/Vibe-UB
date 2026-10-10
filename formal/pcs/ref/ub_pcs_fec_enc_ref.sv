`timescale 1ns / 1ps

// Formula reference for ub_pcs_fec_enc (SPEC §2.4, UB-PHY §3.2.2.1).
// Systematic RS(128,120) parity by a per-symbol LFSR. Not a precomputed
// GF(2) matrix. Independent of rtl/pcs/.
//
// Field GF(2^8), primitive x^8+x^4+x^3+x^2+1 (0x11D). Generator roots
// alpha^0 .. alpha^7. Table 3-2 taps g0..g8 = 24,200,173,239,54,81,11,255,1.
// Wire order: msg_in = {m119,...,m0}, cw_out = {m119,...,m0,p7,...,p0}.
// T=2 uses the same eight parity symbols; this leaf has no bypass pin.

module ub_pcs_fec_enc_ref #(
    parameter [8:0] PRIM_POLY = 9'h11D,
    parameter [7:0] G0        = 8'd24,
    parameter [7:0] G1        = 8'd200,
    parameter [7:0] G2        = 8'd173,
    parameter [7:0] G3        = 8'd239,
    parameter [7:0] G4        = 8'd54,
    parameter [7:0] G5        = 8'd81,
    parameter [7:0] G6        = 8'd11,
    parameter [7:0] G7        = 8'd255,
    parameter integer MSG_HIGH_FIRST = 1
) (
    input  wire [959:0]  msg_in,
    output wire [1023:0] cw_out
);

    function automatic [7:0] gf_mul_shift;
        input [7:0] a_in;
        input [7:0] b_in;
        integer bit_i;
        reg [7:0] a;
        reg [7:0] b;
        reg [7:0] p;
        begin
            a = a_in;
            b = b_in;
            p = 8'h00;
            for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
                if (b[0])
                    p = p ^ a;
                if (a[7])
                    a = {a[6:0], 1'b0} ^ PRIM_POLY[7:0];
                else
                    a = {a[6:0], 1'b0};
                b = {1'b0, b[7:1]};
            end
            gf_mul_shift = p;
        end
    endfunction

    function automatic [63:0] lfsr_parity;
        input [959:0] msg;
        integer si;
        integer gi;
        integer idx;
        reg [7:0] tap [0:7];
        reg [7:0] r [0:7];
        reg [7:0] nxt [0:7];
        reg [7:0] fb;
        begin
            tap[0] = G0;
            tap[1] = G1;
            tap[2] = G2;
            tap[3] = G3;
            tap[4] = G4;
            tap[5] = G5;
            tap[6] = G6;
            tap[7] = G7;
            for (gi = 0; gi < 8; gi = gi + 1)
                r[gi] = 8'h00;
            // One LFSR step per message symbol. Default: m119, then m118, ... m0.
            for (si = 0; si < 120; si = si + 1) begin
                idx = MSG_HIGH_FIRST ? (119 - si) : si;
                fb = msg[idx * 8 +: 8] ^ r[7];
                nxt[0] = gf_mul_shift(fb, tap[0]);
                for (gi = 1; gi < 8; gi = gi + 1)
                    nxt[gi] = r[gi - 1] ^ gf_mul_shift(fb, tap[gi]);
                for (gi = 0; gi < 8; gi = gi + 1)
                    r[gi] = nxt[gi];
            end
            lfsr_parity = {r[7], r[6], r[5], r[4], r[3], r[2], r[1], r[0]};
        end
    endfunction

    assign cw_out = {msg_in, lfsr_parity(msg_in)};

endmodule
