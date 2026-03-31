module ub_pcs_gray_decoder_tb;
    reg [1:0] symbols;
    wire [1:0] bits;
    ub_pcs_gray_decoder uut (.symbols(symbols), .bits(bits));
    initial begin
        $display("Testing Gray Decoder...");
        symbols = 2'b00; #10; $display("symbols: %b, bits: %b (Expected: 00)", symbols, bits);
        symbols = 2'b01; #10; $display("symbols: %b, bits: %b (Expected: 01)", symbols, bits);
        symbols = 2'b10; #10; $display("symbols: %b, bits: %b (Expected: 11)", symbols, bits);
        symbols = 2'b11; #10; $display("symbols: %b, bits: %b (Expected: 10)", symbols, bits);
        $finish;
    end
endmodule
