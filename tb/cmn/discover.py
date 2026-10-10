"""Discover ``ub_cmn_mem_1r1w`` fixed-netlist variants (SPEC §2.2).

pycc does not emit Verilog ``parameter``. Each DEPTH/WIDTH set is a separate
module ``<leaf>_<tag>``:

* PRODUCT: ``rtl/cmn/<leaf>_<tag>.v``
* TEST_HOOKS: ``rtl/cmn/hooks/<leaf>_<tag>.v`` (same module name, §11)

DEPTH/WIDTH come from the tag, a sidecar metadata file, header comments, or
a pycircuit tag table — never from Verilator ``-G``.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from model.ub_cmn_mem_1r1w import clog2

REPO_ROOT = Path(__file__).resolve().parents[2]
RTL_CMN = REPO_ROOT / "rtl" / "cmn"
RTL_CMN_HOOKS = RTL_CMN / "hooks"
LEAF = "ub_cmn_mem_1r1w"
LEAF_SUFFIXES = {".v", ".sv"}
META_SUFFIXES = {".json", ".yml", ".yaml"}

_MODULE_RE = re.compile(r"^\s*module\s+(\w+)", re.MULTILINE)
_TAG_DEPTH_WIDTH = (
    re.compile(r"^d(?P<depth>\d+)w(?P<width>\d+)(?:_placeholder)?$"),
    re.compile(r"^d(?P<depth>\d+)_w(?P<width>\d+)(?:_placeholder)?$"),
    re.compile(r"^depth(?P<depth>\d+)_width(?P<width>\d+)(?:_placeholder)?$"),
)
_COMMENT_DW = re.compile(
    r"\bDEPTH\s*=\s*(\d+)\b.*\bWIDTH\s*=\s*(\d+)\b"
    r"|\bWIDTH\s*=\s*(\d+)\b.*\bDEPTH\s*=\s*(\d+)\b",
    re.IGNORECASE | re.DOTALL,
)
_PORT_WADDR = re.compile(r"\bwaddr\b[^;\n]*\[\s*(\d+)\s*:\s*0\s*\]", re.IGNORECASE)
_PORT_WDATA = re.compile(r"\bwdata\b[^;\n]*\[\s*(\d+)\s*:\s*0\s*\]", re.IGNORECASE)


@dataclass(frozen=True)
class MemVariant:
    """One fixed netlist. ``module`` is the Verilog module name (no parameters)."""

    path: Path
    module: str
    tag: str
    depth: int
    width: int
    netlist: str  # "product" | "hooks"
    placeholder: bool = False
    source: str = "tag"
    extras: dict = field(default_factory=dict)

    @property
    def aw(self) -> int:
        return max(1, clog2(self.depth))

    @property
    def id(self) -> str:
        tag = self.tag or "default"
        return f"{self.netlist}:{self.module}:{tag}"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _module_name(text: str, fallback: str) -> str:
    match = _MODULE_RE.search(text)
    return match.group(1) if match else fallback


def _split_leaf_tag(module: str) -> tuple[str, bool] | None:
    if module == LEAF:
        return "", False
    prefix = LEAF + "_"
    if not module.startswith(prefix):
        return None
    tag = module[len(prefix) :]
    placeholder = tag.endswith("_placeholder")
    if placeholder:
        tag = tag[: -len("_placeholder")]
    return tag, placeholder


def _parse_tag_depth_width(tag: str) -> tuple[int, int] | None:
    if not tag:
        return None
    for cre in _TAG_DEPTH_WIDTH:
        match = cre.match(tag)
        if match:
            return int(match.group("depth")), int(match.group("width"))
    return None


def _load_sidecar(path: Path) -> dict:
    for suffix in META_SUFFIXES:
        meta = path.with_suffix(suffix)
        if not meta.is_file():
            continue
        text = _read_text(meta)
        if suffix == ".json":
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        # Minimal YAML: key: value lines. Avoid a PyYAML dependency.
        out: dict = {}
        for line in text.splitlines():
            stripped = line.split("#", 1)[0].strip()
            if not stripped or ":" not in stripped:
                continue
            key, val = stripped.split(":", 1)
            out[key.strip()] = val.strip().strip("\"'")
        return out
    return {}


def _looks_like_mapping(obj: object) -> bool:
    return isinstance(obj, dict)


def _coerce_dw(raw: dict) -> tuple[int, int] | None:
    def pick(*keys: str) -> int | None:
        for key in keys:
            if key in raw and raw[key] not in (None, ""):
                return int(raw[key], 0) if isinstance(raw[key], str) else int(raw[key])
        return None

    depth = pick("DEPTH", "depth")
    width = pick("WIDTH", "width")
    if depth is None or width is None:
        return None
    return depth, width


def _from_comments(text: str) -> tuple[int, int] | None:
    match = _COMMENT_DW.search(text)
    if not match:
        return None
    if match.group(1) is not None:
        return int(match.group(1)), int(match.group(2))
    return int(match.group(4)), int(match.group(3))


def _port_widths(text: str) -> tuple[int | None, int | None]:
    waddr = _PORT_WADDR.search(text)
    wdata = _PORT_WDATA.search(text)
    aw = int(waddr.group(1)) + 1 if waddr else None
    width = int(wdata.group(1)) + 1 if wdata else None
    return aw, width


def _pycircuit_tag_table(repo: Path) -> dict[str, dict]:
    """Best-effort read of design-B's tag → {DEPTH, WIDTH} table."""
    cmn = repo / "pycircuit" / "cmn"
    if not cmn.is_dir():
        return {}
    table: dict[str, dict] = {}
    for path in sorted(cmn.rglob("*")):
        if path.suffix.lower() not in {".py", ".json", ".yml", ".yaml"}:
            continue
        try:
            text = _read_text(path)
        except OSError:
            continue
        if path.suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            if _looks_like_mapping(data):
                for key, val in data.items():
                    if _looks_like_mapping(val) and _coerce_dw(val):
                        table[str(key)] = val
        # Python: TAGS / VARIANTS / PARAMS dict literals with DEPTH/WIDTH.
        for match in re.finditer(
            r"[\"']([A-Za-z0-9_]+)[\"']\s*:\s*\{([^}]+)\}", text
        ):
            tag, body = match.group(1), match.group(2)
            raw: dict = {}
            for pair in re.finditer(
                r"[\"']?(DEPTH|WIDTH|depth|width)[\"']?\s*[:=]\s*(\d+)", body
            ):
                raw[pair.group(1)] = int(pair.group(2))
            if _coerce_dw(raw):
                table[tag] = raw
    return table


def parse_variant_file(
    path: Path,
    *,
    netlist: str,
    repo: Path | None = None,
    tag_table: dict[str, dict] | None = None,
) -> MemVariant | None:
    """Parse one leaf file. None if it is not this primitive or DEPTH/WIDTH unknown."""
    if path.suffix.lower() not in LEAF_SUFFIXES:
        return None
    text = _read_text(path)
    module = _module_name(text, path.stem)
    split = _split_leaf_tag(module)
    if split is None:
        return None
    tag, placeholder = split
    if module.endswith("_tb") or "if_props" in module or "formal" in module:
        return None

    source = "tag"
    dw = _parse_tag_depth_width(tag)
    if dw is None:
        side = _coerce_dw(_load_sidecar(path))
        if side:
            dw = side
            source = "sidecar"
    if dw is None:
        comment = _from_comments(text)
        if comment:
            dw = comment
            source = "comment"
    table = tag_table if tag_table is not None else {}
    if dw is None and tag in table:
        got = _coerce_dw(table[tag])
        if got:
            dw = got
            source = "pycircuit"
    if dw is None and "" in table and not tag:
        got = _coerce_dw(table[""])
        if got:
            dw = got
            source = "pycircuit"
    if dw is None:
        return None

    depth, width = dw
    if depth < 1 or width < 1:
        return None
    _aw, port_w = _port_widths(text)
    extras: dict = {}
    if port_w is not None and port_w != width:
        extras["port_width_mismatch"] = port_w
    if _aw is not None:
        extras["port_aw"] = _aw
    extras["repo"] = str(repo) if repo is not None else ""
    return MemVariant(
        path=path.resolve(),
        module=module,
        tag=tag,
        depth=depth,
        width=width,
        netlist=netlist,
        placeholder=placeholder or tag.endswith("placeholder") or path.stem.endswith(
            "_placeholder"
        ),
        source=source,
        extras=extras,
    )


def _iter_netlist_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(root.iterdir()):
        if path.is_file() and path.suffix.lower() in LEAF_SUFFIXES:
            out.append(path)
    return out


def discover_variants(repo: Path | None = None) -> list[MemVariant]:
    """PRODUCT files in ``rtl/cmn/`` plus HOOKS files in ``rtl/cmn/hooks/``."""
    root = Path(repo) if repo is not None else REPO_ROOT
    table = _pycircuit_tag_table(root)
    found: list[MemVariant] = []
    seen: set[tuple[str, str]] = set()
    groups = (
        (root / "rtl" / "cmn", "product"),
        (root / "rtl" / "cmn" / "hooks", "hooks"),
    )
    for directory, netlist in groups:
        for path in _iter_netlist_files(directory):
            var = parse_variant_file(
                path, netlist=netlist, repo=root, tag_table=table
            )
            if var is None:
                continue
            key = (var.netlist, var.module)
            if key in seen:
                continue
            seen.add(key)
            found.append(var)
    return found


def discover_by_netlist(
    netlist: str, repo: Path | None = None
) -> list[MemVariant]:
    return [v for v in discover_variants(repo) if v.netlist == netlist]


def find_product_leaf(repo: Path | None = None) -> Path | None:
    """Back-compat: first PRODUCT variant path, if any."""
    found = discover_by_netlist("product", repo)
    return found[0].path if found else None


def verilator_on_path() -> bool:
    return shutil.which("verilator") is not None


def cocotb_importable() -> bool:
    try:
        import cocotb  # noqa: F401
    except ImportError:
        return False
    return True


def rtl_sim_skip_reason(
    repo: Path | None = None, *, netlist: str | None = None
) -> str | None:
    """Why the cocotb + Verilator suite cannot run. None = ready."""
    variants = (
        discover_by_netlist(netlist, repo)
        if netlist is not None
        else discover_variants(repo)
    )
    if not variants:
        where = (
            "rtl/cmn/hooks/"
            if netlist == "hooks"
            else "rtl/cmn/" if netlist == "product" else "rtl/cmn/ and rtl/cmn/hooks/"
        )
        return (
            f"No parseable {LEAF} variants under {where} "
            "(SPEC §2.2 <leaf>_<tag> fixed netlists). "
            "Product leaf is owned by design-B and has not landed. "
            "Skipping cocotb/Verilator simulation; Python self-check still runs."
        )
    if not verilator_on_path():
        return (
            "Verilator not on PATH; cannot run the cocotb + Verilator "
            f"{LEAF} suite even though variants were discovered."
        )
    if not cocotb_importable():
        return (
            "cocotb is not importable; cannot run the RTL simulation "
            "suite. Install tb/requirements.txt."
        )
    return None
