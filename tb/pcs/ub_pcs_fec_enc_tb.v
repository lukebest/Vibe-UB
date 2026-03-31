module ub_pcs_fec_enc_tb;
    reg clk, rst_n, valid_in;
    reg [120*8-1:0] msg_in;
    wire [128*8-1:0] cw_out;
    wire valid_out;

    ub_pcs_fec_enc uut (
        .clk(clk), .rst_n(rst_n),
        .msg_in(msg_in), .valid_in(valid_in),
        .cw_out(cw_out), .valid_out(valid_out)
    );

    always #5 clk = ~clk;

    initial begin
        $dumpfile("ub_pcs_fec_enc_tb.vcd");
        $dumpvars(0, ub_pcs_fec_enc_tb);
        clk = 0; rst_n = 0; valid_in = 0; msg_in = 0;
        #20 rst_n = 1;
        #10;
        @(posedge clk);
        #1 valid_in = 1; msg_in = {120{8'h55}};
        @(posedge clk);
        #1 valid_in = 0;
        
        @(posedge clk);
        if (valid_out) begin
            $display("Codeword Output: %h", cw_out);
            $display("Parity Symbols: %h", cw_out[63:0]);
        end else begin
            #1; // Try one more small delay
            if (valid_out) begin
                $display("Codeword Output: %h", cw_out);
                $display("Parity Symbols: %h", cw_out[63:0]);
            end else begin
                $display("Error: valid_out not asserted.");
            end
        end
        
        #100 $finish;
    end
endmodule
