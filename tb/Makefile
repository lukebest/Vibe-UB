# Dual-netlist entry for the TB self-check (SPEC §11).
#   make selfcheck-both SIM=icarus
#   make selfcheck-both SIM=verilator
# TEST_HOOKS=0 -> harness/tb_passthru_hooks0.sv (no tb_* ports)
# TEST_HOOKS=1 -> harness/tb_passthru_hooks1.sv (SPEC §10 hooks)

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
TB_ROOT   := $(REPO_ROOT)/tb

export PYTHONPATH := $(REPO_ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))

TEST_HOOKS ?= 0
SIM        ?= icarus
LINE_COV   ?= 0

TOPLEVEL_LANG := verilog
TOPLEVEL      := tb_passthru
MODULE        := tb.tests.tb_selfcheck

ifeq ($(TEST_HOOKS),1)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_passthru_hooks1.sv
else
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_passthru_hooks0.sv
endif

export COCOTB_REDUCED_LOG_FMT ?= 1
export COCOTB_HDL_TIMEUNIT ?= 1ns
export COCOTB_HDL_TIMEPRECISION ?= 1ps

ifeq ($(SIM),verilator)
EXTRA_ARGS += --timescale 1ns/1ps -Wno-fatal
ifeq ($(LINE_COV),1)
EXTRA_ARGS += --coverage
endif
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: selfcheck selfcheck-both models pytest cov-line summarize

selfcheck:
	$(MAKE) SIM=$(SIM) TEST_HOOKS=$(TEST_HOOKS) sim

selfcheck-both:
	rm -rf sim_build
	$(MAKE) SIM=$(SIM) TEST_HOOKS=0 sim
	rm -rf sim_build
	$(MAKE) SIM=$(SIM) TEST_HOOKS=1 sim

models pytest:
	cd $(TB_ROOT) && python3 -m pytest

# Verilator line-coverage dump for the HOOKS stand-in (SPEC §11 (b) denominator).
cov-line:
	rm -rf sim_build $(TB_ROOT)/reports/cov_line/selfcheck
	mkdir -p $(TB_ROOT)/reports/cov_line
	$(MAKE) SIM=verilator TEST_HOOKS=1 LINE_COV=1 sim
	-verilator_coverage --annotate $(TB_ROOT)/reports/cov_line/selfcheck \
		$(TB_ROOT)/coverage.dat sim_build/coverage.dat 2>/dev/null || true

summarize:
	python3 $(TB_ROOT)/scripts/summarize_tp.py
