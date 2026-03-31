module ub_pcs_fec_syndrome (
    input [128*8-1:0] cw_in,
    output [8*8-1:0] syndromes
);
    `include "ub_gf_math.vh"

    // S_j = sum_{i=0}^{127} r_i * alpha^(i*j) for j=0 to 7
    // r_127 is the first received (leftmost in cw_in), r_0 is the latest.
    // cw_in = {r_127, r_126, ..., r_0}
    
    function automatic [7:0] gf_pow_alpha;
        input integer exp;
        reg [7:0] res;
        integer k;
        begin
            res = 8'h01;
            for (k = 0; k < exp; k = k + 1) begin
                if (res[7])
                    res = (res << 1) ^ 8'h1D;
                else
                    res = res << 1;
            end
            gf_pow_alpha = res;
        end
    endfunction

    reg [7:0] s [0:7];
    integer i, j;
    
    always @(*) begin
        for (j = 0; j < 8; j = j + 1) begin
            s[j] = 8'h00;
            for (i = 0; i < 128; i = i + 1) begin
                // cw_in[(127-i)*8 +: 8] would be r_i if r_127 is the first byte.
                // Wait, if cw_in = {r_127, ..., r_0}, then:
                // r_0   is cw_in[7:0]
                // r_1   is cw_in[15:8]
                // ...
                // r_127 is cw_in[1023:1016]
                // So r_i is cw_in[i*8 +: 8].
                s[j] = s[j] ^ gf_mul(cw_in[i*8 +: 8], gf_pow_alpha(i*j));
            end
        end
    end

    assign syndromes = {s[7], s[6], s[5], s[4], s[3], s[2], s[1], s[0]};

endmodule
