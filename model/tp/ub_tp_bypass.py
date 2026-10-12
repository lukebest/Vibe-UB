"""ub_tp_bypass golden (CODING_STYLE §5; architecture Xia).

CFG9 bypass transport, priority path. Transaction-level scoreboard
reference — RTL-independent, no cycle count, no TPH, no ICRC.

Interface source of truth: docs/arch/LAYER_CONTRACTS.md §2 / §3
(merged #59 / #63). Leaf inventory: MODULE_INVENTORY ``ub_tp_bypass``
(§6.3、§7.1). Mode text: UB §6.3 / §6.3.2; CFG9 and no ICRC: B.2.6.

Priority path (locked):

- Data ports 160 bit, 1 flit / cycle, valid/ready/sop/eop.
- TP→NW sidebands: sl[3:0], nlp[2:0], bypass=1, dcna[15:0],
  lbf[7:0], rt[1:0], cci[15:0].
- NW→TP: err (eop-aligned), icrc_err (held 0 in CFG9), flush,
  drop, nw_link_up.
- TA↔TP: ta2tp_op_* (opcode[7:0], tassn[15:0]), ta2tp_bypass,
  ta2tp_dcna[15:0], tp2ta_* delivery (done/fail/err, msn,
  op+payload).

TX maps ``ta2tp_dcna`` → ``tp2nw_dcna`` and forces ``tp2nw_bypass=1``.
Payload flits are copied as-is (no TPH bytes). SL / NLP / LBF / RT /
CCI are TP→NW request sidebands the caller supplies; this leaf copies
them. NLP is an opaque 3-bit value (TAH codepoint is unknown).

RX copies ``nw2tp_*`` payload to ``tp2ta_data_*``. ``nw2tp_err`` becomes
``tp2ta_err`` on the last-flit eop. ``nw2tp_drop`` discards that packet
(no TA delivery). ``nw2tp_icrc_err`` stays 0.

Bypass has no TPACK state machine (LAYER_CONTRACTS §3; §6.8).
``tp2ta_done`` / ``tp2ta_fail`` are environment-visible (peer TAACK or
local write complete; beat alignment unknown). ``flush`` / link-down
fail every pending tassn and complete every pending TPMSN the caller
already bound.

Do not copy UB Base Spec text. Cite section numbers only.

Unknowns
--------
These contract items stay out of the model API (widths / encodings
unlocked; this golden does not fill them):

- ``ta2tp_op_len`` width (LAYER_CONTRACTS §3; PR #58 Q-8)
- ``ta2tp_mode[1:0]`` encoding (ROI/ROT/ROL/UNO; §7.3.3–4)
- ``rspst`` / ``rspinfo`` widths (ROL ``ta2tp_cmp_*``; §6.2.1、§6.8.2)
- 24-bit DCNA / CNA format port width (priority path is 16-bit; §5.2.1)
- NTH.NLP → TAH codepoints (§5.2; PR #61)

Related unlocked items also omitted (not invented): packet byte cap,
flush beat count, pending-TASSN cap, ``tp2ta_fail`` reason codes,
RX ``nw2tp_scna`` / ``nw2tp_cci`` extra sidebands, NTH strip-or-not
on RX, TPMSN assign beat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

# LAYER_CONTRACTS §2 / §3; UB §4.3.2.1 / SPEC M1 FLIT_W.
FLIT_W = 160
FLITS_PER_BEAT = 1
FLIT_MASK = (1 << FLIT_W) - 1

# LPH.CFG bypass = 9 (LAYER_CONTRACTS §2; UB §4.3.2.2.2、§6.3.2、B.2.6).
CFG_BYPASS = 9

SL_W = 4
NLP_W = 3
DCNA_W = 16
LBF_W = 8
RT_W = 2
CCI_W = 16
OPCODE_W = 8
TASSN_W = 16
TPMSN_W = 24

SL_MASK = (1 << SL_W) - 1
NLP_MASK = (1 << NLP_W) - 1
DCNA_MASK = (1 << DCNA_W) - 1
LBF_MASK = (1 << LBF_W) - 1
RT_MASK = (1 << RT_W) - 1
CCI_MASK = (1 << CCI_W) - 1
OPCODE_MASK = (1 << OPCODE_W) - 1
TASSN_MASK = (1 << TASSN_W) - 1
TPMSN_MASK = (1 << TPMSN_W) - 1

UNKNOWNS: tuple[str, ...] = (
    "ta2tp_op_len width",
    "ta2tp_mode[1:0] encoding",
    "rspst / rspinfo widths",
    "24-bit DCNA port width",
    "NTH.NLP → TAH codepoints",
)


class UbTpBypassError(ValueError):
    """Illegal bypass transaction (width, framing, or contract rule)."""


def _fit(name: str, value: int, width: int, mask: int) -> int:
    v = int(value)
    if v < 0 or v > mask:
        raise UbTpBypassError(f"{name}={value} does not fit {width} bits")
    return v


def _as_bool(value: bool | int, name: str) -> bool:
    if value in (0, 1, False, True):
        return bool(value)
    raise UbTpBypassError(f"{name} must be 0 or 1, got {value!r}")


@dataclass(frozen=True)
class Flit:
    """One 160-bit payload flit with sop/eop (LAYER_CONTRACTS §2 / §3)."""

    data: int
    sop: bool
    eop: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _fit("data", self.data, FLIT_W, FLIT_MASK))
        object.__setattr__(self, "sop", _as_bool(self.sop, "sop"))
        object.__setattr__(self, "eop", _as_bool(self.eop, "eop"))


@dataclass(frozen=True)
class TaOp:
    """TA→TP submit descriptor, locked fields only (LAYER_CONTRACTS §3).

    ``opcode[7:0]``, ``tassn[15:0]``, ``bypass``, ``dcna[15:0]``.
    ``mode`` and ``op_len`` are omitted (unknowns).
    """

    opcode: int
    tassn: int
    bypass: bool
    dcna: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "opcode", _fit("ta2tp_opcode", self.opcode, OPCODE_W, OPCODE_MASK)
        )
        object.__setattr__(
            self, "tassn", _fit("ta2tp_tassn", self.tassn, TASSN_W, TASSN_MASK)
        )
        object.__setattr__(self, "bypass", _as_bool(self.bypass, "ta2tp_bypass"))
        object.__setattr__(
            self, "dcna", _fit("ta2tp_dcna", self.dcna, DCNA_W, DCNA_MASK)
        )


@dataclass(frozen=True)
class NwTxSideband:
    """TP→NW request sidebands other than dcna/bypass (LAYER_CONTRACTS §2).

    Caller supplies sl / nlp / lbf / rt / cci. NLP is stored as a 3-bit
    integer; this model does not map it to a TAH codepoint.
    """

    sl: int
    nlp: int
    lbf: int
    rt: int
    cci: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "sl", _fit("tp2nw_sl", self.sl, SL_W, SL_MASK))
        object.__setattr__(self, "nlp", _fit("tp2nw_nlp", self.nlp, NLP_W, NLP_MASK))
        object.__setattr__(self, "lbf", _fit("tp2nw_lbf", self.lbf, LBF_W, LBF_MASK))
        object.__setattr__(self, "rt", _fit("tp2nw_rt", self.rt, RT_W, RT_MASK))
        object.__setattr__(self, "cci", _fit("tp2nw_cci", self.cci, CCI_W, CCI_MASK))


@dataclass(frozen=True)
class NwTxPacket:
    """One TA→NW bypass packet after mapping (no TPH)."""

    flits: tuple[Flit, ...]
    sl: int
    nlp: int
    bypass: bool
    dcna: int
    lbf: int
    rt: int
    cci: int
    cfg: int = CFG_BYPASS


@dataclass(frozen=True)
class TaDelivery:
    """TP→TA receive delivery (LAYER_CONTRACTS §3 ``tp2ta_op_*`` / data).

    ``tassn`` / ``tpmsn`` are environment tags (TAH layout is not parsed).
    """

    flits: tuple[Flit, ...]
    err: bool
    tassn: int | None = None
    tpmsn: int | None = None


@dataclass(frozen=True)
class TaComplete:
    """``tp2ta_done`` / ``tp2ta_fail`` (mutex) plus optional ``tp2ta_msn_*``."""

    tassn: int
    done: bool
    fail: bool
    tpmsn: int | None = None

    def __post_init__(self) -> None:
        if self.done == self.fail:
            raise UbTpBypassError("tp2ta_done and tp2ta_fail must be mutex")


def check_payload(flits: Sequence[Flit]) -> tuple[Flit, ...]:
    """sop…eop framing: one packet, contiguous, 1 flit / beat.

    LAYER_CONTRACTS §2 assertions 1 and 6: ``sop&&eop`` is legal;
    another packet must not appear between sop and eop.
    """
    if not flits:
        raise UbTpBypassError("payload is empty")
    out = tuple(flits)
    if not out[0].sop:
        raise UbTpBypassError("first flit must have sop=1")
    if not out[-1].eop:
        raise UbTpBypassError("last flit must have eop=1")
    for i, flit in enumerate(out):
        if i > 0 and flit.sop:
            raise UbTpBypassError("sop inside an open packet")
        if i < len(out) - 1 and flit.eop:
            raise UbTpBypassError("eop before the last flit")
    return out


@dataclass
class _Pending:
    op: TaOp
    tpmsn: int | None


class UbTpBypass:
    """Transaction-level golden for leaf ``ub_tp_bypass``.

    ``submit()`` is a TA→NW handshake that already completed
    (valid&&ready). ``receive()`` is the matching NW→TA delivery.
    Cycle-accurate ready backpressure is outside this model.
    """

    def __init__(self) -> None:
        self.nw_link_up = True
        self.flush = False
        self.nw2tp_icrc_err = 0
        self._pending: dict[int, _Pending] = {}

    @property
    def name(self) -> str:
        return "ub_tp_bypass"

    @property
    def pending_tassn(self) -> frozenset[int]:
        return frozenset(self._pending)

    def reset(self) -> None:
        """Clear pending ops. Entity reset (LAYER_CONTRACTS §3 / §10.6.1)."""
        self._pending.clear()
        self.nw_link_up = True
        self.flush = False
        self.nw2tp_icrc_err = 0

    def submit(
        self,
        op: TaOp,
        payload: Sequence[Flit],
        sideband: NwTxSideband,
        *,
        tpmsn: int | None = None,
    ) -> NwTxPacket:
        """TA→NW: copy payload, map TA fields, attach NW sidebands.

        ``ta2tp_bypass`` must be 1. ``tp2nw_bypass`` is 1. No TPH is
        inserted (§6.3、B.2.6). ``nw_link_up==0`` or ``flush`` rejects
        a new packet (LAYER_CONTRACTS §2).
        """
        if not self.nw_link_up:
            raise UbTpBypassError("nw_link_up==0: no TX handshake")
        if self.flush:
            raise UbTpBypassError("flush: new packet is rejected")
        if not op.bypass:
            raise UbTpBypassError("ub_tp_bypass requires ta2tp_bypass==1")
        if op.tassn in self._pending:
            raise UbTpBypassError(f"tassn={op.tassn} already pending")
        flits = check_payload(payload)
        msn = None if tpmsn is None else _fit("tp2ta_tpmsn", tpmsn, TPMSN_W, TPMSN_MASK)
        self._pending[op.tassn] = _Pending(op=op, tpmsn=msn)
        return NwTxPacket(
            flits=flits,
            sl=sideband.sl,
            nlp=sideband.nlp,
            bypass=True,
            dcna=op.dcna,
            lbf=sideband.lbf,
            rt=sideband.rt,
            cci=sideband.cci,
            cfg=CFG_BYPASS,
        )

    def receive(
        self,
        payload: Sequence[Flit],
        *,
        err: bool | int = False,
        drop: bool | int = False,
        tassn: int | None = None,
        tpmsn: int | None = None,
    ) -> TaDelivery | None:
        """NW→TA: copy payload; map err; honour drop.

        ``nw2tp_icrc_err`` is held at 0 (CFG9, B.2.6). ``drop`` discards
        the packet (LAYER_CONTRACTS §2). ``err`` is meaningful on eop
        and becomes ``tp2ta_err``.
        """
        self.nw2tp_icrc_err = 0
        drop_b = _as_bool(drop, "nw2tp_drop")
        err_b = _as_bool(err, "nw2tp_err")
        flits = check_payload(payload)
        if drop_b:
            return None
        tag = None if tassn is None else _fit("tp2ta_tassn", tassn, TASSN_W, TASSN_MASK)
        msn = None if tpmsn is None else _fit("tp2ta_tpmsn", tpmsn, TPMSN_W, TPMSN_MASK)
        return TaDelivery(flits=flits, err=err_b, tassn=tag, tpmsn=msn)

    def complete(
        self,
        tassn: int,
        *,
        fail: bool = False,
        tpmsn: int | None = None,
    ) -> TaComplete:
        """Record ``tp2ta_done`` or ``tp2ta_fail`` for a pending tassn.

        Beat vs TAACK / local write is unknown (LAYER_CONTRACTS §3);
        the caller fires this when that completion is observed.
        """
        tag = _fit("tp2ta_tassn", tassn, TASSN_W, TASSN_MASK)
        pending = self._pending.pop(tag, None)
        if pending is None:
            raise UbTpBypassError(f"tassn={tag} is not pending")
        msn = pending.tpmsn if tpmsn is None else _fit(
            "tp2ta_tpmsn", tpmsn, TPMSN_W, TPMSN_MASK
        )
        return TaComplete(tassn=tag, done=not fail, fail=bool(fail), tpmsn=msn)

    def apply_drop(self, tassn: int) -> TaComplete:
        """NW drop of a tracked packet: no data delivery, fail that tassn."""
        return self.complete(tassn, fail=True)

    def apply_flush(self) -> tuple[TaComplete, ...]:
        """``nw2tp_flush``: fail every pending tassn (LAYER_CONTRACTS §3).

        Flush beat count is unknown; this is the transaction result
        (empty pending set).
        """
        self.flush = True
        return self._fail_all_pending()

    def apply_link_down(self) -> tuple[TaComplete, ...]:
        """``nw_link_up==0``: no further TX; fail pending; hold flush."""
        self.nw_link_up = False
        self.flush = True
        return self._fail_all_pending()

    def end_flush(self) -> None:
        """Release flush after pending set is empty."""
        if self._pending:
            raise UbTpBypassError("flush ends only when no tassn is pending")
        if self.nw_link_up:
            self.flush = False

    def _fail_all_pending(self) -> tuple[TaComplete, ...]:
        tags = tuple(sorted(self._pending))
        out: list[TaComplete] = []
        for tag in tags:
            out.append(self.complete(tag, fail=True))
        return tuple(out)


def iter_tx_beats(packet: NwTxPacket) -> Iterable[dict[str, int | bool]]:
    """Expand a packet to 1-flit-per-beat records (priority path)."""
    for flit in packet.flits:
        yield {
            "tp2nw_data": flit.data,
            "tp2nw_sop": flit.sop,
            "tp2nw_eop": flit.eop,
            "tp2nw_sl": packet.sl,
            "tp2nw_nlp": packet.nlp,
            "tp2nw_bypass": 1,
            "tp2nw_dcna": packet.dcna,
            "tp2nw_lbf": packet.lbf,
            "tp2nw_rt": packet.rt,
            "tp2nw_cci": packet.cci,
        }
