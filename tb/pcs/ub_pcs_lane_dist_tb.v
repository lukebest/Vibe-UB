module ub_pcs_lane_dist_tb;
    reg [127:0] data_in; // 64 PAM4 symbols
    wire [31:0] lane0, lane1, lane2, lane3;
    ub_pcs_lane_dist uut (
        .data_in(data_in),
        .lane0(lane0), .lane1(lane1), .lane2(lane2), .lane3(lane3)
    );
    initial begin
        data_in = 128'h0123456789ABCDEF0123456789ABCDEF;
        #10;
        $display("Lane 0: %h", lane0);
        $display("Lane 1: %h", lane1);
        $display("Lane 2: %h", lane2);
        $display("Lane 3: %h", lane3);
        $finish;
    end
endmodule
