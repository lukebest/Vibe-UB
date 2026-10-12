// TB-only behavioral stand-in for ub_mem_ptw_desc_dec.
// Same ports and 1-cycle registered handshake as the public contract.
// `raw` carries a TB software protocol (not a table descriptor layout).
// Drive walk outcomes through the memory-response port of ub_mem_ptw.
//
// TB protocol in raw[63:0]:
//   [0]     v
//   [2:1]   kind
//   [38:3]  addr
//   [41:39] attr_idx
//   [43:42] ap
//   [44]    uxn
//   [45]    pxn
//   [46]    af
//   [47]    illegal
//   [51:48] ill_cause

module ub_mem_ptw_desc_dec (
  input         core_clk,
  input         rst_pyc,
  input         in_valid,
  input  [63:0] raw,
  input  [1:0]  desc_lvl,
  input         out_ready,
  output        in_ready,
  output        out_valid,
  output        desc_v,
  output [1:0]  desc_kind,
  output [35:0] desc_addr,
  output [2:0]  desc_attr_idx,
  output [1:0]  desc_ap,
  output        desc_uxn,
  output        desc_pxn,
  output        desc_af,
  output        desc_illegal,
  output [3:0]  desc_ill_cause
);

  reg        rst_gone;
  reg        pending;
  reg        q_v;
  reg [1:0]  q_kind;
  reg [35:0] q_addr;
  reg [2:0]  q_idx;
  reg [1:0]  q_ap;
  reg        q_uxn;
  reg        q_pxn;
  reg        q_af;
  reg        q_ill;
  reg [3:0]  q_cause;

  wire accept;
  wire live;

  assign live = (raw == raw) && (desc_lvl == desc_lvl);
  assign in_ready = rst_gone && (~pending || out_ready) && live;
  assign accept = in_valid && in_ready;
  assign out_valid = pending;
  assign desc_v = q_v;
  assign desc_kind = q_kind;
  assign desc_addr = q_addr;
  assign desc_attr_idx = q_idx;
  assign desc_ap = q_ap;
  assign desc_uxn = q_uxn;
  assign desc_pxn = q_pxn;
  assign desc_af = q_af;
  assign desc_illegal = q_ill;
  assign desc_ill_cause = q_cause;

  always @(posedge core_clk) begin
    if (rst_pyc) begin
      rst_gone <= 1'b0;
      pending <= 1'b0;
      q_v <= 1'b0;
      q_kind <= 2'b00;
      q_addr <= 36'b0;
      q_idx <= 3'b0;
      q_ap <= 2'b0;
      q_uxn <= 1'b0;
      q_pxn <= 1'b0;
      q_af <= 1'b0;
      q_ill <= 1'b0;
      q_cause <= 4'b0;
    end else begin
      rst_gone <= 1'b1;
      if (accept) begin
        pending <= 1'b1;
        q_ill <= raw[47];
        q_cause <= raw[51:48];
        if (raw[47]) begin
          q_v <= 1'b0;
          q_kind <= 2'b00;
          q_addr <= 36'b0;
          q_idx <= 3'b0;
          q_ap <= 2'b0;
          q_uxn <= 1'b0;
          q_pxn <= 1'b0;
          q_af <= 1'b0;
        end else begin
          q_v <= raw[0];
          q_kind <= raw[2:1];
          q_addr <= raw[38:3];
          q_idx <= raw[41:39];
          q_ap <= raw[43:42];
          q_uxn <= raw[44];
          q_pxn <= raw[45];
          q_af <= raw[46];
        end
      end else if (pending && out_ready) begin
        pending <= 1'b0;
      end
    end
  end

endmodule
