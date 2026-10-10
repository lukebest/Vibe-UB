"""Cycle-accurate 1R1W storage primitive (CODING_STYLE §10 / PR #20).

Registered ``rdata``, 1-cycle read latency, same-address same-cycle
read-old, 1R1W. The rdata register and the array are not reset.

``rdata`` is defined only after a read of a written address: before the
first such read, and after a read of a never-written entry when
``ASSERT_NO_UNINIT_READ=0``, ``tick()`` / ``rdata`` are ``None`` and
``rdata_valid`` / ``is_defined`` are false. Scoreboards compare ``rdata``
only when the model marks it defined.

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


class UbCmnMemAddrError(ValueError):
    """``waddr`` / ``raddr`` outside ``[0, DEPTH)`` while ``we`` / ``re``."""


class UbCmnMemUnwrittenError(ValueError):
    """Read of an entry that has not been written since model reset."""


class UbCmnMem1r1w:
    """Cycle-accurate behavioural model of ``ub_cmn_mem_1r1w``.

    ``tick()`` is one rising ``core_clk``. After a tick with ``re`` of a
    written address, ``rdata`` is that entry's old data (read-old if the
    same address was also written). ``rdata`` holds when ``re`` is 0.

    Array entries start undefined. ``reset_written()`` marks every entry
    undefined again; it does not reset the rdata register.

    ``assert_no_uninit_read`` (ASSERT_NO_UNINIT_READ, default True): a
    read of a never-written entry is a violation. Set False when valid
    bits live outside the array (gate blackbox ``valid_outside: true``);
    that read returns undefined data and the owner masks it.
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
        self._mem: list[int | None] = [None] * self.depth
        self._written = [False] * self.depth
        self._rdata: int | None = None
        self.flags: list[str] = []

    @property
    def rdata(self) -> int | None:
        return self._rdata

    @property
    def rdata_valid(self) -> bool:
        return self._rdata is not None

    @property
    def is_defined(self) -> bool:
        return self._rdata is not None

    @property
    def written(self) -> tuple[bool, ...]:
        return tuple(self._written)

    def reset_written(self) -> None:
        """Mark every array entry undefined. Does not reset ``rdata``."""
        self._mem = [None] * self.depth
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
    ) -> int | None:
        """Advance one clock. Return ``rdata`` after the edge (or ``None``)."""
        we_b = bool(we)
        re_b = bool(re)
        wdata_m = int(wdata) & self._mask
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
            and not self._written[int(raddr)]
        ):
            pending.append(
                UbCmnMemUnwrittenError(f"read of never-written entry {int(raddr)}")
            )

        # Capture first so a same-address write does not forward (read-old).
        if re_b and 0 <= int(raddr) < self.depth:
            if self._written[int(raddr)] and self._mem[int(raddr)] is not None:
                self._rdata = int(self._mem[int(raddr)]) & self._mask
            else:
                self._rdata = None

        if we_b and 0 <= int(waddr) < self.depth:
            self._mem[int(waddr)] = wdata_m
            self._written[int(waddr)] = True

        for exc in pending:
            self._flag(exc)

        return self._rdata


class UbCmnMem1r1wSimpleRef:
    """Minimal dict reference for random legal traffic (no OOR / unwritten)."""

    def __init__(self, depth: int, width: int) -> None:
        self.depth = int(depth)
        self.width = int(width)
        self._mask = (1 << self.width) - 1
        self._mem: list[int | None] = [None] * self.depth
        self.rdata: int | None = None

    def tick(
        self,
        we: bool | int,
        waddr: int,
        wdata: int,
        re: bool | int,
        raddr: int,
    ) -> int | None:
        if re:
            val = self._mem[int(raddr)]
            self.rdata = None if val is None else int(val) & self._mask
        if we:
            self._mem[int(waddr)] = int(wdata) & self._mask
        return self.rdata
