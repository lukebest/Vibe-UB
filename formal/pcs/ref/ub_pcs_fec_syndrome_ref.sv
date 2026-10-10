`timescale 1ns / 1ps

// Formula reference for ub_pcs_fec_syndrome (SPEC §2.4, UB-PHY §3.2.3.5).
// S_j = r(alpha^j) by Horner, one symbol at a time. Independent of rtl/pcs/.
//
// r(x) = r127 x^127 + ... + r0; cw_in = {r127,...,r0}.
// syndromes = {S7,...,S0}. T=2 extra check (S4..S7 of a T=2-corrected
// word must be zero) is a decoder rule; this leaf always emits S0..S7.

module ub_pcs_fec_syndrome_ref #(
    parameter [8:0] PRIM_POLY = 9'h11D,
    parameter integer CW_HIGH_FIRST = 1
) (
    input  wire [1023:0] cw_in,
    output wire [63:0]   syndromes
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

    function automatic [7:0] alpha_pow;
        input integer exp;
        integer k;
        reg [7:0] acc;
        begin
            acc = 8'h01;
            for (k = 0; k < exp; k = k + 1)
                acc = gf_mul_shift(acc, 8'h02);
            alpha_pow = acc;
        end
    endfunction

    function automatic [63:0] horner_syndromes;
        input [1023:0] cw;
        integer j;
        integer si;
        integer idx;
        reg [7:0] aj;
        reg [7:0] acc;
        reg [7:0] s [0:7];
        begin
            for (j = 0; j < 8; j = j + 1) begin
                aj = alpha_pow(j);
                acc = 8'h00;
                // High-first Horner: ((r127*aj + r126)*aj + ... ) + r0.
                for (si = 0; si < 128; si = si + 1) begin
                    idx = CW_HIGH_FIRST ? (127 - si) : si;
                    acc = gf_mul_shift(acc, aj) ^ cw[idx * 8 +: 8];
                end
                s[j] = acc;
            end
            horner_syndromes = {s[7], s[6], s[5], s[4], s[3], s[2], s[1], s[0]};
        end
    endfunction

    assign syndromes = horner_syndromes(cw_in);

endmodule
