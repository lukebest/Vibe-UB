#!/usr/bin/env python3
"""Private-leaf helpers for impl quick-synth (S-01(b)).

Public CI black-boxes any module that has a contract under
``docs/arch/<layer>/contracts/<leaf>.md`` or a stub at
``rtl/<layer>/stub/<leaf>.v``. Attest mode hashes the contract via
``scripts/gate/contract_hash.py`` (PR #47); this module does not
reimplement that digest.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

ATTEST_FIELDS = (
    "leaf",
    "contract_sha256",
    "netlist_sha256",
    "toolchain_sha256",
    "clock",
    "cells",
    "area_um2",
    "regs",
    "logic_depth",
    "depth_incl_buf",
    "wns_ns",
    "crit_path",
    "status",
)
CRIT_PATH_PUBLIC = "public"
CRIT_PATH_PRIVATE = "私有叶子内部"
CRIT_PATH_OK = {CRIT_PATH_PUBLIC, CRIT_PATH_PRIVATE}
PUBLIC_ATTEST_DIR = Path("reports") / "private"
PRIVATE_REPO_ATTEST_DIR = Path("attest")
CONTRACT_HASH_MISSING = (
    "scripts/gate/contract_hash.py is missing; "
    "attest mode needs PR #47 (gate: S-01(b) private leaves + contract check)"
)

FRONT_MATTER_RE = re.compile(
    r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)",
    re.S,
)
FENCE_RE = re.compile(
    r"\A```ya?ml[ \t]*\n(.*?)```",
    re.S,
)
HASH_HEADER_RE = re.compile(
    r"contract_sha256:\s*([0-9a-fA-F]{64}|HANDWRITTEN)\b"
)
INST_RE_TMPL = (
    r"\b{mod}(?:\s+#\s*\([^;]*\))?\s+(?P<inst>\w+)\s*\("
)


def file_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract_contract_yaml(text: str) -> str | None:
    """Leading YAML segment (``---`` front matter or a `` ```yaml `` fence)."""
    m = FRONT_MATTER_RE.match(text)
    if m:
        return m.group(1)
    m = FENCE_RE.match(text)
    if m:
        return m.group(1)
    return None


def load_yaml_mapping(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise ValueError("PyYAML is required to parse contract YAML") from exc
    obj = yaml.safe_load(text)
    if not isinstance(obj, dict):
        raise ValueError("contract YAML must be a mapping")
    return obj


def parse_contract_header(path: Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    body = extract_contract_yaml(text)
    if body is None:
        raise ValueError(f"{path}: no leading YAML segment")
    data = load_yaml_mapping(body)
    data["_path"] = str(path)
    data["_text"] = text
    return data


def layer_of_contract(path: Path, root: Path) -> str:
    try:
        parts = Path(path).resolve().relative_to(Path(root).resolve()).parts
    except ValueError:
        parts = Path(path).parts
    if len(parts) >= 5 and parts[0] == "docs" and parts[1] == "arch":
        return parts[2]
    return layer_from_leaf(Path(path).stem)


def layer_from_leaf(name: str) -> str:
    parts = name.split("_")
    if len(parts) >= 3 and parts[0] == "ub":
        return parts[1]
    return "unknown"


def discover_contract_files(root: Path) -> list[Path]:
    files: list[Path] = []
    arch = Path(root) / "docs" / "arch"
    if not arch.is_dir():
        return files
    for layer_dir in sorted(p for p in arch.iterdir() if p.is_dir()):
        contracts = layer_dir / "contracts"
        if not contracts.is_dir():
            continue
        for path in sorted(contracts.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            files.append(path)
    return files


def discover_stub_files(root: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    rtl = Path(root) / "rtl"
    if not rtl.is_dir():
        return found
    for layer_dir in sorted(p for p in rtl.iterdir() if p.is_dir()):
        stub_dir = layer_dir / "stub"
        if not stub_dir.is_dir():
            continue
        for path in sorted(stub_dir.iterdir()):
            if path.suffix in {".v", ".sv"}:
                found[path.stem] = path
    return found


def latency_cycles(data: dict[str, Any] | None) -> int:
    if not data:
        return 1
    lat = data.get("latency")
    if isinstance(lat, bool):
        return 1
    if isinstance(lat, (int, float)):
        return int(lat)
    if isinstance(lat, dict):
        kind = str(lat.get("kind") or lat.get("type") or "").strip().lower()
        if kind == "combinational":
            return 0
        if lat.get("cycles") is not None:
            try:
                return int(lat["cycles"])
            except (TypeError, ValueError):
                return 1
        if lat.get("max_cycles") is not None:
            try:
                return int(lat["max_cycles"])
            except (TypeError, ValueError):
                return 1
        return 0 if kind == "combinational" else 1
    return 1


def clock_period_ns(data: dict[str, Any] | None) -> float | None:
    if not data:
        return None
    clock = data.get("clock")
    if not isinstance(clock, dict):
        return None
    val = clock.get("period_ns")
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return None
    return None


def clock_name(data: dict[str, Any] | None, default: str = "core_clk") -> str:
    if not data:
        return default
    clock = data.get("clock")
    if isinstance(clock, dict) and clock.get("name"):
        return str(clock["name"])
    return default


def attest_clock(data: dict[str, Any] | None) -> dict[str, Any]:
    """``clock`` for attest YAML: name + period_ns copied from the contract."""
    clock = data.get("clock") if isinstance(data, dict) else None
    if not isinstance(clock, dict):
        return {"name": "core_clk", "period_ns": 12.412}
    out: dict[str, Any] = {
        "name": clock.get("name") or "core_clk",
        "period_ns": clock.get("period_ns"),
    }
    return out


def port_width(port: dict[str, Any], params: list[Any] | None = None) -> int:
    width = port.get("width")
    if isinstance(width, bool):
        return 1
    if isinstance(width, int):
        return width
    if isinstance(width, float):
        return int(width)
    text = str(width or "1").strip()
    if text.lower() == "unknown":
        return 1
    for item in params or []:
        if isinstance(item, dict) and item.get("name") == text:
            try:
                return int(item.get("default") or 1)
            except (TypeError, ValueError):
                return 1
    try:
        return int(text)
    except ValueError:
        return 1


def contract_ports(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw = data.get("ports") if isinstance(data.get("ports"), list) else []
    params = data.get("params") if isinstance(data.get("params"), list) else []
    out: list[dict[str, Any]] = []
    for port in raw:
        if not isinstance(port, dict) or not port.get("name"):
            continue
        direction = str(port.get("dir") or "in")
        if direction in {"in", "input"}:
            vdir = "input"
        elif direction in {"out", "output"}:
            vdir = "output"
        else:
            vdir = "inout"
        width = port_width(port, params)
        out.append(
            {
                "name": str(port["name"]),
                "dir": vdir,
                "width": width,
                "msb": width - 1 if width > 1 else 0,
                "lsb": 0,
            }
        )
    return out


def build_private_catalog(root: Path) -> dict[str, dict[str, Any]]:
    """Map leaf name → catalog entry (contract and/or stub)."""
    catalog: dict[str, dict[str, Any]] = {}
    stubs = discover_stub_files(root)
    for path in discover_contract_files(root):
        try:
            data = parse_contract_header(path)
        except ValueError:
            data = {"leaf": path.stem}
        leaf = str(data.get("leaf") or path.stem)
        layer = layer_of_contract(path, root)
        catalog[leaf] = {
            "name": leaf,
            "layer": layer,
            "parent": data.get("parent"),
            "contract_path": path,
            "contract": data,
            "stub_path": stubs.get(leaf),
            "period_ns": clock_period_ns(data),
            "clock_name": clock_name(data),
            "latency_cycles": latency_cycles(data),
            "comb_budget_ns": data.get("comb_budget_ns"),
            "ports": contract_ports(data),
        }
    for leaf, stub in stubs.items():
        if leaf in catalog:
            catalog[leaf]["stub_path"] = stub
            continue
        header = read_stub_hash_header(stub)
        catalog[leaf] = {
            "name": leaf,
            "layer": stub.parent.parent.name,
            "parent": None,
            "contract_path": None,
            "contract": None,
            "stub_path": stub,
            "period_ns": None,
            "clock_name": "core_clk",
            "latency_cycles": 1,
            "comb_budget_ns": None,
            "ports": [],
            "stub_header": header,
        }
    return catalog


def is_private_leaf(name: str, catalog: dict[str, dict[str, Any]]) -> bool:
    if name in catalog:
        return True
    return any(name == n or name.startswith(n + "_") for n in catalog)


def private_entry(name: str, catalog: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if name in catalog:
        return catalog[name]
    for n, rec in catalog.items():
        if name == n or name.startswith(n + "_"):
            return rec
    return None


def read_stub_hash_header(path: Path) -> str | None:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    m = HASH_HEADER_RE.search(text)
    return m.group(1) if m else None


def instance_names(verilog: str, mod: str) -> list[str]:
    rx = re.compile(INST_RE_TMPL.format(mod=re.escape(mod)))
    return [m.group("inst") for m in rx.finditer(verilog)]


def count_instances(verilog: str, mod: str) -> int:
    return len(instance_names(verilog, mod))


def find_instantiated_private(
    verilog: str, catalog: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for name in sorted(catalog, key=len, reverse=True):
        insts = instance_names(verilog, name)
        if not insts:
            continue
        rec = catalog[name]
        found.append(
            {
                **rec,
                "n_inst": len(insts),
                "instances": insts,
            }
        )
    return found


def load_contract_sha256(repo: Path):
    """Import ``contract_sha256`` from PR #47. Do not reimplement the digest."""
    mod_path = Path(repo) / "scripts" / "gate" / "contract_hash.py"
    if not mod_path.is_file():
        raise FileNotFoundError(CONTRACT_HASH_MISSING)
    spec = importlib.util.spec_from_file_location(
        "vibe_ub_gate_contract_hash", mod_path
    )
    if spec is None or spec.loader is None:
        raise FileNotFoundError(CONTRACT_HASH_MISSING)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "contract_sha256", None)
    if fn is None:
        raise FileNotFoundError(CONTRACT_HASH_MISSING)
    return fn


def public_attest_path(root: Path, layer: str, leaf: str) -> Path:
    return Path(root) / PUBLIC_ATTEST_DIR / layer / f"{leaf}.yml"


def load_public_attest(root: Path, layer: str, leaf: str) -> dict[str, Any] | None:
    path = public_attest_path(root, layer, leaf)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    try:
        data = load_yaml_mapping(text)
    except ValueError:
        return None
    return data


def write_attest_yaml(path: Path, data: dict[str, Any]) -> None:
    """Write exactly the GATE-PRIV-006 / attest field set, in that order."""
    missing = [k for k in ATTEST_FIELDS if k not in data]
    if missing:
        raise ValueError(f"attest payload missing fields: {missing}")
    extra = [k for k in data if k not in ATTEST_FIELDS]
    if extra:
        raise ValueError(f"attest payload has extra fields: {extra}")
    lines: list[str] = []
    for key in ATTEST_FIELDS:
        val = data[key]
        if key == "clock":
            if not isinstance(val, dict):
                raise ValueError("clock must be a mapping")
            lines.append("clock:")
            lines.append(f"  name: {val['name']}")
            lines.append(f"  period_ns: {val['period_ns']}")
            continue
        lines.append(f"{key}: {_yaml_plain(val)}")
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _yaml_plain(val: Any) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int) and not isinstance(val, bool):
        return str(val)
    if isinstance(val, float):
        if val != val:
            return "null"
        text = f"{val:.6f}".rstrip("0").rstrip(".")
        return text if text else "0"
    text = str(val)
    if text == "" or any(c in text for c in ":#{}[],&*?|>!%@`'\"") or text[:1] in " \t":
        return json.dumps(text, ensure_ascii=False)
    return text


def attest_field_names(text: str) -> list[str]:
    """Top-level keys in document order (clock is one key)."""
    keys: list[str] = []
    for line in text.splitlines():
        if not line or line.startswith(" ") or line.startswith("\t"):
            continue
        if ":" not in line:
            continue
        keys.append(line.split(":", 1)[0])
    return keys


def classify_crit_path(
    start_desc: str | None,
    end_desc: str | None,
    *,
    start_name: str | None = None,
    end_name: str | None = None,
) -> str:
    """``public`` when the worst path touches a top-level port."""
    blob = " ".join(
        x or "" for x in (start_desc, end_desc, start_name, end_name)
    ).lower()
    if "input port" in blob or "output port" in blob or "inout port" in blob:
        return CRIT_PATH_PUBLIC
    if re.search(r"\bport\b", blob):
        return CRIT_PATH_PUBLIC
    return CRIT_PATH_PRIVATE


def parse_sta_endpoints(text: str) -> dict[str, str | None]:
    start_m = re.search(
        r"Startpoint:\s+(\S+)(?:\s+\(([^)]*)\))?", text
    )
    end_m = re.search(
        r"Endpoint:\s+(\S+)(?:\s+\(([^)]*)\))?", text
    )
    return {
        "start_name": start_m.group(1) if start_m else None,
        "start_desc": start_m.group(2) if start_m else None,
        "end_name": end_m.group(1) if end_m else None,
        "end_desc": end_m.group(2) if end_m else None,
    }


def redact_private_names(text: str, private_names: set[str]) -> str:
    """Drop hierarchical internals of a private leaf; keep the leaf name."""
    if not text or not private_names:
        return text
    out = text
    for name in sorted(private_names, key=len, reverse=True):
        out = re.sub(
            rf"\b{re.escape(name)}(?:/[A-Za-z0-9_./$]+)+",
            name,
            out,
        )
    return out


def looks_like_private_internal(name: str, private_names: set[str]) -> bool:
    for leaf in private_names:
        if name == leaf:
            return False
        if name.startswith(leaf + "/") or f"/{leaf}/" in name:
            return True
    return False


def write_ports_blackbox(
    module: str,
    ports: list[dict[str, Any]],
    dest: Path,
    *,
    header: str | None = None,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    names = [p["name"] for p in ports] or ["core_clk"]
    lines = []
    if header:
        lines.append(header)
    lines.append(f"// public blackbox interface for {module}")
    lines.append(f"module {module} (")
    lines.append("  " + ",\n  ".join(names))
    lines.append(");")
    if not ports:
        lines.append("  input core_clk;")
    for p in ports:
        rng = f" [{p['msb']}:{p['lsb']}]" if p.get("width", 1) > 1 else ""
        lines.append(f"  {p['dir']}{rng} {p['name']};")
    lines.append("endmodule")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def write_private_sta_stub(
    module: str,
    ports: list[dict[str, Any]],
    dest: Path,
    *,
    clk: str | None,
    latency: int,
) -> dict[str, Any]:
    """STA model: register outputs when latency>=1; combo assign when 0."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    names = [p["name"] for p in ports] or ["core_clk"]
    lines = [
        f"// STA model for private leaf {module} (latency={latency})",
        f"module {module} (",
        "  " + ",\n  ".join(names),
        ");",
    ]
    if not ports:
        lines.append("  input core_clk;")
    for p in ports:
        rng = f" [{p['msb']}:{p['lsb']}]" if p.get("width", 1) > 1 else ""
        lines.append(f"  {p['dir']}{rng} {p['name']};")
    outs = [p for p in ports if p["dir"] in ("output", "inout")]
    registered = bool(clk and latency >= 1)
    if registered:
        for p in outs:
            w = int(p.get("width") or 1)
            rn = p["name"]
            if w == 1:
                lines.append(
                    f"  sky130_fd_sc_hd__dfxtp_1 {rn}_q ("
                    f" .CLK({clk}), .D(1'b0), .Q({rn}) );"
                )
            else:
                lsb = int(p.get("lsb") or 0)
                msb = int(p.get("msb") or (w - 1))
                step = 1 if msb >= lsb else -1
                for i in range(w):
                    idx = lsb + i * step
                    lines.append(
                        f"  sky130_fd_sc_hd__dfxtp_1 {rn}_q_{i} ("
                        f" .CLK({clk}), .D(1'b0), .Q({rn}[{idx}]) );"
                    )
    else:
        for p in outs:
            w = int(p.get("width") or 1)
            if w > 1:
                lines.append(f"  assign {p['name']} = {w}'b0;")
            else:
                lines.append(f"  assign {p['name']} = 1'b0;")
    lines.append("endmodule")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "module": module,
        "clk": clk,
        "latency": latency,
        "registered": registered,
        "n_outputs": len(outs),
    }


def write_combo_max_delay_sdc(
    dest: Path,
    items: list[dict[str, Any]],
) -> Path | None:
    """``set_max_delay comb_budget_ns`` from instance inputs to outputs."""
    lines = ["# private-leaf combinational budget (latency==0)",]
    wrote = False
    for rec in items:
        budget = rec.get("comb_budget_ns")
        if budget is None:
            continue
        try:
            budget_f = float(budget)
        except (TypeError, ValueError):
            continue
        ports = rec.get("ports") or []
        ins = [
            p["name"]
            for p in ports
            if p["dir"] in ("input", "inout")
            and p["name"] not in {rec.get("clock_name"), rec.get("clk")}
        ]
        outs = [p["name"] for p in ports if p["dir"] in ("output", "inout")]
        for inst in rec.get("instances") or []:
            if not ins or not outs:
                continue
            from_pins = " ".join(f"{inst}/{n}" for n in ins)
            to_pins = " ".join(f"{inst}/{n}" for n in outs)
            lines.append(
                f"set_max_delay {budget_f} -from [get_pins {{ {from_pins} }}] "
                f"-to [get_pins {{ {to_pins} }}]"
            )
            wrote = True
    if not wrote:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return dest


def private_skip_row(
    rec: dict[str, Any],
    *,
    n_inst: int = 0,
    attest: dict[str, Any] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    area = None
    label = None
    if attest is not None and attest.get("area_um2") is not None and n_inst:
        try:
            area = float(attest["area_um2"]) * n_inst
            label = "私有 CI 出数"
        except (TypeError, ValueError):
            area = None
    note_list = list(notes or [])
    if rec.get("contract_path"):
        note_list.append(f"contract {rec['contract_path']}")
    if rec.get("stub_path"):
        header = rec.get("stub_header") or (
            read_stub_hash_header(rec["stub_path"])
            if rec.get("stub_path")
            else None
        )
        extra = f" ({header})" if header else ""
        note_list.append(f"stub {rec['stub_path']}{extra}")
    if label:
        note_list.append(label)
    return {
        "top": rec.get("name"),
        "variant": "PRIVATE_SKIP",
        "ok": True,
        "private_skip": True,
        "layer": rec.get("layer"),
        "parent": rec.get("parent"),
        "n_inst": n_inst,
        "cells_mapped": 0,
        "area_um2": 0.0,
        "private_ci_area_um2": area,
        "private_ci_label": label,
        "flops": 0,
        "latency_cycles": rec.get("latency_cycles"),
        "notes": note_list,
        "anomalies": [],
        "delta_vs_baseline": "excluded (PRIVATE_SKIP)",
        "qor_over_10pct": [],
        "sram_est_um2": 0.0,
        "src": str(rec["stub_path"]) if rec.get("stub_path") else "",
    }
