module ub_tp_loopback_tb;

    reg clk, rst_n;

    // TA Layer → TP Transmitter
    reg  [159:0] ta_data;
    reg        ta_valid, ta_sop, ta_eop;
    wire       ta_ready;

    // TP Transmitter → NL Layer (loopback)
    wire [159:0] tp_tx_data;
    wire       tp_tx_valid, tp_tx_sop, tp_tx_eop;
    reg        tp_tx_ready;

    // NL Layer → TP Receiver (loopback)
    reg  [159:0] nl_rx_data;
    reg        nl_rx_valid, nl_rx_sop, nl_rx_eop;
    wire       nl_rx_ready;

    // TP Receiver → TA Layer
    wire [159:0] tp_rx_data;
    wire       tp_rx_valid, tp_rx_sop, tp_rx_eop;
    reg        tp_rx_ready;

    // Feedback: Receiver → Transmitter
    wire [23:0] tp_ack_psn;
    wire       tp_ack_valid;
    wire [23:0] tp_nak_psn;
    wire       tp_nak_valid;

    // Status
    wire [23:0] tp_tx_psn;
    wire       tp_tx_busy;
    wire [23:0] tp_rx_expected_psn;
    wire       tp_rx_drop;
    wire       tp_rx_dup;

    // Instantiate TP Transmitter
    ub_tp_transmitter #(
        .PSN_BITS(24),
        .RETRANSMIT_DEPTH(32),
        .MAX_RETRIES(3)
    ) tx_dut (
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

    // Instantiate TP Receiver
    ub_tp_receiver #(
        .PSN_BITS(24),
        .REORDER_DEPTH(32)
    ) rx_dut (
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

    // Loopback: TP Transmitter → TP Receiver
    always @(posedge clk) begin
        nl_rx_valid <= tp_tx_valid;
        nl_rx_sop <= tp_tx_sop;
        nl_rx_eop <= tp_tx_eop;
        nl_rx_data <= tp_tx_data;
        tp_tx_ready <= nl_rx_ready;
    end

    // Clock generation
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end

    // Test sequence
    integer error_count;
    initial begin
        $dumpfile("ub_tp_loopback_tb.vcd");
        $dumpvars(0, ub_tp_loopback_tb);

        // Initialize
        rst_n = 0;
        ta_data = 0;
        ta_valid = 0;
        ta_sop = 0;
        ta_eop = 0;
        tp_rx_ready = 1;
        error_count = 0;

        #20;
        rst_n = 1;
        #20;

        $display("========================================");
        $display("Loopback Test: Basic transmission");
        $display("========================================");

        // Send packet 1
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

        // Wait for reception
        fork
            begin: wait_rx
                wait(tp_rx_valid);
                $display("Time=%0t: Received packet: %h", $time, tp_rx_data);
                // Verilog doesn't allow part-select on literal constant
                if (tp_rx_data[71:24] != 48'hef0123456789) begin  // bits [71:24] of 160'h123456789ABCDEF0123456789ABCDEF
                    $display("ERROR: Data mismatch! Expected 48'hef0123456789, got %h", tp_rx_data[71:24]);
                    error_count = error_count + 1;
                end
            end
            begin: timeout
                repeat(100) @(posedge clk);
                $display("ERROR: Timeout waiting for packet!");
                error_count = error_count + 1;
            end
        join_any
        disable wait_rx;
        disable timeout;

        repeat(20) @(posedge clk);

        $display("========================================");
        if (error_count == 0) begin
            $display("Test PASSED!");
        end else begin
            $display("Test FAILED with %0d errors!", error_count);
        end
        $display("========================================");
        $finish;
    end

    // Monitor outputs
    always @(posedge clk) begin
        if (tp_tx_valid) begin
            $display("Time=%0t: TX: PSN=%h, Data=%h", $time, tp_tx_psn, tp_tx_data);
        end
        if (tp_rx_valid) begin
            $display("Time=%0t: RX: ExpectedPSN=%h, Data=%h", $time, tp_rx_expected_psn, tp_rx_data);
        end
        if (tp_ack_valid) begin
            $display("Time=%0t: TPACK: PSN=%h", $time, tp_ack_psn);
        end
        if (tp_nak_valid) begin
            $display("Time=%0t: TPNAK: PSN=%h", $time, tp_nak_psn);
        end
    end

endmodule

