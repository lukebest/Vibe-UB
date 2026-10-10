`timescale 1ns / 1ps

// Deliberately wrong: Horner in the AES field (0x11B) instead of 0x11D.
module ub_pcs_fec_syndrome_ref_poly11b (
    input  wire [1023:0] cw_in,
    output wire [63:0]   syndromes
);
    ub_pcs_fec_syndrome_ref #(
        .PRIM_POLY(9'h11B)
    ) u_bad (
        .cw_in(cw_in),
        .syndromes(syndromes)
    );
endmodule
