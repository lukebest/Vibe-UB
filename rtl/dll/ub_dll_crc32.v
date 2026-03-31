module ub_dll_crc32 (
    input clk, rst_n,
    input [159:0] data_in,
    input data_valid,
    output reg [31:0] crc_out
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

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) 
            crc_out <= 32'hFFFFFFFF;
        else if (data_valid) 
            crc_out <= next_crc32(crc_out, data_in);
    end
endmodule
