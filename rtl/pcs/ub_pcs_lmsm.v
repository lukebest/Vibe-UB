module ub_pcs_lmsm (
    input clk, rst_n,
    input start_train,
    output [2:0] state_dbg
);
    localparam LINK_IDLE = 3'd0;
    localparam PROBE_WAIT = 3'd1;
    localparam DISC_ACTIVE = 3'd2;

    reg [2:0] state;
    reg [3:0] probe_cnt;

    assign state_dbg = state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= LINK_IDLE;
            probe_cnt <= 4'd0;
        end else begin
            case (state)
                LINK_IDLE: begin
                    if (start_train) begin
                        state <= PROBE_WAIT;
                        probe_cnt <= 4'd0;
                    end
                end
                PROBE_WAIT: begin
                    if (probe_cnt == 4'd9) begin
                        state <= DISC_ACTIVE;
                    end else begin
                        probe_cnt <= probe_cnt + 4'd1;
                    end
                end
                DISC_ACTIVE: begin
                    // Stay in DISC_ACTIVE for now
                    state <= DISC_ACTIVE;
                end
                default: state <= LINK_IDLE;
            endcase
        end
    end
endmodule
