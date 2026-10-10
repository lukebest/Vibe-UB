# Dual-netlist TB entry (SPEC §11).
# Self-check (no product DUT):
#   make selfcheck-both SIM=icarus
# Leaf batch 1:
#   make leaf LEAF=ub_rst_sync TEST_HOOKS=0 SIM=icarus
#   make leaf-batch1 SIM=icarus
# DUT filelist:
#   TEST_HOOKS=0 -> rtl/<block>/<module>.v  (PRODUCT)
#   TEST_HOOKS=1 -> rtl/<block>/hooks/<module>.v if present, else PRODUCT
#   ub_rst_sync is whitelist SV: always rtl/common/ub_rst_sync.sv (no hooks copy)
# Leaves listed in SPEC §10 as having no hooks: HOOKS ports == PRODUCT.
# Leaf wrappers do not add tb_* and do not bind the hook agent.

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
export SIM
export LEAF
export COCOTB_REDUCED_LOG_FMT ?= 1
export COCOTB_HDL_TIMEUNIT ?= 1ns
export COCOTB_HDL_TIMEPRECISION ?= 1ps

TOPLEVEL_LANG := verilog

# Prefer hooks/ netlist when TEST_HOOKS=1 and the file exists; else PRODUCT.
ifeq ($(TEST_HOOKS),1)
rtl_dut = $(if $(wildcard $(RTL)/$(1)/hooks/$(2)),$(RTL)/$(1)/hooks/$(2),$(RTL)/$(1)/$(2))
else
rtl_dut = $(RTL)/$(1)/$(2)
endif

ifeq ($(LEAF),ub_rst_sync)
TOPLEVEL := tb_ub_rst_sync
MODULE   := tb.tests.tb_rst_sync
DUT_RTL  := $(RTL)/common/ub_rst_sync.sv
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_rst_sync.sv $(DUT_RTL)
else ifeq ($(LEAF),ub_pyc_rst_adapt)
TOPLEVEL := tb_ub_rst_adapt
MODULE   := tb.tests.tb_rst_adapt
DUT_RTL  := $(call rtl_dut,common,ub_pyc_rst_adapt.v)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_rst_adapt.sv $(DUT_RTL)
else ifeq ($(LEAF),ub_pcs_lane_dist)
TOPLEVEL := tb_ub_lane_dist
MODULE   := tb.tests.tb_lane_dist
DUT_RTL  := $(call rtl_dut,pcs,ub_pcs_lane_dist.v)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_lane_dist.sv $(DUT_RTL)
else ifeq ($(LEAF),ub_pcs_lane_dedist)
TOPLEVEL := tb_ub_lane_dedist
MODULE   := tb.tests.tb_lane_dedist
DUT_RTL  := $(call rtl_dut,pcs,ub_pcs_lane_dedist.v)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_lane_dedist.sv $(DUT_RTL)
else ifeq ($(LEAF),ub_pcs_lane_collect)
TOPLEVEL := tb_ub_lane_collect
MODULE   := tb.tests.tb_lane_collect
DUT_RTL  := $(call rtl_dut,pcs,ub_pcs_lane_dist.v) $(call rtl_dut,pcs,ub_pcs_lane_dedist.v)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_lane_collect.sv $(DUT_RTL)
else ifeq ($(LEAF),ub_dll_bcrc)
TOPLEVEL := tb_ub_bcrc
MODULE   := tb.tests.tb_bcrc
DUT_RTL  := $(call rtl_dut,dll,ub_dll_bcrc.v)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_bcrc.sv $(DUT_RTL)
else ifeq ($(LEAF),ub_dll_bcrc_check)
TOPLEVEL := tb_ub_bcrc_check
MODULE   := tb.tests.tb_bcrc_check
DUT_RTL  := $(call rtl_dut,dll,ub_dll_bcrc_check.v)
VERILOG_SOURCES := $(TB_ROOT)/harness/tb_ub_bcrc_check.sv $(DUT_RTL)
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

# -DTB_TEST_HOOKS is only for the passthrough self-check harness, not leaf TBs.
ifeq ($(LEAF),)
ifeq ($(TEST_HOOKS),1)
ifeq ($(SIM),verilator)
EXTRA_ARGS += -DTB_TEST_HOOKS
else
COMPILE_ARGS += -DTB_TEST_HOOKS
endif
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

ifneq ($(LEAF),)
$(info DUT_RTL=$(DUT_RTL) TEST_HOOKS=$(TEST_HOOKS))
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
