module ub_tp_receiver_tb;

    reg clk, rst_n;

    // NL Layer Interface
    reg  [159:0] nl_rx_data;
    reg        nl_rx_valid, nl_rx_sop, nl_rx_eop;
    wire       nl_rx_ready;

    // TA Layer Interface
    wire [159:0] tp_rx_data;
    wire       tp_rx_valid, tp_rx_sop, tp_rx_eop;
    reg        tp_rx_ready;

    // Feedback Interface
    wire [23:0] tp_ack_psn;
    wire       tp_ack_valid;
    wire [23:0] tp_nak_psn;
    wire       tp_nak_valid;

    // Status
    wire [23:0] tp_rx_expected_psn;
    wire       tp_rx_drop;
    wire       tp_rx_dup;

    // Instantiate DUT
    ub_tp_receiver #(
        .PSN_BITS(24),
        .REORDER_DEPTH(32)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .nl_rx_data(nl_rx_data),
        .nl_rx_valid(nl_rx_valid),
        .nl_rx_sop(nl_rx_sop),
        .nl_rx_eop(nl_rx_eop),
        .nl_rx_ready(nl_rx_ready),
        .tp_rx_data(tp_rx_data),
        .tp_rx_valid(tp_rx_valid),
        .tp_rx_sop(tp_rx_sop),
        .tp_rx_eop(tp_rx_eop),
        .tp_rx_ready(tp_rx_ready),
        .tp_ack_psn(tp_ack_psn),
        .tp_ack_valid(tp_ack_valid),
        .tp_nak_psn(tp_nak_psn),
        .tp_nak_valid(tp_nak_valid),
        .tp_rx_expected_psn(tp_rx_expected_psn),
        .tp_rx_drop(tp_rx_drop),
        .tp_rx_dup(tp_rx_dup)
    );

    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Task to send a TP packet with RTPH
    task send_tp_packet;
        input [23:0] psn;
        input [159:0] data;
        begin
            @(posedge clk);
            // Build RTPH: opcode=0x00, ver=0, padding=0, NLP=0
            nl_rx_data[159:152] = 8'h00;  // TPOpcode
            nl_rx_data[151:150] = 2'b00;  // TPVer
            nl_rx_data[149:148] = 2'b00;  // Padding
            nl_rx_data[147:144] = 4'h0;   // NLP
            nl_rx_data[143:120] = 24'h0;  // SrcTPN
            nl_rx_data[119:96] = 24'h0;   // DstTPN
            nl_rx_data[95:72] = 24'h0;    // Reserved
            nl_rx_data[23:0] = psn;        // PSN
            nl_rx_data[71:24] = data[71:24];  // Payload
            nl_rx_sop = 1;
            nl_rx_eop = 1;
            nl_rx_valid = 1;

            @(posedge clk);
            while (!nl_rx_ready) @(posedge clk);
            nl_rx_valid = 0;
            nl_rx_sop = 0;
            nl_rx_eop = 0;
        end
    endtask

    // Test sequence
    initial begin
        $dumpfile("ub_tp_receiver_tb.vcd");
        $dumpvars(0, ub_tp_receiver_tb);

        // Initialize
        rst_n = 0;
        nl_rx_data = 0;
        nl_rx_valid = 0;
        nl_rx_sop = 0;
        nl_rx_eop = 0;
        tp_rx_ready = 1;

        #20;
        rst_n = 1;
        #20;

        $display("========================================");
        $display("Test 1: In-order packet reception");
        $display("========================================");

        // Send PSN 0
        send_tp_packet(24'h000000, 160'h123456789ABCDEF0123456789ABCDEF);
        repeat(10) @(posedge clk);

        $display("========================================");
        $display("Test 2: Out-of-order packet reception");
        $display("========================================");

        // Send PSN 2 first (out of order)
        send_tp_packet(24'h000002, 160'hFEDCBA9876543210FEDCBA9876543210);
        repeat(10) @(posedge clk);

        // Now send PSN 1
        send_tp_packet(24'h000001, 160'hAAAA5555AAAA5555AAAA5555AAAA5555);
        repeat(10) @(posedge clk);

        $display("========================================");
        $display("Test completed!");
        $display("========================================");
        $finish;
    end

    // Monitor outputs
    always @(posedge clk) begin
        if (tp_rx_valid) begin
            $display("Time=%0t: TP RX Data=%h, Expected PSN=%h, Drop=%b, Dup=%b",
                     $time, tp_rx_data, tp_rx_expected_psn, tp_rx_drop, tp_rx_dup);
        end
        if (tp_ack_valid) begin
            $display("Time=%0t: TPACK PSN=%h", $time, tp_ack_psn);
        end
        if (tp_nak_valid) begin
            $display("Time=%0t: TPNAK PSN=%h", $time, tp_nak_psn);
        end
    end

endmodule

