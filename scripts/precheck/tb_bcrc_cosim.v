// Cosim: pycc ub_dll_bcrc vs independent bit-serial SPEC reference.
// Directed + $urandom. Local pre-check only (scripts/precheck/; non-gating).
`timescale 1ns/1ps
module tb_bcrc_cosim;
  reg         core_clk;
  reg         rst_pyc;
  reg         start;
  reg         valid_in;
  reg [159:0] data_in;
  reg         last;
  wire [31:0] crc_dut, crc_ref;
  wire        done_dut, done_ref;

  ub_dll_bcrc dut (
    .core_clk(core_clk), .rst_pyc(rst_pyc), .start(start),
    .valid_in(valid_in), .data_in(data_in), .last(last),
    .crc_word(crc_dut), .done(done_dut)
  );
  ub_dll_bcrc_spec ref (
    .core_clk(core_clk), .rst_pyc(rst_pyc), .start(start),
    .valid_in(valid_in), .data_in(data_in), .last(last),
    .crc_word(crc_ref), .done(done_ref)
  );

  integer i, errors, cycles;
  initial core_clk = 0;
  always #5 core_clk = ~core_clk;

  task automatic tick;
    begin
      @(posedge core_clk);
      #1;
      if (done_dut !== done_ref) begin
        $display("FAIL done dut=%b ref=%b @%0d", done_dut, done_ref, cycles);
        errors = errors + 1;
      end
      if (crc_dut !== crc_ref) begin
        $display("FAIL crc dut=%h ref=%h @%0d", crc_dut, crc_ref, cycles);
        errors = errors + 1;
      end
      cycles = cycles + 1;
    end
  endtask

  task automatic beat(input [159:0] d, input last_i);
    begin
      valid_in = 1'b1;
      data_in  = d;
      last     = last_i;
      tick();
      valid_in = 1'b0;
      last     = 1'b0;
    end
  endtask

  task automatic do_start;
    begin
      start = 1'b1;
      valid_in = 1'b0;
      last = 1'b0;
      tick();
      start = 1'b0;
    end
  endtask

  initial begin
    errors = 0;
    cycles = 0;
    start = 0; valid_in = 0; last = 0; data_in = 0;
    rst_pyc = 1'b1;
    repeat (3) tick();
    rst_pyc = 1'b0;
    tick();

    // directed: single last-flit all-zero payload
    do_start();
    beat(160'h0, 1'b1);

    // directed: incrementing bytes 0..15, last
    do_start();
    beat({32'h0, 128'h0F0E0D0C0B0A09080706050403020100}, 1'b1);

    // directed: two-flit (full then last)
    do_start();
    beat({160{1'b1}}, 1'b0);
    beat(160'hA5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5A5, 1'b1);

    // idle between, start without eat
    tick();
    tick();
    do_start();
    beat(160'h1, 1'b1);

    // random: 64 single-flit + 32 two-flit
    for (i = 0; i < 64; i = i + 1) begin
      do_start();
      beat({$urandom, $urandom, $urandom, $urandom, $urandom}, 1'b1);
    end
    for (i = 0; i < 32; i = i + 1) begin
      do_start();
      beat({$urandom, $urandom, $urandom, $urandom, $urandom}, 1'b0);
      beat({$urandom, $urandom, $urandom, $urandom, $urandom}, 1'b1);
    end

    if (errors != 0) begin
      $display("BCRC COSIM FAIL errors=%0d cycles=%0d", errors, cycles);
      $fatal(1);
    end
    $display("BCRC COSIM PASS errors=0 cycles=%0d", cycles);
    $finish;
  end
endmodule
