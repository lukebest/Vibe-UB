# Dual-netlist port self-check for ub_tp_bypass (SPEC §11).
#   make selfcheck-both SIM=icarus

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
TB_ROOT   := $(REPO_ROOT)/tb
RTL_TP    := $(REPO_ROOT)/rtl/tp

export PYTHONPATH := $(REPO_ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))

TEST_HOOKS ?= 0
SIM        ?= icarus

TOPLEVEL_LANG := verilog
TOPLEVEL      := ub_tp_bypass
MODULE        := tb.tp.sim_cocotb

ifeq ($(TEST_HOOKS),1)
VERILOG_SOURCES := $(RTL_TP)/hooks/ub_tp_bypass.v
else
VERILOG_SOURCES := $(RTL_TP)/ub_tp_bypass.v
endif

VERILOG_INCLUDE_DIRS += $(REPO_ROOT)/rtl/pyc_lib

export COCOTB_REDUCED_LOG_FMT ?= 1
export COCOTB_HDL_TIMEUNIT ?= 1ns
export COCOTB_HDL_TIMEPRECISION ?= 1ps
export TP_SEED ?= 1

ifeq ($(SIM),verilator)
EXTRA_ARGS += --timescale 1ns/1ps -Wno-fatal -I$(REPO_ROOT)/rtl/pyc_lib
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: selfcheck selfcheck-both

selfcheck:
	$(MAKE) SIM=$(SIM) TEST_HOOKS=$(TEST_HOOKS) sim

selfcheck-both:
	rm -rf sim_build
	$(MAKE) SIM=$(SIM) TEST_HOOKS=0 sim
	rm -rf sim_build
	$(MAKE) SIM=$(SIM) TEST_HOOKS=1 sim
