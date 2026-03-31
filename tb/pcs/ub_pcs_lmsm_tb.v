module ub_pcs_lmsm_tb;
    reg clk, rst_n, start_train;
    wire [2:0] current_state; // Debug output

    ub_pcs_lmsm uut (
        .clk(clk), .rst_n(rst_n),
        .start_train(start_train),
        .state_dbg(current_state)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst_n = 0; start_train = 0;
        #20 rst_n = 1;
        #10 if (current_state !== 3'd0) $display("FAIL: Not in LINK_IDLE");
        else $display("PASS: In LINK_IDLE");

        // Set start_train
        @(posedge clk);
        start_train <= 1;
        @(posedge clk);
        #1;
        if (current_state !== 3'd1) $display("FAIL: Expected PROBE_WAIT (3'd1), got %d", current_state);
        else $display("PASS: In PROBE_WAIT");
        start_train <= 0;

        // Wait for Discovery
        repeat (10) @(posedge clk);
        #1;
        if (current_state !== 3'd2) $display("FAIL: Expected DISC_ACTIVE (3'd2), got %d", current_state);
        else $display("PASS: In DISC_ACTIVE");

        $finish;
    end
endmodule
