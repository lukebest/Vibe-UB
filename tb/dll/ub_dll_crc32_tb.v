module ub_dll_crc32_tb;
    reg clk, rst_n, data_valid;
    reg [159:0] data_in;
    wire [31:0] crc_out;
    ub_dll_crc32 uut (
        .clk(clk), .rst_n(rst_n),
        .data_in(data_in), .data_valid(data_valid),
        .crc_out(crc_out)
    );
    always #5 clk = ~clk;
    initial begin
        clk = 0; rst_n = 0; data_valid = 0; data_in = 0;
        #20 rst_n = 1;
        #10 data_valid = 1; data_in = 160'h123456789ABCDEF0123456789ABCDEF012345678;
        #10 data_valid = 0;
        #50 $finish;
    end
endmodule
