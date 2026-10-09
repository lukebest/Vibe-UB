# M1 leaf RTL (batch 1). PRODUCT netlist = TEST_HOOKS=0.
# Layout: SPEC §2.2 / CODING_STYLE §5 — rtl/<block>/<module>.v
# HOOKS would be rtl/<block>/hooks/<module>.v; SPEC §10 lists none here.

PY ?= python3
RTL := rtl
WHITELIST := $(RTL)/common/ub_rst_sync.sv
VERILATOR ?= verilator
YOSYS ?= yosys

LEAVES := \
	$(RTL)/common/ub_pyc_rst_adapt.v \
	$(RTL)/pcs/ub_pcs_scrambler.v \
	$(RTL)/pcs/ub_pcs_descrambler.v \
	$(RTL)/pcs/ub_pcs_lane_dist.v \
	$(RTL)/pcs/ub_pcs_lane_dedist.v \
	$(RTL)/dll/ub_dll_bcrc.v \
	$(RTL)/dll/ub_dll_bcrc_check.v

# OPEN SPEC §13 scrambler items have no product default (syntax stubs are 0).
# Lint / Yosys must pass explicit elaboration tokens. Source of truth:
# pycircuit/lib/elab_open.py — not old PR #5 / Switch (tap 17, seed 2'b01).
SCR_OPEN_G = $(shell $(PY) -c "import sys; sys.path.insert(0,'pycircuit'); from lib.elab_open import verilator_gflags; print(verilator_gflags())")
SCR_OPEN_CH = $(shell $(PY) -c "import sys; sys.path.insert(0,'pycircuit'); from lib.elab_open import yosys_chparam_cmd; print(yosys_chparam_cmd())")

.PHONY: all emit selfcheck lint synth clean

all: emit selfcheck lint

emit:
	$(PY) pycircuit/emit.py

selfcheck:
	$(PY) pycircuit/selfcheck.py

lint: emit
	@err=0; \
	for f in $(WHITELIST) $(LEAVES); do \
	  gflags=""; \
	  case $$f in \
	    *ub_pcs_scrambler.v|*ub_pcs_descrambler.v) gflags="$(SCR_OPEN_G)" ;; \
	  esac; \
	  echo "==== verilator --lint-only -Wall $$gflags $$f ===="; \
	  if $(VERILATOR) --lint-only -Wall $$gflags $$f; then \
	    echo OK; \
	  else \
	    echo FAIL; err=1; \
	  fi; \
	done; \
	echo "==== verilator --lint-only -Wall -GNUM_LANES=8 $(RTL)/pcs/ub_pcs_lane_dist.v ===="; \
	if $(VERILATOR) --lint-only -Wall -GNUM_LANES=8 $(RTL)/pcs/ub_pcs_lane_dist.v; then echo OK; else echo FAIL; err=1; fi; \
	echo "==== verilator --lint-only -Wall -GNUM_LANES=8 $(RTL)/pcs/ub_pcs_lane_dedist.v ===="; \
	if $(VERILATOR) --lint-only -Wall -GNUM_LANES=8 $(RTL)/pcs/ub_pcs_lane_dedist.v; then echo OK; else echo FAIL; err=1; fi; \
	exit $$err

synth: emit
	@err=0; \
	for f in $(WHITELIST) $(LEAVES); do \
	  top=$$(basename $$f | sed 's/\.[sv]*$$//'); \
	  ch=""; \
	  case $$f in \
	    *ub_pcs_scrambler.v|*ub_pcs_descrambler.v) ch="$(SCR_OPEN_CH); " ;; \
	  esac; \
	  echo "==== yosys read/synth $$top ===="; \
	  if $(YOSYS) -q -p "read_verilog -sv $$f; $${ch}hierarchy -check -top $$top; proc; opt; stat"; then \
	    echo OK; \
	  else \
	    echo FAIL; err=1; \
	  fi; \
	done; \
	exit $$err

clean:
	@echo "PRODUCT leaves are the committed rtl/<block>/*.v; not removed."
