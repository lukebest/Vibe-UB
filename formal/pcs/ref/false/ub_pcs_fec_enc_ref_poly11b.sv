`timescale 1ns / 1ps

// Deliberately wrong: primitive polynomial 0x11B (AES field) instead of 0x11D.
module ub_pcs_fec_enc_ref_poly11b (
    input  wire [959:0]  msg_in,
    output wire [1023:0] cw_out
);
    ub_pcs_fec_enc_ref #(
        .PRIM_POLY(9'h11B)
    ) u_bad (
        .msg_in(msg_in),
        .cw_out(cw_out)
    );
endmodule
