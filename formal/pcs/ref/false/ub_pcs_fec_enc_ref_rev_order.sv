`timescale 1ns / 1ps

// Deliberately wrong: feed m0 .. m119 instead of m119 .. m0.
module ub_pcs_fec_enc_ref_rev_order (
    input  wire [959:0]  msg_in,
    output wire [1023:0] cw_out
);
    ub_pcs_fec_enc_ref #(
        .MSG_HIGH_FIRST(0)
    ) u_bad (
        .msg_in(msg_in),
        .cw_out(cw_out)
    );
endmodule
