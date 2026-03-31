module ub_pcs_lane_dedist_tb;
    reg [31:0] lane0, lane1, lane2, lane3;
    wire [127:0] data_out;
    ub_pcs_lane_dedist uut (
        .lane0(lane0), .lane1(lane1), .lane2(lane2), .lane3(lane3),
        .data_out(data_out)
    );
    initial begin
        lane0 = 32'h01234567;
        lane1 = 32'h89ABCDEF;
        lane2 = 32'h01234567;
        lane3 = 32'h89ABCDEF;
        #10;
        $display("lane0: %h, lane1: %h, lane2: %h, lane3: %h", lane0, lane1, lane2, lane3);
        $display("data_out: %h", data_out);
        $finish;
    end
endmodule
