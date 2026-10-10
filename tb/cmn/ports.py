"""Leaf clock / reset / data port contract (Xia; CODING_STYLE §5 / §10).

Clock is ``core_clk`` (M1 unique clock). Reset matches every existing
leaf in ``rtl/`` (``ub_pcs_*``, ``ub_dll_*``, controllers): ``rst_n``,
active-low. CODING_STYLE §5 also names top-level ``rst_n``; ``rst_pyc``
is the post-``ub_pyc_rst_adapt`` business polarity, not a port on those
leaves.

Parse names from the netlist ANSI port list. If the netlist does not
match, raise — do not silently map ``clk`` → ``core_clk``.
"""

from __future__ import annotations

import re
from pathlib import Path

CLK_PORT = "core_clk"
RST_PORT = "rst_n"
RST_ACTIVE_LOW = True
DATA_PORTS: tuple[str, ...] = ("we", "waddr", "wdata", "re", "raddr", "rdata")
REQUIRED_PORTS: tuple[str, ...] = (CLK_PORT, RST_PORT) + DATA_PORTS

_CLK_LIKE = ("core_clk", "clk", "clock")
_RST_LIKE = ("rst_n", "rst_pyc", "rst_n_sync", "rst", "reset", "reset_n")

_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE = re.compile(r"//.*?$", re.MULTILINE)
_MODULE_PORTS = re.compile(
    r"\bmodule\s+(?P<name>\w+)\s*\((?P<body>.*?)\)\s*;",
    re.DOTALL,
)
_PORT_DECL = re.compile(
    r"\b(?P<dir>input|output|inout)\b"
    r"(?:\s+(?:wire|reg|logic|signed|unsigned))*"
    r"(?:\s*\[[^\]]+\])?"
    r"\s+(?P<name>\w+)",
    re.IGNORECASE,
)


class LeafPortError(ValueError):
    """Netlist ports do not match the Xia / CODING_STYLE leaf contract."""


def rst_assert_value() -> int:
    return 0 if RST_ACTIVE_LOW else 1


def rst_deassert_value() -> int:
    return 1 if RST_ACTIVE_LOW else 0


def strip_verilog_comments(text: str) -> str:
    text = _COMMENT_BLOCK.sub("", text)
    return _COMMENT_LINE.sub("", text)


def parse_module_ports(text: str, module: str | None = None) -> tuple[str, ...]:
    """ANSI port names of ``module`` (or the first module if name is None)."""
    cleaned = strip_verilog_comments(text)
    for match in _MODULE_PORTS.finditer(cleaned):
        if module is None or match.group("name") == module:
            names = tuple(m.group("name") for m in _PORT_DECL.finditer(match.group("body")))
            return names
    return ()


def parse_module_ports_file(path: Path, module: str | None = None) -> tuple[str, ...]:
    return parse_module_ports(
        path.read_text(encoding="utf-8", errors="replace"), module
    )


def _like(names: tuple[str, ...], candidates: tuple[str, ...]) -> tuple[str, ...]:
    found = [n for n in names if n in candidates]
    return tuple(found)


def format_port_mismatch(module: str, found: tuple[str, ...]) -> str:
    clk_like = _like(found, _CLK_LIKE)
    rst_like = _like(found, _RST_LIKE)
    missing = [p for p in REQUIRED_PORTS if p not in found]
    extra_clk = [n for n in clk_like if n != CLK_PORT]
    parts = [
        f"{module} port mismatch: expected clock '{CLK_PORT}', reset '{RST_PORT}'",
        f"and data {list(DATA_PORTS)}",
        f"found ports: {', '.join(found) if found else '(none)'}",
        f"clock-like: {', '.join(clk_like) if clk_like else '(none)'}",
        f"reset-like: {', '.join(rst_like) if rst_like else '(none)'}",
    ]
    if missing:
        parts.append(f"missing: {', '.join(missing)}")
    if extra_clk:
        parts.append(
            f"refusing to silently map {extra_clk} → {CLK_PORT}"
        )
    return ". ".join(parts) + "."


def check_leaf_ports(
    ports: tuple[str, ...],
    *,
    module: str = "ub_cmn_mem_1r1w",
) -> None:
    """Raise ``LeafPortError`` unless ``ports`` is the Xia contract."""
    have = set(ports)
    if CLK_PORT in have and RST_PORT in have and all(p in have for p in DATA_PORTS):
        return
    raise LeafPortError(format_port_mismatch(module, ports))


__all__ = [
    "CLK_PORT",
    "DATA_PORTS",
    "LeafPortError",
    "REQUIRED_PORTS",
    "RST_ACTIVE_LOW",
    "RST_PORT",
    "check_leaf_ports",
    "format_port_mismatch",
    "parse_module_ports",
    "parse_module_ports_file",
    "rst_assert_value",
    "rst_deassert_value",
    "strip_verilog_comments",
]
