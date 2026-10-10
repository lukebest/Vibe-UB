"""Sequence items. randomize() via cocotb-coverage crv (D8)."""

from __future__ import annotations

from cocotb_coverage.crv import Randomized
from uvm import UVMSequenceItem, uvm_object_utils


class VrItem(UVMSequenceItem, Randomized):
    """valid/ready beat (SPEC §3.1)."""

    def __init__(self, name="vr_item"):
        UVMSequenceItem.__init__(self, name)
        Randomized.__init__(self)
        self.data = 0
        self.add_rand("data", list(range(0x10000)))

    def do_copy(self, rhs):
        super().do_copy(rhs)
        self.data = rhs.data


class VoItem(UVMSequenceItem, Randomized):
    """valid-only beat (SPEC §3.1). Sink must accept every valid cycle."""

    def __init__(self, name="vo_item"):
        UVMSequenceItem.__init__(self, name)
        Randomized.__init__(self)
        self.data = 0
        self.add_rand("data", list(range(0x10000)))

    def do_copy(self, rhs):
        super().do_copy(rhs)
        self.data = rhs.data


class CsrItem(UVMSequenceItem, Randomized):
    """CSR access (SPEC §3.2.3): 32-bit whole word, 16-bit byte address."""

    def __init__(self, name="csr_item"):
        UVMSequenceItem.__init__(self, name)
        Randomized.__init__(self)
        self.write = 0
        self.addr = 0
        self.wdata = 0
        self.rdata = 0
        self.err = 0
        self.add_rand("write", [0, 1])
        self.add_rand("addr", list(range(0, 0x100, 4)))
        self.add_rand("wdata", list(range(0x10000)))

    def do_copy(self, rhs):
        super().do_copy(rhs)
        self.write = rhs.write
        self.addr = rhs.addr
        self.wdata = rhs.wdata
        self.rdata = rhs.rdata
        self.err = rhs.err


uvm_object_utils(VrItem)
uvm_object_utils(VoItem)
uvm_object_utils(CsrItem)
