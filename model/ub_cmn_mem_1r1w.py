"""Cycle-accurate 1R1W storage primitive (CODING_STYLE §10 / PR #20).

Registered ``rdata``, 1-cycle read latency, same-address same-cycle
read-old, 1R1W. Array contents are not reset (no ``rst_n`` / ``rst_pyc``).

Architecture-owned scoreboard reference. Pure Python — no cocotb, no
``rtl/``, no ``pycircuit/``. Timing is the Xia proposal (spec silent);
if the spec later rules otherwise, update this module with the spec.

Do not copy UB Base Spec text. Cite section numbers only.
"""

from __future__ import annotations


def clog2(n: int) -> int:
    """Verilog ``$clog2``: clog2(1)=0, clog2(2)=1, clog2(3)=2."""
    if n < 1:
        raise ValueError("DEPTH must be >= 1")
    return (n - 1).bit_length()


class UbCmnMemAddrError(ValueError):
    """``waddr`` / ``raddr`` outside ``[0, DEPTH)`` while ``we`` / ``re``."""


class UbCmnMemUnwrittenError(ValueError):
    """Read of an entry that has not been written since model reset."""


class UbCmnMem1r1w:
    """Cycle-accurate behavioural model of ``ub_cmn_mem_1r1w``.

    ``tick()`` is one rising ``clk``. After a tick with ``re``, ``rdata``
    holds the value captured at that edge (old data if the same address
    was also written). ``rdata`` holds when ``re`` is 0.

    Per-entry ``written`` starts false. ``reset_written()`` clears those
    flags only — array contents stay (hardware has no array reset).

    ``assert_no_uninit_read`` (ASSERT_NO_UNINIT_READ, default True): flag a
    read of a never-written entry. Set False when valid bits live outside
    the array (gate blackbox ``valid_outside: true``, e.g. C-line UMMU/TLB);
    verification owns the valid-bit assertion in that case.
    """

    def __init__(
        self,
        depth: int,
        width: int,
        *,
        assert_no_uninit_read: bool = True,
        strict: bool = True,
    ) -> None:
        if depth < 1:
            raise ValueError("DEPTH must be >= 1")
        if width < 1:
            raise ValueError("WIDTH must be >= 1")
        self.depth = int(depth)
        self.width = int(width)
        self.aw = clog2(self.depth)
        self.assert_no_uninit_read = bool(assert_no_uninit_read)
        self.strict = bool(strict)
        self._mask = (1 << self.width) - 1
        self._mem = [0] * self.depth
        self._written = [False] * self.depth
        self._rdata = 0
        self.flags: list[str] = []

    @property
    def rdata(self) -> int:
        return self._rdata

    @property
    def written(self) -> tuple[bool, ...]:
        return tuple(self._written)

    def reset_written(self) -> None:
        """Mark every entry unwritten. Does not clear ``_mem`` or ``rdata``."""
        self._written = [False] * self.depth
        self.flags.clear()

    def _flag(self, exc: Exception) -> None:
        self.flags.append(f"{type(exc).__name__}: {exc}")
        if self.strict:
            raise exc

    def tick(
        self,
        we: bool | int,
        waddr: int,
        wdata: int,
        re: bool | int,
        raddr: int,
    ) -> int:
        """Advance one clock. Return ``rdata`` after the edge."""
        we_b = bool(we)
        re_b = bool(re)
        wdata_m = int(wdata) & self._mask

        if we_b and not (0 <= int(waddr) < self.depth):
            self._flag(
                UbCmnMemAddrError(f"waddr={waddr} out of range DEPTH={self.depth}")
            )
        if re_b and not (0 <= int(raddr) < self.depth):
            self._flag(
                UbCmnMemAddrError(f"raddr={raddr} out of range DEPTH={self.depth}")
            )
        elif (
            re_b
            and self.assert_no_uninit_read
            and not self._written[int(raddr)]
        ):
            self._flag(
                UbCmnMemUnwrittenError(f"read of never-written entry {int(raddr)}")
            )

        # Capture first so a same-address write does not forward (read-old).
        if re_b and 0 <= int(raddr) < self.depth:
            self._rdata = self._mem[int(raddr)] & self._mask

        if we_b and 0 <= int(waddr) < self.depth:
            self._mem[int(waddr)] = wdata_m
            self._written[int(waddr)] = True

        return self._rdata


class UbCmnMem1r1wSimpleRef:
    """Minimal dict reference for random legal traffic (no OOR / unwritten)."""

    def __init__(self, depth: int, width: int) -> None:
        self.depth = int(depth)
        self.width = int(width)
        self._mask = (1 << self.width) - 1
        self._mem = [0] * self.depth
        self.rdata = 0

    def tick(
        self,
        we: bool | int,
        waddr: int,
        wdata: int,
        re: bool | int,
        raddr: int,
    ) -> int:
        if re:
            self.rdata = self._mem[int(raddr)] & self._mask
        if we:
            self._mem[int(waddr)] = int(wdata) & self._mask
        return self.rdata
