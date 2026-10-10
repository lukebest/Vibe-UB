# M1 leaf RTL (batch 1).
# PRODUCT = TEST_HOOKS=0 → rtl/<block>/<module>.v
# HOOKS   = TEST_HOOKS=1 → rtl/<block>/hooks/<module>.v
# SPEC §10 lists no hook ports here, so HOOKS == PRODUCT.
# Whitelist ub_rst_sync.sv is handwritten: no hooks/ copy (CODING_STYLE §3).
# STEP 1 pycc leaves: rst_adapt, lane _x4/_x8, BCRC gen/check.
# STEP 2 pending: scrambler / descrambler leftover f-string emitters.

PY ?= python3
RTL := rtl
WHITELIST := $(RTL)/common/ub_rst_sync.sv
PYC_REG := $(RTL)/common/pyc_reg.v
VERILATOR ?= verilator
YOSYS ?= yosys

LEAVES := \
	$(RTL)/common/ub_pyc_rst_adapt.v \
	$(RTL)/pcs/ub_pcs_scrambler.v \
	$(RTL)/pcs/ub_pcs_descrambler.v \
	$(RTL)/pcs/ub_pcs_lane_dist_x4.v \
	$(RTL)/pcs/ub_pcs_lane_dist_x8.v \
	$(RTL)/pcs/ub_pcs_lane_dedist_x4.v \
	$(RTL)/pcs/ub_pcs_lane_dedist_x8.v \
	$(RTL)/dll/ub_dll_bcrc.v \
	$(RTL)/dll/ub_dll_bcrc_check.v

HOOKS := \
	$(RTL)/common/hooks/ub_pyc_rst_adapt.v \
	$(RTL)/pcs/hooks/ub_pcs_scrambler.v \
	$(RTL)/pcs/hooks/ub_pcs_descrambler.v \
	$(RTL)/pcs/hooks/ub_pcs_lane_dist_x4.v \
	$(RTL)/pcs/hooks/ub_pcs_lane_dist_x8.v \
	$(RTL)/pcs/hooks/ub_pcs_lane_dedist_x4.v \
	$(RTL)/pcs/hooks/ub_pcs_lane_dedist_x8.v \
	$(RTL)/dll/hooks/ub_dll_bcrc.v \
	$(RTL)/dll/hooks/ub_dll_bcrc_check.v

# OPEN SPEC §13 scrambler items have no product default (syntax stubs are 0).
SCR_OPEN_G = $(shell $(PY) -c "import sys; sys.path.insert(0,'pycircuit'); from lib.elab_open import verilator_gflags; print(verilator_gflags())")
SCR_OPEN_CH = $(shell $(PY) -c "import sys; sys.path.insert(0,'pycircuit'); from lib.elab_open import yosys_chparam_cmd; print(yosys_chparam_cmd())")

.PHONY: all emit selfcheck lint synth equiv clean

all: emit selfcheck lint equiv

emit:
	$(PY) scripts/emit_rtl.py

selfcheck:
	$(PY) pycircuit/selfcheck.py

lint: emit
	@err=0; \
	for f in $(WHITELIST) $(LEAVES) $(HOOKS); do \
	  gflags=""; extra=""; \
	  case $$f in \
	    *ub_pcs_scrambler.v|*ub_pcs_descrambler.v) gflags="$(SCR_OPEN_G)" ;; \
	    *ub_dll_bcrc*.v) extra="$(PYC_REG)" ;; \
	  esac; \
	  echo "==== verilator --lint-only -Wall $$gflags $$f $$extra ===="; \
	  if $(VERILATOR) --lint-only -Wall $$gflags $$f $$extra; then \
	    echo OK; \
	  else \
	    echo FAIL; err=1; \
	  fi; \
	done; \
	exit $$err

synth: emit
	@err=0; \
	for f in $(WHITELIST) $(LEAVES) $(HOOKS); do \
	  top=$$(basename $$f | sed 's/\.[sv]*$$//'); \
	  ch=""; extra=""; \
	  case $$f in \
	    *ub_pcs_scrambler.v|*ub_pcs_descrambler.v) ch="$(SCR_OPEN_CH); " ;; \
	    *ub_dll_bcrc*.v) extra="$(PYC_REG)" ;; \
	  esac; \
	  echo "==== yosys read/synth $$f (top $$top) ===="; \
	  if $(YOSYS) -q -p "read_verilog -sv $$extra $$f; $${ch}hierarchy -check -top $$top; proc; opt; stat"; then \
	    echo OK; \
	  else \
	    echo FAIL; err=1; \
	  fi; \
	done; \
	exit $$err

equiv: emit
	$(PY) scripts/equiv_product_hooks.py --no-emit

clean:
	@echo "PRODUCT/HOOKS leaves are the committed rtl/<block>/*.v; not removed."
