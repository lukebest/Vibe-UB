# One-button tool gate. CI jobs call the same scripts/gate/*.sh files.
.PHONY: gate lint synth-check cdc-rdc formal regmap-consistency tb-selfcheck rtl-emit-consistency hooks-port-consistency versions

gate:
	scripts/gate/run_all.sh

rtl-emit-consistency:
	scripts/gate/rtl_emit_consistency.sh

hooks-port-consistency:
	scripts/gate/hooks_port_consistency.sh

lint:
	scripts/gate/lint.sh

synth-check:
	scripts/gate/synth_check.sh

cdc-rdc:
	scripts/gate/cdc_rdc.sh

formal:
	scripts/gate/formal.sh

regmap-consistency:
	scripts/gate/regmap_consistency.sh

tb-selfcheck:
	scripts/gate/tb_selfcheck.sh

versions:
	scripts/gate/print_versions.sh
