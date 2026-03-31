module ub_dll_crc_check_tb;
    reg clk, rst_n, valid_in;
    reg [159:0] data_in;
    reg [31:0] expected_crc;
    wire crc_pass;

    ub_dll_crc_check uut (
        .clk(clk), .rst_n(rst_n),
        .data_in(data_in), .expected_crc(expected_crc), .valid_in(valid_in),
        .crc_pass(crc_pass)
    );

    always #5 clk = ~clk;
    initial begin
        clk = 0; rst_n = 0; valid_in = 0; data_in = 0; expected_crc = 0;
        #20 rst_n = 1;
        #10 valid_in = 1; data_in = 160'hAAAA; expected_crc = 32'hAAAA;
        #10 valid_in = 0;
        #50 $finish;
    end
endmodule
