# Regenerate and lint ub_lmsm (PRODUCT + HOOKS).
#   make -C rtl/lmsm
#   make -C rtl/lmsm lint
#   make -C rtl/lmsm yosys

PYTHON ?= python3
VERILATOR ?= verilator
YOSYS ?= yosys

PRODUCT = product/ub_lmsm.v
HOOKS   = hooks/ub_lmsm.v

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
