module ub_pcs_scrambler (
    input clk, rst_n,
    input [159:0] data_in,
    input valid_in,
    output reg [159:0] data_out,
    output reg valid_out
);
    reg [57:0] lfsr; // Example 58-bit scrambler for high-speed protocols
    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lfsr <= 58'h3FFFFFFFFFFFFFF;
            data_out <= 0;
            valid_out <= 0;
        end else if (valid_in) begin
            for (i = 0; i < 160; i = i + 1) begin
                data_out[i] <= data_in[i] ^ lfsr[57];
                lfsr <= {lfsr[56:0], lfsr[57] ^ lfsr[38]}; // x^58 + x^39 + 1
            end
            valid_out <= 1;
        end else begin
            valid_out <= 0;
        end
    end
endmodule
