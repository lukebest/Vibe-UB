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

    localparam [31:0] RO_ID = 32'hA5A50001;

    reg [31:0] scratch;
    reg [31:0] test_reg;

    assign csr_ready   = 1'b1;
    assign vr_in_ready = (!vr_out_valid) | vr_out_ready;

    wire aligned        = (csr_addr[1:0] == 2'b00);
    wire mapped_scratch = aligned & (csr_addr == 16'h0000);
    wire mapped_ro      = aligned & (csr_addr == 16'h0004);
    wire mapped_test    = aligned & (csr_addr[15:8] == 8'h03);
    wire mapped         = mapped_scratch | mapped_ro | mapped_test;
    wire test_live      = (tb_test_mode == 1'b1);

    always @(posedge core_clk) begin
        if (!rst_n) begin
            vr_out_data  <= 32'd0;
            vr_out_valid <= 1'b0;
            vo_out_data  <= 32'd0;
            vo_out_valid <= 1'b0;
            scratch      <= 32'd0;
            test_reg     <= 32'd0;
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
                    // SPEC §3.2.3: TEST window mapped, read 0, write ignore, err=0
                    csr_err   <= 1'b0;
                    csr_rdata <= 32'd0;
                end else if (csr_wr) begin
                    if (mapped_scratch)
                        scratch <= csr_wdata;
                    else if (mapped_test && test_live)
                        test_reg <= csr_wdata;
                end else begin
                    if (mapped_scratch)
                        csr_rdata <= scratch;
                    else if (mapped_ro)
                        csr_rdata <= RO_ID;
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
                // Harness-only mapping so the hook agent can be smoke-tested.
                // Product DUT will mux these onto LMSM/DLL (SPEC §10.2).
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
