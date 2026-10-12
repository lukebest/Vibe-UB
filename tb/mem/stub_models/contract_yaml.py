"""Load the fixed-field YAML header from a C-line decode-leaf contract.

Xia (#43) puts this block at the top of every
``docs/arch/mem/contracts/<leaf>.md`` (README §8). The gate will parse
the same block. This module is the only place that knows the header
shape.

Fixed keys: ``leaf``, ``parent``, ``clock`` (name, period_ns, reset,
reset type), ``latency`` (kind, cycles, max_cycles),
``ports`` (name, dir, width, desc), ``params`` (list of name/default),
``ill_cause_width``, ``status``.

Optional keys (parsed when present, ignored if absent):

- ``comb_budget_ns`` — withdrawn for ``ub_mem_dec_ent_dec`` (L0 is registered)
- ``assertions`` — one assertion per line / list / mapping
- encoding / policy maps (``ill_cause``, ``desc_kind``, ranges, …)

Widths may be an int, a params name (``EID_W``), or ``unknown``.
This file does not parse field bit positions out of ``raw``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contract_hash import contract_sha256

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "contract YAML header loader needs PyYAML (scripts/gate/requirements.txt)"
    ) from exc


class ContractHeaderError(ValueError):
    """Header missing, malformed, or a required field cannot be resolved."""


class ContractHeaderMissing(ContractHeaderError):
    """File has no YAML front matter / leading yaml fence."""


_FRONT_MATTER_RE = re.compile(
    r"\A\s*---[ \t]*\n(.*?)\n---[ \t]*\s*(?:\n|\Z)",
    re.S,
)
_FENCE_RE = re.compile(
    r"\A\s*(?:#[^\n]*\n\s*)?```ya?ml[ \t]*\n(.*?)\n```",
    re.S,
)

_LAT_COMB = {"combinational", "comb", "c", "combo", "0"}
_LAT_REG = {"registered", "reg", "r", "flop", "1"}
_LEGAL_RE = re.compile(r"合法\s*(\d+)\s*\.\.\s*(\d+)")

# Top-level keys that are first-class on ContractHeader. Everything
# else is kept in ``extra`` so a later #43 head can add fields without
# a loader rewrite beyond this set.
_CORE_KEYS = {
    "leaf",
    "parent",
    "clock",
    "latency",
    "comb_budget_ns",
    "ports",
    "params",
    "ill_cause_width",
    "status",
    "assertions",
}


def extract_yaml_header(text: str) -> str | None:
    """Return the raw YAML header text, or None if the file has none."""
    match = _FRONT_MATTER_RE.search(text)
    if match:
        return match.group(1)
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1)
    return None


def _pick(mapping: dict[str, Any], *names: str, required: bool = True, default: Any = None) -> Any:
    for name in names:
        if name in mapping and mapping[name] is not None:
            return mapping[name]
    if required:
        raise ContractHeaderError(f"missing field (tried {names})")
    return default


def _as_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractHeaderError(f"{field_name} must be an int, got {value!r}")
    return int(value)


def _as_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractHeaderError(f"{field_name} must be a number, got {value!r}")
    return float(value)


def _norm_dir(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"in", "input", "i"}:
        return "in"
    if text in {"out", "output", "o"}:
        return "out"
    raise ContractHeaderError(f"port dir {value!r} is not in/out")


def _norm_lat_kind(value: Any) -> str:
    text = str(value).strip().lower()
    if text in _LAT_COMB:
        return "combinational"
    if text in _LAT_REG:
        return "registered"
    raise ContractHeaderError(f"latency kind {value!r} is not combinational/registered")


def _params_map(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, list):
        raise ContractHeaderError("params must be a list of {name, default} or a mapping")
    out: dict[str, Any] = {}
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ContractHeaderError(f"params[{idx}] must be a mapping")
        name = str(_pick(item, "name"))
        out[name] = _pick(item, "default", "value", required=False, default=None)
    return out


def resolve_width(value: Any, params: dict[str, Any], port_name: str) -> tuple[int | None, bool]:
    """Return (width, unknown). ``unknown`` YAML stays unresolved."""
    if isinstance(value, str) and value.strip().lower() == "unknown":
        return None, True
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 1:
            raise ContractHeaderError(f"port {port_name} width {value} < 1")
        return value, False
    if isinstance(value, str):
        key = value.strip()
        if key in params and params[key] is not None:
            return resolve_width(params[key], params, port_name)
        if key.isdigit():
            return resolve_width(int(key), params, port_name)
    raise ContractHeaderError(
        f"port {port_name} width {value!r} is not an int, params name, or unknown"
    )


@dataclass(frozen=True)
class ClockSpec:
    name: str
    period_ns: float
    reset: str
    reset_type: str


@dataclass(frozen=True)
class LatencySpec:
    kind: str
    cycles: int
    max_cycles: int

    @property
    def type(self) -> str:
        return self.kind

    @property
    def upper_bound(self) -> int:
        return self.max_cycles


def parse_legal_span(text: str) -> tuple[int, int] | None:
    match = _LEGAL_RE.search(text or "")
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


@dataclass(frozen=True)
class PortSpec:
    name: str
    direction: str
    width: int | None
    description: str
    width_expr: int | str
    width_unknown: bool = False
    legal: tuple[int, int] | None = None


@dataclass(frozen=True)
class AssertionSpec:
    name: str
    text: str = ""


@dataclass(frozen=True)
class ContractHeader:
    leaf: str
    parent: str
    clock: ClockSpec
    latency: LatencySpec
    comb_budget_ns: float | None
    ports: tuple[PortSpec, ...]
    params: dict[str, Any] = field(default_factory=dict)
    ill_cause_width: int = 4
    status: str = "draft"
    assertions: tuple[AssertionSpec, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    def port(self, name: str) -> PortSpec:
        for item in self.ports:
            if item.name == name:
                return item
        raise KeyError(name)

    def has_port(self, name: str) -> bool:
        return any(p.name == name for p in self.ports)

    def port_map(self) -> dict[str, PortSpec]:
        return {item.name: item for item in self.ports}

    def in_ports(self) -> tuple[PortSpec, ...]:
        return tuple(p for p in self.ports if p.direction == "in")

    def out_ports(self) -> tuple[PortSpec, ...]:
        return tuple(p for p in self.ports if p.direction == "out")

    def param(self, name: str, default: Any = None) -> Any:
        if name in self.params:
            return self.params[name]
        return self.extra.get(name, default)

    def assertion_names(self) -> tuple[str, ...]:
        return tuple(a.name for a in self.assertions)


def parse_latency(raw: Any, *, field_name: str = "latency") -> LatencySpec:
    if not isinstance(raw, dict):
        raise ContractHeaderError(f"{field_name} must be a mapping")
    kind = _norm_lat_kind(_pick(raw, "kind", "type"))
    cycles = _as_int(_pick(raw, "cycles"), f"{field_name}.cycles")
    upper = _as_int(
        _pick(raw, "max_cycles", "upper_bound", "upper bound", "upper"),
        f"{field_name}.max_cycles",
    )
    if cycles < 0 or upper < 0:
        raise ContractHeaderError(f"{field_name} cycles/max_cycles must be >= 0")
    if cycles > upper:
        raise ContractHeaderError(f"{field_name} cycles {cycles} > max_cycles {upper}")
    if kind == "combinational" and cycles != 0:
        raise ContractHeaderError(f"{field_name} combinational cycles must be 0")
    return LatencySpec(kind=kind, cycles=cycles, max_cycles=upper)


def parse_assertions(raw: Any) -> tuple[AssertionSpec, ...]:
    """Accept a mapping, a list, or one-assertion-per-line text."""
    if raw is None:
        return ()
    items: list[AssertionSpec] = []
    if isinstance(raw, str):
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                name, text = line.split(":", 1)
                items.append(AssertionSpec(name.strip().strip("`"), text.strip()))
            else:
                items.append(AssertionSpec(line.strip().strip("`"), ""))
        return tuple(items)
    if isinstance(raw, dict):
        return tuple(
            AssertionSpec(str(key).strip().strip("`"), "" if val is None else str(val))
            for key, val in raw.items()
        )
    if isinstance(raw, list):
        for idx, item in enumerate(raw):
            if isinstance(item, str):
                items.extend(parse_assertions(item))
                continue
            if not isinstance(item, dict):
                raise ContractHeaderError(f"assertions[{idx}] must be a string or mapping")
            if "name" in item:
                items.append(
                    AssertionSpec(
                        str(item["name"]).strip().strip("`"),
                        str(item.get("text") or item.get("desc") or item.get("property") or ""),
                    )
                )
                continue
            if len(item) == 1:
                key, val = next(iter(item.items()))
                items.append(AssertionSpec(str(key).strip().strip("`"), "" if val is None else str(val)))
                continue
            raise ContractHeaderError(f"assertions[{idx}] needs name or a single key")
        return tuple(items)
    raise ContractHeaderError("assertions must be a list, mapping, or string")


def parse_contract_yaml(text: str, *, source: str = "") -> ContractHeader:
    """Parse a YAML header document (not the Markdown body)."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContractHeaderError(f"YAML parse failed{f' in {source}' if source else ''}: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractHeaderError("header YAML must be a mapping")

    params = _params_map(_pick(data, "params", required=False, default=[]))

    clock_raw = _pick(data, "clock")
    if not isinstance(clock_raw, dict):
        raise ContractHeaderError("clock must be a mapping")
    clock = ClockSpec(
        name=str(_pick(clock_raw, "name")),
        period_ns=_as_float(_pick(clock_raw, "period_ns"), "clock.period_ns"),
        reset=str(_pick(clock_raw, "reset")),
        reset_type=str(_pick(clock_raw, "reset_type", "reset type", "type")),
    )

    latency = parse_latency(_pick(data, "latency"))
    budget_raw = _pick(data, "comb_budget_ns", required=False, default=None)
    budget = None if budget_raw is None else _as_float(budget_raw, "comb_budget_ns")

    ports_raw = _pick(data, "ports")
    if not isinstance(ports_raw, list) or not ports_raw:
        raise ContractHeaderError("ports must be a non-empty list")
    ports: list[PortSpec] = []
    seen: set[str] = set()
    for idx, item in enumerate(ports_raw):
        if not isinstance(item, dict):
            raise ContractHeaderError(f"ports[{idx}] must be a mapping")
        name = str(_pick(item, "name"))
        if name in seen:
            raise ContractHeaderError(f"duplicate port {name}")
        seen.add(name)
        width_expr = _pick(item, "width")
        width, unknown = resolve_width(width_expr, params, name)
        desc = str(_pick(item, "desc", "description", required=False, default=""))
        legal = None
        if "legal" in item and item["legal"] is not None:
            raw_legal = item["legal"]
            if isinstance(raw_legal, (list, tuple)) and len(raw_legal) == 2:
                legal = (int(raw_legal[0]), int(raw_legal[1]))
        if legal is None:
            legal = parse_legal_span(desc)
        ports.append(
            PortSpec(
                name=name,
                direction=_norm_dir(_pick(item, "dir", "direction")),
                width=width,
                description=desc,
                width_expr=width_expr if isinstance(width_expr, (int, str)) else str(width_expr),
                width_unknown=unknown,
                legal=legal,
            )
        )

    extra = {key: data[key] for key in data if key not in _CORE_KEYS}
    header = ContractHeader(
        leaf=str(_pick(data, "leaf")),
        parent=str(_pick(data, "parent")),
        clock=clock,
        latency=latency,
        comb_budget_ns=budget,
        ports=tuple(ports),
        params=params,
        ill_cause_width=_as_int(_pick(data, "ill_cause_width"), "ill_cause_width"),
        status=str(_pick(data, "status", required=False, default="draft")),
        assertions=parse_assertions(_pick(data, "assertions", required=False, default=None)),
        extra=extra,
        source=source,
    )
    if header.ill_cause_width < 1:
        raise ContractHeaderError("ill_cause_width must be >= 1")
    return header


def load_contract_file(path: Path | str) -> ContractHeader:
    dest = Path(path)
    text = dest.read_text(encoding="utf-8")
    raw = extract_yaml_header(text)
    if raw is None:
        raise ContractHeaderMissing(f"{dest.name} has no YAML header; wait #43 next head")
    return parse_contract_yaml(raw, source=str(dest.name))


@dataclass(frozen=True)
class ContractDocument:
    header: ContractHeader
    body: str
    yaml_digest: str
    path: Path


def load_contract_document(path: Path | str) -> ContractDocument:
    dest = Path(path)
    text = dest.read_text(encoding="utf-8")
    raw = extract_yaml_header(text)
    if raw is None:
        raise ContractHeaderMissing(f"{dest.name} has no YAML header; wait #43 next head")
    header = parse_contract_yaml(raw, source=str(dest.name))
    return ContractDocument(
        header=header,
        body=text,
        yaml_digest=contract_sha256(dest),
        path=dest,
    )


def find_contracts_dir(start: Path | None = None) -> Path:
    """Walk parents for ``docs/arch/mem/contracts``. No hardcoded workspace path."""
    here = (start or Path(__file__).resolve()).resolve()
    for base in [here, *here.parents]:
        cand = base / "docs" / "arch" / "mem" / "contracts"
        if cand.is_dir():
            return cand
    raise FileNotFoundError("docs/arch/mem/contracts not found from this file")


def list_leaf_contract_paths(contracts_dir: Path | None = None) -> tuple[Path, ...]:
    root = contracts_dir or find_contracts_dir()
    return tuple(sorted(root.glob("ub_*.md")))
