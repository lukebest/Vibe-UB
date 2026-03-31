`timescale 1ns/1ps

module ub_controller_tx_tb;
    reg clk, rst_n;
    reg [159:0] net_data;
    reg net_valid, net_sop, net_eop;
    wire net_ready;
    wire [31:0] lane0, lane1, lane2, lane3;
    wire lane_valid;

    ub_controller_tx uut (
        .clk(clk),
        .rst_n(rst_n),
        .net_data(net_data),
        .net_valid(net_valid),
        .net_sop(net_sop),
        .net_eop(net_eop),
        .net_ready(net_ready),
        .lane0(lane0),
        .lane1(lane1),
        .lane2(lane2),
        .lane3(lane3),
        .lane_valid(lane_valid)
    );

    always #5 clk = ~clk;

    integer i;
    initial begin
        $dumpfile("ub_controller_tx_tb.vcd");
        $dumpvars(0, ub_controller_tx_tb);

        clk = 0;
        rst_n = 0;
        net_data = 0;
        net_valid = 0;
        net_sop = 0;
        net_eop = 0;

        #25;
        rst_n = 1;
        #20;

        // Send a packet of 6 flits to fill exactly one FEC codeword (6 * 160 = 960 bits)
        for (i = 0; i < 6; i = i + 1) begin
            @(posedge clk);
            net_valid <= 1;
            net_sop <= (i == 0);
            net_eop <= (i == 5);
            net_data <= {128'h0123456789ABCDEF0123456789ABCDEF, 32'hA5A5A5A5} ^ {160{i[0]}};
        end
        @(posedge clk);
        net_valid <= 0;
        net_sop <= 0;
        net_eop <= 0;

        // Wait for the processing pipeline and lane distribution
        begin : wait_loop
            for (i = 0; i < 100; i = i + 1) begin
                @(posedge clk);
                if (lane_valid) begin
                    $display("Success: lane_valid detected");
                    disable wait_loop;
                end
            end
            $display("Failure: lane_valid timeout");
            $finish;
        end

        // Wait for distribution to finish
        while (lane_valid) @(posedge clk);
        #10;

        $display("Simulation complete");
        $finish;
    end

    // Monitor lane outputs when valid
    always @(posedge clk) begin
        if (lane_valid) begin
            $display("Lanes: L0=%h, L1=%h, L2=%h, L3=%h", lane0, lane1, lane2, lane3);
        end
    end

endmodule
