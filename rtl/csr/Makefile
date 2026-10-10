# Regenerate and lint ub_csr (PRODUCT + HOOKS).
#   PRODUCT → rtl/csr/ub_csr.v
#   HOOKS   → rtl/csr/hooks/ub_csr.v
#   make -C rtl/csr
#   make -C rtl/csr lint
#   make -C rtl/csr yosys
#   make -C rtl/csr elaborate

PYTHON ?= python3
VERILATOR ?= verilator
YOSYS ?= yosys

PRODUCT = ub_csr.v
HOOKS   = hooks/ub_csr.v

.PHONY: all gen lint yosys elaborate clean

all: gen lint

gen:
	$(PYTHON) ub_csr_regs.py

lint: gen
	$(VERILATOR) --lint-only -Wall $(PRODUCT)
	$(VERILATOR) --lint-only -Wall $(HOOKS)

yosys: gen
	$(YOSYS) -q -p 'read_verilog $(PRODUCT); synth -run begin:fine -top ub_csr; stat'
	$(YOSYS) -q -p 'read_verilog $(HOOKS); synth -run begin:fine -top ub_csr; stat'

elaborate: gen
	$(PYTHON) -c "from ub_csr_regs import elaborate; print(elaborate(0)); print(elaborate(1))"

clean:
	rm -f $(PRODUCT) $(HOOKS)
