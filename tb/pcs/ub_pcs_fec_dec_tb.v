module ub_pcs_fec_dec_tb;
    reg clk, rst_n, valid_in;
    reg [128*8-1:0] cw_in;
    wire [120*8-1:0] msg_out;
    wire valid_out, fec_fail;

    ub_pcs_fec_dec uut (
        .clk(clk), .rst_n(rst_n),
        .cw_in(cw_in), .valid_in(valid_in),
        .msg_out(msg_out), .valid_out(valid_out), .fec_fail(fec_fail)
    );

    // Encoder for generating valid codewords
    reg enc_valid_in;
    reg [120*8-1:0] enc_msg_in;
    wire [128*8-1:0] enc_cw_out;
    wire enc_valid_out;

    ub_pcs_fec_enc u_enc (
        .clk(clk), .rst_n(rst_n),
        .msg_in(enc_msg_in), .valid_in(enc_valid_in),
        .cw_out(enc_cw_out), .valid_out(enc_valid_out)
    );

    always #5 clk = ~clk;

    reg [128*8-1:0] stored_cw;
    reg cw_valid;

    initial begin
        $dumpfile("ub_pcs_fec_dec_tb.vcd");
        $dumpvars(0, ub_pcs_fec_dec_tb);
        clk = 0; rst_n = 0; valid_in = 0; cw_in = 0;
        enc_valid_in = 0; enc_msg_in = 0;
        stored_cw = 0; cw_valid = 0;
        
        #20 rst_n = 1;
        #10;
        
        // Test 1: All zeros codeword (valid)
        @(posedge clk);
        #1 valid_in = 1; cw_in = 0;
        @(posedge clk);
        #1 valid_in = 0;
        @(posedge clk);
        if (valid_out) begin
            $display("Test 1: All zeros - fec_fail: %b (Expected: 0)", fec_fail);
            if (fec_fail != 0) $display("ERROR: Test 1 failed");
        end
        
        // Test 2: Generate a valid codeword
        @(posedge clk);
        #1 enc_valid_in = 1; enc_msg_in = {120{8'hA5}};
        @(posedge clk);
        #1 enc_valid_in = 0;
        
        // Wait for encoder output and feed it to decoder
        @(posedge clk);
        while (!enc_valid_out) @(posedge clk);
        
        if (enc_valid_out) begin
            stored_cw = enc_cw_out;
            cw_valid = 1;
            #1 valid_in = 1; cw_in = stored_cw;
            @(posedge clk);
            #1 valid_in = 0;
            @(posedge clk);
            if (valid_out) begin
                $display("Test 2: Valid Codeword - fec_fail: %b (Expected: 0)", fec_fail);
                if (fec_fail != 0) $display("ERROR: Test 2 failed");
            end
        end

        // Test 3: Inject single bit error
        @(posedge clk);
        if (cw_valid) begin
            #1 valid_in = 1; cw_in = stored_cw ^ 1024'h1; // Flip one bit in parity
            @(posedge clk);
            #1 valid_in = 0;
            @(posedge clk);
            if (valid_out) begin
                $display("Test 3: Single bit error - fec_fail: %b (Expected: 1)", fec_fail);
                if (fec_fail != 1) $display("ERROR: Test 3 failed");
            end
        end

        #100 $finish;
    end
endmodule
