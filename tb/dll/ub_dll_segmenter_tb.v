module ub_dll_segmenter_tb;
    reg clk, rst_n;
    reg [159:0] net_data;
    reg net_valid, net_sop, net_eop;
    wire net_ready;
    wire [159:0] flit_out;
    wire flit_valid;

    ub_dll_segmenter uut (
        .clk(clk), .rst_n(rst_n),
        .net_data(net_data), .net_valid(net_valid),
        .net_sop(net_sop), .net_eop(net_eop), .net_ready(net_ready),
        .flit_out(flit_out), .flit_valid(flit_valid)
    );

    always #5 clk = ~clk;
    initial begin
        clk = 0; rst_n = 0; net_valid = 0;
        #20 rst_n = 1;
        #10 net_valid = 1; net_sop = 1; net_data = 160'hAAAA;
        #10 net_sop = 0; net_eop = 1;
        #10 net_valid = 0;
        #100 $finish;
    end
endmodule
