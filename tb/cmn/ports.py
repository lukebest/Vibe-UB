"""Leaf port contract (Xia; CODING_STYLE §5 / §10).

Clock is ``core_clk``. This primitive has **no reset port** (array and
rdata are not reset). Parse names from the netlist ANSI list. Do not
silently map ``clk`` → ``core_clk``. A reset port on the leaf is an error.
"""

from __future__ import annotations

import re
from pathlib import Path

CLK_PORT = "core_clk"
DATA_PORTS: tuple[str, ...] = ("we", "waddr", "wdata", "re", "raddr", "rdata")
REQUIRED_PORTS: tuple[str, ...] = (CLK_PORT,) + DATA_PORTS

CLK_MISMATCH_ZH = "叶子时钟口为 clk，预期 core_clk"
RST_FORBIDDEN_ZH = "叶子不应有复位口"

_CLK_LIKE = ("core_clk", "clk", "clock")
_RST_LIKE = ("rst_n", "rst_pyc", "rst_n_sync", "rst", "reset", "reset_n")

_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_COMMENT_LINE = re.compile(r"//.*?$", re.MULTILINE)
_MODULE_PORTS = re.compile(
    r"\bmodule\s+(?P<name>\w+)"
    r"(?:\s*#\s*\(.*?\))?"
    r"\s*\((?P<body>.*?)\)\s*;",
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
    return tuple(n for n in names if n in candidates)


def format_port_mismatch(module: str, found: tuple[str, ...]) -> str:
    clk_like = _like(found, _CLK_LIKE)
    rst_like = _like(found, _RST_LIKE)
    missing = [p for p in REQUIRED_PORTS if p not in found]
    parts: list[str] = [f"{module} port mismatch"]
    if "clk" in found and CLK_PORT not in found:
        parts.append(CLK_MISMATCH_ZH)
    elif CLK_PORT not in found:
        parts.append(f"expected clock '{CLK_PORT}'")
    if rst_like:
        parts.append(f"{RST_FORBIDDEN_ZH}: {', '.join(rst_like)}")
    parts.append(f"found ports: {', '.join(found) if found else '(none)'}")
    if missing:
        parts.append(f"missing: {', '.join(missing)}")
    if "clk" in found and CLK_PORT not in found:
        parts.append("refusing to silently map clk → core_clk")
    return ". ".join(parts) + "."


def check_leaf_ports(
    ports: tuple[str, ...],
    *,
    module: str = "ub_cmn_mem_1r1w",
) -> None:
    """Raise ``LeafPortError`` unless ports are ``core_clk`` + data and no reset."""
    have = set(ports)
    rst_like = _like(ports, _RST_LIKE)
    if CLK_PORT in have and all(p in have for p in DATA_PORTS) and not rst_like:
        return
    raise LeafPortError(format_port_mismatch(module, ports))


__all__ = [
    "CLK_MISMATCH_ZH",
    "CLK_PORT",
    "DATA_PORTS",
    "LeafPortError",
    "REQUIRED_PORTS",
    "RST_FORBIDDEN_ZH",
    "check_leaf_ports",
    "format_port_mismatch",
    "parse_module_ports",
    "parse_module_ports_file",
    "strip_verilog_comments",
]
