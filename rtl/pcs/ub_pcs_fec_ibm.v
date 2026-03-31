`timescale 1ns / 1ps

module ub_pcs_fec_ibm (
    input clk,
    input rst_n,
    input [63:0] syndromes, // {S7, S6, S5, S4, S3, S2, S1, S0}
    input start,
    output reg done,
    output [39:0] lambda,   // {L4, L3, L2, L1, L0}
    output [31:0] omega     // {O3, O2, O1, O0}
);

    `include "ub_gf_math.vh"

    reg [7:0] s [0:7];
    reg [7:0] L [0:4];
    reg [7:0] B [0:4];
    reg [7:0] delta;
    reg [3:0] l_cnt;
    reg [1:0] cycle_cnt;
    reg active;

    assign lambda = {L[4], L[3], L[2], L[1], L[0]};

    // Omega(x) = Lambda(x) * S(x) mod x^4 (we only need degree 0 to 3)
    // Omega0 = L0*S0
    // Omega1 = L0*S1 + L1*S0
    // Omega2 = L0*S2 + L1*S1 + L2*S0
    // Omega3 = L0*S3 + L1*S2 + L2*S1 + L3*S0
    assign omega = {
        gf_mul(L[0], s[3]) ^ gf_mul(L[1], s[2]) ^ gf_mul(L[2], s[1]) ^ gf_mul(L[3], s[0]),
        gf_mul(L[0], s[2]) ^ gf_mul(L[1], s[1]) ^ gf_mul(L[2], s[0]),
        gf_mul(L[0], s[1]) ^ gf_mul(L[1], s[0]),
        gf_mul(L[0], s[0])
    };

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            done <= 1'b0;
            cycle_cnt <= 2'b0;
            for (i=0; i<5; i=i+1) begin
                L[i] <= 8'h0;
                B[i] <= 8'h0;
            end
            delta <= 8'h01;
            l_cnt <= 4'h0;
            for (i=0; i<8; i=i+1) s[i] <= 8'h0;
        end else if (start) begin
            active <= 1'b1;
            done <= 1'b0;
            cycle_cnt <= 2'b0;
            s[0] <= syndromes[7:0];
            s[1] <= syndromes[15:8];
            s[2] <= syndromes[23:16];
            s[3] <= syndromes[31:24];
            s[4] <= syndromes[39:32];
            s[5] <= syndromes[47:40];
            s[6] <= syndromes[55:48];
            s[7] <= syndromes[63:56];
            
            L[0] <= 8'h01; L[1] <= 8'h0; L[2] <= 8'h0; L[3] <= 8'h0; L[4] <= 8'h0;
            B[0] <= 8'h01; B[1] <= 8'h0; B[2] <= 8'h0; B[3] <= 8'h0; B[4] <= 8'h0;
            delta <= 8'h01;
            l_cnt <= 4'h0;
        end else if (active) begin
            // Using blocking assignments for internal combinatorial logic within the cycle
            reg [7:0] cur_L [0:4];
            reg [7:0] cur_B [0:4];
            reg [7:0] cur_delta;
            reg [3:0] cur_l_cnt;
            reg [7:0] d1, d2;
            reg [7:0] n1_L [0:4], n1_B [0:4], n1_delta;
            reg [3:0] n1_l_cnt;
            reg [7:0] n2_L [0:4], n2_B [0:4], n2_delta;
            reg [3:0] n2_l_cnt;
            integer j;

            for (j=0; j<5; j=j+1) begin
                cur_L[j] = L[j];
                cur_B[j] = B[j];
            end
            cur_delta = delta;
            cur_l_cnt = l_cnt;

            // Iteration A: r = cycle_cnt*2 + 1
            d1 = 8'h0;
            for (j=0; j<5; j=j+1) begin
                if (cycle_cnt*2 >= j)
                    d1 = d1 ^ gf_mul(cur_L[j], s[cycle_cnt*2-j]);
            end
            
            for (j=0; j<5; j=j+1) begin
                n1_L[j] = gf_mul(cur_delta, cur_L[j]) ^ gf_mul(d1, (j==0) ? 8'h0 : cur_B[j-1]);
            end
            if (d1 != 8'h0 && (cur_l_cnt * 2 < (cycle_cnt*2 + 1))) begin
                for (j=0; j<5; j=j+1) n1_B[j] = cur_L[j];
                n1_delta = d1;
                n1_l_cnt = (cycle_cnt*2 + 1) - cur_l_cnt;
            end else begin
                for (j=0; j<5; j=j+1) n1_B[j] = (j==0) ? 8'h0 : cur_B[j-1];
                n1_delta = cur_delta;
                n1_l_cnt = cur_l_cnt;
            end

            // Iteration B: r = cycle_cnt*2 + 2
            d2 = 8'h0;
            for (j=0; j<5; j=j+1) begin
                if (cycle_cnt*2 + 1 >= j)
                    d2 = d2 ^ gf_mul(n1_L[j], s[cycle_cnt*2+1-j]);
            end
            
            for (j=0; j<5; j=j+1) begin
                n2_L[j] = gf_mul(n1_delta, n1_L[j]) ^ gf_mul(d2, (j==0) ? 8'h0 : n1_B[j-1]);
            end
            if (d2 != 8'h0 && (n1_l_cnt * 2 < (cycle_cnt*2 + 2))) begin
                for (j=0; j<5; j=j+1) n2_B[j] = n1_L[j];
                n2_delta = d2;
                n2_l_cnt = (cycle_cnt*2 + 2) - n1_l_cnt;
            end else begin
                for (j=0; j<5; j=j+1) n2_B[j] = (j==0) ? 8'h0 : n1_B[j-1];
                n2_delta = n1_delta;
                n2_l_cnt = n1_l_cnt;
            end

            // Final state update for this cycle
            for (j=0; j<5; j=j+1) begin
                L[j] <= n2_L[j];
                B[j] <= n2_B[j];
            end
            delta <= n2_delta;
            l_cnt <= n2_l_cnt;

            if (cycle_cnt == 2'd3) begin
                active <= 1'b0;
                done <= 1'b1;
            end else begin
                cycle_cnt <= cycle_cnt + 2'd1;
            end
        end else begin
            done <= 1'b0;
        end
    end

endmodule
