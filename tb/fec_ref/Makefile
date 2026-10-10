# Icarus + cocotb self-check for formal/pcs/ref FEC formula leaves.
# SPEC §2.2: PYTHONPATH is <repo>/pycircuit first; repo root stays off it.

REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
TB_DIR    := $(REPO_ROOT)/tb
REF_DIR   := $(REPO_ROOT)/formal/pcs/ref
FALSE_DIR := $(REF_DIR)/false

export PATH := $(HOME)/.local/bin:$(PATH)
# pycircuit first (SPEC §2.2). This TB dir next so MODULE imports resolve.
# Repo root is intentionally absent.
export PYTHONPATH := $(REPO_ROOT)/pycircuit:$(TB_DIR)/fec_ref
export PYTHONSAFEPATH := 1
export PYTHONUNBUFFERED := 1

SIM               ?= icarus
TOPLEVEL_LANG     := verilog
MODULE            := test_ub_pcs_fec_ref
FEC_REF_VARIANT   ?= enc_ref

export FEC_REF_VARIANT
export COCOTB_REDUCED_LOG_FMT ?= 1
export COCOTB_HDL_TIMEUNIT ?= 1ns
export COCOTB_HDL_TIMEPRECISION ?= 1ps

ifeq ($(FEC_REF_VARIANT),enc_ref)
TOPLEVEL := ub_pcs_fec_enc_ref
VERILOG_SOURCES := $(REF_DIR)/ub_pcs_fec_enc_ref.sv
else ifeq ($(FEC_REF_VARIANT),syn_ref)
TOPLEVEL := ub_pcs_fec_syndrome_ref
VERILOG_SOURCES := $(REF_DIR)/ub_pcs_fec_syndrome_ref.sv
else ifeq ($(FEC_REF_VARIANT),enc_bad_coeff)
TOPLEVEL := ub_pcs_fec_enc_ref_bad_coeff
VERILOG_SOURCES := $(REF_DIR)/ub_pcs_fec_enc_ref.sv $(FALSE_DIR)/ub_pcs_fec_enc_ref_bad_coeff.sv
else ifeq ($(FEC_REF_VARIANT),enc_rev_order)
TOPLEVEL := ub_pcs_fec_enc_ref_rev_order
VERILOG_SOURCES := $(REF_DIR)/ub_pcs_fec_enc_ref.sv $(FALSE_DIR)/ub_pcs_fec_enc_ref_rev_order.sv
else ifeq ($(FEC_REF_VARIANT),enc_poly11b)
TOPLEVEL := ub_pcs_fec_enc_ref_poly11b
VERILOG_SOURCES := $(REF_DIR)/ub_pcs_fec_enc_ref.sv $(FALSE_DIR)/ub_pcs_fec_enc_ref_poly11b.sv
else
$(error unknown FEC_REF_VARIANT=$(FEC_REF_VARIANT))
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: selfcheck

run_one = \
	rm -rf sim_build; \
	$(MAKE) SIM=$(SIM) FEC_REF_VARIANT=$(1) sim && \
	python3 -P $(TB_DIR)/fec_ref/check_sim.py

selfcheck:
	$(call run_one,enc_ref)
	$(call run_one,syn_ref)
	$(call run_one,enc_bad_coeff)
	$(call run_one,enc_rev_order)
	$(call run_one,enc_poly11b)
