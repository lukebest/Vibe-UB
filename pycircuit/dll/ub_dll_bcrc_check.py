"""ub_dll_bcrc_check — DLL BCRC checker (SPEC §2.6; UB-DL §4.3.2.2 / §4.7.2).

Same CRC as ``ub_dll_bcrc``. On ``last``, compares the computed remainder
against ``crc_recv[CRC_W-1:0]`` (reserved bit and ERROR_FLAG are not part
of the remainder compare — packing is a parameter / open question).
"""

from __future__ import annotations

from lib import params as P
from dll.ub_dll_bcrc import _emit_bcrc

MODULE = "ub_dll_bcrc_check"


def emit_verilog(
    *,
    flit_w: int = P.FLIT_W,
    crc_w: int = P.BCRC_W,
    poly: int = P.BCRC_POLY,
    word_w: int = P.BCRC_WORD_W,
) -> str:
    return _emit_bcrc(
        MODULE,
        check=True,
        flit_w=flit_w,
        crc_w=crc_w,
        poly=poly,
        word_w=word_w,
    )
