"""Functional cover points for the 1R1W leaf (VERIF_PLAN §4.3 / D8)."""

from __future__ import annotations


class Mem1r1wCoverage:
    """Simple hit-set. Bins: conflict, boundary, param combo, op kind."""

    def __init__(self) -> None:
        self.hits: set[str] = set()

    def sample(
        self,
        *,
        depth: int,
        width: int,
        assert_no_uninit_read: bool,
        we: int | bool,
        waddr: int,
        re: int | bool,
        raddr: int,
        wmask: int | None = None,
        nseg: int = 1,
    ) -> None:
        we_b = bool(we)
        re_b = bool(re)
        self.hits.add(
            f"params:{int(depth)}x{int(width)}:anur={int(bool(assert_no_uninit_read))}"
        )
        if we_b and not re_b:
            self.hits.add("op.we_only")
        elif re_b and not we_b:
            self.hits.add("op.re_only")
        elif we_b and re_b:
            self.hits.add("op.both")
        else:
            self.hits.add("op.idle")

        in_w = we_b and 0 <= int(waddr) < int(depth)
        in_r = re_b and 0 <= int(raddr) < int(depth)
        if in_w and int(waddr) == 0:
            self.hits.add("boundary_0")
        if in_r and int(raddr) == 0:
            self.hits.add("boundary_0")
        last = int(depth) - 1
        if in_w and int(waddr) == last:
            self.hits.add("boundary_last")
        if in_r and int(raddr) == last:
            self.hits.add("boundary_last")
        if in_w and in_r and int(waddr) == int(raddr):
            self.hits.add("conflict")
        if we_b and not (0 <= int(waddr) < int(depth)):
            self.hits.add("oor_waddr")
        if re_b and not (0 <= int(raddr) < int(depth)):
            self.hits.add("oor_raddr")
        if we_b and int(nseg) > 1 and wmask is not None:
            mask = int(wmask) & ((1 << int(nseg)) - 1)
            all_seg = (1 << int(nseg)) - 1
            if mask == 0:
                self.hits.add("wmask_zero")
            elif mask == all_seg:
                self.hits.add("wmask_all")
            bits = mask.bit_count()
            if bits == 1:
                self.hits.add("wmask_single")
                self.hits.add("wmask_onehot")
                self.hits.add(f"wmask_onehot:{mask.bit_length() - 1}")
            elif bits == 2 and (mask & (mask >> 1)):
                self.hits.add("wmask_adjacent")

    def require(self, *names: str) -> None:
        missing = [n for n in names if n not in self.hits]
        if missing:
            raise AssertionError(
                f"cover bins not hit: {missing}; have={sorted(self.hits)}"
            )

    def require_param(self, depth: int, width: int, assert_no_uninit_read: bool) -> None:
        self.require(
            f"params:{int(depth)}x{int(width)}:anur={int(bool(assert_no_uninit_read))}"
        )
