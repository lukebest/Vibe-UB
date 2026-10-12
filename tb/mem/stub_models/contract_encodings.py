"""Illegal-cause / desc_kind / ENC_* tables loaded from the contract.

Prefer maps a later contract head may put on the YAML header
(``ill_cause``, ``desc_kind``, ``enc_classes``, ``desc_lvl_enc``).
If those keys are absent, read the shared tables in
``docs/arch/mem/contracts/README.md`` and the per-leaf Markdown
cross (``desc_lvl`` × ``ENC_INVALID`` / ``ENC_TBL_PG`` / ``ENC_BLOCK``).

No leaf-specific 2 MB / 1 GB policy is invented here, and the stub
never decodes ``raw``. Encoding classes are symbols only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract_yaml import ContractHeader, find_contracts_dir, load_contract_document

ENC_INVALID = "ENC_INVALID"
ENC_TBL_PG = "ENC_TBL_PG"
ENC_BLOCK = "ENC_BLOCK"
ENC_CLASSES: tuple[str, ...] = (ENC_INVALID, ENC_TBL_PG, ENC_BLOCK)
DESC_LEVELS: tuple[int, ...] = (0, 1, 2, 3)

_ILL_ROW_RE = re.compile(
    r"^\|\s*(\d+)\s*\|\s*`([A-Z][A-Z0-9_]*)`\s*\|",
    re.M,
)
_KIND_RE = re.compile(
    r"desc_kind\[1:0\][^\n]*?"
    r"0\s*=\s*(\w+)\s*[，,]\s*1\s*=\s*(\w+)\s*[，,]\s*2\s*=\s*(\w+)\s*[，,]\s*3\s*=\s*(\w+)",
    re.S,
)
_AP_NAME_RE = re.compile(r"`(AP_[A-Z0-9_]+)`")
_ENC_SYM_RE = re.compile(r"`(ENC_[A-Z0-9_]+)`")
_CROSS_HEADER_RE = re.compile(
    r"\|\s*级\s*\|\s*`?(ENC_[A-Z0-9_]+)`?\s*\|\s*`?(ENC_[A-Z0-9_]+)`?\s*\|\s*`?(ENC_[A-Z0-9_]+)`?\s*\|"
)
_LEVEL_ROW_RE = re.compile(
    r"\|\s*L([0-3])\s*\|\s*([^|\n]+)\|\s*([^|\n]+)\|\s*([^|\n]+)\|"
)


@dataclass(frozen=True)
class EncodingTable:
    ill_cause: dict[str, int]
    desc_kind: dict[str, int]
    zero_outputs_on_illegal: bool
    cause_priority: str
    rst_active: int
    source: str

    def ill_name(self, code: int) -> str | None:
        for name, value in self.ill_cause.items():
            if value == code:
                return name
        return None

    def ill_code(self, name: str) -> int:
        return self.ill_cause[name]

    def kind_code(self, name: str) -> int:
        return self.desc_kind[name]


def _as_int_map(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ValueError(f"encoding map must be a mapping, got {type(raw).__name__}")
    out: dict[str, int] = {}
    for key, val in raw.items():
        out[str(key)] = int(val)
    return out


def parse_readme_encodings(text: str) -> tuple[dict[str, int], dict[str, int]]:
    ill = {name: int(code) for code, name in _ILL_ROW_RE.findall(text)}
    kind: dict[str, int] = {}
    match = _KIND_RE.search(text)
    if match:
        kind = {match.group(i + 1): i for i in range(4)}
    return ill, kind


def load_readme_encodings(contracts_dir: Path | None = None) -> tuple[dict[str, int], dict[str, int], Path]:
    root = contracts_dir or find_contracts_dir()
    readme = root / "README.md"
    ill, kind = parse_readme_encodings(readme.read_text(encoding="utf-8"))
    if not ill:
        raise ValueError(f"{readme.name} has no ill_cause table to load")
    return ill, kind, readme


def parse_markdown_assertions(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_AP_NAME_RE.findall(text)))


def encodings_from_header(
    header: ContractHeader,
    *,
    contracts_dir: Path | None = None,
) -> EncodingTable:
    """Header YAML wins; README fills any map the header omitted."""
    extra = header.extra
    params = header.params
    source_bits: list[str] = []

    ill_raw = extra.get("ill_cause") or extra.get("ill_cause_encoding") or params.get("ill_cause")
    kind_raw = extra.get("desc_kind") or extra.get("desc_kind_encoding") or params.get("desc_kind")
    readme_ill: dict[str, int] = {}
    readme_kind: dict[str, int] = {}
    if ill_raw is None or kind_raw is None:
        readme_ill, readme_kind, readme = load_readme_encodings(contracts_dir)
        source_bits.append(readme.name)

    ill = _as_int_map(ill_raw) if ill_raw is not None else dict(readme_ill)
    kind = _as_int_map(kind_raw) if kind_raw is not None else dict(readme_kind)
    if ill_raw is not None:
        source_bits.append(f"{header.source or header.leaf}:ill_cause")
    if kind_raw is not None:
        source_bits.append(f"{header.source or header.leaf}:desc_kind")

    zero = extra.get("zero_outputs_on_illegal", params.get("zero_outputs_on_illegal", True))
    priority = str(extra.get("cause_priority", params.get("cause_priority", "min_nonzero")))
    rst = int(extra.get("rst_active", params.get("rst_active", 1)))
    return EncodingTable(
        ill_cause=ill,
        desc_kind=kind,
        zero_outputs_on_illegal=bool(zero),
        cause_priority=str(priority),
        rst_active=rst,
        source="+".join(source_bits) or header.source,
    )


@dataclass(frozen=True)
class EncCell:
    level: int
    enc_class: str
    kind: str
    fault: bool
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "fault": self.fault,
            "note": self.note,
        }


@dataclass(frozen=True)
class EncClassTable:
    classes: tuple[str, ...]
    cells: dict[tuple[int, str], EncCell]
    port: str
    source: str
    yaml_digest: str = ""

    def cell(self, level: int, enc_class: str) -> EncCell:
        key = (int(level), str(enc_class))
        if key not in self.cells:
            raise KeyError(f"no contract cell for desc_lvl={level} enc_class={enc_class}")
        return self.cells[key]

    def keys(self) -> tuple[tuple[int, str], ...]:
        return tuple(
            (level, enc)
            for level in DESC_LEVELS
            for enc in self.classes
            if (level, enc) in self.cells
        )

    def as_nested(self) -> dict[str, dict[str, dict[str, Any]]]:
        nested: dict[str, dict[str, dict[str, Any]]] = {}
        for level, enc in self.keys():
            nested.setdefault(str(level), {})[enc] = self.cells[(level, enc)].as_dict()
        return nested


def _cell_from_prose(level: int, enc_class: str, text: str) -> EncCell:
    body = text.strip()
    fault = "翻译故障" in body
    note = ""
    lowered = body.lower()
    if fault:
        kind = "invalid"
    elif "table" in lowered:
        kind = "table"
    elif "page" in lowered:
        kind = "page"
    elif "block" in lowered:
        kind = "block"
    else:
        kind = "invalid"
        fault = True
    if "1 GB" in body or "1GB" in body:
        note = "1 GB"
    elif "2 MB" in body or "2MB" in body:
        note = "2 MB"
    elif "4 KB" in body or "4KB" in body:
        note = "4 KB"
    elif "保留" in body:
        note = "reserved"
    return EncCell(level=level, enc_class=enc_class, kind=kind, fault=fault, note=note)


def _cell_from_mapping(level: int, enc_class: str, raw: Any) -> EncCell:
    if isinstance(raw, str):
        return _cell_from_prose(level, enc_class, raw)
    if not isinstance(raw, dict):
        raise ValueError(f"enc cell {level}x{enc_class} must be a mapping or string")
    kind = str(raw.get("kind", "invalid"))
    if "fault" in raw:
        fault = bool(raw["fault"])
    else:
        fault = kind == "invalid"
    return EncCell(
        level=int(level),
        enc_class=str(enc_class),
        kind=kind,
        fault=fault,
        note=str(raw.get("note", "")),
    )


def fallback_enc_class_table(*, source: str = "fallback-final-rule", yaml_digest: str = "") -> EncClassTable:
    """Contract §3 twelve cells. Used only when YAML/Markdown omit the table."""
    specs: tuple[tuple[int, str, str, bool, str], ...] = (
        (0, ENC_INVALID, "invalid", True, ""),
        (0, ENC_TBL_PG, "table", False, ""),
        (0, ENC_BLOCK, "invalid", True, "reserved"),
        (1, ENC_INVALID, "invalid", True, ""),
        (1, ENC_TBL_PG, "table", False, ""),
        (1, ENC_BLOCK, "block", False, "1 GB"),
        (2, ENC_INVALID, "invalid", True, ""),
        (2, ENC_TBL_PG, "table", False, ""),
        (2, ENC_BLOCK, "block", False, "2 MB"),
        (3, ENC_INVALID, "invalid", True, ""),
        (3, ENC_TBL_PG, "page", False, "4 KB"),
        (3, ENC_BLOCK, "invalid", True, "reserved"),
    )
    cells = {
        (level, enc): EncCell(level=level, enc_class=enc, kind=kind, fault=fault, note=note)
        for level, enc, kind, fault, note in specs
    }
    return EncClassTable(
        classes=ENC_CLASSES,
        cells=cells,
        port="desc_lvl",
        source=source,
        yaml_digest=yaml_digest,
    )


def parse_enc_class_table_markdown(text: str) -> EncClassTable | None:
    header = _CROSS_HEADER_RE.search(text)
    if header is None:
        return None
    classes = (header.group(1), header.group(2), header.group(3))
    cells: dict[tuple[int, str], EncCell] = {}
    for match in _LEVEL_ROW_RE.finditer(text):
        level = int(match.group(1))
        for enc, raw in zip(classes, match.groups()[1:]):
            cells[(level, enc)] = _cell_from_prose(level, enc, raw)
    if len(cells) != len(DESC_LEVELS) * len(classes):
        return None
    return EncClassTable(
        classes=classes,
        cells=cells,
        port="desc_lvl",
        source="markdown-cross",
        yaml_digest="",
    )


def parse_enc_class_table_yaml(header: ContractHeader) -> EncClassTable | None:
    extra = header.extra
    params = header.params
    raw = (
        extra.get("desc_lvl_enc")
        or extra.get("enc_cross")
        or extra.get("enc_class_cross")
        or params.get("desc_lvl_enc")
    )
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("desc_lvl_enc must be a mapping of level -> enc_class -> cell")
    classes_raw = extra.get("enc_classes") or params.get("enc_classes") or list(ENC_CLASSES)
    classes = tuple(str(item) for item in classes_raw)
    cells: dict[tuple[int, str], EncCell] = {}
    for level, row in raw.items():
        if not isinstance(row, dict):
            raise ValueError(f"desc_lvl_enc[{level}] must be a mapping")
        for enc, cell in row.items():
            cells[(int(level), str(enc))] = _cell_from_mapping(int(level), str(enc), cell)
    port = str(extra.get("desc_lvl_port") or params.get("desc_lvl_port") or "desc_lvl")
    if header.has_port("desc_lvl"):
        port = "desc_lvl"
    return EncClassTable(
        classes=classes,
        cells=cells,
        port=port,
        source=f"{header.source or header.leaf}:desc_lvl_enc",
        yaml_digest="",
    )


def load_enc_class_table(
    header: ContractHeader,
    *,
    body: str | None = None,
    yaml_digest: str = "",
    contracts_dir: Path | None = None,
) -> EncClassTable | None:
    """YAML extra, then the leaf Markdown cross, then the published 12-cell rule.

    Returns None when the leaf has no ``desc_lvl`` port (not a PTW decoder).
    """
    if not header.has_port("desc_lvl"):
        parsed = parse_enc_class_table_yaml(header)
        return parsed
    table = parse_enc_class_table_yaml(header)
    source_bits: list[str] = []
    if table is not None:
        source_bits.append(table.source)
    text = body
    if text is None:
        root = contracts_dir or find_contracts_dir()
        path = root / f"{header.leaf}.md"
        if path.is_file():
            doc = load_contract_document(path)
            text = doc.body
            yaml_digest = yaml_digest or doc.yaml_digest
    if table is None and text:
        table = parse_enc_class_table_markdown(text)
        if table is not None:
            source_bits.append(table.source)
    if table is None:
        table = fallback_enc_class_table(yaml_digest=yaml_digest)
        source_bits.append(table.source)
    return EncClassTable(
        classes=table.classes,
        cells=table.cells,
        port=table.port if header.has_port(table.port) else "desc_lvl",
        source="+".join(source_bits) or table.source,
        yaml_digest=yaml_digest,
    )


def markdown_assertion_names(
    header: ContractHeader,
    *,
    body: str | None = None,
    contracts_dir: Path | None = None,
) -> tuple[str, ...]:
    text = body
    if text is None:
        root = contracts_dir or find_contracts_dir()
        path = root / f"{header.leaf}.md"
        if path.is_file():
            text = path.read_text(encoding="utf-8")
    if not text:
        return ()
    return parse_markdown_assertions(text)
