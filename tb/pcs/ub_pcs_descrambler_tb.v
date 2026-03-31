module ub_pcs_descrambler_tb;
    reg clk, rst_n, valid_in;
    reg [159:0] data_in;
    wire [159:0] data_out;
    wire valid_out;

    ub_pcs_descrambler uut (
        .clk(clk), .rst_n(rst_n),
        .data_in(data_in), .valid_in(valid_in),
        .data_out(data_out), .valid_out(valid_out)
    );

    always #5 clk = ~clk;
    initial begin
        $monitor("Time=%0t valid_in=%b data_in=%h valid_out=%b data_out=%h", $time, valid_in, data_in, valid_out, data_out);
        clk = 0; rst_n = 0; valid_in = 0; data_in = 0;
        #20 rst_n = 1;
        #10 valid_in = 1; data_in = 160'hAAAA; // Scrambled data
        #10 valid_in = 0;
        #50 $finish;
    end
endmodule
