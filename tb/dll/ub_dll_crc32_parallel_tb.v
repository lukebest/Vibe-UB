module ub_dll_crc32_parallel_tb;
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
        clk = 0; rst_n = 0; data_valid = 0; data_in = 160'h0;
        #20 rst_n = 1;
        #10 data_valid = 1; data_in = 160'h0123456789ABCDEF0123456789ABCDEF01234567;
        #10 data_valid = 0;
        #20 if (crc_out == 32'h45326075) $display("PASS: CRC matches expected 0x45326075");
        else $display("FAIL: CRC 0x%h != expected 0x45326075", crc_out);
        $finish;
    end
endmodule
