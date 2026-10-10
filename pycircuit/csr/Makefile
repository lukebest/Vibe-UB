# Local elaborate + lint for ub_csr_<tag> (SPEC §2.2).
# Verilog is compile()+pycc --emit=verilog (D5), committed at
#   PRODUCT → rtl/csr/ub_csr_<tag>.v
#   HOOKS   → rtl/csr/hooks/ub_csr_<tag>.v
# via scripts/emit_rtl.py. --check byte-compares a pycc regen.

PYTHON ?= python3

.PHONY: all elaborate lint

all: elaborate lint

elaborate:
	$(PYTHON) -c "import runpy; ns=runpy.run_path('ub_csr_regs.py'); \
	[print(ns['elaborate'](h, variant=t)) for t in ns['VARIANTS'] for h in (0,1)]"

lint:
	$(PYTHON) ../../scripts/lint_csr.sh
