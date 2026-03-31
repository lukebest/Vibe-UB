module ub_dll_reassembler_tb;
    reg clk, rst_n, flit_valid;
    reg [159:0] flit_in;
    wire [159:0] net_data;
    wire net_valid, net_sop, net_eop;

    ub_dll_reassembler uut (
        .clk(clk), .rst_n(rst_n),
        .flit_in(flit_in), .flit_valid(flit_valid),
        .net_data(net_data), .net_valid(net_valid), .net_sop(net_sop), .net_eop(net_eop),
        .net_ready(1'b1)
    );

    always #5 clk = ~clk;
    initial begin
        $monitor("T=%0t flit_in=%h valid=%b sop=%b eop=%b data=%h", $time, flit_in, net_valid, net_sop, net_eop, net_data);
        clk = 0; rst_n = 0; flit_valid = 0; flit_in = 0;
        #20 rst_n = 1;
        #10 flit_valid = 1; flit_in = {8'h80, 152'h0}; // CRD bit set in first byte
        #10 flit_valid = 1; flit_in = 160'hBBBB;
        #10 flit_valid = 0;
        #50 $finish;
    end
endmodule
