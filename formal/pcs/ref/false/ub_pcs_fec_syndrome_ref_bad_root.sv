`timescale 1ns / 1ps

// Deliberately wrong: evaluate r(alpha^{j+1}) so roots are alpha^1..alpha^8.
module ub_pcs_fec_syndrome_ref_bad_root (
    input  wire [1023:0] cw_in,
    output wire [63:0]   syndromes
);
    ub_pcs_fec_syndrome_ref #(
        .ROOT_BASE(1)
    ) u_bad (
        .cw_in(cw_in),
        .syndromes(syndromes)
    );
endmodule
