#!/usr/bin/env python3
"""Load and validate docs/regmap/regmap.yaml (stdlib + PyYAML).

This is the documented Python validator for the register map. A JSON Schema
lives at docs/regmap/schema.json; this module enforces the semantic rules
that schema cannot express (overlap, uniqueness, reset fit, enum width).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YAML = REPO_ROOT / "docs" / "regmap" / "regmap.yaml"
DEFAULT_SCHEMA = REPO_ROOT / "docs" / "regmap" / "schema.json"

ACCESS_TYPES = frozenset({"RW", "RO", "WO", "W1C", "MIX"})
WORD_BITS = 32
WORD_ALIGN = 4


class RegmapError(ValueError):
    """Semantic or structural register-map error."""


def parse_int(value: Any, *, allow_na: bool = False) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise RegmapError(f"boolean is not a numeric value: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if allow_na and text == "NA":
            return None
        if text.startswith(("0x", "0X")):
            return int(text, 16)
        return int(text, 0)
    raise RegmapError(f"cannot parse integer from {value!r}")


def field_width(field: dict[str, Any]) -> int:
    return int(field["msb"]) - int(field["lsb"]) + 1


def field_mask(field: dict[str, Any]) -> int:
    width = field_width(field)
    return ((1 << width) - 1) << int(field["lsb"])


def reset_int(field: dict[str, Any]) -> int | None:
    return parse_int(field.get("reset"), allow_na=True)


def is_window_reg(reg: dict[str, Any]) -> bool:
    if reg.get("kind") == "window":
        return True
    fields = reg.get("fields") or []
    return any(f.get("kind") == "window" or f.get("name") == "WINDOW" for f in fields)


def load_regmap(path: Path | None = None) -> dict[str, Any]:
    src = Path(path) if path is not None else DEFAULT_YAML
    with src.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise RegmapError(f"{src}: root must be a mapping")
    return data


def load_schema(path: Path | None = None) -> dict[str, Any]:
    src = Path(path) if path is not None else DEFAULT_SCHEMA
    return json.loads(src.read_text(encoding="utf-8"))


def _require(obj: dict[str, Any], keys: Iterable[str], where: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise RegmapError(f"{where}: missing keys {missing}")


def validate_schema_lite(data: dict[str, Any]) -> list[str]:
    """Structural checks mirroring docs/regmap/schema.json (no jsonschema dep)."""
    errors: list[str] = []
    for key in ("meta", "global_rules", "windows", "registers"):
        if key not in data:
            errors.append(f"root missing {key}")
    meta = data.get("meta") or {}
    for key in (
        "title",
        "companion_spec",
        "spec_baseline",
        "bus",
        "byte_order",
        "machine_readable_columns",
        "access_types",
    ):
        if key not in meta:
            errors.append(f"meta missing {key}")
    bus = meta.get("bus") or {}
    for key in (
        "data_width_bits",
        "addr_width_bits",
        "alignment_bytes",
        "full_word_writes_only",
        "wstrb",
        "read_latency_cycles",
        "unmapped",
    ):
        if key not in bus:
            errors.append(f"meta.bus missing {key}")
    if bus.get("data_width_bits") != 32:
        errors.append("bus.data_width_bits must be 32")
    if bus.get("addr_width_bits") != 16:
        errors.append("bus.addr_width_bits must be 16")
    if bus.get("alignment_bytes") != 4:
        errors.append("bus.alignment_bytes must be 4")
    if bus.get("full_word_writes_only") is not True:
        errors.append("bus.full_word_writes_only must be true")
    if bus.get("wstrb") is not False:
        errors.append("bus.wstrb must be false")
    if bus.get("read_latency_cycles") != 1:
        errors.append("bus.read_latency_cycles must be 1")
    unmapped = bus.get("unmapped") or {}
    if unmapped.get("read_data") != 0 or unmapped.get("read_csr_err") != 1:
        errors.append("unmapped read must be data=0 csr_err=1")
    if unmapped.get("write") != "ignore" or unmapped.get("write_csr_err") != 1:
        errors.append("unmapped write must be ignore / csr_err=1")
    rules = data.get("global_rules") or {}
    if rules.get("full_word_writes_only") is not True:
        errors.append("global_rules.full_word_writes_only must be true")
    if rules.get("read_latency_cycles") != 1:
        errors.append("global_rules.read_latency_cycles must be 1")
    if rules.get("unmapped_csr_err") is not True:
        errors.append("global_rules.unmapped_csr_err must be true")
    return errors


def validate_semantics(data: dict[str, Any]) -> list[str]:
    """Field overlap, 32-bit fit, unique aligned addresses, enum/reset widths."""
    errors: list[str] = []
    windows = {w["id"]: w for w in data.get("windows") or [] if "id" in w}
    seen_offsets: dict[int, str] = {}
    seen_names: dict[str, int] = {}

    for reg in data.get("registers") or []:
        name = reg.get("name", "<unnamed>")
        where = f"register {name}"
        try:
            _require(reg, ("name", "offset", "window", "fields"), where)
            offset = parse_int(reg["offset"])
            if offset is None:
                raise RegmapError("offset is required")
        except RegmapError as exc:
            errors.append(str(exc))
            continue

        if offset in seen_offsets:
            errors.append(
                f"{where} offset 0x{offset:04X} duplicates {seen_offsets[offset]}"
            )
        seen_offsets[offset] = name
        if name in seen_names:
            errors.append(f"{where} name duplicates offset 0x{seen_names[name]:04X}")
        seen_names[name] = offset

        if offset % WORD_ALIGN != 0:
            errors.append(f"{where} offset 0x{offset:04X} is not word-aligned")
        if offset < 0 or offset > 0xFFFF:
            errors.append(f"{where} offset 0x{offset:04X} outside 16-bit address")

        win_id = reg.get("window")
        if win_id not in windows:
            errors.append(f"{where} window {win_id!r} is not defined")
        else:
            start = parse_int(windows[win_id]["start"]) or 0
            end = parse_int(windows[win_id]["end"]) or 0
            if not (start <= offset <= end):
                errors.append(
                    f"{where} offset 0x{offset:04X} outside window "
                    f"{win_id} 0x{start:04X}-0x{end:04X}"
                )

        occupied = 0
        field_names: set[str] = set()
        for field in reg.get("fields") or []:
            fname = field.get("name", "<field>")
            fwhere = f"{where}.{fname}"
            try:
                _require(
                    field,
                    ("name", "msb", "lsb", "access", "reset", "description", "spec_ref"),
                    fwhere,
                )
                msb = int(field["msb"])
                lsb = int(field["lsb"])
            except (RegmapError, TypeError, ValueError) as exc:
                errors.append(f"{fwhere}: {exc}")
                continue

            if fname in field_names:
                errors.append(f"{fwhere}: duplicate field name")
            field_names.add(fname)

            if not (0 <= lsb <= msb <= 31):
                errors.append(f"{fwhere}: bits [{msb}:{lsb}] not within 31:0")
                continue
            width = msb - lsb + 1
            mask = (1 << width) - 1
            bits = mask << lsb
            if occupied & bits:
                errors.append(f"{fwhere}: overlaps another field")
            occupied |= bits

            access = field.get("access")
            if access not in ACCESS_TYPES:
                errors.append(f"{fwhere}: invalid access {access!r}")

            rst = reset_int(field)
            if rst is not None and rst != (rst & mask):
                errors.append(
                    f"{fwhere}: reset {field.get('reset')!r} does not fit width {width}"
                )

            for enum in field.get("enums") or []:
                val = parse_int(enum.get("value"))
                if val is None:
                    errors.append(f"{fwhere}: enum missing value")
                    continue
                if val != (val & mask):
                    errors.append(
                        f"{fwhere}: enum {enum.get('name')}={val} does not fit width {width}"
                    )

            for val in field.get("legal_values") or []:
                ival = parse_int(val)
                if ival is None or ival != (ival & mask):
                    errors.append(f"{fwhere}: legal value {val!r} does not fit width {width}")

            for val in field.get("reserved_values") or []:
                ival = parse_int(val)
                if ival is None or ival != (ival & mask):
                    errors.append(
                        f"{fwhere}: reserved value {val!r} does not fit width {width}"
                    )

            if field.get("pulse_cycles") is not None:
                cycles = parse_int(field["pulse_cycles"])
                if cycles is None or cycles < 1:
                    errors.append(f"{fwhere}: pulse_cycles must be >= 1")

        if not is_window_reg(reg) and occupied != (1 << WORD_BITS) - 1:
            missing = ((1 << WORD_BITS) - 1) ^ occupied
            errors.append(
                f"{where}: bits not fully specified (uncovered mask 0x{missing:08X}); "
                "add RSVD or document a hole"
            )

    return errors


def validate_regmap(data: dict[str, Any]) -> list[str]:
    return validate_schema_lite(data) + validate_semantics(data)


def assert_valid(data: dict[str, Any]) -> None:
    errors = validate_regmap(data)
    if errors:
        joined = "\n".join(f"  - {e}" for e in errors)
        raise RegmapError(f"regmap validation failed:\n{joined}")


def iter_fields(data: dict[str, Any]):
    for reg in data.get("registers") or []:
        for field in reg.get("fields") or []:
            yield reg, field


def window_by_id(data: dict[str, Any], win_id: str) -> dict[str, Any]:
    for win in data.get("windows") or []:
        if win.get("id") == win_id:
            return win
    raise KeyError(win_id)
