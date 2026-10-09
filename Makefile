# M1 leaf RTL (batch 1). PRODUCT netlist = TEST_HOOKS=0.
# Legacy handwritten rtl/{pcs,dll}/*.v is D10 — do not regenerate over it.

PY ?= python3
GEN := rtl/gen
WHITELIST := rtl/common/ub_rst_sync.sv
VERILATOR ?= verilator
YOSYS ?= yosys

LEAVES := \
	$(GEN)/common/ub_pyc_rst_adapt.v \
	$(GEN)/pcs/ub_pcs_scrambler.v \
	$(GEN)/pcs/ub_pcs_descrambler.v \
	$(GEN)/pcs/ub_pcs_lane_dist.v \
	$(GEN)/pcs/ub_pcs_lane_dedist.v \
	$(GEN)/dll/ub_dll_bcrc.v \
	$(GEN)/dll/ub_dll_bcrc_check.v

.PHONY: all emit selfcheck lint synth clean

all: emit selfcheck lint

emit:
	$(PY) pycircuit/emit.py

selfcheck:
	$(PY) pycircuit/selfcheck.py

lint: emit
	@err=0; \
	for f in $(WHITELIST) $(LEAVES); do \
	  echo "==== verilator --lint-only -Wall $$f ===="; \
	  if $(VERILATOR) --lint-only -Wall $$f; then \
	    echo OK; \
	  else \
	    echo FAIL; err=1; \
	  fi; \
	done; \
	exit $$err

synth: emit
	@err=0; \
	for f in $(WHITELIST) $(LEAVES); do \
	  top=$$(basename $$f | sed 's/\.[sv]*$$//'); \
	  echo "==== yosys read/synth $$top ===="; \
	  if $(YOSYS) -q -p "read_verilog -sv $$f; hierarchy -check -top $$top; proc; opt; stat"; then \
	    echo OK; \
	  else \
	    echo FAIL; err=1; \
	  fi; \
	done; \
	exit $$err

clean:
	rm -f $(LEAVES)
