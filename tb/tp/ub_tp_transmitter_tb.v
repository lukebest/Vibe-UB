module ub_tp_transmitter_tb;

    reg clk, rst_n;

    // TA Layer Interface
    reg  [159:0] ta_data;
    reg        ta_valid, ta_sop, ta_eop;
    wire       ta_ready;

    // NL Layer Interface
    wire [159:0] tp_tx_data;
    wire       tp_tx_valid, tp_tx_sop, tp_tx_eop;
    reg        tp_tx_ready;

    // Feedback Interface
    reg  [23:0] tp_ack_psn;
    reg        tp_ack_valid;
    reg  [23:0] tp_nak_psn;
    reg        tp_nak_valid;

    // Status
    wire [23:0] tp_tx_psn;
    wire       tp_tx_busy;

    // Instantiate DUT
    ub_tp_transmitter #(
        .PSN_BITS(24),
        .RETRANSMIT_DEPTH(32),
        .MAX_RETRIES(3)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .ta_data(ta_data),
        .ta_valid(ta_valid),
        .ta_sop(ta_sop),
        .ta_eop(ta_eop),
        .ta_ready(ta_ready),
        .tp_tx_data(tp_tx_data),
        .tp_tx_valid(tp_tx_valid),
        .tp_tx_sop(tp_tx_sop),
        .tp_tx_eop(tp_tx_eop),
        .tp_tx_ready(tp_tx_ready),
        .tp_ack_psn(tp_ack_psn),
        .tp_ack_valid(tp_ack_valid),
        .tp_nak_psn(tp_nak_psn),
        .tp_nak_valid(tp_nak_valid),
        .tp_tx_psn(tp_tx_psn),
        .tp_tx_busy(tp_tx_busy)
    );

    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Test sequence
    initial begin
        $dumpfile("ub_tp_transmitter_tb.vcd");
        $dumpvars(0, ub_tp_transmitter_tb);

        // Initialize
        rst_n = 0;
        ta_data = 0;
        ta_valid = 0;
        ta_sop = 0;
        ta_eop = 0;
        tp_tx_ready = 1;
        tp_ack_psn = 0;
        tp_ack_valid = 0;
        tp_nak_psn = 0;
        tp_nak_valid = 0;

        #20;
        rst_n = 1;
        #20;

        $display("========================================");
        $display("Test 1: Basic packet transmission");
        $display("========================================");

        // Send first packet
        @(posedge clk);
        ta_data = 160'h123456789ABCDEF0123456789ABCDEF;
        ta_sop = 1;
        ta_eop = 1;
        ta_valid = 1;

        @(posedge clk);
        while (!ta_ready) @(posedge clk);
        ta_valid = 0;
        ta_sop = 0;
        ta_eop = 0;

        // Wait for transmission
        repeat(10) @(posedge clk);

        $display("========================================");
        $display("Test 2: Multiple packets");
        $display("========================================");

        // Send second packet
        @(posedge clk);
        ta_data = 160'hFEDCBA9876543210FEDCBA9876543210;
        ta_sop = 1;
        ta_eop = 1;
        ta_valid = 1;

        @(posedge clk);
        while (!ta_ready) @(posedge clk);
        ta_valid = 0;
        ta_sop = 0;
        ta_eop = 0;

        repeat(10) @(posedge clk);

        $display("========================================");
        $display("Test 3: ACK processing");
        $display("========================================");

        // Send ACK for PSN 0
        @(posedge clk);
        tp_ack_psn = 24'h000000;
        tp_ack_valid = 1;
        @(posedge clk);
        tp_ack_valid = 0;

        repeat(10) @(posedge clk);

        $display("========================================");
        $display("Test completed!");
        $display("========================================");
        $finish;
    end

    // Monitor outputs
    always @(posedge clk) begin
        if (tp_tx_valid) begin
            $display("Time=%0t: TP TX Data=%h, PSN=%h, SOP=%b, EOP=%b",
                     $time, tp_tx_data, tp_tx_data[23:0], tp_tx_sop, tp_tx_eop);
        end
    end

endmodule

