module ub_pcs_fec_enc (
    input clk, rst_n,
    input [120*8-1:0] msg_in,
    input valid_in,
    output reg [128*8-1:0] cw_out,
    output reg valid_out
);
    `include "ub_gf_math.vh"
    // RS(128,120) generator coefficients (decimal): 24, 200, 173, 239, 54, 81, 11, 255, 1
    // g0=24, g1=200, g2=173, g3=239, g4=54, g5=81, g6=11, g7=255, g8=1

    function automatic [63:0] calculate_parity;
        input [120*8-1:0] msg;
        reg [7:0] r [0:7];
        reg [7:0] in_val;
        integer i, j;
        begin
            for (j = 0; j < 8; j = j + 1) r[j] = 8'h00;
            
            for (i = 119; i >= 0; i = i - 1) begin
                in_val = msg[i*8 +: 8] ^ r[7];
                r[7] = r[6] ^ gf_mul(in_val, 8'd255); // g7
                r[6] = r[5] ^ gf_mul(in_val, 8'd11);  // g6
                r[5] = r[4] ^ gf_mul(in_val, 8'd81);  // g5
                r[4] = r[3] ^ gf_mul(in_val, 8'd54);  // g4
                r[3] = r[2] ^ gf_mul(in_val, 8'd239); // g3
                r[2] = r[1] ^ gf_mul(in_val, 8'd173); // g2
                r[1] = r[0] ^ gf_mul(in_val, 8'd200); // g1
                r[0] = gf_mul(in_val, 8'd24);         // g0
            end
            
            calculate_parity = {r[7], r[6], r[5], r[4], r[3], r[2], r[1], r[0]};
        end
    endfunction

    wire [63:0] parity_comb;
    assign parity_comb = calculate_parity(msg_in);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cw_out <= 0;
            valid_out <= 0;
        end else if (valid_in) begin
            cw_out <= {msg_in, parity_comb};
            valid_out <= 1;
        end else begin
            valid_out <= 0;
        end
    end
endmodule
