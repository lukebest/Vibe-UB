# Regenerate and lint ub_dll_retry_req_sm + ub_dll_retry_ack_sm (PRODUCT).
# Generated location follows SPEC §2.2 / CODING_STYLE §5: rtl/dll/
#   PRODUCT → rtl/dll/<module>.v
# SPEC §10 lists no hooks for these leaves — no rtl/dll/hooks/.
# D10 legacy under rtl/dll/ (crc32 / segmenter / …) is not in this lint set.
#
#   make -C rtl/dll
#   make -C rtl/dll lint
#   make -C rtl/dll yosys
#   make -C rtl/dll selfcheck
#
# pyCircuit pin (D5): lukebest/pyCircuit @ 43cc5918 (pyc4.0).
# PRODUCT .v is reproduced by the Python emitter; pycc/LLVM is not required.

PYTHON ?= python3
VERILATOR ?= verilator
YOSYS ?= yosys

REQ_PY  = ub_dll_retry_req_sm.py
ACK_PY  = ub_dll_retry_ack_sm.py
REQ_V   = ub_dll_retry_req_sm.v
ACK_V   = ub_dll_retry_ack_sm.v
LEAVES  = $(REQ_V) $(ACK_V)

.PHONY: all gen lint yosys selfcheck clean

all: gen selfcheck lint yosys

gen:
	$(PYTHON) $(REQ_PY)
	$(PYTHON) $(ACK_PY)

selfcheck: gen
	$(PYTHON) selfcheck.py

lint: gen
	@err=0; \
	for f in $(LEAVES); do \
	  echo "==== verilator --lint-only -Wall $$f ===="; \
	  if $(VERILATOR) --lint-only -Wall $$f; then \
	    echo OK; \
	  else \
	    echo FAIL; err=1; \
	  fi; \
	done; \
	exit $$err

# User gate: read / hierarchy / proc / opt / stat. Fail on latch cells.
yosys: gen
	@err=0; \
	for f in $(LEAVES); do \
	  top=$${f%.v}; \
	  echo "==== yosys read/hierarchy/proc/opt/stat $$top ===="; \
	  log=$$(mktemp); \
	  if $(YOSYS) -q -p "read_verilog $$f; hierarchy -check -top $$top; proc; opt; stat" > $$log 2>&1; then \
	    if grep -E -q '\\\$dlatch|\\$_DLATCH' $$log; then \
	      echo FAIL latches; cat $$log; err=1; \
	    else \
	      echo OK; cat $$log; \
	    fi; \
	  else \
	    echo FAIL; cat $$log; err=1; \
	  fi; \
	  rm -f $$log; \
	done; \
	exit $$err

clean:
	rm -f $(REQ_V) $(ACK_V)
