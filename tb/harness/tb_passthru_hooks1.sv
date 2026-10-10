// TB-only passthrough. NOT product RTL. Must not live under rtl/.
// Stand-in for TEST_HOOKS=1 (SPEC §11 HOOKS): SPEC §10 tb_* ports.
module tb_passthru (
    input  wire        core_clk,
    input  wire        rst_n,
    input  wire [31:0] vr_in_data,
    input  wire        vr_in_valid,
    output wire        vr_in_ready,
    output reg  [31:0] vr_out_data,
    output reg         vr_out_valid,
    input  wire        vr_out_ready,
    input  wire [31:0] vo_in_data,
    input  wire        vo_in_valid,
    output reg  [31:0] vo_out_data,
    output reg         vo_out_valid,
    input  wire        csr_req,
    input  wire        csr_wr,
    input  wire [15:0] csr_addr,
    input  wire [31:0] csr_wdata,
    output wire        csr_ready,
    output reg         csr_rvalid,
    output reg  [31:0] csr_rdata,
    output reg         csr_err,
    input  wire        tb_test_mode,
    input  wire [3:0]  tb_inj_am_lock,
    input  wire        tb_inj_lid_bad,
    input  wire [15:0] tb_inj_crd_cells,
    output reg         tb_obs_link_ready,
    output reg         tb_obs_link_up,
    output reg  [4:0]  tb_obs_lmsm_st,
    output reg  [15:0] tb_obs_crd_cells,
    output reg  [15:0] tb_obs_crd_pend,
    output reg         tb_obs_crd_low,
    output reg         tb_obs_crd_bp,
    output reg  [10:0] tb_obs_crd_to,
    output reg  [1:0]  tb_obs_dll_sm_st,
    output reg  [9:0]  tb_obs_consume_flits
);

`include "tb_csr_map.svh"

    reg [31:0] port_cna;
    reg [31:0] test_reg;
    reg [31:0] cnt [0:8];
    integer    ci;

    assign csr_ready   = 1'b1;
    assign vr_in_ready = (!vr_out_valid) | vr_out_ready;

    wire aligned           = (csr_addr[1:0] == 2'b00);
    wire mapped_ctrl       = aligned & (csr_addr == CSR_CTRL);
    wire mapped_status     = aligned & (csr_addr == CSR_STATUS);
    wire mapped_cna        = aligned & (csr_addr == CSR_PORT_CNA);
    wire mapped_cnt        = aligned & (csr_addr >= CSR_CNT_BASE) & (csr_addr <= CSR_CNT_CRD_UF);
    wire mapped_cnt_clr    = aligned & (csr_addr == CSR_CNT_CLR);
    wire mapped_test       = aligned & (csr_addr >= CSR_TEST_LO) & (csr_addr <= CSR_TEST_HI);
    wire mapped_appd_lmsm  = aligned & (csr_addr == CSR_APPD_LMSM_ST);
    wire mapped_appd_err   = aligned & (csr_addr == CSR_APPD_PORT_ERR);
    wire mapped            = mapped_ctrl | mapped_status | mapped_cna | mapped_cnt
                             | mapped_cnt_clr | mapped_test | mapped_appd_lmsm | mapped_appd_err;
    wire test_live         = (tb_test_mode == 1'b1);

    function automatic [3:0] cnt_index;
        input [15:0] addr;
        begin
            // 0x0200,0x0204,...,0x0220 → 0..8
            cnt_index = addr[5:2];
        end
    endfunction

    always @(posedge core_clk) begin
        if (!rst_n) begin
            vr_out_data  <= 32'd0;
            vr_out_valid <= 1'b0;
            vo_out_data  <= 32'd0;
            vo_out_valid <= 1'b0;
            port_cna     <= 32'd0;
            test_reg     <= 32'd0;
            for (ci = 0; ci < 9; ci = ci + 1)
                cnt[ci] <= 32'd0;
            csr_rvalid   <= 1'b0;
            csr_rdata    <= 32'd0;
            csr_err      <= 1'b0;
            tb_obs_link_ready     <= 1'b0;
            tb_obs_link_up        <= 1'b0;
            tb_obs_lmsm_st        <= 5'd0;
            tb_obs_crd_cells      <= 16'd0;
            tb_obs_crd_pend       <= 16'd0;
            tb_obs_crd_low        <= 1'b0;
            tb_obs_crd_bp         <= 1'b0;
            tb_obs_crd_to         <= 11'd0;
            tb_obs_dll_sm_st      <= 2'd0;
            tb_obs_consume_flits  <= 10'd0;
        end else begin
            if (vr_in_valid && vr_in_ready) begin
                vr_out_data  <= vr_in_data;
                vr_out_valid <= 1'b1;
            end else if (vr_out_ready) begin
                vr_out_valid <= 1'b0;
            end

            vo_out_valid <= vo_in_valid;
            vo_out_data  <= vo_in_data;

            csr_rvalid <= 1'b0;
            csr_rdata  <= 32'd0;
            csr_err    <= 1'b0;
            if (csr_req) begin
                csr_rvalid <= ~csr_wr;
                if (!mapped) begin
                    csr_err   <= 1'b1;
                    csr_rdata <= 32'd0;
                end else if (mapped_test && !test_live) begin
                    // SPEC §3.2.3 / REGMAP §2.4: mapped, read 0, write ignore, err=0
                    csr_err   <= 1'b0;
                    csr_rdata <= 32'd0;
                end else if (csr_wr) begin
                    if (mapped_cna)
                        port_cna <= csr_wdata;
                    else if (mapped_cnt_clr) begin
                        for (ci = 0; ci < 9; ci = ci + 1)
                            if (csr_wdata[ci])
                                cnt[ci] <= 32'd0;
                    end else if (mapped_test && test_live)
                        test_reg <= csr_wdata;
                end else begin
                    if (mapped_cna)
                        csr_rdata <= port_cna;
                    else if (mapped_status || mapped_ctrl || mapped_cnt_clr)
                        csr_rdata <= 32'd0;
                    else if (mapped_cnt)
                        csr_rdata <= cnt[cnt_index(csr_addr)];
                    else if (mapped_appd_lmsm || mapped_appd_err)
                        csr_rdata <= 32'd0;
                    else if (mapped_test && test_live)
                        csr_rdata <= test_reg;
                end
            end

            // SPEC §10.1: tb_test_mode=0 => obs held at 0; inj does not intervene.
            if (!test_live) begin
                tb_obs_link_ready     <= 1'b0;
                tb_obs_link_up        <= 1'b0;
                tb_obs_lmsm_st        <= 5'd0;
                tb_obs_crd_cells      <= 16'd0;
                tb_obs_crd_pend       <= 16'd0;
                tb_obs_crd_low        <= 1'b0;
                tb_obs_crd_bp         <= 1'b0;
                tb_obs_crd_to         <= 11'd0;
                tb_obs_dll_sm_st      <= 2'd0;
                tb_obs_consume_flits  <= 10'd0;
            end else begin
                tb_obs_link_up        <= tb_inj_lid_bad;
                tb_obs_link_ready     <= tb_inj_lid_bad;
                tb_obs_lmsm_st        <= {1'b0, tb_inj_am_lock};
                tb_obs_crd_cells      <= tb_inj_crd_cells;
                tb_obs_crd_pend       <= 16'd0;
                tb_obs_crd_low        <= (tb_inj_crd_cells == 16'd0);
                tb_obs_crd_bp         <= 1'b0;
                tb_obs_crd_to         <= 11'd0;
                tb_obs_dll_sm_st      <= 2'd0;
                tb_obs_consume_flits  <= 10'd0;
            end
        end
    end

endmodule
