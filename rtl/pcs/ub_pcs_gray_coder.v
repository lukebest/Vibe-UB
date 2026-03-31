module ub_pcs_gray_coder (
    input [1:0] bits,
    output [1:0] symbols
);
    // Standard PAM4 Gray Coding: 00->0, 01->1, 11->2, 10->3
    assign symbols[1] = bits[1];
    assign symbols[0] = bits[1] ^ bits[0];
endmodule
