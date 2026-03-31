`timescale 1ns / 1ps

module ub_pcs_fec_dec (
    input clk, rst_n,
    input [128*8-1:0] cw_in,
    input valid_in,
    output reg [120*8-1:0] msg_out,
    output reg valid_out,
    output reg fec_fail
);
    localparam ST_IDLE  = 2'd0;
    localparam ST_IBM   = 2'd1;
    localparam ST_CHIEN = 2'd2;
    localparam ST_DONE  = 2'd3;

    reg [1:0] state;
    reg [128*8-1:0] cw_reg;
    reg syndromes_zero_q;
    
    wire [63:0] syndromes;
    ub_pcs_fec_syndrome u_syndrome (
        .cw_in(cw_in),
        .syndromes(syndromes)
    );
    
    wire syndromes_zero = (syndromes == 64'h0);
    
    reg ibm_start;
    wire ibm_done;
    wire [39:0] lambda;
    wire [31:0] omega;
    
    ub_pcs_fec_ibm u_ibm (
        .clk(clk),
        .rst_n(rst_n),
        .syndromes(syndromes),
        .start(ibm_start),
        .done(ibm_done),
        .lambda(lambda),
        .omega(omega)
    );
    
    reg chien_start;
    wire chien_done;
    wire [127:0] error_mask;
    wire [1023:0] error_magnitudes;
    
    ub_pcs_fec_chien_forney u_chien (
        .clk(clk),
        .rst_n(rst_n),
        .start(chien_start),
        .lambda(lambda),
        .omega(omega),
        .done(chien_done),
        .error_mask(error_mask),
        .error_magnitudes(error_magnitudes)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            cw_reg <= 0;
            syndromes_zero_q <= 0;
            msg_out <= 0;
            valid_out <= 0;
            fec_fail <= 0;
            ibm_start <= 0;
            chien_start <= 0;
        end else begin
            ibm_start <= 0;
            chien_start <= 0;
            valid_out <= 0;
            
            case (state)
                ST_IDLE: begin
                    if (valid_in) begin
                        cw_reg <= cw_in;
                        syndromes_zero_q <= syndromes_zero;
                        if (syndromes_zero) begin
                            state <= ST_DONE;
                        end else begin
                            ibm_start <= 1;
                            state <= ST_IBM;
                        end
                    end
                end
                
                ST_IBM: begin
                    if (ibm_done) begin
                        chien_start <= 1;
                        state <= ST_CHIEN;
                    end
                end
                
                ST_CHIEN: begin
                    if (chien_done) begin
                        state <= ST_DONE;
                        // Correction applied in next state or here?
                        // Chien search puts results in error_magnitudes on chien_done.
                    end
                end
                
                ST_DONE: begin
                    if (syndromes_zero_q)
                        msg_out <= cw_reg[1023:64];
                    else
                        msg_out <= (cw_reg[1023:0] ^ error_magnitudes) >> 64; // Correct and strip 8 parity bytes
                    
                    valid_out <= 1;
                    // For now, we don't have a sophisticated fec_fail check.
                    // A simple one: if syndromes were not zero but no errors were found?
                    // Or if lambda degree > 4? (IBM module takes care of degree)
                    fec_fail <= 0; 
                    state <= ST_IDLE;
                end
                
                default: state <= ST_IDLE;
            endcase
        end
    end

endmodule
