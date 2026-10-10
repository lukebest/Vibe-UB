"""YAML-attribute-driven ub_csr pyCircuit leaf emitter."""

from __future__ import annotations

from typing import Any

from regmap_lib import field_width, is_window_reg, parse_int, reset_int

BANNER = "GENERATED — edit docs/regmap/regmap.yaml"


def _qname(reg: str, field: str) -> str:
    return f"q_{reg.lower()}_{field.lower()}"


def _sel(reg: str) -> str:
    return f"sel_{reg.lower()}"


def _sv_width(width: int) -> str:
    return "      " if width == 1 else f"[{width - 1}:0]".rjust(6)


def _sv_lit(width: int, value: int) -> str:
    return f"{width}'h{value:x}"


def _field_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    win_info = {w["id"]: w for w in data["windows"]}
    for reg in data["registers"]:
        win = win_info[reg["window"]]
        for field in reg["fields"]:
            rows.append(
                {
                    "reg": reg["name"],
                    "offset": parse_int(reg["offset"]) or 0,
                    "window": reg["window"],
                    "test": bool(win.get("test_gated")),
                    "window_kind": is_window_reg(reg),
                    "entire_test": bool(win.get("entire_range_mapped")),
                    "field": field["name"],
                    "msb": int(field["msb"]),
                    "lsb": int(field["lsb"]),
                    "width": field_width(field),
                    "access": field["access"],
                    "reset": reset_int(field),
                    "self_clearing": bool(field.get("self_clearing")),
                    "saturating": bool(field.get("saturating")),
                    "pulse_cycles": field.get("pulse_cycles"),
                    "pulse_output": field.get("pulse_output"),
                    "clear_target": field.get("clear_target"),
                    "source": field.get("source"),
                    "hw_port": field.get("hw_port"),
                    "event_port": field.get("event_port"),
                    "increment_port": field.get("increment_port"),
                    "increment_gate": field.get("increment_gate"),
                    "config_output": field.get("config_output"),
                    "rsvd": field["name"] == "RSVD",
                }
            )
    return rows


def emit_ub_csr_regs(data: dict[str, Any]) -> str:
    """Emit rtl/csr/ub_csr_regs.py — table + attribute-driven Verilog engine."""
    rows = _field_rows(data)
    regs = data["registers"]
    windows = data["windows"]
    irq = data.get("irq") or {}
    rules = data["global_rules"]

    table_src = _py_repr_table(rows, regs, windows, irq, rules)
    engine = _ENGINE_SRC
    return f'''\
"""ub_csr register file — generated from docs/regmap/regmap.yaml.

{BANNER}

Attribute-driven CSR leaf (SPEC §2.2 / §3.2.3 / §11, CODING_STYLE).
Storage follows pyc_reg semantics: sync, ``rst_pyc`` active-high, ``core_clk``.
``TEST_HOOKS`` is expanded at Python generation time (two netlists).

Behaviors are emitted from YAML attributes, not hand-specialized per register:
W1C sticky + event ports; saturating RO counters + increment ports + CNT_CLR;
WO self-clear; PORT_RST ``pulse_cycles`` → ``port_rst_pulse``; IRQ aggregation;
TEST window gating; unmapped ``csr_err``; full-word writes; 1-cycle read.

Wiring event sources into ``ev_*`` / ``inc_*`` and fanning ``port_rst_pulse``
to PCS/LMSM/DLL/credit is **outside** this module (parent / ub_controller).

Regenerate: ``python3 scripts/gen_regmap.py``
Check:      ``python3 scripts/gen_regmap.py --check``
"""

from __future__ import annotations

from pathlib import Path

BANNER = {BANNER!r}

{table_src}

HERE = Path(__file__).resolve().parent
PRODUCT_V = HERE / "ub_csr.v"
HOOKS_V = HERE / "hooks" / "ub_csr.v"

{engine}
'''


def _py_repr_table(
    rows: list[dict[str, Any]],
    regs: list[dict[str, Any]],
    windows: list[dict[str, Any]],
    irq: dict[str, Any],
    rules: dict[str, Any],
) -> str:
    def lit(obj: Any) -> str:
        return repr(obj)

    lines = ["# Serialized map — do not edit; change docs/regmap/regmap.yaml", "FIELDS = ("]
    keys = (
        "reg",
        "offset",
        "window",
        "test",
        "window_kind",
        "field",
        "msb",
        "lsb",
        "width",
        "access",
        "reset",
        "self_clearing",
        "saturating",
        "pulse_cycles",
        "pulse_output",
        "clear_target",
        "source",
        "hw_port",
        "event_port",
        "increment_port",
        "increment_gate",
        "config_output",
        "rsvd",
    )
    for row in rows:
        slim = {k: row[k] for k in keys}
        lines.append(f"    {slim!r},")
    lines.append(")")
    lines.append("")
    lines.append("REGS = (")
    for reg in regs:
        lines.append(
            f"    {{'name': {reg['name']!r}, 'offset': {parse_int(reg['offset']) or 0}, "
            f"'window': {reg['window']!r}, 'kind': "
            f"{'window' if is_window_reg(reg) else 'register'!r}}},"
        )
    lines.append(")")
    lines.append("")
    lines.append("WINDOWS = (")
    for win in windows:
        lines.append(
            f"    {{'id': {win['id']!r}, 'start': {parse_int(win['start']) or 0}, "
            f"'end': {parse_int(win['end']) or 0}, "
            f"'test_gated': {bool(win.get('test_gated'))}, "
            f"'entire_range_mapped': {bool(win.get('entire_range_mapped'))}}},"
        )
    lines.append(")")
    lines.append("")
    lines.append(f"IRQ = {irq!r}")
    lines.append(f"RULES = { {k: rules[k] for k in rules if k != 'notes'} !r}")
    lines.append("PORT_RST_PULSE_CYCLES = 16")
    lines.append("")
    return "\n".join(lines)


# Generic engine embedded in the generated module. Walks FIELDS/REGS/WINDOWS/IRQ.
_ENGINE_SRC = r'''
def _header(test_hooks: int) -> str:
    return (
        "// Generated by rtl/csr/ub_csr_regs.py from docs/regmap/regmap.yaml.\n"
        f"// {BANNER}\n"
        f"// pyc4.0 leaf ub_csr. TEST_HOOKS={test_hooks} (Python generation-time).\n"
        "// Attribute-driven: W1C / saturating / WO self-clear / pulse_cycles /"
        " TEST gate / csr_err.\n"
        "// SPEC §2.2 / §3.2.3 / §11.\n"
    )


def _wdecl(width: int) -> str:
    return "      " if width == 1 else f"[{width - 1}:0]".rjust(6)


def emit_verilog(test_hooks: bool) -> str:
    """Emit one netlist from FIELDS / REGS / WINDOWS / IRQ attributes."""
    th = 1 if test_hooks else 0
    lines: list[str] = [_header(th)]

    def w(s: str = "") -> None:
        lines.append(s)

    hw = [f for f in FIELDS if f.get("hw_port")]
    ev = [f for f in FIELDS if f.get("event_port")]
    inc = [f for f in FIELDS if f.get("increment_port")]
    cfg = [f for f in FIELDS if f.get("config_output")]
    pulse = [f for f in FIELDS if f.get("pulse_output") and f.get("pulse_cycles")]
    w1c = [f for f in FIELDS if f["access"] == "W1C" and not f["rsvd"]]
    sat = [f for f in FIELDS if f.get("saturating")]
    rw = [f for f in FIELDS if f["access"] == "RW" and not f["rsvd"]]
    clr = [f for f in FIELDS if f.get("clear_target")]
    test_win = next(x for x in WINDOWS if x.get("test_gated"))

    w("module ub_csr (")
    ports = [
        "  input  wire        core_clk",
        "  input  wire        rst_pyc",
        "  input  wire        csr_req",
        "  input  wire        csr_wr",
        "  input  wire [15:0] csr_addr",
        "  input  wire [31:0] csr_wdata",
        "  output wire        csr_ready",
        "  output reg         csr_rvalid",
        "  output reg  [31:0] csr_rdata",
        "  output reg         csr_err",
    ]
    for f in hw:
        ports.append(f"  input  wire {_wdecl(f['width'])} {f['hw_port']}")
    for f in ev:
        ports.append(f"  input  wire        {f['event_port']}")
    for f in inc:
        ports.append(f"  input  wire        {f['increment_port']}")
    for f in pulse:
        ports.append(f"  output wire        {f['pulse_output']}")
    for f in cfg:
        ports.append(f"  output wire {_wdecl(f['width'])} {f['config_output']}")
    ports.append(f"  output wire        {IRQ.get('output', 'irq')}")
    if th:
        ports.append("  input  wire        tb_test_mode")
    w(",\n".join(ports))
    w(");")
    w("")
    w("  assign csr_ready = 1'b1; // full-word, no wait (SPEC §3.2.3)")
    w("  wire addr_aligned = (csr_addr[1:0] == 2'b00);")
    w("  wire req_fire     = csr_req;")
    w("  wire wr_fire      = req_fire & csr_wr;")
    w(
        f"  wire in_test      = (csr_addr[15:0] >= 16'h{test_win['start']:04X})"
        f" && (csr_addr[15:0] <= 16'h{test_win['end']:04X});"
    )
    if th:
        w("  wire test_active  = tb_test_mode;")
    else:
        w("  wire test_active  = 1'b0; // PRODUCT TEST_HOOKS=0")
    w("  wire test_hit     = in_test & addr_aligned;")
    w("")

    seen = set()
    for reg in REGS:
        if reg["name"] in seen:
            continue
        seen.add(reg["name"])
        w(
            f"  wire {_sel(reg['name'])} = addr_aligned"
            f" && (csr_addr[15:0] == 16'h{reg['offset']:04X});"
        )
    fn_sels = " | ".join(
        _sel(r["name"]) for r in REGS if r["window"] not in ("TEST",)
    )
    test_sels = " | ".join(_sel(r["name"]) for r in REGS if r["window"] == "TEST")
    w(f"  wire sel_fn   = {fn_sels};")
    w(f"  wire sel_test = {test_sels};")
    w("  wire wr_ok_fn   = wr_fire & sel_fn;")
    w("  wire wr_ok_test = wr_fire & sel_test & test_active;")
    w("  wire wr_ok      = wr_ok_fn | wr_ok_test;")
    w("")

    # storage declarations
    for f in rw + w1c + sat:
        w(f"  reg {_wdecl(f['width'])} {_qname(f['reg'], f['field'])};")
    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        w(f"  reg [{cw - 1}:0] cnt_{f['reg'].lower()}_{f['field'].lower()};")
    w("")

    # write enables
    for f in rw + w1c + pulse + clr:
        gate = "wr_ok_test" if f["test"] else "wr_ok_fn"
        w(f"  wire wr_{f['reg'].lower()}_{f['field'].lower()} = {gate} & {_sel(f['reg'])};")
    w("")

    # clear strobes from CNT_CLR
    for f in clr:
        w(
            f"  wire clr_{f['clear_target'].lower()} ="
            f" wr_{f['reg'].lower()}_{f['field'].lower()} & csr_wdata[{f['lsb']}];"
        )
    w("")

    # increment gates (prefer the field's config_output so TEST gating applies)
    for f in sat:
        gate = f.get("increment_gate")
        if gate:
            gfield = next(
                x for x in FIELDS
                if x["reg"] == gate["reg"] and x["field"] == gate["field"]
            )
            gsig = gfield.get("config_output") or _qname(gate["reg"], gate["field"])
            cond = f"~{gsig}" if gate.get("invert") else gsig
            w(f"  wire {f['increment_port']}_qual = {f['increment_port']} & {cond};")
        else:
            w(f"  wire {f['increment_port']}_qual = {f['increment_port']};")
    w("")

    w("  always @(posedge core_clk) begin")
    w("    if (rst_pyc) begin")
    for f in rw + w1c + sat:
        rst = 0 if f["reset"] is None else int(f["reset"])
        w(f"      {_qname(f['reg'], f['field'])} <= {_sv_lit(f['width'], rst)};")
    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        w(f"      cnt_{f['reg'].lower()}_{f['field'].lower()} <= {cw}'d0;")
    w("    end else begin")
    for f in rw:
        q = _qname(f["reg"], f["field"])
        wr = f"wr_{f['reg'].lower()}_{f['field'].lower()}"
        sl = f"csr_wdata[{f['msb']}:{f['lsb']}]" if f["width"] > 1 else f"csr_wdata[{f['lsb']}]"
        w(f"      if ({wr}) {q} <= {sl};")
    for f in w1c:
        q = _qname(f["reg"], f["field"])
        wr = f"wr_{f['reg'].lower()}_{f['field'].lower()}"
        evn = f["event_port"]
        w(f"      {q} <= ({q} | {evn}) & ~({wr} & csr_wdata[{f['lsb']}]);")
    for f in sat:
        q = _qname(f["reg"], f["field"])
        clr_n = f"clr_{f['reg'].lower()}"
        ones = f"{f['width']}'h" + ("f" * ((f["width"] + 3) // 4))
        w(f"      if ({clr_n})")
        w(f"        {q} <= {_sv_lit(f['width'], 0)};")
        w(f"      else if ({f['increment_port']}_qual && {q} != {ones})")
        w(f"        {q} <= {q} + 1'b1;")
    for f in pulse:
        cyc = int(f["pulse_cycles"])
        cw = max(1, cyc.bit_length())
        cnt = f"cnt_{f['reg'].lower()}_{f['field'].lower()}"
        wr = f"wr_{f['reg'].lower()}_{f['field'].lower()}"
        w(f"      if ({wr} & csr_wdata[{f['lsb']}])")
        w(f"        {cnt} <= {cw}'d{cyc};")
        w(f"      else if ({cnt} != {cw}'d0)")
        w(f"        {cnt} <= {cnt} - 1'b1;")
    w("    end")
    w("  end")
    w("")

    for f in pulse:
        cnt = f"cnt_{f['reg'].lower()}_{f['field'].lower()}"
        cw = max(1, int(f["pulse_cycles"]).bit_length())
        w(f"  assign {f['pulse_output']} = ({cnt} != {cw}'d0);")

    for f in cfg:
        q = _qname(f["reg"], f["field"])
        rst = 0 if f["reset"] is None else int(f["reset"])
        if f["test"]:
            w(
                f"  assign {f['config_output']} = test_active ? {q} :"
                f" {_sv_lit(f['width'], rst)};"
            )
        else:
            w(f"  assign {f['config_output']} = {q};")
    w("")

    # IRQ: enable & OR(status & ~mask). MASK bit 1 = block (REGMAP).
    st_bits = [f for f in w1c if f["reg"] == IRQ.get("status_reg", "IRQ_STATUS")]
    st_bits = sorted(st_bits, key=lambda x: x["lsb"])
    en = IRQ.get("enable") or {"reg": "CTRL", "field": "IRQ_EN"}
    mk = IRQ.get("mask") or {"reg": "IRQ_MASK", "field": "MASK"}
    st_cat = ", ".join(_qname(f["reg"], f["field"]) for f in reversed(st_bits))
    w(f"  wire [{len(st_bits) - 1}:0] irq_sticky = {{{st_cat}}};")
    w(f"  wire [{len(st_bits) - 1}:0] irq_mask_w = {_qname(mk['reg'], mk['field'])};")
    w(f"  assign {IRQ.get('output', 'irq')} = {_qname(en['reg'], en['field'])} & |(irq_sticky & ~irq_mask_w);")
    w("")

    # read data per register
    by_reg: dict[str, list] = {}
    for f in FIELDS:
        by_reg.setdefault(f["reg"], []).append(f)
    for rname, flist in by_reg.items():
        parts = []
        for f in sorted(flist, key=lambda x: -x["lsb"]):
            width = f["width"]
            if f["rsvd"] or f.get("window_kind") or (
                f["access"] == "WO" and f.get("self_clearing")
            ):
                parts.append(f"{width}'h0")
            elif f.get("hw_port"):
                parts.append(f["hw_port"])
            elif f["access"] in ("RW", "W1C") or f.get("saturating"):
                parts.append(_qname(f["reg"], f["field"]))
            elif f["access"] == "RO" and f["reset"] is not None:
                parts.append(_sv_lit(width, int(f["reset"])))
            else:
                parts.append(f"{width}'h0")
        w(f"  wire [31:0] rdata_{rname.lower()} = {{{', '.join(parts)}}};")
    w("")
    w("  reg [31:0] rdata_n;")
    w("  reg        err_n;")
    w("  always @* begin")
    w("    rdata_n = 32'h0;")
    w("    err_n   = 1'b0;")
    w("    if (req_fire) begin")
    w("      if (!addr_aligned) begin")
    w("        err_n = 1'b1;")
    w("      end else if (test_hit) begin")
    w("        err_n = 1'b0; // mapped; PRODUCT / tb_test_mode=0: rdata=0 write-ignore")
    w("        if (test_active) begin")
    for reg in [r for r in REGS if r["window"] == "TEST"]:
        w(f"          if ({_sel(reg['name'])}) rdata_n = rdata_{reg['name'].lower()};")
    w("        end")
    w("      end else begin")
    first = True
    for reg in [r for r in REGS if r["window"] != "TEST"]:
        kw = "if" if first else "else if"
        first = False
        w(f"        {kw} ({_sel(reg['name'])}) rdata_n = rdata_{reg['name'].lower()};")
    w("        else err_n = 1'b1; // unmapped")
    w("      end")
    w("    end")
    w("  end")
    w("")

    w("  always @(posedge core_clk) begin")
    w("    if (rst_pyc) begin")
    w("      csr_rvalid <= 1'b0;")
    w("      csr_rdata  <= 32'h0;")
    w("      csr_err    <= 1'b0;")
    w("    end else begin")
    w("      csr_rvalid <= req_fire & ~csr_wr; // 1-cycle read; write rvalid=0")
    w("      csr_rdata  <= rdata_n;")
    w("      csr_err    <= req_fire ? err_n : 1'b0;")
    w("    end")
    w("  end")
    w("")
    w("endmodule")
    w("")
    return "\n".join(lines) + "\n"


def _sv_lit(width: int, value: int) -> str:
    return f"{width}'h{value:x}"


def _sel(name: str) -> str:
    return f"sel_{name.lower()}"


def _qname(reg: str, field: str) -> str:
    return f"q_{reg.lower()}_{field.lower()}"


def elaborate(test_hooks: int = 0) -> dict:
    """Import/elaborate with pyc4.0 if present. Does not require pyCircuit."""
    status = {
        "test_hooks": int(test_hooks),
        "pycircuit": False,
        "elaborated": False,
        "reason": None,
        "verilog_chars": len(emit_verilog(bool(test_hooks))),
    }
    try:
        from pycircuit import Circuit, module, u  # type: ignore
    except ImportError as exc:
        status["reason"] = f"pycircuit not importable: {exc}"
        return status
    status["pycircuit"] = True

    @module
    def build(m: Circuit) -> None:
        clk = m.clock("core_clk")
        rst = m.reset("rst_pyc")
        _ = (clk, rst, u)
        m.input("csr_req", width=1)
        ready = m.out("csr_ready_q", clk=clk, rst=rst, width=1, init=u(1, 1))
        ready.set(u(1, 1))
        m.output("csr_ready", ready)

    try:
        _ = build
        status["elaborated"] = True
        status["reason"] = "pycircuit imported; @module build() constructed"
    except Exception as exc:  # pragma: no cover
        status["reason"] = f"pycircuit imported but elaborate failed: {exc}"
    return status


def main() -> int:
    PRODUCT_V.parent.mkdir(parents=True, exist_ok=True)
    HOOKS_V.parent.mkdir(parents=True, exist_ok=True)
    PRODUCT_V.write_text(emit_verilog(False), encoding="utf-8")
    HOOKS_V.write_text(emit_verilog(True), encoding="utf-8")
    print(f"wrote {PRODUCT_V}")
    print(f"wrote {HOOKS_V}")
    print(elaborate(0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
