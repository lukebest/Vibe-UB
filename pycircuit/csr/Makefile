# Local elaborate + lint for ub_csr_<tag> (SPEC §2.2).
# Verilog is compile()+pycc --emit=verilog (D5), not committed here.
# scripts/emit_rtl.py (PR #5) will write
#   PRODUCT → rtl/csr/ub_csr_<tag>.v
#   HOOKS   → rtl/csr/hooks/ub_csr_<tag>.v
# until then, lint emits to a temp dir when pycc is on PATH.

PYTHON ?= python3

.PHONY: all elaborate lint

all: elaborate lint

elaborate:
	$(PYTHON) -c "import runpy; ns=runpy.run_path('ub_csr_regs.py'); \
	[print(ns['elaborate'](h, variant=t)) for t in ns['VARIANTS'] for h in (0,1)]"

lint:
	$(PYTHON) ../../scripts/lint_csr.sh
