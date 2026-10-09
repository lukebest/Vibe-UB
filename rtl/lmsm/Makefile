# Regenerate and lint ub_lmsm (PRODUCT + HOOKS).
# Generated location follows SPEC §2.2 / CODING_STYLE §5: rtl/lmsm/
#   PRODUCT → rtl/lmsm/ub_lmsm.v
#   HOOKS   → rtl/lmsm/ub_lmsm_hooks.v
#   make -C rtl/lmsm
#   make -C rtl/lmsm lint
#   make -C rtl/lmsm yosys

PYTHON ?= python3
VERILATOR ?= verilator
YOSYS ?= yosys

PRODUCT = ub_lmsm.v
HOOKS   = ub_lmsm_hooks.v

.PHONY: all gen lint yosys clean

all: gen lint

gen:
	$(PYTHON) ub_lmsm.py

lint: gen
	$(VERILATOR) --lint-only -Wall $(PRODUCT)
	$(VERILATOR) --lint-only -Wall $(HOOKS)

yosys: gen
	$(YOSYS) -q -p 'read_verilog $(PRODUCT); hierarchy -check -top ub_lmsm; proc; stat'
	$(YOSYS) -q -p 'read_verilog $(HOOKS); hierarchy -check -top ub_lmsm; proc; stat'

clean:
	rm -f $(PRODUCT) $(HOOKS)
	rm -rf product hooks
