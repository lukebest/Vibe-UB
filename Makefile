# Emit pycc PRODUCT + HOOKS netlists. Leaf registry: pycircuit/emit.py LEAVES.
# SPEC §10 lists no tb_* ports — HOOKS (TEST_HOOKS=1) matches PRODUCT ports.

PY ?= python3

.PHONY: emit

emit:
	$(PY) scripts/emit_rtl.py
