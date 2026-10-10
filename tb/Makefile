# Dual-netlist TB entry (SPEC §11).
# Self-check (no product DUT):
#   make selfcheck-both SIM=icarus
# Leaf batch 1 (product leaves under rtl/):
#   make leaf LEAF=ub_rst_sync TEST_HOOKS=0 SIM=icarus
#   make leaf-batch1 SIM=icarus
# TEST_HOOKS=0: no tb_* ports. TEST_HOOKS=1: unused SPEC §10 ports (leaves have none).

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
TB_ROOT   := $(REPO_ROOT)/tb
RTL       := $(REPO_ROOT)/rtl

export PYTHONPATH := $(REPO_ROOT)$(if $(PYTHONPATH),:$(PYTHONPATH))

TEST_HOOKS ?= 0
SIM        ?= icarus
LINE_COV   ?= 0
LEAF       ?=
NUM_LANES  ?= 4
PYC_RST_ACTIVE_HIGH ?= 1

export TEST_HOOKS
export NUM_LANES
export PYC_RST_ACTIVE_HIGH
export COCOTB_REDUCED_LOG_FMT ?= 1
export COCOTB_HDL_TIMEUNIT ?= 1ns
export COCOTB_HDL_TIMEPRECISION ?= 1ps

TOPLEVEL_LANG := verilog

ifeq ($(LEAF),ub_rst_sync)
TOPLEVEL := tb_ub_rst_sync
MODULE   := tb.tests.tb_rst_sync
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_rst_sync.sv $(RTL)/common/ub_rst_sync.sv
else ifeq ($(LEAF),ub_pyc_rst_adapt)
TOPLEVEL := tb_ub_rst_adapt
MODULE   := tb.tests.tb_rst_adapt
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_rst_adapt.sv $(RTL)/common/ub_pyc_rst_adapt.v
else ifeq ($(LEAF),ub_pcs_lane_dist)
TOPLEVEL := tb_ub_lane_dist
MODULE   := tb.tests.tb_lane_dist
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_lane_dist.sv $(RTL)/pcs/ub_pcs_lane_dist.v
else ifeq ($(LEAF),ub_pcs_lane_dedist)
TOPLEVEL := tb_ub_lane_dedist
MODULE   := tb.tests.tb_lane_dedist
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_lane_dedist.sv $(RTL)/pcs/ub_pcs_lane_dedist.v
else ifeq ($(LEAF),ub_pcs_lane_collect)
TOPLEVEL := tb_ub_lane_collect
MODULE   := tb.tests.tb_lane_collect
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_lane_collect.sv \
	$(RTL)/pcs/ub_pcs_lane_dist.v $(RTL)/pcs/ub_pcs_lane_dedist.v
else ifeq ($(LEAF),ub_dll_bcrc)
TOPLEVEL := tb_ub_bcrc
MODULE   := tb.tests.tb_bcrc
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_bcrc.sv $(RTL)/dll/ub_dll_bcrc.v
else ifeq ($(LEAF),ub_dll_bcrc_check)
TOPLEVEL := tb_ub_bcrc_check
MODULE   := tb.tests.tb_bcrc_check
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_bcrc_check.sv $(RTL)/dll/ub_dll_bcrc_check.v
else
TOPLEVEL := tb_passthru
MODULE   := tb.tests.tb_selfcheck
ifeq ($(TEST_HOOKS),1)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_passthru_hooks1.sv
else
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_passthru_hooks0.sv
endif
endif

VERILOG_INCLUDE_DIRS += $(TB_ROOT)/harness

ifeq ($(TEST_HOOKS),1)
ifeq ($(SIM),verilator)
EXTRA_ARGS += -DTB_TEST_HOOKS
else
COMPILE_ARGS += -DTB_TEST_HOOKS
endif
endif

ifeq ($(LEAF),ub_pyc_rst_adapt)
ifeq ($(SIM),verilator)
EXTRA_ARGS += -GPYC_RST_ACTIVE_HIGH=$(PYC_RST_ACTIVE_HIGH)
else
COMPILE_ARGS += -P$(TOPLEVEL).PYC_RST_ACTIVE_HIGH=$(PYC_RST_ACTIVE_HIGH)
endif
endif

ifneq ($(filter $(LEAF),ub_pcs_lane_dist ub_pcs_lane_dedist ub_pcs_lane_collect),)
ifeq ($(SIM),verilator)
EXTRA_ARGS += -GNUM_LANES=$(NUM_LANES)
else
COMPILE_ARGS += -P$(TOPLEVEL).NUM_LANES=$(NUM_LANES)
endif
endif

ifeq ($(SIM),verilator)
EXTRA_ARGS += --timescale 1ns/1ps -Wno-fatal
ifeq ($(LINE_COV),1)
EXTRA_ARGS += --coverage
endif
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: selfcheck selfcheck-both models pytest cov-line summarize leaf leaf-batch1

selfcheck:
	$(MAKE) SIM=$(SIM) TEST_HOOKS=$(TEST_HOOKS) sim

selfcheck-both:
	rm -rf sim_build
	$(MAKE) SIM=$(SIM) TEST_HOOKS=0 sim
	rm -rf sim_build
	$(MAKE) SIM=$(SIM) TEST_HOOKS=1 sim

leaf:
	rm -rf sim_build
	$(MAKE) SIM=$(SIM) TEST_HOOKS=$(TEST_HOOKS) LEAF=$(LEAF) \
		NUM_LANES=$(NUM_LANES) PYC_RST_ACTIVE_HIGH=$(PYC_RST_ACTIVE_HIGH) sim

leaf-batch1:
	$(TB_ROOT)/scripts/run_leaf_batch1.sh $(SIM)

models pytest:
	cd $(TB_ROOT) && python3 -m pytest

cov-line:
	rm -rf sim_build $(TB_ROOT)/reports/cov_line/selfcheck
	mkdir -p $(TB_ROOT)/reports/cov_line
	$(MAKE) SIM=verilator TEST_HOOKS=1 LINE_COV=1 sim
	-verilator_coverage --annotate $(TB_ROOT)/reports/cov_line/selfcheck \
		$(TB_ROOT)/coverage.dat sim_build/coverage.dat 2>/dev/null || true

summarize:
	python3 $(TB_ROOT)/scripts/summarize_tp.py
