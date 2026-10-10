`timescale 1ns / 1ps

// Deliberately wrong: Table 3-2 g1 = 200 replaced by 201.
module ub_pcs_fec_enc_ref_bad_coeff (
    input  wire [959:0]  msg_in,
    output wire [1023:0] cw_out
);
    ub_pcs_fec_enc_ref #(
        .G1(8'd201)
    ) u_bad (
        .msg_in(msg_in),
        .cw_out(cw_out)
    );
endmodule
