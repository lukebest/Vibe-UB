#!/usr/bin/env python3
"""Generate register-map artifacts from docs/regmap/regmap.yaml.

stdlib + PyYAML only. Output is deterministic (no timestamps).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gen_csr import emit_ub_csr_regs  # noqa: E402
from regmap_lib import (  # noqa: E402
    DEFAULT_YAML,
    assert_valid,
    field_mask,
    field_width,
    is_window_reg,
    load_regmap,
    parse_int,
    reset_int,
)

BANNER = "GENERATED — edit docs/regmap/regmap.yaml"
NL = "\n"


def one_line(text: Any) -> str:
    return " ".join(str(text).split())


def hex4(value: int) -> str:
    return f"0x{value:04X}"


def reset_hex(field: dict[str, Any]) -> str:
    raw = field.get("reset")
    if raw == "NA" or raw is None:
        return "NA"
    if isinstance(raw, str):
        return raw
    return hex(int(raw))


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# docs/REGMAP.md
# ---------------------------------------------------------------------------

def emit_regmap_md(data: dict[str, Any]) -> str:
    meta = data["meta"]
    bus = meta["bus"]
    prose = data.get("prose") or {}
    out: list[str] = []
    w = out.append

    w(f"<!-- {BANNER} -->")
    w(f"# {meta['title']}")
    w("")
    w("| 项 | 值 |")
    w("| --- | --- |")
    w(f"| 配套规格 | [{meta['companion_spec']}]({meta['companion_spec']}) |")
    w(f"| 规范基线 | {meta['spec_baseline']} |")
    w(
        f"| 总线 | [{meta['companion_spec']}]({meta['companion_spec']}) "
        f"{bus.get('spec_ref', '§3.2.3').split()[-1]}："
        f"{bus['data_width_bits']}-bit 整字，无 `csr_wstrb`；"
        f"{bus['addr_width_bits']}-bit 字节地址，{bus['alignment_bytes']} 字节对齐；"
        f"读固定 {bus['read_latency_cycles']} 拍；"
        f"写响应下一拍 `csr_rvalid={bus.get('write_rvalid', 0)}` 且 `csr_err` 有效；"
        f"未映射读 {bus['unmapped']['read_data']}/`csr_err={bus['unmapped']['read_csr_err']}`，"
        f"写忽略/`csr_err={bus['unmapped']['write_csr_err']}` |"
    )
    w(f"| 字节序 | {meta['byte_order']} |")
    w("")
    if meta.get("team_process_note"):
        w(one_line(meta["team_process_note"]))
        w("")
    w(f"**引用约定：** {one_line(meta.get('citation_note', ''))}")
    w("")
    cols = ",".join(meta["machine_readable_columns"])
    w(f"**机器可读列：** `{cols}`")
    w("")
    notes = meta.get("column_notes") or {}
    if "offset_hex" in notes:
        w(f"- `offset_hex`：{notes['offset_hex']}")
    if "access" in notes:
        w(f"- `access`：{notes['access']}")
    if "reset_hex" in notes:
        w(f"- `reset_hex`：{notes['reset_hex']}")
    if "spec_ref" in notes:
        w(f"- `spec_ref`：{notes['spec_ref']}")
    if meta.get("test_window_rule"):
        w(f"- {one_line(meta['test_window_rule'])}")
    w("")
    w("---")
    w("")
    w("## 1. 窗口划分")
    w("")
    w("| 窗口 | 字节范围 | 内容 |")
    w("| --- | --- | --- |")
    for win in data["windows"]:
        start = parse_int(win["start"]) or 0
        end = parse_int(win["end"]) or 0
        w(f"| {win['name']} | `{hex4(start)}`–`{hex4(end)}` | {one_line(win['contents'])} |")
    w("")
    unimplemented = data.get("unimplemented") or []
    if unimplemented:
        w("不实现：" + "、".join(unimplemented) + "。")
        w("")
    w("---")
    w("")
    w("## 2. 字段表")
    w("")
    if data.get("reserved_policy"):
        w(one_line(data["reserved_policy"]))
        w("")

    by_window: dict[str, list[dict[str, Any]]] = {}
    for reg in data["registers"]:
        by_window.setdefault(reg["window"], []).append(reg)

    for win in data["windows"]:
        section = win.get("section") or win["name"]
        w(f"### {section}")
        w("")
        if win["id"] == "PARAM" and prose.get("param_intro"):
            w(one_line(prose["param_intro"]))
            w("")
        if win["id"] == "ERR" and prose.get("err_intro"):
            w(one_line(prose["err_intro"]))
            w("")
        if win["id"] == "TEST":
            for note in win.get("notes") or []:
                w(one_line(note))
                w("")
        if win["id"] == "APPD_PORT" and prose.get("appd_intro"):
            w(one_line(prose["appd_intro"]))
            w("")
        w("| offset_hex | reg_name | field_name | hi | lo | access | reset_hex | description | spec_ref |")
        w("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for reg in by_window.get(win["id"], []):
            off = hex4(parse_int(reg["offset"]) or 0)
            for field in reg["fields"]:
                w(
                    f"| {off} | {reg['name']} | {field['name']} | "
                    f"{field['msb']} | {field['lsb']} | {field['access']} | "
                    f"{reset_hex(field)} | {one_line(field['description'])} | "
                    f"{field['spec_ref']} |"
                )
        w("")
        if win["id"] == "CTRL_STATUS" and prose.get("irq"):
            w(one_line(prose["irq"]))
            w("")
        if win["id"] == "PARAM" and prose.get("init_block"):
            w(one_line(prose["init_block"]))
            w("")
        if win["id"] == "ERR" and prose.get("err_appd"):
            w(one_line(prose["err_appd"]))
            w("")
        if win["id"] == "TEST":
            if prose.get("test_credit_hooks"):
                w(one_line(prose["test_credit_hooks"]))
                w("")
            if prose.get("test_not_in_window"):
                w(one_line(prose["test_not_in_window"]))
                w("")
            if prose.get("test_hooks0"):
                w(one_line(prose["test_hooks0"]))
                w("")
        if win["id"] == "APPD_PORT":
            if prose.get("appd_mix"):
                w(one_line(prose["appd_mix"]))
                w("")
            if prose.get("appd_unimplemented"):
                w(one_line(prose["appd_unimplemented"]))
                w("")

    w("---")
    w("")
    w("## 3. 生成约定")
    w("")
    if prose.get("gen_intro"):
        w(one_line(prose["gen_intro"]))
        w("")
    for item in prose.get("gen_rules") or []:
        w(f"- {one_line(item)}")
    w("")
    if prose.get("gen_access"):
        w(one_line(prose["gen_access"]))
        w("")
    if prose.get("appd_migrate"):
        w(one_line(prose["appd_migrate"]))
        w("")
    return NL.join(out)


# ---------------------------------------------------------------------------
# Python constants (shared by verification)
# ---------------------------------------------------------------------------

def emit_py_constants(data: dict[str, Any]) -> str:
    lines = [
        f'"""UB M1 CSR constants. {BANNER}"""',
        "",
        "from __future__ import annotations",
        "",
        "WORD_BITS = 32",
        "ADDR_BITS = 16",
        "ALIGN_BYTES = 4",
        "READ_LATENCY_CYCLES = 1",
        "PORT_RST_PULSE_CYCLES = 16",
        "",
        "ACCESS_RW = \"RW\"",
        "ACCESS_RO = \"RO\"",
        "ACCESS_WO = \"WO\"",
        "ACCESS_W1C = \"W1C\"",
        "ACCESS_MIX = \"MIX\"",
        "",
        "WINDOWS = {",
    ]
    for win in data["windows"]:
        start = parse_int(win["start"]) or 0
        end = parse_int(win["end"]) or 0
        lines.append(
            f"    {win['id']!r}: {{'name': {win['name']!r}, 'start': {start:#06x}, 'end': {end:#06x}}},"
        )
    lines.append("}")
    lines.append("")

    for win in data["windows"]:
        start = parse_int(win["start"]) or 0
        end = parse_int(win["end"]) or 0
        ident = win["id"]
        lines.append(f"WIN_{ident}_START = {start:#06x}")
        lines.append(f"WIN_{ident}_END = {end:#06x}")
    lines.append("")

    for reg in data["registers"]:
        off = parse_int(reg["offset"]) or 0
        rname = reg["name"]
        lines.append(f"{rname} = {off:#06x}")
        lines.append(f"{rname}_OFFSET = {off:#06x}")
        for field in reg["fields"]:
            fname = field["name"]
            ident = f"{rname}_{fname}"
            lsb = int(field["lsb"])
            msb = int(field["msb"])
            width = field_width(field)
            mask = field_mask(field)
            lines.append(f"{ident}_LSB = {lsb}")
            lines.append(f"{ident}_MSB = {msb}")
            lines.append(f"{ident}_WIDTH = {width}")
            lines.append(f"{ident}_MASK = {mask:#010x}")
            lines.append(f"{ident}_SHIFT = {lsb}")
            lines.append(f"{ident}_ACCESS = {field['access']!r}")
            rst = reset_int(field)
            if rst is not None:
                lines.append(f"{ident}_RESET = {rst:#x}")
            else:
                lines.append(f"{ident}_RESET = None  # NA; see {field['spec_ref']}")
            for enum in field.get("enums") or []:
                ename = str(enum["name"]).upper()
                lines.append(f"{ident}_{ename} = {int(enum['value'])}")
            if field.get("legal_values"):
                vals = ", ".join(str(int(v)) for v in field["legal_values"])
                lines.append(f"{ident}_LEGAL = ({vals},)")
            if field.get("reserved_values"):
                vals = ", ".join(str(int(v)) for v in field["reserved_values"])
                lines.append(f"{ident}_RESERVED = ({vals},)")
            if field.get("self_clearing"):
                lines.append(f"{ident}_SELF_CLEARING = True")
            if field.get("saturating"):
                lines.append(f"{ident}_SATURATING = True")
            if field.get("pulse_cycles"):
                lines.append(f"{ident}_PULSE_CYCLES = {int(field['pulse_cycles'])}")
        lines.append("")

    lines.append("REGISTERS = (")
    for reg in data["registers"]:
        off = parse_int(reg["offset"]) or 0
        kind = "window" if is_window_reg(reg) else "register"
        lines.append(
            f"    {{'name': {reg['name']!r}, 'offset': {off:#06x}, "
            f"'window': {reg['window']!r}, 'kind': {kind!r}}},"
        )
    lines.append(")")
    lines.append("")
    lines.append("")
    lines.append("def field_get(word: int, mask: int, shift: int) -> int:")
    lines.append("    return (int(word) & int(mask)) >> int(shift)")
    lines.append("")
    lines.append("")
    lines.append("def field_insert(word: int, mask: int, shift: int, value: int) -> int:")
    lines.append("    return (int(word) & ~int(mask)) | ((int(value) << int(shift)) & int(mask))")
    lines.append("")
    return NL.join(lines)


# ---------------------------------------------------------------------------
# C header + HAL
# ---------------------------------------------------------------------------

def emit_c_header(data: dict[str, Any]) -> str:
    lines = [
        f"/* {BANNER} */",
        "#ifndef UB_REGS_H",
        "#define UB_REGS_H",
        "",
        "#include <stdint.h>",
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
        "#define UB_CSR_WORD_BITS          32u",
        "#define UB_CSR_ADDR_BITS          16u",
        "#define UB_CSR_ALIGN_BYTES        4u",
        "#define UB_CSR_READ_LATENCY       1u",
        "#define UB_CSR_PORT_RST_CYCLES    16u",
        "",
    ]
    for win in data["windows"]:
        ident = win["id"]
        start = parse_int(win["start"]) or 0
        end = parse_int(win["end"]) or 0
        lines.append(f"#define UB_WIN_{ident}_START  {start:#06x}u")
        lines.append(f"#define UB_WIN_{ident}_END    {end:#06x}u")
    lines.append("")
    for reg in data["registers"]:
        off = parse_int(reg["offset"]) or 0
        rname = reg["name"]
        lines.append(f"#define UB_REG_{rname}  {off:#06x}u")
        for field in reg["fields"]:
            fname = field["name"]
            ident = f"UB_{rname}_{fname}"
            lsb = int(field["lsb"])
            width = field_width(field)
            mask = field_mask(field)
            lines.append(f"#define {ident}_SHIFT  {lsb}u")
            lines.append(f"#define {ident}_WIDTH  {width}u")
            lines.append(f"#define {ident}_MASK   {mask:#010x}u")
            rst = reset_int(field)
            if rst is not None:
                lines.append(f"#define {ident}_RESET  {rst:#x}u")
            for enum in field.get("enums") or []:
                ename = str(enum["name"]).upper()
                lines.append(f"#define {ident}_{ename}  {int(enum['value'])}u")
        lines.append("")
    lines.extend(
        [
            "static inline uint32_t ub_fld_get(uint32_t word, uint32_t mask, unsigned shift)",
            "{",
            "    return (word & mask) >> shift;",
            "}",
            "",
            "static inline uint32_t ub_fld_insert(uint32_t word, uint32_t mask, unsigned shift, uint32_t value)",
            "{",
            "    return (word & ~mask) | ((value << shift) & mask);",
            "}",
            "",
        ]
    )
    for reg in data["registers"]:
        if is_window_reg(reg):
            continue
        rname = reg["name"]
        for field in reg["fields"]:
            if field["name"] == "RSVD":
                continue
            fname = field["name"]
            ident = f"UB_{rname}_{fname}"
            fn = f"ub_{rname.lower()}_{fname.lower()}"
            lines.append(
                f"static inline uint32_t {fn}_get(uint32_t word)"
            )
            lines.append("{")
            lines.append(f"    return ub_fld_get(word, {ident}_MASK, {ident}_SHIFT);")
            lines.append("}")
            lines.append("")
            if field["access"] in ("RW", "WO", "W1C"):
                lines.append(
                    f"static inline uint32_t {fn}_insert(uint32_t word, uint32_t value)"
                )
                lines.append("{")
                lines.append(
                    f"    return ub_fld_insert(word, {ident}_MASK, {ident}_SHIFT, value);"
                )
                lines.append("}")
                lines.append("")
    lines.extend(
        [
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            "#endif /* UB_REGS_H */",
            "",
        ]
    )
    return NL.join(lines)


def emit_hal_h(data: dict[str, Any]) -> str:
    lines = [
        f"/* {BANNER} */",
        "#ifndef UB_REGS_ACCESS_H",
        "#define UB_REGS_ACCESS_H",
        "",
        "#include \"ub_regs.h\"",
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
        "typedef uint32_t (*ub_csr_read_fn)(void *ctx, uint16_t addr);",
        "typedef void (*ub_csr_write_fn)(void *ctx, uint16_t addr, uint32_t data);",
        "",
        "typedef struct ub_csr_bus {",
        "    ub_csr_read_fn read;",
        "    ub_csr_write_fn write;",
        "    void *ctx;",
        "} ub_csr_bus_t;",
        "",
        "uint32_t ub_reg_read(const ub_csr_bus_t *bus, uint16_t addr);",
        "void ub_reg_write(const ub_csr_bus_t *bus, uint16_t addr, uint32_t data);",
        "",
        "/* Full-word only (SPEC §3.2.3). Unaligned addresses are the bus's csr_err path. */",
        "",
    ]
    for reg in data["registers"]:
        rname = reg["name"].lower()
        lines.append(f"uint32_t ub_{rname}_read(const ub_csr_bus_t *bus);")
        if is_window_reg(reg):
            continue
        writable = any(f["access"] in ("RW", "WO", "W1C") for f in reg["fields"])
        if writable:
            lines.append(f"void ub_{rname}_write(const ub_csr_bus_t *bus, uint32_t data);")
    lines.extend(
        [
            "",
            "#ifdef __cplusplus",
            "}",
            "#endif",
            "",
            "#endif /* UB_REGS_ACCESS_H */",
            "",
        ]
    )
    return NL.join(lines)


def emit_hal_c(data: dict[str, Any]) -> str:
    lines = [
        f"/* {BANNER} */",
        "#include \"ub_regs_access.h\"",
        "",
        "uint32_t ub_reg_read(const ub_csr_bus_t *bus, uint16_t addr)",
        "{",
        "    return bus->read(bus->ctx, addr);",
        "}",
        "",
        "void ub_reg_write(const ub_csr_bus_t *bus, uint16_t addr, uint32_t data)",
        "{",
        "    bus->write(bus->ctx, addr, data);",
        "}",
        "",
    ]
    for reg in data["registers"]:
        rname = reg["name"]
        lname = rname.lower()
        lines.append(f"uint32_t ub_{lname}_read(const ub_csr_bus_t *bus)")
        lines.append("{")
        lines.append(f"    return ub_reg_read(bus, (uint16_t)UB_REG_{rname});")
        lines.append("}")
        lines.append("")
        if is_window_reg(reg):
            continue
        writable = any(f["access"] in ("RW", "WO", "W1C") for f in reg["fields"])
        if writable:
            lines.append(f"void ub_{lname}_write(const ub_csr_bus_t *bus, uint32_t data)")
            lines.append("{")
            lines.append(f"    ub_reg_write(bus, (uint16_t)UB_REG_{rname}, data);")
            lines.append("}")
            lines.append("")
    return NL.join(lines)


# ---------------------------------------------------------------------------
# uvm-python RAL
# ---------------------------------------------------------------------------

def uvm_access(access: str) -> str:
    if access == "MIX":
        return "RW"
    return access


def py_ident(name: str) -> str:
    return name.lower()


def emit_ral(data: dict[str, Any]) -> str:
    lines = [
        f'"""UB M1 uvm-python register model. {BANNER}',
        "",
        "Lives at tb/ral/ub_regmodel.py (PR #6 tb/ is on main).",
        "",
        "Assumptions: uvm-python (tpoikela/uvm-python / lukebest/uvm-python) UVMReg,",
        "UVMRegField.configure(parent, size, lsb_pos, access, volatile, reset,",
        "has_reset, is_rand, individually_accessible). MIX/NA App. D windows are",
        "address placeholders only (REGMAP §3).",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "try:",
        "    from uvm.macros import uvm_object_utils",
        "    from uvm.reg import UVMReg, UVMRegBlock, UVMRegField",
        "    HAVE_UVM = True",
        "except ImportError:  # pragma: no cover - uvm-python not required to import",
        "    HAVE_UVM = False",
        "",
        "    def uvm_object_utils(_cls):",
        "        return _cls",
        "",
        "    class UVMReg:",
        "        def __init__(self, name, n_bits, has_coverage=0):",
        "            self.get_name = lambda: name",
        "            self.n_bits = n_bits",
        "            self._fields = []",
        "",
        "        def add_field(self, field):",
        "            self._fields.append(field)",
        "",
        "    class UVMRegField:",
        "        class type_id:",
        "            @staticmethod",
        "            def create(name):",
        "                obj = UVMRegField()",
        "                obj.get_name = lambda n=name: n",
        "                return obj",
        "",
        "        def configure(self, parent, size, lsb_pos, access, volatile, reset,",
        "                      has_reset, is_rand, individually_accessible):",
        "            self.size = size",
        "            self.lsb_pos = lsb_pos",
        "            self.access = access",
        "            self.volatile = volatile",
        "            self.reset = reset",
        "            self.has_reset = has_reset",
        "            if parent is not None:",
        "                parent.add_field(self)",
        "",
        "    class UVMRegBlock:",
        "        def __init__(self, name):",
        "            self.get_name = lambda: name",
        "            self.default_map = None",
        "            self._regs = []",
        "",
        "        def create_map(self, name, base_addr, n_bytes, endian, byte_addressing=1):",
        "            self.default_map = _Map(name, base_addr, n_bytes, endian)",
        "            return self.default_map",
        "",
        "        def lock_model(self):",
        "            self.locked = True",
        "",
        "    class _Map:",
        "        def __init__(self, name, base_addr, n_bytes, endian):",
        "            self.name = name",
        "            self.base_addr = base_addr",
        "            self.n_bytes = n_bytes",
        "            self.endian = endian",
        "            self.entries = []",
        "",
        "        def add_reg(self, reg, offset, rights, unmapped=0):",
        "            self.entries.append((reg, offset, rights, unmapped))",
        "",
        "",
    ]

    for reg in data["registers"]:
        cls = f"ub_{py_ident(reg['name'])}_reg"
        lines.append(f"class {cls}(UVMReg):")
        lines.append(f'    def __init__(self, name="{reg["name"]}"):')
        lines.append("        super().__init__(name, 32, 0)")
        for field in reg["fields"]:
            fname = field["name"]
            attr = fname if fname != "WINDOW" else "WINDOW"
            lines.append(
                f"        self.{attr} = UVMRegField.type_id.create({fname!r})"
            )
        lines.append("")
        lines.append("    def build(self):")
        for field in reg["fields"]:
            fname = field["name"]
            attr = fname if fname != "WINDOW" else "WINDOW"
            width = field_width(field)
            lsb = int(field["lsb"])
            access = uvm_access(field["access"])
            rst = reset_int(field)
            has_reset = 0 if rst is None else 1
            rst_v = 0 if rst is None else rst
            volatile = 1 if field["access"] in ("RO", "W1C", "WO") else 0
            lines.append(
                f"        self.{attr}.configure(self, {width}, {lsb}, {access!r}, "
                f"{volatile}, {rst_v}, {has_reset}, 1, 0)"
            )
        if is_window_reg(reg):
            lines.append(
                f"        # WINDOW placeholder; expand from {reg['fields'][0]['spec_ref']}"
            )
        lines.append("")
        lines.append("")
        lines.append(f"{cls} = uvm_object_utils({cls})")
        lines.append("")
        lines.append("")

    lines.append("class ub_reg_block(UVMRegBlock):")
    lines.append('    def __init__(self, name="ub_reg_block"):')
    lines.append("        super().__init__(name)")
    for reg in data["registers"]:
        attr = py_ident(reg["name"])
        cls = f"ub_{attr}_reg"
        lines.append(f"        self.{attr} = {cls}.type_id.create({reg['name']!r}) if HAVE_UVM else {cls}({reg['name']!r})")
    lines.append("")
    lines.append("    def build(self):")
    lines.append('        self.default_map = self.create_map("default_map", 0, 4, "LITTLE_ENDIAN")')
    for reg in data["registers"]:
        attr = py_ident(reg["name"])
        off = parse_int(reg["offset"]) or 0
        rights = "RO" if all(f["access"] == "RO" for f in reg["fields"]) else "RW"
        lines.append(f"        self.{attr}.configure(self) if HAVE_UVM else None")
        lines.append(f"        self.{attr}.build()")
        lines.append(f"        self.default_map.add_reg(self.{attr}, {off:#06x}, {rights!r})")
    lines.append("        self.lock_model()")
    lines.append("")
    lines.append("")
    lines.append("ub_reg_block = uvm_object_utils(ub_reg_block)")
    lines.append("")
    lines.append("")
    lines.append("def create_ub_regmodel(name: str = \"ub_reg_block\"):")
    lines.append("    model = ub_reg_block(name) if not HAVE_UVM else ub_reg_block.type_id.create(name)")
    lines.append("    if HAVE_UVM:")
    lines.append("        # type_id.create path still needs build()")
    lines.append("        pass")
    lines.append("    if not hasattr(model, 'default_map') or model.default_map is None:")
    lines.append("        model.build()")
    lines.append("    elif HAVE_UVM:")
    lines.append("        model.build()")
    lines.append("    return model")
    lines.append("")
    return NL.join(lines)


def emit_csr_init() -> str:
    return (
        f'"""ub_csr package. {BANNER}"""\n'
        "from .ub_csr_regs import PORT_RST_PULSE_CYCLES, elaborate, emit_verilog, generate\n"
        "\n"
        "__all__ = [\"PORT_RST_PULSE_CYCLES\", \"elaborate\", \"emit_verilog\", \"generate\"]\n"
    )


def emit_gen_init() -> str:
    return f'"""Generated register artifacts. {BANNER}"""\n'


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# Official generated paths (docs/regmap/README.md).
# pyCircuit source lives under pycircuit/<layer>/. rtl/ is generated Verilog
# only, written by scripts/emit_rtl.py (PR #5; not on main yet — follow-up).
OUTPUT_PATHS = (
    "docs/REGMAP.md",
    "pycircuit/csr/ub_csr_regs.py",
    "tb/ral/ub_regmodel.py",
    "sw/include/ub_regs.h",
    "sw/hal/ub_regs_access.h",
    "sw/hal/ub_regs_access.c",
    "model/regs.py",
)

COMPANION_PATHS = (
    "pycircuit/csr/__init__.py",
    "tb/ral/__init__.py",
    "model/__init__.py",
)


def render_all(data: dict[str, Any]) -> dict[str, str]:
    return {
        "docs/REGMAP.md": emit_regmap_md(data),
        "pycircuit/csr/ub_csr_regs.py": emit_ub_csr_regs(data),
        "pycircuit/csr/__init__.py": emit_csr_init(),
        "tb/ral/ub_regmodel.py": emit_ral(data),
        "tb/ral/__init__.py": emit_gen_init(),
        "model/regs.py": emit_py_constants(data),
        "model/__init__.py": emit_gen_init(),
        "sw/include/ub_regs.h": emit_c_header(data),
        "sw/hal/ub_regs_access.h": emit_hal_h(data),
        "sw/hal/ub_regs_access.c": emit_hal_c(data),
    }


def generate(data: dict[str, Any], out_root: Path) -> list[Path]:
    written: list[Path] = []
    for rel_path, text in render_all(data).items():
        dest = out_root / rel_path
        write_text(dest, text)
        written.append(dest)
    return written


def check_drift(data: dict[str, Any], repo_root: Path) -> list[str]:
    """Regenerate into a temp dir and diff against committed outputs."""
    import tempfile

    drift: list[str] = []
    expected = render_all(data)
    with tempfile.TemporaryDirectory(prefix="regmap-check-") as tmp:
        tmp_root = Path(tmp)
        generate(data, tmp_root)
        for rel_path, text in expected.items():
            committed = repo_root / rel_path
            fresh = tmp_root / rel_path
            if not committed.is_file():
                drift.append(f"{rel_path}: missing in tree")
                continue
            old = committed.read_text(encoding="utf-8")
            new = fresh.read_text(encoding="utf-8")
            if old != new:
                drift.append(f"{rel_path}: differs from generator ({len(old)} vs {len(new)} bytes)")
            if text != new:
                drift.append(f"{rel_path}: temp write mismatch")
    return drift


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yaml", type=Path, default=DEFAULT_YAML)
    parser.add_argument("--out-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="load + validate YAML, do not write outputs",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate into a temp dir and exit non-zero on drift",
    )
    args = parser.parse_args(argv)
    data = load_regmap(args.yaml)
    assert_valid(data)
    if args.validate_only:
        print(f"OK {args.yaml}")
        return 0
    if args.check:
        drift = check_drift(data, REPO_ROOT)
        if drift:
            print("regmap drift:")
            for item in drift:
                print(f"  {item}")
            print("run: python3 scripts/gen_regmap.py")
            return 1
        print("regmap check OK")
        return 0
    out_root = args.out_root.resolve()
    paths = generate(data, out_root)
    for path in paths:
        print(f"wrote {rel(path, out_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
