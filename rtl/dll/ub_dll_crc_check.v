module ub_dll_crc_check (
    input clk, rst_n,
    input [159:0] data_in,
    input [31:0] expected_crc,
    input valid_in,
    output reg crc_pass
);
    // Standard CRC-32 (Ethernet polynomial: 0x04C11DB7)
    function [31:0] next_crc32;
        input [31:0] current_crc;
        input [159:0] data;
        integer i;
        reg [31:0] crc;
        begin
            crc = current_crc;
            for (i = 159; i >= 0; i = i - 1) begin
                if (crc[31] ^ data[i])
                    crc = (crc << 1) ^ 32'h04C11DB7;
                else
                    crc = (crc << 1);
            end
            next_crc32 = crc;
        end
    endfunction

    reg [31:0] running_crc;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running_crc <= 32'hFFFFFFFF;
            crc_pass <= 0;
        end else if (valid_in) begin
            running_crc <= next_crc32(running_crc, data_in);
            crc_pass <= (next_crc32(running_crc, data_in) == expected_crc);
        end
    end
endmodule
