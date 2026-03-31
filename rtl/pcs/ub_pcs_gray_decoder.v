module ub_pcs_gray_decoder (
    input [1:0] symbols,
    output [1:0] bits
);
    // Standard PAM4 Gray Decoding: Inverse of gray_coder
    // symbols[1] = bits[1]
    // symbols[0] = bits[1] ^ bits[0]
    // Therefore:
    // bits[1] = symbols[1]
    // bits[0] = symbols[1] ^ symbols[0]
    assign bits[1] = symbols[1];
    assign bits[0] = symbols[1] ^ symbols[0];
endmodule
