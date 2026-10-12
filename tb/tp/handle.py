"""Fake DUT handle: wave-1 passthrough, no RTL.

Honest fake matches the leaf: payload copy, ``dcna`` from the op,
``bypass=1``, ``sl`` / ``nlp`` / ``lbf`` / ``rt`` / ``cci`` tied 0,
RX ``err`` on eop. Corrupt fakes lock the compare direction.
"""

from __future__ import annotations

from model.tp.ub_tp_bypass import Flit

from tb.tp.items import ObservedRx, ObservedTx, RxSpec, TxSpec, flits_from_data


class FakeBypassHandle:
    """Transaction-level stand-in for ``ub_tp_bypass`` (wave-1)."""

    def __init__(
        self,
        *,
        swap_data: bool = False,
        alias_dcna: bool = False,
        clear_bypass: bool = False,
        force_sl: int | None = None,
    ) -> None:
        self.swap_data = bool(swap_data)
        self.alias_dcna = bool(alias_dcna)
        self.clear_bypass = bool(clear_bypass)
        self.force_sl = force_sl
        self.flush = False
        self.link_up = True
        self.tx_trace: list[ObservedTx] = []
        self.rx_trace: list[ObservedRx] = []

    def _map_data(self, data: tuple[int, ...]) -> tuple[int, ...]:
        if not self.swap_data:
            return data
        return tuple(word ^ 1 for word in data)

    def send_tx(self, spec: TxSpec) -> ObservedTx:
        if not self.link_up or self.flush:
            raise RuntimeError("fake: TX blocked (link-down or flush)")
        flits = flits_from_data(self._map_data(spec.data))
        dcna = (spec.dcna >> 1) if self.alias_dcna else spec.dcna
        obs = ObservedTx(
            flits=flits,
            bypass=0 if self.clear_bypass else 1,
            dcna=dcna,
            sl=0 if self.force_sl is None else int(self.force_sl),
            nlp=0,
            lbf=0,
            rt=0,
            cci=0,
        )
        self.tx_trace.append(obs)
        return obs

    def send_rx(self, spec: RxSpec) -> ObservedRx | None:
        if spec.drop:
            return None
        flits = flits_from_data(self._map_data(spec.data))
        # err is meaningful on eop (LAYER_CONTRACTS §2).
        last = Flit(flits[-1].data, sop=flits[-1].sop, eop=True)
        body = flits[:-1] + (last,)
        obs = ObservedRx(flits=body, err=bool(spec.err))
        self.rx_trace.append(obs)
        return obs


__all__ = ["FakeBypassHandle"]
