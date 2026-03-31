# Makefile for TP Layer Verification

VCS = vcs -sverilog -ntb_opts uvm-1.2 +define+UVM_NO_DEPRECATED -full64 -timescale=1ns/1ps -debug_access+all -Mnoarchive -o simv

RTL_PATH = ../../rtl
TP_RTL = $(RTL_PATH)/tp

FILELIST = \
	+incdir+$(RTL_PATH) \
	+incdir+$(TP_RTL) \
	$(TP_RTL)/ub_tp_transmitter.v \
	$(TP_RTL)/ub_tp_receiver.v \
	$(TP_RTL)/ub_tp_controller_tx.v \
	$(TP_RTL)/ub_tp_controller_rx.v

.PHONY: all clean transmitter receiver loopback uvm_loopback

all: transmitter receiver loopback uvm_loopback

transmitter:
	$(VCS) $(FILELIST) ub_tp_transmitter_tb.v -l compile_tx.log
	./simv -l sim_tx.log

receiver:
	$(VCS) $(FILELIST) ub_tp_receiver_tb.v -l compile_rx.log
	./simv -l sim_rx.log

loopback:
	$(VCS) $(FILELIST) ub_tp_loopback_tb.v -l compile_loopback.log
	./simv -l sim_loopback.log

uvm_loopback:
	$(VCS) $(FILELIST) env/ub_tp_intf.sv env/ub_tp_dut_wrap.sv env/ub_tp_env.sv env/ub_tp_test.sv ub_tp_uvm_loopback_tb.sv -l compile_uvm.log
	./simv -l sim_uvm.log

clean:
	rm -rf csrc simv* *.log *.vcd DVEfiles urgReport ucli.key

