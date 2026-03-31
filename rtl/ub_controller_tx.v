module ub_controller_tx (
    input clk, rst_n,
    // Network Interface
    input [159:0] net_data,
    input net_valid, net_sop, net_eop,
    output net_ready,
    // Physical Interface (PAM4 Symbols to lanes)
    output [31:0] lane0, lane1, lane2, lane3,
    output lane_valid
);

    // --- DLL Layer ---
    wire [159:0] flit_seg;
    wire flit_seg_valid;
    ub_dll_segmenter u_segmenter (
        .clk(clk),
        .rst_n(rst_n),
        .net_data(net_data),
        .net_valid(net_valid),
        .net_sop(net_sop),
        .net_eop(net_eop),
        .net_ready(net_ready),
        .flit_out(flit_seg),
        .flit_valid(flit_seg_valid)
    );

    wire [31:0] b_crc;
    ub_dll_crc32 u_crc32 (
        .clk(clk),
        .rst_n(rst_n),
        .data_in(flit_seg),
        .data_valid(flit_seg_valid),
        .crc_out(b_crc)
    );

    // --- PCS Layer ---
    wire [159:0] flit_scram;
    wire flit_scram_valid;
    ub_pcs_scrambler u_scrambler (
        .clk(clk),
        .rst_n(rst_n),
        .data_in(flit_seg),
        .valid_in(flit_seg_valid),
        .data_out(flit_scram),
        .valid_out(flit_scram_valid)
    );

    // Accumulate 6 flits (960 bits) for RS-FEC encoder
    reg [959:0] fec_msg;
    reg [2:0] flit_cnt;
    reg fec_msg_valid;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            flit_cnt <= 0;
            fec_msg_valid <= 0;
            fec_msg <= 0;
        end else if (flit_scram_valid) begin
            fec_msg <= {fec_msg[799:0], flit_scram};
            if (flit_cnt == 5) begin
                flit_cnt <= 0;
                fec_msg_valid <= 1;
            end else begin
                flit_cnt <= flit_cnt + 1;
                fec_msg_valid <= 0;
            end
        end else begin
            fec_msg_valid <= 0;
        end
    end

    wire [1023:0] cw_out;
    wire cw_valid;
    ub_pcs_fec_enc u_fec_enc (
        .clk(clk),
        .rst_n(rst_n),
        .msg_in(fec_msg),
        .valid_in(fec_msg_valid),
        .cw_out(cw_out),
        .valid_out(cw_valid)
    );

    // Gray Coding (512 instances of 2-bit symbols)
    wire [1023:0] symbols_out;
    genvar g;
    generate
        for (g = 0; g < 512; g = g + 1) begin : g_gray
            ub_pcs_gray_coder u_gray (
                .bits(cw_out[g*2 +: 2]),
                .symbols(symbols_out[g*2 +: 2])
            );
        end
    endgenerate

    // Serialization and Lane Distribution
    // The lane distributor takes 128 bits per cycle.
    // One FEC codeword (1024 bits) takes 8 cycles to distribute.
    reg [1023:0] symbols_reg;
    reg [2:0] dist_cnt;
    reg dist_active;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dist_cnt <= 0;
            dist_active <= 0;
            symbols_reg <= 0;
        end else if (cw_valid) begin
            symbols_reg <= symbols_out;
            dist_cnt <= 0;
            dist_active <= 1;
        end else if (dist_active) begin
            if (dist_cnt == 7) begin
                dist_active <= 0;
            end
            dist_cnt <= dist_cnt + 1;
        end
    end

    wire [127:0] dist_in = symbols_reg >> (dist_cnt * 128);
    ub_pcs_lane_dist u_lane_dist (
        .data_in(dist_in),
        .lane0(lane0),
        .lane1(lane1),
        .lane2(lane2),
        .lane3(lane3)
    );

    assign lane_valid = dist_active;

endmodule
