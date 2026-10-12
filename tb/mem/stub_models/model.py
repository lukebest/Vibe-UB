"""Cycle-accurate stub decoder. Ports / latency / encodings come from the contract.

The model never inspects bit fields inside ``raw``. Illegal beats are
injected by ``set_inject``. PTW descriptor outcomes are selected by a
symbolic encoding class (``ENC_INVALID`` / ``ENC_TBL_PG`` / ``ENC_BLOCK``)
crossed with ``desc_lvl``. The stub does not decode ``raw``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Iterable

from .asserts import ContractAssertionError, InterfaceChecker
from .contract_encodings import (
    ENC_CLASSES,
    EncClassTable,
    EncodingTable,
    encodings_from_header,
    load_enc_class_table,
)
from .contract_yaml import ContractHeader, LatencySpec, parse_latency
from .coverage import StubModelCoverage


def _mask(width: int) -> int:
    return (1 << width) - 1


def _bit(values: dict[str, int], name: str, default: int = 0) -> int:
    return int(values.get(name, default)) & 1


def _rand_bits(rng: random.Random, width: int | None) -> int:
    if width is None:
        return rng.getrandbits(16)
    if width <= 0:
        return 0
    return rng.getrandbits(width) & _mask(width)


def _as_injects(symbols: str | Iterable[str] | None) -> tuple[str, ...]:
    if symbols is None:
        return ()
    if isinstance(symbols, str):
        return (symbols,) if symbols else ()
    return tuple(str(s) for s in symbols if s)


@dataclass
class _Payload:
    sideband: dict[str, int]
    injects: tuple[str, ...]
    latency: LatencySpec
    overlay: dict[str, int]
    enc_class: str | None = None


@dataclass
class StubDecoderBase:
    header: ContractHeader
    encoding: EncodingTable | None = None
    seed: int = 0
    enc_table: EncClassTable | None = None

    def __post_init__(self) -> None:
        if self.encoding is None:
            self.encoding = encodings_from_header(self.header)
        if self.enc_table is None:
            self.enc_table = load_enc_class_table(self.header)
        self.rng = random.Random(self.seed)
        self.coverage = StubModelCoverage(self.header.leaf, self.enc_table)
        self.checker = InterfaceChecker.from_header(self.header, self.encoding, self.enc_table)
        self._injects: tuple[str, ...] = ()
        self._enc_class: str | None = None
        self._overlay: dict[str, int] = {}
        self._inflight: _Payload | None = None
        self._held: dict[str, int] | None = None
        self._held_ctrl: dict[str, Any] | None = None
        self._since_rel = 0
        self._rst_name = self.header.clock.reset
        self.checker._check_clk()
        self._check_encoding_fits()

    @property
    def leaf(self) -> str:
        return self.header.leaf

    @property
    def port_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.header.ports)

    @property
    def port_widths(self) -> dict[str, int | None]:
        return {p.name: p.width for p in self.header.ports}

    @property
    def latency_cycles(self) -> int:
        return self.header.latency.cycles

    @property
    def latency_upper_bound(self) -> int:
        return self.header.latency.max_cycles

    def set_inject(self, symbols: str | Iterable[str] | None) -> None:
        injects = _as_injects(symbols)
        for name in injects:
            if name not in self.encoding.ill_cause:
                raise ValueError(f"{name} not in contract ill_cause map {sorted(self.encoding.ill_cause)}")
        self._injects = injects

    def set_legal_overlay(self, fields: dict[str, int] | None) -> None:
        """Force named legal outputs (still zeroed when a beat is illegal)."""
        self._overlay = {} if not fields else {str(k): int(v) for k, v in fields.items()}

    def set_enc_class(self, enc_class: str | None) -> None:
        """Select the input encoding class symbolically. No bit encoding."""
        if enc_class is None:
            self._enc_class = None
            return
        name = str(enc_class)
        allowed = self.enc_table.classes if self.enc_table is not None else ENC_CLASSES
        if name not in allowed:
            raise ValueError(f"{name} is not a contract encoding class {allowed}")
        self._enc_class = name

    def _check_encoding_fits(self) -> None:
        width = self.header.ill_cause_width
        for name, value in self.encoding.ill_cause.items():
            if value < 0 or value > _mask(width):
                raise ContractAssertionError(
                    "ENC",
                    f"{name}={value} does not fit ill_cause_width={width} (from {self.encoding.source})",
                )

    def _ctrl_in_names(self) -> tuple[str, ...]:
        skip = {self.header.clock.name, self.header.clock.reset, "in_valid", "out_ready"}
        return tuple(p.name for p in self.header.in_ports() if p.name not in skip)

    def _data_out_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.header.out_ports() if p.name not in {"in_ready", "out_valid"})

    def _ill_ports(self) -> tuple[str, str]:
        illegal = next(p.name for p in self.header.out_ports() if p.name.endswith("_illegal"))
        cause = next(p.name for p in self.header.out_ports() if p.name.endswith("_ill_cause"))
        return illegal, cause

    def _l1_latency(self) -> LatencySpec | None:
        raw = self.header.param("l1_latency")
        if raw is None:
            raw = self.header.extra.get("l1_latency")
        if raw is not None:
            return parse_latency(raw, field_name="l1_latency")
        cycles = self.header.param("l1_latency_cycles")
        if cycles is not None:
            n = int(cycles)
            return LatencySpec(kind="registered", cycles=n, max_cycles=n)
        if self.header.has_port("src_l1"):
            return LatencySpec(kind="registered", cycles=1, max_cycles=1)
        return None

    def _latency_for(self, sideband: dict[str, int]) -> LatencySpec:
        if self.header.has_port("src_l1") and sideband.get("src_l1", 0):
            alt = self._l1_latency()
            if alt is not None:
                return alt
        return self.header.latency

    def _zeros(self) -> dict[str, int]:
        return {name: 0 for name in self._data_out_names()}

    def _chosen_cause(self, injects: tuple[str, ...]) -> int:
        codes = [self.encoding.ill_code(n) for n in injects]
        nonzero = [c for c in codes if c]
        if not nonzero:
            return self.encoding.ill_cause.get("ILL_NONE", 0)
        if self.encoding.cause_priority == "min_nonzero":
            return min(nonzero)
        return nonzero[0]

    def _legal_range(self, port_name: str) -> tuple[int, int] | None:
        if self.header.has_port(port_name):
            span = self.header.port(port_name).legal
            if span is not None:
                return span
        key = f"{port_name}_legal"
        raw = self.header.param(key)
        if raw is None:
            raw = self.header.extra.get(key)
        if raw is None:
            return None
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            return int(raw[0]), int(raw[1])
        if isinstance(raw, dict) and "min" in raw and "max" in raw:
            return int(raw["min"]), int(raw["max"])
        return None

    def _pick_enc_class(self) -> str | None:
        if self._enc_class is not None:
            return self._enc_class
        if self.enc_table is None:
            return None
        return self.rng.choice(list(self.enc_table.classes))

    def _make_result(self, payload: _Payload) -> dict[str, int]:
        out: dict[str, int] = {}
        illegal_name, cause_name = self._ill_ports()
        cause = self._chosen_cause(payload.injects)
        is_ill = cause != 0
        for port in self.header.out_ports():
            if port.name in {"in_ready", "out_valid", illegal_name, cause_name}:
                continue
            if self.encoding.zero_outputs_on_illegal and is_ill:
                out[port.name] = 0
                continue
            span = self._legal_range(port.name)
            if span is not None:
                lo, hi = span
                out[port.name] = self.rng.randint(lo, hi)
            else:
                out[port.name] = _rand_bits(self.rng, port.width)
            if port.name in payload.overlay and not is_ill:
                out[port.name] = payload.overlay[port.name]
        if is_ill:
            out[illegal_name] = 1
            out[cause_name] = cause
        else:
            out[illegal_name] = 0
            out[cause_name] = self.encoding.ill_cause.get("ILL_NONE", 0)
            if (
                self.enc_table is None
                and "desc_kind" in out
                and "desc_kind" not in payload.overlay
                and self.encoding.desc_kind
            ):
                out["desc_kind"] = self.rng.choice(list(self.encoding.desc_kind.values()))
            if self.header.has_port("mapte_last") and payload.sideband.get("mode_multi", 0) == 0:
                out["mapte_last"] = 1
        self._apply_enc_class(out, payload, is_ill)
        self.coverage.sample("illegal" if is_ill else "legal")
        for name in payload.injects:
            self.coverage.sample(name)
        return out

    def _apply_enc_class(self, out: dict[str, int], payload: _Payload, is_ill: bool) -> None:
        table = self.enc_table
        if table is None or payload.enc_class is None:
            return
        if is_ill:
            return
        level = int(payload.sideband.get(table.port, 0))
        cell = table.cell(level, payload.enc_class)
        illegal_name, cause_name = self._ill_ports()
        none = self.encoding.ill_cause.get("ILL_NONE", 0)
        if cell.fault:
            if "desc_v" in out:
                out["desc_v"] = 0
            if "desc_kind" in out:
                out["desc_kind"] = self.encoding.kind_code("invalid")
            out[illegal_name] = 0
            out[cause_name] = none
            return
        if "desc_v" in out:
            out["desc_v"] = 1
        if "desc_kind" in out:
            out["desc_kind"] = self.encoding.kind_code(cell.kind)
        out[illegal_name] = 0
        out[cause_name] = none

    def _pack(self, data: dict[str, int] | None, in_ready: int, out_valid: int) -> dict[str, int]:
        packed = {p.name: 0 for p in self.header.out_ports()}
        if data:
            packed.update(data)
        packed["in_ready"] = in_ready & 1
        packed["out_valid"] = out_valid & 1
        return packed

    def _rst_active(self, ins: dict[str, int]) -> bool:
        return int(ins.get(self._rst_name, 0)) == self.encoding.rst_active

    def _compute_in_ready(self, out_ready: int, outstanding: bool, since_rel: int) -> int:
        """Must not read this-cycle in_valid (AP_*_RDY).

        One outstanding beat: ``in_ready=0`` while a result is held or
        pipelined. That keeps L0 from overwriting a beat still on the
        output (OUT_HOLD / single-undecoded). ``out_ready`` is accepted
        so the signature stays stable; occupancy already covers stall.
        """
        if since_rel <= 0:
            return 0
        if outstanding:
            return 0
        return 1

    def _ctrl_of(self, payload: _Payload) -> dict[str, Any]:
        return {
            "injects": payload.injects,
            "sideband": payload.sideband,
            "mode_multi": payload.sideband.get("mode_multi"),
            "enc_class": payload.enc_class,
        }

    def step(self, ins: dict[str, int]) -> dict[str, int]:
        rst = 1 if self._rst_active(ins) else 0
        out_ready = _bit(ins, "out_ready")
        in_valid = _bit(ins, "in_valid")

        if rst:
            self._inflight = None
            self._held = None
            self._held_ctrl = None
            self._since_rel = 0
            outs = self._pack(self._zeros(), 0, 0)
            self.coverage.sample("reset")
            self.checker.check_cycle(
                ins,
                outs,
                rst=1,
                accepted=False,
                latency=None,
                injects=(),
                ready_without_valid=0,
                new_result=False,
                result_ctrl={},
                since_release=0,
            )
            return outs

        presented_pipe = False
        if self._inflight is not None and self._held is None:
            self._held = self._make_result(self._inflight)
            self._held_ctrl = self._ctrl_of(self._inflight)
            self._inflight = None
            presented_pipe = True

        outstanding = self._held is not None or self._inflight is not None
        ready_probe = self._compute_in_ready(out_ready, outstanding, self._since_rel)
        in_ready = ready_probe
        accepted = bool(in_valid and in_ready)
        acc_lat: LatencySpec | None = None
        acc_injects = self._injects
        new_result = presented_pipe
        accepted_enc: str | None = None

        if accepted:
            sideband = {name: int(ins.get(name, 0)) for name in self._ctrl_in_names()}
            acc_lat = self._latency_for(sideband)
            accepted_enc = self._pick_enc_class()
            payload = _Payload(
                sideband=sideband,
                injects=self._injects,
                latency=acc_lat,
                overlay=dict(self._overlay),
                enc_class=accepted_enc,
            )
            self.coverage.sample("accept")
            if self.enc_table is not None and accepted_enc is not None:
                level = int(sideband.get(self.enc_table.port, 0))
                self.coverage.sample_lvl_x_enc(level, accepted_enc)
            if acc_lat.cycles == 0:
                self._held = self._make_result(payload)
                self._held_ctrl = self._ctrl_of(payload)
                new_result = True
            elif acc_lat.cycles == 1:
                self._inflight = payload
            else:
                raise ContractAssertionError(
                    self.checker.wants("LAT1") or "LAT",
                    f"stub only models 0/1 cycle latency, got {acc_lat.cycles}",
                )
        else:
            self.coverage.sample("stall_or_idle")

        cycle_out = self._held
        cycle_ctrl = dict(self._held_ctrl or {})
        cycle_ctrl["accepted_enc_class"] = accepted_enc
        cycle_valid = cycle_out is not None
        if cycle_valid and not out_ready:
            self.coverage.sample("backpressure")
        if cycle_valid and out_ready:
            snap = cycle_out
            self._held = None
            self._held_ctrl = None
        else:
            snap = cycle_out

        self._since_rel += 1
        outs = self._pack(snap if cycle_valid else self._zeros(), in_ready, int(cycle_valid))
        self.checker.check_cycle(
            ins,
            outs,
            rst=0,
            accepted=accepted,
            latency=acc_lat,
            injects=acc_injects,
            ready_without_valid=ready_probe,
            new_result=new_result,
            result_ctrl=cycle_ctrl,
            since_release=self._since_rel,
        )
        return outs
