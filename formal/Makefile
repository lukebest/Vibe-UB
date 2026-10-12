# Standalone SymbiYosys jobs. Discovers formal/<iface>/<iface>.sby.
# tb/cmn/ and pycircuit/cmn/ are owned by verification-B / design-B.

SBY    ?= sby
IFACES := $(sort $(patsubst %/,%,$(dir $(wildcard */*.sby))))

.PHONY: all clean $(IFACES)

all: $(IFACES)

$(IFACES):
	cd $@ && $(SBY) -f --sequential $@.sby

clean:
	@for d in $(IFACES); do \
	  rm -rf $$d/$$d_bmc $$d/$$d_cover $$d/$$d_prove; \
	done
