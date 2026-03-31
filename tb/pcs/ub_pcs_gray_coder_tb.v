module ub_pcs_gray_coder_tb;
    reg [1:0] bits;
    wire [1:0] symbols;
    ub_pcs_gray_coder uut (.bits(bits), .symbols(symbols));
    initial begin
        $monitor("bits=%b symbols=%b", bits, symbols);
        bits = 2'b00; #10; // Expected 00
        bits = 2'b01; #10; // Expected 01
        bits = 2'b11; #10; #10; // Expected 10
        bits = 2'b10; #10; // Expected 11
        $finish;
    end
endmodule
