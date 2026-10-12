"""ub_tp_bypass stimulus / observe items (LAYER_CONTRACTS §2 / §3).

Unknown-width / unknown-encoding fields stay out of the item
(``ta2tp_op_len``, ``ta2tp_mode``, rspst/rspinfo, 24-bit DCNA,
NTH.NLP→TAH). Wave-1 leaf ties ``sl`` / ``nlp`` / ``lbf`` / ``rt`` /
``cci`` to 0 (tp_uarch §11); the scoreboard still compares those
outputs.
"""

from __future__ import annotations

from dataclasses import dataclass

from model.tp.ub_tp_bypass import (
    CFG_BYPASS,
    Flit,
    NwTxPacket,
    NwTxSideband,
    TaDelivery,
    check_payload,
)


# Wave-1 DUT has no TA-side source for these; outputs are tied 0.
LEAF_SIDEBAND = NwTxSideband(sl=0, nlp=0, lbf=0, rt=0, cci=0)

TX_CHECKED: tuple[str, ...] = (
    "data",
    "sop",
    "eop",
    "bypass",
    "dcna",
    "sl",
    "nlp",
    "lbf",
    "rt",
    "cci",
)
RX_CHECKED: tuple[str, ...] = ("data", "sop", "eop", "err")
# Contract-unknown or not a DUT port — never compared.
UNCHECKED: tuple[str, ...] = (
    "ta2tp_op_len",
    "ta2tp_mode",
    "rspst",
    "rspinfo",
    "dcna24",
    "nw2tp_icrc_err",
    "nlp_tah",
    "opcode",
    "tassn",
    "tpmsn",
    "done",
    "fail",
)


def flits_from_data(data: tuple[int, ...]) -> tuple[Flit, ...]:
    if not data:
        raise ValueError("payload is empty")
    if len(data) == 1:
        return (Flit(data[0], sop=True, eop=True),)
    out = [Flit(data[0], sop=True, eop=False)]
    for word in data[1:-1]:
        out.append(Flit(word, sop=False, eop=False))
    out.append(Flit(data[-1], sop=False, eop=True))
    return check_payload(tuple(out))


@dataclass(frozen=True)
class TxSpec:
    """One TA→NW bypass packet (1 flit / beat)."""

    data: tuple[int, ...]
    dcna: int
    tassn: int = 1


@dataclass(frozen=True)
class RxSpec:
    """One NW→TA bypass packet. ``drop`` is model-only (no DUT pin)."""

    data: tuple[int, ...]
    err: bool = False
    drop: bool = False
    tassn: int | None = None


@dataclass(frozen=True)
class ObservedTx:
    flits: tuple[Flit, ...]
    bypass: int
    dcna: int
    sl: int
    nlp: int
    lbf: int
    rt: int
    cci: int

    def as_packet(self) -> NwTxPacket:
        return NwTxPacket(
            flits=self.flits,
            sl=self.sl,
            nlp=self.nlp,
            bypass=bool(self.bypass),
            dcna=self.dcna,
            lbf=self.lbf,
            rt=self.rt,
            cci=self.cci,
            cfg=CFG_BYPASS,
        )


@dataclass(frozen=True)
class ObservedRx:
    flits: tuple[Flit, ...]
    err: bool

    def as_delivery(self) -> TaDelivery:
        return TaDelivery(flits=self.flits, err=self.err)


__all__ = [
    "LEAF_SIDEBAND",
    "RX_CHECKED",
    "TX_CHECKED",
    "UNCHECKED",
    "ObservedRx",
    "ObservedTx",
    "RxSpec",
    "TxSpec",
    "flits_from_data",
]
