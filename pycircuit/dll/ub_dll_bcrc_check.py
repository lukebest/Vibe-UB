"""ub_dll_bcrc_check — DLL BCRC checker (SPEC §2.6; UB-DL §4.3.2.2.4 / §4.7.2 / §7).

Same CRC30 / byte-MSB-first stream as ``ub_dll_bcrc``. On ``last``:
  - compare computed CRC30 to ``crc_recv[29:0]`` only (ERROR_FLAG not in the check)
  - ``error_flag_rx`` = ``crc_recv[30]`` for the parent to drive ``nw_rx_err``
  - bit31 reserved, ignored on receive
"""

from __future__ import annotations

from lib import params as P
from dll.ub_dll_bcrc import _emit_bcrc

MODULE = "ub_dll_bcrc_check"


def emit_verilog(
    test_hooks: bool = False,
    *,
    flit_w: int = P.FLIT_W,
    crc_w: int = P.BCRC_W,
    poly: int = P.BCRC_POLY,
    word_w: int = P.BCRC_WORD_W,
) -> str:
    return _emit_bcrc(
        MODULE,
        check=True,
        test_hooks=test_hooks,
        flit_w=flit_w,
        crc_w=crc_w,
        poly=poly,
        word_w=word_w,
    )
