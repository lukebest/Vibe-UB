"""Python-side contract interface assertions.

When the YAML header has ``assertions``, only those names are checked.
Otherwise the checker uses the ``AP_*`` names in the Markdown body.
If the body has none, it falls back to the published suffix set.

Checks only use ports visible at the stub boundary. Properties that
need a ``raw`` field decode are recorded as skipped, not guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .contract_encodings import EncClassTable, EncodingTable, markdown_assertion_names
from .contract_yaml import ContractHeader, LatencySpec


class ContractAssertionError(AssertionError):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(f"{name}: {message}")
        self.assertion = name


def _bit(values: dict[str, int], name: str, default: int = 0) -> int:
    return int(values.get(name, default)) & 1


def _mask(width: int) -> int:
    return (1 << width) - 1


def assertion_suffix(name: str) -> str:
    """AP_PTW_ILL_2MB -> ILL_2MB; AP_DENT_LAT_L0 -> LAT_L0."""
    text = name.strip()
    if text.startswith("AP_"):
        text = text[3:]
    parts = text.split("_")
    if len(parts) >= 2:
        return "_".join(parts[1:])
    return text


FALLBACK_SUFFIXES: tuple[str, ...] = (
    "CLK",
    "HS_IN",
    "RDY",
    "LAT1",
    "LAT_L0",
    "LAT_L1",
    "HS_OUT",
    "OUT_HOLD",
    "IN_RDY_RST",
    "RST",
    "ILL_EQ",
    "ILL_ZERO",
    "ILL_PRI",
    "ILL_2MB",
    "ILL_AD",
    "ILL_S2",
    "ILL_OBLK",
    "ILL_HOLD",
    "KIND",
    "KIND_LVL",
    "LVL",
    "XCLASS",
    "FAULT",
    "BLOCK",
    "BB_SZ",
    "SINGLE_LAST",
    "EID_W",
)

# Observable only with a raw-field decode or a nanosecond timing check.
NOT_AT_STUB: frozenset[str] = frozenset({"SEL", "AF", "COMB_BUDGET"})


@dataclass
class BeatRecord:
    cycle: int
    latency: int
    upper: int
    injects: tuple[str, ...]
    src_l1: int | None
    mode_multi: int | None
    enc_class: str | None = None
    desc_lvl: int | None = None
    presented: bool = False


@dataclass
class InterfaceChecker:
    header: ContractHeader
    encoding: EncodingTable
    enabled: tuple[str, ...]
    enc_table: EncClassTable | None = None
    pending: list[BeatRecord] = field(default_factory=list)
    cycle: int = 0
    prev_ins: dict[str, int] | None = None
    prev_outs: dict[str, int] | None = None
    prev_rst: int = 1
    skipped: list[str] = field(default_factory=list)

    @classmethod
    def from_header(
        cls,
        header: ContractHeader,
        encoding: EncodingTable,
        enc_table: EncClassTable | None = None,
    ) -> InterfaceChecker:
        if header.assertions:
            enabled = header.assertion_names()
        else:
            md = markdown_assertion_names(header)
            if md:
                enabled = md
            else:
                prefix = _prefix_for(header.leaf)
                enabled = tuple(f"{prefix}_{sfx}" for sfx in FALLBACK_SUFFIXES)
        return cls(header=header, encoding=encoding, enabled=enabled, enc_table=enc_table)

    def wants(self, suffix: str) -> str | None:
        for name in self.enabled:
            if assertion_suffix(name) == suffix:
                return name
        return None

    def check(self, suffix: str, cond: bool, message: str) -> None:
        name = self.wants(suffix)
        if name is None:
            return
        if suffix in NOT_AT_STUB:
            if name not in self.skipped:
                self.skipped.append(name)
            return
        if not cond:
            raise ContractAssertionError(name, message)

    def reset(self) -> None:
        self.pending.clear()
        self.cycle = 0
        self.prev_ins = None
        self.prev_outs = None
        self.prev_rst = 1

    def check_cycle(
        self,
        ins: dict[str, int],
        outs: dict[str, int],
        *,
        rst: int,
        accepted: bool,
        latency: LatencySpec | None,
        injects: tuple[str, ...],
        ready_without_valid: int,
        new_result: bool,
        result_ctrl: dict[str, Any],
        since_release: int,
    ) -> None:
        self._check_clk()
        self._check_widths(outs)
        if rst:
            self.check("RST", all(int(outs.get(p.name, 0)) == 0 for p in self.header.out_ports()), "reset outputs not all 0")
            self.pending.clear()
        else:
            self.check(
                "RDY",
                _bit(outs, "in_ready") == (ready_without_valid & 1),
                f"in_ready={outs.get('in_ready')} depends on this-cycle in_valid (probe={ready_without_valid})",
            )
            self._check_in_rdy_rst(outs, ins, since_release)
            self._check_hold_in(ins)
            self._check_hold_out(outs, ins)
            if accepted:
                if latency is None:
                    raise ContractAssertionError(self.wants("LAT1") or "LAT", "accept without latency")
                self.pending.append(
                    BeatRecord(
                        cycle=self.cycle,
                        latency=latency.cycles,
                        upper=latency.max_cycles,
                        injects=injects,
                        src_l1=int(ins["src_l1"]) if "src_l1" in ins else None,
                        mode_multi=int(ins["mode_multi"]) if "mode_multi" in ins else None,
                        enc_class=result_ctrl.get("accepted_enc_class"),
                        desc_lvl=int(ins["desc_lvl"]) if "desc_lvl" in ins else None,
                    )
                )
                self._check_lvl(ins)
            if new_result:
                self._on_new_result(outs, result_ctrl)
            if _bit(outs, "out_valid"):
                self._check_out_valid_props(ins, outs, result_ctrl)
            self._check_latency_bound()
        self.prev_ins = dict(ins)
        self.prev_outs = dict(outs)
        self.prev_rst = rst
        self.cycle += 1

    def _check_clk(self) -> None:
        names = [p.name for p in self.header.ports]
        self.check("CLK", self.header.clock.name in names, f"clock {self.header.clock.name} missing")
        self.check("CLK", self.header.clock.reset in names, f"reset {self.header.clock.reset} missing")
        extra = [n for n in names if n.endswith("_clk") and n != self.header.clock.name]
        self.check("CLK", not extra, f"extra clocks {extra}")

    def _check_widths(self, outs: dict[str, int]) -> None:
        for port in self.header.out_ports():
            if port.width is None:
                continue
            value = int(outs.get(port.name, 0))
            if value < 0 or value > _mask(port.width):
                raise ContractAssertionError(
                    self.wants("RST") or "WIDTH",
                    f"{port.name}={value} does not fit width {port.width}",
                )

    def _check_in_rdy_rst(self, outs: dict[str, int], ins: dict[str, int], since_release: int) -> None:
        ready = _bit(outs, "in_ready")
        stalled = _bit(outs, "out_valid") and not _bit(ins, "out_ready")
        presenting = _bit(outs, "out_valid")
        if since_release <= 0:
            return
        if since_release == 1:
            return
        # Occupied output slot: in_ready stays 0 so L0 cannot overwrite.
        # Idle and not backpressured: Xia IN_RDY_RST requires 1.
        if not stalled and not presenting:
            self.check("IN_RDY_RST", ready == 1, f"since_release={since_release} in_ready={ready} expected 1")

    def _hold_in_names(self) -> tuple[str, ...]:
        skip = {self.header.clock.name, self.header.clock.reset, "in_valid", "out_ready"}
        return tuple(p.name for p in self.header.in_ports() if p.name not in skip)

    def _hold_out_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.header.out_ports() if p.name not in {"in_ready"})

    def _check_hold_in(self, ins: dict[str, int]) -> None:
        prev = self.prev_ins
        prev_outs = self.prev_outs
        if prev is None or prev_outs is None or self.prev_rst:
            return
        if _bit(prev, "in_valid") and not _bit(prev_outs, "in_ready"):
            for name in self._hold_in_names():
                self.check(
                    "HS_IN",
                    int(ins.get(name, 0)) == int(prev.get(name, 0)),
                    f"{name} changed while in_valid && !in_ready",
                )
            self.check("HS_IN", _bit(ins, "in_valid") == 1, "in_valid dropped before accept")

    def _check_hold_out(self, outs: dict[str, int], ins: dict[str, int]) -> None:
        prev_ins = self.prev_ins
        prev = self.prev_outs
        if prev is None or prev_ins is None or self.prev_rst:
            return
        if _bit(prev, "out_valid") and not _bit(prev_ins, "out_ready"):
            self.check("OUT_HOLD", _bit(outs, "out_valid") == 1, "out_valid dropped under backpressure")
            self.check("HS_OUT", _bit(outs, "out_valid") == 1, "out_valid dropped before accept")
            for name in self._hold_out_names():
                same = int(outs.get(name, 0)) == int(prev.get(name, 0))
                self.check("OUT_HOLD", same, f"{name} changed while out_valid && !out_ready")
                self.check("HS_OUT", same, f"{name} changed while out_valid && !out_ready")

    def _on_new_result(self, outs: dict[str, int], result_ctrl: dict[str, Any]) -> None:
        if not self.pending:
            raise ContractAssertionError(self.wants("LAT1") or "LAT", "new result with no accepted beat")
        open_beats = [b for b in self.pending if not b.presented]
        if not open_beats:
            raise ContractAssertionError(self.wants("LAT1") or "LAT", "new result but every beat already presented")
        beat = open_beats[0]
        beat.presented = True
        delay = self.cycle - beat.cycle
        if beat.latency == 0:
            self.check("LAT_L0", delay == 0, f"L0 delay {delay} != 0")
        elif beat.src_l1:
            self.check("LAT_L1", delay == beat.latency, f"L1 delay {delay} != {beat.latency}")
            self.check("LAT_L1", delay <= beat.upper, f"L1 delay {delay} > max_cycles {beat.upper}")
        else:
            self.check("LAT1", delay == beat.latency, f"delay {delay} != {beat.latency}")
            self.check("LAT1", delay <= beat.upper, f"delay {delay} > max_cycles {beat.upper}")
        self._check_injects(outs, beat.injects)

    def _check_latency_bound(self) -> None:
        for beat in self.pending:
            if beat.presented:
                continue
            waited = self.cycle - beat.cycle
            if waited > beat.upper:
                suffix = "LAT_L1" if beat.src_l1 else ("LAT_L0" if beat.latency == 0 else "LAT1")
                self.check(suffix, False, f"no out_valid within max_cycles {beat.upper} (waited {waited})")

    def _ill_ports(self) -> tuple[str, str]:
        illegal = next(p.name for p in self.header.out_ports() if p.name.endswith("_illegal"))
        cause = next(p.name for p in self.header.out_ports() if p.name.endswith("_ill_cause"))
        return illegal, cause

    def _check_injects(self, outs: dict[str, int], injects: tuple[str, ...]) -> None:
        _illegal_name, cause_name = self._ill_ports()
        cause = int(outs.get(cause_name, 0))
        codes = [self.encoding.ill_code(name) for name in injects if name in self.encoding.ill_cause]
        nonzero = [c for c in codes if c]
        if nonzero and self.encoding.cause_priority == "min_nonzero":
            expect = min(nonzero)
            self.check("ILL_PRI", cause == expect, f"cause {cause} != min {expect} of {nonzero}")
        if any(n == "ILL_MAP_2MB" for n in injects):
            self.check("ILL_2MB", cause == self.encoding.ill_code("ILL_MAP_2MB"), f"{cause_name}={cause}")
        if any(n == "ILL_HW_AD" for n in injects):
            self.check("ILL_AD", cause == self.encoding.ill_code("ILL_HW_AD"), f"{cause_name}={cause}")
        if any(n == "ILL_S2" for n in injects):
            self.check("ILL_S2", cause == self.encoding.ill_code("ILL_S2"), f"{cause_name}={cause}")
        if any(n == "ILL_MAPT_OTHER_BLK" for n in injects):
            self.check("ILL_OBLK", cause == self.encoding.ill_code("ILL_MAPT_OTHER_BLK"), f"{cause_name}={cause}")

    def _check_lvl(self, ins: dict[str, int]) -> None:
        if self.header.has_port("desc_lvl"):
            level = int(ins.get("desc_lvl", 0))
            self.check("LVL", level in {0, 1, 2, 3}, f"desc_lvl={level} not in L0..L3")
        if self.header.has_port("lvl"):
            span = self.header.port("lvl").legal or (0, 3)
            level = int(ins.get("lvl", 0))
            self.check("LVL", span[0] <= level <= span[1], f"lvl={level} not in {span}")

    def _check_enc_cross(self, outs: dict[str, int], result_ctrl: dict[str, Any]) -> None:
        table = self.enc_table
        if table is None:
            return
        enc = result_ctrl.get("enc_class")
        side = result_ctrl.get("sideband") or {}
        if enc is None:
            return
        level = int(side.get(table.port, 0))
        key = (level, str(enc))
        self.check("XCLASS", key in table.cells, f"({level}, {enc}) is not a contract cell")
        if key not in table.cells:
            return
        cell = table.cells[key]
        illegal_name, cause_name = self._ill_ports()
        illegal = _bit(outs, illegal_name)
        cause = int(outs.get(cause_name, 0))
        none = self.encoding.ill_cause.get("ILL_NONE", 0)
        if illegal:
            return
        if cell.fault:
            self.check("FAULT", _bit(outs, "desc_v") == 0, f"fault cell desc_v={outs.get('desc_v')}")
            self.check("FAULT", int(outs.get("desc_kind", 0)) == self.encoding.kind_code("invalid"), f"fault kind={outs.get('desc_kind')}")
            self.check("FAULT", illegal == 0, "fault cell must not be config-illegal")
            self.check("FAULT", cause == none, f"fault cause={cause} != ILL_NONE")
            return
        expect_kind = self.encoding.kind_code(cell.kind)
        self.check("KIND_LVL", int(outs.get("desc_kind", 0)) == expect_kind, f"kind={outs.get('desc_kind')} != {cell.kind}")
        self.check("KIND_LVL", _bit(outs, "desc_v") == 1, f"{enc} L{level} desc_v={outs.get('desc_v')}")
        self.check("KIND_LVL", illegal == 0, f"{enc} L{level} illegal")
        if enc == "ENC_BLOCK" and level in {1, 2}:
            self.check("BLOCK", int(outs.get("desc_kind", 0)) == self.encoding.kind_code("block"), f"block kind={outs.get('desc_kind')}")
            self.check("BLOCK", illegal == 0, "L1/L2 ENC_BLOCK must be legal")

    def _check_out_valid_props(self, ins: dict[str, int], outs: dict[str, int], result_ctrl: dict[str, Any]) -> None:
        illegal_name, cause_name = self._ill_ports()
        illegal = _bit(outs, illegal_name)
        cause = int(outs.get(cause_name, 0))
        allowed = set(self.encoding.ill_cause.values())
        self.check("ILL_EQ", illegal == int(cause != 0), f"{illegal_name}={illegal} {cause_name}={cause}")
        self.check("ILL_HOLD", cause in allowed, f"{cause_name}={cause} not in contract encoding")
        if illegal and self.encoding.zero_outputs_on_illegal:
            for port in self.header.out_ports():
                if port.name in {illegal_name, cause_name, "in_ready", "out_valid"}:
                    continue
                self.check("ILL_ZERO", int(outs.get(port.name, 0)) == 0, f"{port.name}={outs.get(port.name)} != 0")
        if self.header.has_port("desc_kind") and not illegal:
            kind = int(outs.get("desc_kind", 0))
            self.check("KIND", kind in set(self.encoding.desc_kind.values()), f"desc_kind={kind} not in contract map")
        if self.header.has_port("mapte_last"):
            multi = result_ctrl.get("mode_multi")
            if multi is None:
                multi = ins.get("mode_multi")
            if int(multi or 0) == 0 and not illegal:
                self.check("SINGLE_LAST", _bit(outs, "mapte_last") == 1, "mode_multi=0 requires last=1")
        if self.header.has_port("dent_eid"):
            eid_w = self.header.port("dent_eid").width
            expect = self.header.params.get("EID_W")
            if eid_w is not None and expect is not None:
                self.check("EID_W", int(eid_w) == int(expect), f"dent_eid width {eid_w} != EID_W {expect}")
        if self.header.has_port("ctx_mapt_bb_sz"):
            size = int(outs.get("ctx_mapt_bb_sz", 0))
            if not illegal:
                self.check("BB_SZ", 0 <= size <= 9, f"ctx_mapt_bb_sz={size} not in 0..9")
            elif 10 <= size <= 15:
                self.check("BB_SZ", cause == self.encoding.ill_code("ILL_RSVD"), f"bb_sz={size} cause={cause}")
        self._check_enc_cross(outs, result_ctrl)
        for suffix in NOT_AT_STUB:
            if self.wants(suffix):
                self.check(suffix, True, "")


def _prefix_for(leaf: str) -> str:
    table = {
        "ub_mem_ptw_desc_dec": "AP_PTW",
        "ub_mem_dec_ent_dec": "AP_DENT",
        "ub_mem_tecte_dec": "AP_TECTE",
        "ub_mem_tcte_dec": "AP_TCTE",
        "ub_mem_l1tct_dec": "AP_L1TCT",
        "ub_mem_mapte_dec": "AP_MAPTE",
    }
    if leaf in table:
        return table[leaf]
    token = leaf.replace("ub_mem_", "").replace("_dec", "").split("_")[0].upper()
    return f"AP_{token}"


CheckFn = Callable[..., None]
