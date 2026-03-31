module ub_pcs_lane_dedist (
    input [31:0] lane0, lane1, lane2, lane3,
    output [127:0] data_out
);
    genvar g;
    generate
        for (g = 0; g < 16; g = g + 1) begin
            assign data_out[(g*4+0)*2 +: 2] = lane0[g*2 +: 2];
            assign data_out[(g*4+1)*2 +: 2] = lane1[g*2 +: 2];
            assign data_out[(g*4+2)*2 +: 2] = lane2[g*2 +: 2];
            assign data_out[(g*4+3)*2 +: 2] = lane3[g*2 +: 2];
        end
    endgenerate
endmodule
