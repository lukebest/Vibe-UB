`timescale 1ns/1ps

module ub_controller_rx_tb;
    reg clk, rst_n;
    
    // TX Interface
    reg [159:0] tx_net_data;
    reg tx_net_valid, tx_net_sop, tx_net_eop;
    wire tx_net_ready;
    wire [31:0] lane0, lane1, lane2, lane3;
    wire lane_valid;

    // RX Interface
    wire [159:0] rx_net_data;
    wire rx_net_valid, rx_net_sop, rx_net_eop;
    reg rx_net_ready;
    wire fec_fail, crc_pass;

    // Instantiate TX
    ub_controller_tx u_tx (
        .clk(clk), .rst_n(rst_n),
        .net_data(tx_net_data), .net_valid(tx_net_valid),
        .net_sop(tx_net_sop), .net_eop(tx_net_eop),
        .net_ready(tx_net_ready),
        .lane0(lane0), .lane1(lane1), .lane2(lane2), .lane3(lane3),
        .lane_valid(lane_valid)
    );

    // Instantiate RX (Loopback lanes from TX)
    ub_controller_rx uut (
        .clk(clk), .rst_n(rst_n),
        .lane0(lane0), .lane1(lane1), .lane2(lane2), .lane3(lane3),
        .lane_valid(lane_valid),
        .net_data(rx_net_data), .net_valid(rx_net_valid),
        .net_sop(rx_net_sop), .net_eop(rx_net_eop),
        .net_ready(rx_net_ready),
        .fec_fail(fec_fail), .crc_pass(crc_pass)
    );

    always #5 clk = ~clk;

    integer i;
    reg [159:0] sent_flits [0:5];
    reg [159:0] received_flits [0:5];
    integer rx_cnt;

    initial begin
        $dumpfile("ub_controller_rx_tb.vcd");
        $dumpvars(0, ub_controller_rx_tb);

        clk = 0; rst_n = 0;
        tx_net_data = 0; tx_net_valid = 0; tx_net_sop = 0; tx_net_eop = 0;
        rx_net_ready = 1;
        rx_cnt = 0;

        #25; rst_n = 1; #20;

        // Send a packet of 6 flits to fill one FEC codeword
        $display("--- Sending 6 flits ---");
        for (i = 0; i < 6; i = i + 1) begin
            @(posedge clk);
            tx_net_valid <= 1;
            tx_net_sop <= (i == 0);
            tx_net_eop <= (i == 5);
            tx_net_data <= {32'h80000000, 128'h0123456789ABCDEF0123456789ABCDEF} ^ {160{i[3:0]}};
            sent_flits[i] = {32'h80000000, 128'h0123456789ABCDEF0123456789ABCDEF} ^ {160{i[3:0]}};
        end
        @(posedge clk);
        tx_net_valid <= 0;
        tx_net_sop <= 0;
        tx_net_eop <= 0;

        // Wait for RX to receive 6 flits
        $display("--- Waiting for RX flits ---");
        fork
            begin
                while (rx_cnt < 6) begin
                    @(posedge clk);
                    if (rx_net_valid) begin
                        received_flits[rx_cnt] = rx_net_data;
                        $display("RX Flit %0d: %h (SOP=%b, EOP=%b)", rx_cnt, rx_net_data, rx_net_sop, rx_net_eop);
                        rx_cnt = rx_cnt + 1;
                    end
                end
            end
            begin
                #1000;
                if (rx_cnt < 6) begin
                    $display("Error: Timeout waiting for RX flits (received %0d/6)", rx_cnt);
                    $finish;
                end
            end
        join

        // Verify data
        for (i = 0; i < 6; i = i + 1) begin
            // Note: The reassembler might modify the data (e.g., net_sop logic).
            // Our reassembler placeholder logic: if (flit_in[159:152] == 8'h80) net_data <= {32'h0, flit_in[127:0]};
            // My sent flits have 8'h80 at [159:152].
            if (received_flits[i][127:0] !== sent_flits[i][127:0]) begin
                $display("Error: Flit %0d data mismatch!", i);
                $display("Sent: %h", sent_flits[i][127:0]);
                $display("Rcvd: %h", received_flits[i][127:0]);
                $finish;
            end
        end

        $display("Success: All flits received correctly in loopback!");
        $display("Simulation complete");
        $finish;
    end

endmodule
