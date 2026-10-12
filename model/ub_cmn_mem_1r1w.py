"""Cycle-accurate 1R1W storage primitive (CODING_STYLE §10 / PR #20).

Registered ``rdata``, 1-cycle read latency, same-address same-cycle
read-old (per segment), 1R1W. Clock is ``core_clk``. No reset port
(business-leaf name is ``rst_pyc``; this primitive does not bring it
out). The rdata register and the array are not reset.

``WMASK_W`` (default ``WIDTH``) is the write-segment width.
``WIDTH`` must be an integer multiple of ``WMASK_W``;
``NSEG = WIDTH/WMASK_W``. ``NSEG=1`` is whole-word write: the port
list is unchanged. Only when ``NSEG>1`` is there a ``wmask[NSEG-1:0]``
input (``tick(..., wmask=)``); bit i=1 writes segment i, other
segments keep their old value.

``rdata`` is defined only after a read of a written address / segment:
before the first such read, and after a read of a never-written
segment when ``ASSERT_NO_UNINIT_READ=0``, that segment is undefined.
``rdata_valid`` is an ``NSEG``-bit mask (``NSEG=1`` stays a 1-bit
bool, backward-compatible). Undefined segments' ``rdata`` bits are
unspecified (``None`` when no segment is valid). Scoreboards compare
only valid segments.

Architecture-owned scoreboard reference. Pure Python — no cocotb, no
``rtl/``, no ``pycircuit/``. Timing is the Xia proposal (spec silent).

Do not copy UB Base Spec text. Cite section numbers only.
"""

from __future__ import annotations


def clog2(n: int) -> int:
    """Verilog ``$clog2``: clog2(1)=0, clog2(2)=1, clog2(3)=2."""
    if n < 1:
        raise ValueError("DEPTH must be >= 1")
    return (n - 1).bit_length()


def variant_name(depth: int, width: int, wmask_w: int | None = None) -> str:
    """SPEC §2.2 / CODING_STYLE §10 module name.

    ``ub_cmn_mem_1r1w_d<DEPTH>w<WIDTH>``, plus ``m<WMASK_W>`` when
    ``NSEG>1``. Examples: ``ub_cmn_mem_1r1w_d512w512m64``,
    ``ub_cmn_mem_1r1w_d64w64m16``.
    """
    if wmask_w is None:
        wmask_w = width
    if width < 1 or wmask_w < 1:
        raise ValueError("WIDTH and WMASK_W must be >= 1")
    if width % wmask_w != 0:
        raise ValueError(f"WIDTH={width} must be a multiple of WMASK_W={wmask_w}")
    if width // wmask_w == 1:
        return f"ub_cmn_mem_1r1w_d{int(depth)}w{int(width)}"
    return f"ub_cmn_mem_1r1w_d{int(depth)}w{int(width)}m{int(wmask_w)}"


class UbCmnMemAddrError(ValueError):
    """``waddr`` / ``raddr`` outside ``[0, DEPTH)`` while ``we`` / ``re``."""


class UbCmnMemUnwrittenError(ValueError):
    """Read of a word that has at least one never-written segment."""


class UbCmnMem1r1w:
    """Cycle-accurate behavioural model of ``ub_cmn_mem_1r1w``.

    ``tick()`` is one rising ``core_clk``. After a tick with ``re`` of a
    written address, ``rdata`` is that entry's old data (read-old if the
    same address was also written; per segment when ``NSEG>1``).
    ``rdata`` holds when ``re`` is 0.

    Array entries start undefined. ``reset_written()`` marks every
    segment undefined again; it does not reset the rdata register.

    ``assert_no_uninit_read`` (ASSERT_NO_UNINIT_READ, default True): a
    read where **any** segment of the word is unwritten is a violation.
    Set False when valid bits live outside the array (gate blackbox
    ``valid_outside: true``); that read returns undefined data for
    unwritten segments and the owner masks them.
    """

    def __init__(
        self,
        depth: int,
        width: int,
        *,
        wmask_w: int | None = None,
        assert_no_uninit_read: bool = True,
        strict: bool = True,
    ) -> None:
        if depth < 1:
            raise ValueError("DEPTH must be >= 1")
        if width < 1:
            raise ValueError("WIDTH must be >= 1")
        if wmask_w is None:
            wmask_w = width
        wmask_w = int(wmask_w)
        if wmask_w < 1:
            raise ValueError("WMASK_W must be >= 1")
        if width % wmask_w != 0:
            raise ValueError(
                f"WIDTH={width} must be an integer multiple of WMASK_W={wmask_w}"
            )
        self.depth = int(depth)
        self.width = int(width)
        self.wmask_w = wmask_w
        self.nseg = self.width // self.wmask_w
        self.aw = clog2(self.depth)
        self.assert_no_uninit_read = bool(assert_no_uninit_read)
        self.strict = bool(strict)
        self._mask = (1 << self.width) - 1
        self._all_seg = (1 << self.nseg) - 1
        self._mem: list[int | None] = [None] * self.depth
        # Per-address NSEG-bit written mask (0 = no segment written).
        self._written = [0] * self.depth
        self._rdata: int | None = None
        self._rdata_valid = 0
        self.flags: list[str] = []

    @property
    def name(self) -> str:
        return variant_name(self.depth, self.width, self.wmask_w)

    @property
    def rdata(self) -> int | None:
        return self._rdata

    @property
    def rdata_valid(self) -> bool | int:
        """NSEG-bit valid mask. ``NSEG=1`` is a bool (backward-compatible)."""
        if self.nseg == 1:
            return bool(self._rdata_valid)
        return self._rdata_valid

    @property
    def is_defined(self) -> bool:
        """True when every segment of ``rdata`` is defined.

        ``NSEG=1``: same as ``rdata_valid`` (bool). Scoreboard may
        compare the whole word. When ``NSEG>1`` and only some segments
        are valid, this is False — compare via ``valid_mask`` /
        ``segment_defined``.
        """
        return self._rdata_valid == self._all_seg

    @property
    def valid_mask(self) -> int:
        """Raw ``NSEG``-bit ``rdata`` valid mask (always an int)."""
        return self._rdata_valid

    @property
    def written(self) -> tuple:
        """Per-address written flags.

        ``NSEG=1``: tuple of bools (backward-compatible).
        ``NSEG>1``: tuple of NSEG-bit int masks.
        """
        if self.nseg == 1:
            return tuple(bool(w) for w in self._written)
        return tuple(self._written)

    def segment_defined(self, seg: int) -> bool:
        return bool(self._rdata_valid & (1 << int(seg)))

    def segment_bits(self, value: int, seg: int) -> int:
        """Extract segment ``seg`` from a WIDTH-bit word."""
        shift = int(seg) * self.wmask_w
        return (int(value) >> shift) & ((1 << self.wmask_w) - 1)

    def compare_valid_segments(self, actual: int) -> bool:
        """Scoreboard helper: compare only segments marked in ``rdata_valid``."""
        if self._rdata_valid == 0 or self._rdata is None:
            return True
        for seg in range(self.nseg):
            if self._rdata_valid & (1 << seg):
                if self.segment_bits(actual, seg) != self.segment_bits(self._rdata, seg):
                    return False
        return True

    def reset_written(self) -> None:
        """Mark every array segment undefined. Does not reset ``rdata``."""
        self._mem = [None] * self.depth
        self._written = [0] * self.depth
        self.flags.clear()

    def _flag(self, exc: Exception) -> None:
        self.flags.append(f"{type(exc).__name__}: {exc}")
        if self.strict:
            raise exc

    def _seg_mask(self, seg: int) -> int:
        return ((1 << self.wmask_w) - 1) << (int(seg) * self.wmask_w)

    def _apply_wmask(self, old: int | None, wdata: int, wmask: int) -> int:
        base = 0 if old is None else int(old)
        new = base
        for seg in range(self.nseg):
            if wmask & (1 << seg):
                sm = self._seg_mask(seg)
                new = (new & ~sm) | (wdata & sm)
        return new & self._mask

    def tick(
        self,
        we: bool | int,
        waddr: int,
        wdata: int,
        re: bool | int,
        raddr: int,
        wmask: int | None = None,
    ) -> int | None:
        """Advance one clock. Return ``rdata`` after the edge (or ``None``).

        ``wmask`` defaults to all-1s (every segment). When ``NSEG=1``
        there is no architectural ``wmask`` port; omitting it keeps the
        whole-word call signature.
        """
        we_b = bool(we)
        re_b = bool(re)
        wdata_m = int(wdata) & self._mask
        if wmask is None:
            wmask_m = self._all_seg
        else:
            wmask_m = int(wmask) & self._all_seg
        pending: list[Exception] = []

        if we_b and not (0 <= int(waddr) < self.depth):
            pending.append(
                UbCmnMemAddrError(f"waddr={waddr} out of range DEPTH={self.depth}")
            )
        if re_b and not (0 <= int(raddr) < self.depth):
            pending.append(
                UbCmnMemAddrError(f"raddr={raddr} out of range DEPTH={self.depth}")
            )
        elif (
            re_b
            and self.assert_no_uninit_read
            and self._written[int(raddr)] != self._all_seg
        ):
            pending.append(
                UbCmnMemUnwrittenError(
                    f"read of never-written segment(s) at {int(raddr)} "
                    f"(written={self._written[int(raddr)]:b}/{self.nseg})"
                )
            )

        # Capture first so a same-address write does not forward (read-old
        # per segment).
        if re_b and 0 <= int(raddr) < self.depth:
            wr = self._written[int(raddr)]
            if wr == 0:
                self._rdata = None
                self._rdata_valid = 0
            else:
                memv = self._mem[int(raddr)]
                val = 0 if memv is None else int(memv) & self._mask
                assembled = 0
                for seg in range(self.nseg):
                    if wr & (1 << seg):
                        assembled |= val & self._seg_mask(seg)
                self._rdata = assembled
                self._rdata_valid = wr

        if we_b and 0 <= int(waddr) < self.depth and wmask_m:
            self._mem[int(waddr)] = self._apply_wmask(
                self._mem[int(waddr)], wdata_m, wmask_m
            )
            self._written[int(waddr)] |= wmask_m

        for exc in pending:
            self._flag(exc)

        return self._rdata


class UbCmnMem1r1wSimpleRef:
    """Minimal dict reference for random legal traffic (no OOR / uninit)."""

    def __init__(self, depth: int, width: int, wmask_w: int | None = None) -> None:
        if wmask_w is None:
            wmask_w = width
        if width % wmask_w != 0:
            raise ValueError(f"WIDTH={width} must be a multiple of WMASK_W={wmask_w}")
        self.depth = int(depth)
        self.width = int(width)
        self.wmask_w = int(wmask_w)
        self.nseg = self.width // self.wmask_w
        self._mask = (1 << self.width) - 1
        self._all_seg = (1 << self.nseg) - 1
        self._mem: list[int | None] = [None] * self.depth
        self.rdata: int | None = None

    def _seg_mask(self, seg: int) -> int:
        return ((1 << self.wmask_w) - 1) << (int(seg) * self.wmask_w)

    def tick(
        self,
        we: bool | int,
        waddr: int,
        wdata: int,
        re: bool | int,
        raddr: int,
        wmask: int | None = None,
    ) -> int | None:
        if wmask is None:
            wmask_m = self._all_seg
        else:
            wmask_m = int(wmask) & self._all_seg
        if re:
            val = self._mem[int(raddr)]
            self.rdata = None if val is None else int(val) & self._mask
        if we and wmask_m:
            old = self._mem[int(waddr)]
            base = 0 if old is None else int(old)
            new = base
            wdata_m = int(wdata) & self._mask
            for seg in range(self.nseg):
                if wmask_m & (1 << seg):
                    sm = self._seg_mask(seg)
                    new = (new & ~sm) | (wdata_m & sm)
            self._mem[int(waddr)] = new & self._mask
        return self.rdata
