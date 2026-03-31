module ub_controller_rx (
    input clk, rst_n,
    // Physical Interface (PAM4 Symbols from lanes)
    input [31:0] lane0, lane1, lane2, lane3,
    input lane_valid,
    // Network Interface
    output [159:0] net_data,
    output net_valid, net_sop, net_eop,
    input net_ready,
    // Status
    output fec_fail,
    output crc_pass
);

    // --- PCS Layer RX ---

    // Lane De-distribution: 4 lanes of 32 bits -> 128 bits symbols
    wire [127:0] dedist_out;
    ub_pcs_lane_dedist u_lane_dedist (
        .lane0(lane0),
        .lane1(lane1),
        .lane2(lane2),
        .lane3(lane3),
        .data_out(dedist_out)
    );

    // Gray Decoding: 64 symbols of 2 bits each
    wire [127:0] codeword_chunk;
    genvar g;
    generate
        for (g = 0; g < 64; g = g + 1) begin : g_gray_dec
            ub_pcs_gray_decoder u_gray_dec (
                .symbols(dedist_out[g*2 +: 2]),
                .bits(codeword_chunk[g*2 +: 2])
            );
        end
    endgenerate

    // Accumulate 8 cycles (128*8 = 1024 bits) for RS-FEC decoder
    reg [1023:0] fec_cw;
    reg [2:0] cw_cnt;
    reg fec_cw_valid;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cw_cnt <= 0;
            fec_cw_valid <= 0;
            fec_cw <= 0;
        end else if (lane_valid) begin
            fec_cw <= {codeword_chunk, fec_cw[1023:128]};
            if (cw_cnt == 7) begin
                cw_cnt <= 0;
                fec_cw_valid <= 1;
            end else begin
                cw_cnt <= cw_cnt + 1;
                fec_cw_valid <= 0;
            end
        end else begin
            fec_cw_valid <= 0;
        end
    end

    wire [959:0] fec_msg;
    wire fec_msg_valid;
    ub_pcs_fec_dec u_fec_dec (
        .clk(clk),
        .rst_n(rst_n),
        .cw_in(fec_cw),
        .valid_in(fec_cw_valid),
        .msg_out(fec_msg),
        .valid_out(fec_msg_valid),
        .fec_fail(fec_fail)
    );

    // De-accumulate 960 bits to 6 flits (160 bits each)
    reg [959:0] flits_reg;
    reg [2:0] flit_cnt;
    reg flits_active;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            flits_reg <= 0;
            flit_cnt <= 0;
            flits_active <= 0;
        end else if (fec_msg_valid) begin
            flits_reg <= fec_msg;
            flit_cnt <= 0;
            flits_active <= 1;
        end else if (flits_active) begin
            if (flit_cnt == 5) begin
                flits_active <= 0;
            end
            flit_cnt <= flit_cnt + 1;
        end
    end

    wire [159:0] scram_flit = flits_reg >> ((5 - flit_cnt) * 160);
    wire scram_flit_valid = flits_active;

    wire [159:0] descram_flit;
    wire descram_flit_valid;
    ub_pcs_descrambler u_descrambler (
        .clk(clk),
        .rst_n(rst_n),
        .data_in(scram_flit),
        .valid_in(scram_flit_valid),
        .data_out(descram_flit),
        .valid_out(descram_flit_valid)
    );

    // --- DLL Layer RX ---

    // CRC Check: Using first 32 bits as expected CRC for skeleton validation
    ub_dll_crc_check u_crc_check (
        .clk(clk),
        .rst_n(rst_n),
        .data_in(descram_flit),
        .expected_crc(descram_flit[31:0]),
        .valid_in(descram_flit_valid),
        .crc_pass(crc_pass)
    );

    ub_dll_reassembler u_reassembler (
        .clk(clk),
        .rst_n(rst_n),
        .flit_in(descram_flit),
        .flit_valid(descram_flit_valid),
        .net_data(net_data),
        .net_valid(net_valid),
        .net_sop(net_sop),
        .net_eop(net_eop),
        .net_ready(net_ready)
    );

endmodule
