module ub_dll_segmenter (
    input clk, rst_n,
    input [159:0] net_data,
    input net_valid, net_sop, net_eop,
    output net_ready,
    output reg [159:0] flit_out,
    output reg flit_valid
);
    assign net_ready = 1; // Always ready for now

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            flit_out <= 0;
            flit_valid <= 0;
        end else if (net_valid) begin
            if (net_sop) begin
                // Insert LPH (4 bytes) at MSB of first flit
                flit_out <= {32'h80000000, net_data[127:0]}; // CRD=1, VL=0
            end else begin
                flit_out <= net_data;
            end
            flit_valid <= 1;
        end else begin
            flit_valid <= 0;
        end
    end
endmodule
