// TB-only address map. Mirrors tb/vibe_uvm/ub_csr_map.py (REGMAP §2).
// Not product RTL.

localparam [15:0] CSR_CTRL          = 16'h0000;
localparam [15:0] CSR_STATUS        = 16'h0004;
localparam [15:0] CSR_PORT_CNA      = 16'h0010;
localparam [15:0] CSR_CNT_BASE      = 16'h0200;
localparam [15:0] CSR_CNT_CRD_UF    = 16'h0220;
localparam [15:0] CSR_CNT_CLR       = 16'h0224;
localparam [15:0] CSR_TEST_LO       = 16'h0300;
localparam [15:0] CSR_TEST_HI       = 16'h03FF;
localparam [15:0] CSR_APPD_LMSM_ST  = 16'h1E00;
localparam [15:0] CSR_APPD_PORT_ERR = 16'h1F00;
localparam [8:0]  CSR_CNT_CLR_MASK  = 9'h1FF; // bits 0–8, includes CNT_CRD_UF
