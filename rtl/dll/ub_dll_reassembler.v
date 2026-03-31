module ub_dll_reassembler (
    input clk, rst_n,
    input [159:0] flit_in,
    input flit_valid,
    output reg [159:0] net_data,
    output reg net_valid, net_sop, net_eop,
    input net_ready
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            net_data <= 0;
            net_valid <= 0;
            net_sop <= 0;
            net_eop <= 0;
        end else if (flit_valid) begin
            // Placeholder: Assume every flit with LPH is SOP
            if (flit_in[159:152] == 8'h80) begin // Simple check for CRD bit
                net_sop <= 1;
                net_data <= {32'h0, flit_in[127:0]};
            end else begin
                net_sop <= 0;
                net_data <= flit_in;
            end
            net_valid <= 1;
        end else begin
            net_valid <= 0;
        end
    end
endmodule
