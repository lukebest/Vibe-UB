"""Scoreboard: architecture ``UbTpBypass`` is the only data oracle.

Compare DUT (or fake) outputs to the model **transaction by transaction**.
``n_compare`` counts completed TX or RX packets. Fields the contract
marks unknown are not checked (``UNCHECKED``). Wave-1 leaf sidebands
``sl`` / ``nlp`` / ``lbf`` / ``rt`` / ``cci`` are still compared — the
DUT ties them to 0, so the model is fed ``LEAF_SIDEBAND``.
"""

from __future__ import annotations

from model.tp.ub_tp_bypass import (
    CFG_BYPASS,
    NwTxPacket,
    TaDelivery,
    TaOp,
    UbTpBypass,
    UbTpBypassError,
)

from tb.tp.items import (
    LEAF_SIDEBAND,
    RX_CHECKED,
    TX_CHECKED,
    UNCHECKED,
    ObservedRx,
    ObservedTx,
    RxSpec,
    TxSpec,
    flits_from_data,
)


class TpBypassScoreboard:
    """Lock-step ``UbTpBypass``; one compare per completed packet."""

    def __init__(self) -> None:
        self.ref = UbTpBypass()
        self.n_compare = 0
        self.n_mismatch = 0
        self.n_skip = 0
        self.mismatches: list[str] = []
        self.expected_tx: list[NwTxPacket] = []
        self.expected_rx: list[TaDelivery] = []
        self._tassn = 1

    def next_tassn(self) -> int:
        tag = self._tassn
        self._tassn += 1
        return tag

    def expect_tx(self, spec: TxSpec) -> NwTxPacket:
        # Allocate a unique tag. Wave-1 has no done/fail pin, so retire
        # immediately after submit to keep later cases from colliding.
        tassn = self.next_tassn()
        op = TaOp(opcode=0x10, tassn=tassn, bypass=True, dcna=spec.dcna)
        payload = flits_from_data(spec.data)
        pkt = self.ref.submit(op, payload, LEAF_SIDEBAND)
        self.ref.complete(tassn)
        self.expected_tx.append(pkt)
        return pkt

    def expect_rx(self, spec: RxSpec) -> TaDelivery | None:
        payload = flits_from_data(spec.data)
        got = self.ref.receive(
            payload, err=spec.err, drop=spec.drop, tassn=spec.tassn
        )
        if got is not None:
            self.expected_rx.append(got)
        return got

    def apply_flush(self):
        return self.ref.apply_flush()

    def apply_link_down(self):
        return self.ref.apply_link_down()

    def end_flush(self) -> None:
        self.ref.end_flush()

    def reset(self) -> None:
        self.ref.reset()
        self.expected_tx.clear()
        self.expected_rx.clear()

    def compare_tx(self, actual: ObservedTx, ctx: str = "tx") -> bool:
        if not self.expected_tx:
            self.n_compare += 1
            self.n_mismatch += 1
            self.mismatches.append(f"{ctx}: extra DUT TX packet")
            return False
        exp = self.expected_tx.pop(0)
        return self._cmp_tx(exp, actual, ctx)

    def compare_rx(self, actual: ObservedRx, ctx: str = "rx") -> bool:
        if not self.expected_rx:
            self.n_compare += 1
            self.n_mismatch += 1
            self.mismatches.append(f"{ctx}: extra DUT RX packet")
            return False
        exp = self.expected_rx.pop(0)
        return self._cmp_rx(exp, actual, ctx)

    def _cmp_tx(self, exp: NwTxPacket, actual: ObservedTx, ctx: str) -> bool:
        self.n_compare += 1
        bad: list[str] = []
        if len(actual.flits) != len(exp.flits):
            bad.append(f"nflit exp={len(exp.flits)} got={len(actual.flits)}")
        n = min(len(actual.flits), len(exp.flits))
        for i in range(n):
            a, e = actual.flits[i], exp.flits[i]
            if a.data != e.data:
                bad.append(f"flit{i}.data exp={e.data:#x} got={a.data:#x}")
            if a.sop != e.sop:
                bad.append(f"flit{i}.sop exp={int(e.sop)} got={int(a.sop)}")
            if a.eop != e.eop:
                bad.append(f"flit{i}.eop exp={int(e.eop)} got={int(a.eop)}")
        pairs = (
            ("bypass", int(exp.bypass), int(actual.bypass)),
            ("dcna", exp.dcna, actual.dcna),
            ("sl", exp.sl, actual.sl),
            ("nlp", exp.nlp, actual.nlp),
            ("lbf", exp.lbf, actual.lbf),
            ("rt", exp.rt, actual.rt),
            ("cci", exp.cci, actual.cci),
        )
        for name, ev, av in pairs:
            if ev != av:
                bad.append(f"{name} exp={ev:#x} got={av:#x}")
        if exp.cfg != CFG_BYPASS:
            bad.append(f"model cfg={exp.cfg} != CFG9")
        if bad:
            self.n_mismatch += 1
            self.mismatches.append(f"{ctx}: {', '.join(bad)}")
            return False
        return True

    def _cmp_rx(self, exp: TaDelivery, actual: ObservedRx, ctx: str) -> bool:
        self.n_compare += 1
        bad: list[str] = []
        if len(actual.flits) != len(exp.flits):
            bad.append(f"nflit exp={len(exp.flits)} got={len(actual.flits)}")
        n = min(len(actual.flits), len(exp.flits))
        for i in range(n):
            a, e = actual.flits[i], exp.flits[i]
            if a.data != e.data:
                bad.append(f"flit{i}.data exp={e.data:#x} got={a.data:#x}")
            if a.sop != e.sop:
                bad.append(f"flit{i}.sop exp={int(e.sop)} got={int(a.sop)}")
            if a.eop != e.eop:
                bad.append(f"flit{i}.eop exp={int(e.eop)} got={int(a.eop)}")
        if bool(actual.err) != bool(exp.err):
            bad.append(f"err exp={int(exp.err)} got={int(actual.err)}")
        if bad:
            self.n_mismatch += 1
            self.mismatches.append(f"{ctx}: {', '.join(bad)}")
            return False
        return True

    def assert_done(self, expected_n: int) -> None:
        if self.n_skip:
            raise AssertionError(f"n_skip={self.n_skip} (must be 0)")
        if self.expected_tx or self.expected_rx:
            raise AssertionError(
                f"unconsumed expected tx={len(self.expected_tx)} "
                f"rx={len(self.expected_rx)}"
            )
        if self.n_mismatch:
            raise AssertionError(
                f"{self.n_mismatch} scoreboard mismatches: "
                + "; ".join(self.mismatches)
            )
        if self.n_compare <= 0:
            raise AssertionError(
                "n_compare=0; scoreboard compared no transactions"
            )
        if self.n_compare != int(expected_n):
            raise AssertionError(
                f"n_compare={self.n_compare} != expected {expected_n}"
            )

    def assert_clean(self) -> None:
        if self.n_mismatch:
            raise AssertionError(
                f"{self.n_mismatch} scoreboard mismatches: "
                + "; ".join(self.mismatches)
            )


__all__ = [
    "RX_CHECKED",
    "TX_CHECKED",
    "UNCHECKED",
    "TpBypassScoreboard",
    "UbTpBypassError",
]
