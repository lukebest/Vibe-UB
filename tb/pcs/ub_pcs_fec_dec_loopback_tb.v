`timescale 1ns / 1ps

module ub_pcs_fec_dec_loopback_tb;
    reg clk, rst_n, valid_in;
    reg [120*8-1:0] msg_in;
    wire [128*8-1:0] cw_enc;
    wire valid_enc;

    reg [128*8-1:0] cw_corrupted;
    reg valid_dec_in;
    wire [120*8-1:0] msg_out;
    wire valid_out;
    wire fec_fail;

    ub_pcs_fec_enc u_enc (
        .clk(clk), .rst_n(rst_n),
        .msg_in(msg_in), .valid_in(valid_in),
        .cw_out(cw_enc), .valid_out(valid_enc)
    );

    ub_pcs_fec_dec u_dec (
        .clk(clk), .rst_n(rst_n),
        .cw_in(cw_corrupted), .valid_in(valid_dec_in),
        .msg_out(msg_out), .valid_out(valid_out),
        .fec_fail(fec_fail)
    );

    always #5 clk = ~clk;

    integer i, j;
    reg [7:0] error_val;
    integer error_pos [0:7];
    integer num_errors;

    initial begin
        $dumpfile("ub_pcs_fec_dec_loopback_tb.vcd");
        $dumpvars(0, ub_pcs_fec_dec_loopback_tb);
        clk = 0; rst_n = 0; valid_in = 0; msg_in = 0;
        cw_corrupted = 0; valid_dec_in = 0;
        #20 rst_n = 1;
        #10;

        for (num_errors = 0; num_errors <= 4; num_errors = num_errors + 1) begin
            $display("--- Testing with %0d errors ---", num_errors);
            @(posedge clk);
            #1;
            msg_in = 0;
            for (i=0; i<120; i=i+1) msg_in[i*8 +: 8] = $urandom_range(0, 255);
            valid_in = 1;
            @(posedge clk);
            #1 valid_in = 0;

            // Wait for encoder output
            while (!valid_enc) @(posedge clk);
            #1 cw_corrupted = cw_enc;

            // Inject errors
            if (num_errors > 0) begin
                for (i=0; i < num_errors; i=i+1) begin
                    error_pos[i] = $urandom_range(0, 127);
                    // Ensure unique positions for this test
                    for (j=0; j < i; j=j+1) begin
                        if (error_pos[i] == error_pos[j]) begin
                            error_pos[i] = (error_pos[i] + 1) % 128;
                            j = -1; // Restart inner loop
                        end
                    end
                    error_val = $urandom_range(1, 255);
                    cw_corrupted[error_pos[i]*8 +: 8] = cw_corrupted[error_pos[i]*8 +: 8] ^ error_val;
                    $display("Injecting error at byte %0d", error_pos[i]);
                end
            end

            valid_dec_in = 1;
            @(posedge clk);
            #1 valid_dec_in = 0;

            // Wait for decoder output
            while (!valid_out) @(posedge clk);
            
            if (msg_out === msg_in) begin
                $display("SUCCESS: Message corrected correctly for %0d errors.", num_errors);
            end else begin
                $display("FAILURE: Message mismatch for %0d errors!", num_errors);
                $display("Original:  %h", msg_in);
                $display("Corrected: %h", msg_out);
                for (i=0; i<120; i=i+1) begin
                    if (msg_out[i*8 +: 8] !== msg_in[i*8 +: 8]) begin
                         $display("Byte %0d mismatch: expected %h, got %h", i, msg_in[i*8 +: 8], msg_out[i*8 +: 8]);
                    end
                end
                // $finish;
            end
            if (fec_fail) $display("Note: fec_fail asserted.");
            #50;
        end

        $display("--- All integrated tests complete ---");
        #100 $finish;
    end
endmodule
