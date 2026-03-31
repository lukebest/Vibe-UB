module ub_pcs_scrambler_tb;
    reg clk, rst_n;
    reg [159:0] data_in;
    reg valid_in;
    wire [159:0] data_out;
    wire valid_out;

    ub_pcs_scrambler uut (
        .clk(clk),
        .rst_n(rst_n),
        .data_in(data_in),
        .valid_in(valid_in),
        .data_out(data_out),
        .valid_out(valid_out)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst_n = 0; valid_in = 0; data_in = 160'h0;
        #20 rst_n = 1;
        #10 valid_in = 1; data_in = 160'hAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA;
        #10 valid_in = 0;
        #50 $finish;
    end
endmodule
