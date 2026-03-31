`timescale 1ns / 1ps

module ub_pcs_fec_chien_forney (
    input clk,
    input rst_n,
    input start,
    input [39:0] lambda,   // {L4, L3, L2, L1, L0}
    input [31:0] omega,    // {O3, O2, O1, O0}
    output reg done,
    output reg [127:0] error_mask,
    output reg [1023:0] error_magnitudes
);

    `include "ub_gf_math.vh"

    // Evaluation points: x_i = alpha^{255-i} for i = 0 to 127
    
    wire [7:0] L [0:4];
    wire [7:0] O [0:3];
    
    assign {L[4], L[3], L[2], L[1], L[0]} = lambda;
    assign {O[3], O[2], O[1], O[0]} = omega;

    // Intermediate evaluation registers for cycle 1 to cycle 2 transition
    reg [7:0] l_even_q [0:127];
    reg [7:0] l_odd_q [0:127];
    reg [7:0] omega_q [0:127];
    reg active;

    // Helper to get alpha^(exp)
    function automatic [7:0] gf_pow_alpha;
        input integer exp;
        reg [7:0] res;
        integer k;
        begin
            res = 8'h01;
            for (k = 0; k < (exp % 255); k = k + 1) begin
                if (res[7])
                    res = (res << 1) ^ 8'h1D;
                else
                    res = res << 1;
            end
            gf_pow_alpha = res;
        end
    endfunction

    // Helper to get alpha^((255-i)*k % 255)
    function automatic [7:0] apow;
        input integer i;
        input integer k;
        begin
            apow = gf_pow_alpha((255 - i) * k);
        end
    endfunction

    // Parallel evaluation wires
    wire [7:0] l_even_eval [0:127];
    wire [7:0] l_odd_eval [0:127];
    wire [7:0] omega_eval [0:127];

    genvar i;
    generate
        for (i = 0; i < 128; i = i + 1) begin : gen_eval
            // Lambda_even(x) = L0 + L2*x^2 + L4*x^4
            assign l_even_eval[i] = L[0] ^ gf_mul(L[2], apow(i, 2)) ^ gf_mul(L[4], apow(i, 4));
            // Lambda_odd(x) = L1*x + L3*x^3
            assign l_odd_eval[i]  = gf_mul(L[1], apow(i, 1)) ^ gf_mul(L[3], apow(i, 3));
            // Omega(x) = O0 + O1*x + O2*x^2 + O3*x^3
            assign omega_eval[i]  = O[0] ^ gf_mul(O[1], apow(i, 1)) ^ gf_mul(O[2], apow(i, 2)) ^ gf_mul(O[3], apow(i, 3));
        end
    endgenerate

    integer idx;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            done <= 1'b0;
            error_mask <= 128'b0;
            error_magnitudes <= 1024'b0;
            for (idx = 0; idx < 128; idx = idx + 1) begin
                l_even_q[idx] <= 8'h0;
                l_odd_q[idx] <= 8'h0;
                omega_q[idx] <= 8'h0;
            end
        end else if (start) begin
            active <= 1'b1;
            done <= 1'b0;
            // Cycle 1: Capture parallel evaluations
            for (idx = 0; idx < 128; idx = idx + 1) begin
                l_even_q[idx] <= l_even_eval[idx];
                l_odd_q[idx]  <= l_odd_eval[idx];
                omega_q[idx]  <= omega_eval[idx];
            end
        end else if (active) begin
            active <= 1'b0;
            done <= 1'b1;
            // Cycle 2: Parallel Magnitude calculation and Root check
            for (idx = 0; idx < 128; idx = idx + 1) begin
                // Root check: Lambda(x) = L_even(x) + L_odd(x) == 0
                // Forney Algorithm: e_i = Omega(x) / (x * Lambda'(x))
                // In GF(2), x * Lambda'(x) = sum_{k odd} L_k * x^k = Lambda_odd(x)
                // So e_i = Omega(x) / Lambda_odd(x)
                if ((l_even_q[idx] == l_odd_q[idx]) && (l_odd_q[idx] != 8'h0)) begin
                    error_mask[idx] <= 1'b1;
                    error_magnitudes[idx*8 +: 8] <= gf_mul(omega_q[idx], gf_inv(l_odd_q[idx]));
                end else begin
                    error_mask[idx] <= 1'b0;
                    error_magnitudes[idx*8 +: 8] <= 8'h00;
                end
            end
        end else begin
            done <= 1'b0;
        end
    end

endmodule
