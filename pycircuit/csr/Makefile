# Local elaborate + lint for ub_csr.
# Verilog is not committed here. scripts/emit_rtl.py (PR #5) will write
#   PRODUCT → rtl/csr/ub_csr.v
#   HOOKS   → rtl/csr/hooks/ub_csr.v
# until then, lint emits to a temp dir.

PYTHON ?= python3

.PHONY: all elaborate lint

all: elaborate lint

elaborate:
	$(PYTHON) -c "import runpy; ns=runpy.run_path('ub_csr_regs.py'); print(ns['elaborate'](0)); print(ns['elaborate'](1))"

lint:
	$(PYTHON) ../../scripts/lint_csr.sh
