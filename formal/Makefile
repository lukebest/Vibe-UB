# Standalone SymbiYosys jobs for architecture interface assertions.
# Each formal/<iface>/*.sby is self-contained (stub + props).

SBY    ?= sby
IFACES := reset pma_pcs lmsm_pcs csr status irq

.PHONY: all clean $(IFACES)

all: $(IFACES)

$(IFACES):
	cd $@ && $(SBY) -f $@.sby

clean:
	@for d in $(IFACES); do \
	  rm -rf $$d/$$d_bmc $$d/$$d_cover $$d/$$d_prove; \
	done
