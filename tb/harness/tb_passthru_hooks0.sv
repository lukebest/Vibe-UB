// TB-only passthrough. NOT product RTL. Must not live under rtl/.
// Stand-in for TEST_HOOKS=0 (SPEC §11 PRODUCT): no tb_* ports.
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
    output reg         csr_err
);

    localparam [31:0] RO_ID = 32'hA5A50001;

    reg [31:0] scratch;

    assign csr_ready  = 1'b1;
    assign vr_in_ready = (!vr_out_valid) | vr_out_ready;

    wire aligned        = (csr_addr[1:0] == 2'b00);
    wire mapped_scratch = aligned & (csr_addr == 16'h0000);
    wire mapped_ro      = aligned & (csr_addr == 16'h0004);
    wire mapped_test    = aligned & (csr_addr[15:8] == 8'h03);
    wire mapped         = mapped_scratch | mapped_ro | mapped_test;

    always @(posedge core_clk) begin
        if (!rst_n) begin
            vr_out_data  <= 32'd0;
            vr_out_valid <= 1'b0;
            vo_out_data  <= 32'd0;
            vo_out_valid <= 1'b0;
            scratch      <= 32'd0;
            csr_rvalid   <= 1'b0;
            csr_rdata    <= 32'd0;
            csr_err      <= 1'b0;
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
                end else if (mapped_test) begin
                    // PRODUCT / no hooks: TEST window mapped, read 0, write ignore, err=0
                    // (SPEC §3.2.3 / §11 (d))
                    csr_err   <= 1'b0;
                    csr_rdata <= 32'd0;
                end else if (csr_wr) begin
                    if (mapped_scratch)
                        scratch <= csr_wdata;
                end else begin
                    if (mapped_scratch)
                        csr_rdata <= scratch;
                    else if (mapped_ro)
                        csr_rdata <= RO_ID;
                end
            end
        end
    end

endmodule
