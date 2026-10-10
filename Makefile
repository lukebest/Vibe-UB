# Emit pycc PRODUCT netlists. Leaf registry: pycircuit/emit.py LEAVES.
# ub_cmn_mem_1r1w has no SPEC §10 hooks — PRODUCT only (rtl/cmn/).

PY ?= python3

.PHONY: emit

emit:
	$(PY) scripts/emit_rtl.py
