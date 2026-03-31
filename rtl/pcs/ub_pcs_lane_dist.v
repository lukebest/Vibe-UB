module ub_pcs_lane_dist (
    input [127:0] data_in,
    output [31:0] lane0, lane1, lane2, lane3
);
    integer i;
    genvar g;
    generate
        for (g = 0; g < 16; g = g + 1) begin
            assign lane0[g*2 +: 2] = data_in[(g*4+0)*2 +: 2];
            assign lane1[g*2 +: 2] = data_in[(g*4+1)*2 +: 2];
            assign lane2[g*2 +: 2] = data_in[(g*4+2)*2 +: 2];
            assign lane3[g*2 +: 2] = data_in[(g*4+3)*2 +: 2];
        end
    endgenerate
endmodule
