#!/usr/bin/env python3
"""Register-pair compare for scripts/gate/equiv_ref.sh.

Both sides flatten first (pyc_reg → $dff/$adff). Pair after flatten and
before opt_clean. Walk each flattened $dff/$adff/$dffe/$adffe. rp_q_* is
the wire on that cell's Q pin; rp_d_* is the same cell's D pin — the
line after the reset/hold mux, never pyc_reg.d / *.__next. Pairing key:
collect every wire that shares the FF Q bit-group, drop pycc auto-names
(`pyc_reg_N`, `pyc_comb_N`, `__…L<line>` suffixes), normalize (last
hierarchy segment, lower-case), intersect with the other side. Exactly
one common name pairs; 0 or >1 is FAIL(pairing). Cell names are not
keys. Extra/missing/width: return code 4; caller treats that as
regpair=NOTAPPLICABLE(set-mismatch) and switches to uncut output seq
(PM: GATE-EQY-004). Strip clock (and async-reset used by the cut FFs)
so both sides share one named interface; leftover original ports keep
their names. Name-set mismatch is FAIL. Combo prove writes each cut side as an
ordinary AIGER (named PIs/POs, same name order, never `write_aiger
-miter`) and hands both to ABC `&cec`. A property AIGER (0 PO / 1 bad)
plus `&cec` is a script error. NOT EQ without a writable `write_cex`
replay is a script error, not a verdict. After `&cec` timeout, method (5)
affine may prove an XOR-family `rp_d_*` (or emit a replayable CEX).
Reset kind / polarity / value are checked separately (mismatch is FAIL).
All must hold.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from deadreg import leftover_pyc_reg

FF_TYPES = {
    "$dff",
    "$dffe",
    "$ff",
    "$sdff",
    "$sdffe",
    "$sdffce",
    "$adff",
    "$adffe",
    "$dffsr",
    "$dffsre",
    "$aldff",
}

ASYNC_RST_PINS = {
    "$adff": ("ARST",),
    "$adffe": ("ARST",),
    "$dffsr": ("CLR", "SET"),
    "$dffsre": ("CLR", "SET"),
    "$aldff": ("ALOAD",),
}

DELETE_SEL = " ".join(f"t:{t}" for t in sorted(FF_TYPES))

# Pairing after flatten only. pyc_reg must already have become $dff/$adff.
FLAT_FF = {"$dff", "$dffe", "$adff", "$adffe", "$sdff", "$sdffe", "$sdffce", "$ff"}

EXPECTED_KEYS = {
    "ub_dll_bcrc": ("crc", "crc_word", "done"),
    "ub_dll_bcrc_check": ("crc", "crc_word", "done", "recv_q", "ok_q", "fail_q", "eflag_q"),
}

# Design mid-block vector: all five next-states are crc=0, crc_word=0, done=0.
MIDBLOCK_CRC = 0x0F3025FF
MIDBLOCK_DATA = 0x95522B20C1A2B75FE014284D66455D40A1227BC3

NORM_HELP = (
    "flatten first, then $dff Q/D (D = post reset/hold mux, not pyc_reg.d / "
    "*__next). Pairing key = all wires on the Q bit-group, minus pycc "
    "auto-names (pyc_reg_N / pyc_comb_N / __…L<line>), last hierarchy "
    "segment, intersect both sides; exactly one pairs. Cell names are "
    "not keys. Pair before opt_clean. extra/missing/width = "
    "NOTAPPLICABLE(set-mismatch) → uncut output seq (PM)"
)


def _param_int(raw: object) -> int | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if re.fullmatch(r"[01]+", s):
        return int(s, 2)
    if re.fullmatch(r"[0-9a-fA-F]+", s) and len(s) > 8:
        return int(s, 16)
    try:
        return int(s, 0)
    except ValueError:
        return None


_PYC_AUTO_SEG = re.compile(r"^(pyc_reg|pyc_comb)_\d+(_inst)?$", re.I)
_LINE_SFX = re.compile(r"(?:__[A-Za-z_][A-Za-z0-9_]*)*__L\d+$")


def normalize_reg_name(name: str) -> str:
    """Last hierarchy segment after dropping a pycc __…L<line> suffix."""
    n = name.strip()
    if n.startswith("\\"):
        n = n[1:]
    n = n.replace("/", ".")
    n = n.split(".")[-1]
    n = re.sub(r"\[[^\]]+\]$", "", n)
    n = re.sub(r"\$.*$", "", n)
    n = _LINE_SFX.sub("", n)
    n = n.rstrip("_")
    return n.lower()


def is_pycc_auto_name(name: str) -> bool:
    """pyc_reg_N / pyc_comb_N / pyc_reg_N_inst.q and any path containing those."""
    raw = name[1:] if name.startswith("\\") else name
    raw = raw.replace("/", ".")
    return any(_PYC_AUTO_SEG.fullmatch(seg) for seg in raw.split("."))


def strip_q_key(key: str) -> str:
    return re.sub(r"_q$", "", key, flags=re.I)


def net_of_cell_port(mod: dict, bits: list) -> str | None:
    """Exact bit-vector match only. No subset / alias-superset fallback."""
    target = _bits_tuple(bits)
    if not target:
        return None
    scored: list[tuple[int, int, int, str]] = []
    for name, info in (mod.get("netnames") or {}).items():
        if _bits_tuple(info.get("bits") or []) != target:
            continue
        hide = 1 if info.get("hide_name") else 0
        ugly = 1 if ("$" in name or "func" in name) else 0
        scored.append((hide, ugly, len(name), name))
    if not scored:
        return None
    scored.sort()
    return scored[0][3]


def yosys_id(name: str) -> str:
    """Quote a Yosys identifier if it is not a plain id."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "\\" + name + " "


def _bits_tuple(bits: list) -> tuple:
    return tuple(bits)


_LOOP_TEMP = re.compile(r"^(by|bi|i|j|k|n|t|idx|cnt)$", re.I)


def is_arch_q_name(name: str) -> bool:
    """Architectural Q: public, not a $func leftover or loop/block temp."""
    raw = name[1:] if name.startswith("\\") else name
    if "$" in raw:
        return False
    last = raw.replace("/", ".").split(".")[-1]
    if _LOOP_TEMP.fullmatch(last):
        return False
    return True


def public_aliases(mod: dict, bits: list) -> list[str]:
    """Every net name that shares the exact Q/D bit-group (incl. hidden)."""
    target = _bits_tuple(bits)
    if not target:
        return []
    names: list[str] = []
    for name, info in (mod.get("netnames") or {}).items():
        raw = name[1:] if name.startswith("\\") else name
        if raw.startswith("$") or "$" in raw:
            continue
        if _bits_tuple(info.get("bits") or []) != target:
            continue
        names.append(name)
    return sorted(names)


def alias_keys(aliases: list[str]) -> dict[str, str]:
    """normalized architectural key → first original name.

    Drops pycc auto-names (pyc_reg_N / pyc_comb_N / __…L<line>) before
    intersecting with the other side.
    """
    out: dict[str, str] = {}
    for name in aliases:
        if is_pycc_auto_name(name):
            continue
        if not is_arch_q_name(name):
            continue
        key = normalize_reg_name(name)
        if not key or is_pycc_auto_name(key) or _LOOP_TEMP.fullmatch(key):
            continue
        if key not in out:
            out[key] = name
    return out


@dataclass
class Flop:
    cell: str
    ftype: str
    width: int
    q_name: str
    d_name: str | None
    key: str
    kind: str
    polarity: int | None
    value: int | None
    q_bits: tuple = field(default_factory=tuple)
    clk_name: str | None = None
    async_rst: tuple[str, ...] = ()
    q_aliases: tuple[str, ...] = ()
    key_candidates: tuple[str, ...] = ()


def _ff_reset(ftype: str, params: dict) -> tuple[str, int | None, int | None]:
    if ftype in {"$sdff", "$sdffe", "$sdffce"}:
        return (
            "sync",
            _param_int(params.get("SRST_POLARITY")),
            _param_int(params.get("SRST_VALUE")),
        )
    if ftype in {"$adff", "$adffe"}:
        return (
            "async",
            _param_int(params.get("ARST_POLARITY")),
            _param_int(params.get("ARST_VALUE")),
        )
    if ftype in {"$dffsr", "$dffsre"}:
        return ("async", _param_int(params.get("CLR_POLARITY")), None)
    if ftype == "$aldff":
        return ("async", _param_int(params.get("ALOAD_POLARITY")), None)
    return ("none", None, None)


def extract_flops(mod: dict) -> list[Flop]:
    cells = mod.get("cells") or {}
    found: list[Flop] = []
    for cname, cell in cells.items():
        ftype = cell.get("type") or ""
        ftype_norm = ftype.lstrip("\\")
        if ftype not in FLAT_FF:
            continue
        params = cell.get("parameters") or {}
        conns = cell.get("connections") or {}
        q_bits = conns.get("Q") or conns.get("q") or []
        d_bits = conns.get("D") or conns.get("d") or []
        width = _param_int(params.get("WIDTH")) or len(q_bits) or 1
        q_name = net_of_cell_port(mod, q_bits) or cname
        d_name = net_of_cell_port(mod, d_bits)
        aliases = public_aliases(mod, q_bits)
        keys = alias_keys(aliases)
        if not keys:
            # Function-proc leftovers / pycc-only names. Not architectural.
            continue
        kind, pol, val = _ff_reset(ftype, params)
        clk_name = net_of_cell_port(mod, conns.get("CLK") or conns.get("clk") or [])
        arst: list[str] = []
        for pin in ASYNC_RST_PINS.get(ftype, ()):
            n = net_of_cell_port(mod, conns.get(pin) or [])
            if n:
                arst.append(n)
        found.append(
            Flop(
                cell=cname,
                ftype=ftype,
                width=width,
                q_name=q_name,
                d_name=d_name,
                key="",
                kind=kind,
                polarity=pol,
                value=val,
                q_bits=_bits_tuple(q_bits),
                clk_name=clk_name,
                async_rst=tuple(arst),
                q_aliases=tuple(aliases),
                key_candidates=tuple(sorted(keys)),
            )
        )
    return found


def group_by_key(flops: list[Flop]) -> tuple[dict[str, Flop], list[str]]:
    """One flop per normalized key. Ambiguous keys are errors."""
    buckets: dict[str, list[Flop]] = {}
    for ff in flops:
        if not ff.key:
            continue
        buckets.setdefault(ff.key, []).append(ff)
    out: dict[str, Flop] = {}
    errors: list[str] = []
    for key, group in sorted(buckets.items()):
        if len(group) == 1:
            out[key] = group[0]
            continue
        widths = {f.width for f in group}
        names = [f"{f.q_name}:{f.width}" for f in group]
        errors.append(
            f"ambiguous key={key} cells={len(group)} widths={sorted(widths)} names={names}"
        )
    return out, errors


def assign_pairing_keys(
    gold_flops: list[Flop],
    gate_flops: list[Flop],
) -> list[str]:
    """Set ff.key from architectural Q aliases. Cell names are never keys.

    Collect every wire on the Q bit-group, drop pycc auto-names, normalize,
    intersect with the other side. Exactly one common name pairs.
    A side with one leftover name uses that name. 0 or >1 → FAIL(pairing).
    """
    gold_all = {k for ff in gold_flops for k in ff.key_candidates}
    gate_all = {k for ff in gate_flops for k in ff.key_candidates}
    errors: list[str] = []

    def resolve(side: str, flops: list[Flop], other: set[str]) -> None:
        for ff in flops:
            cands = list(ff.key_candidates)
            aliases = ",".join(ff.q_aliases) or "-"
            if len(cands) == 1:
                ff.key = cands[0]
                print(
                    f"equiv_ref REGPAIR resolve {side} cell={ff.cell} "
                    f"q_port={ff.q_name} d_port={ff.d_name} aliases={aliases} "
                    f"picked={ff.key} reason=unique"
                )
                continue
            common = sorted(set(cands) & other)
            if len(common) == 1:
                ff.key = common[0]
                print(
                    f"equiv_ref REGPAIR resolve {side} cell={ff.cell} "
                    f"q_port={ff.q_name} d_port={ff.d_name} aliases={aliases} "
                    f"picked={ff.key} reason=both-sides candidates={','.join(cands)}"
                )
                continue
            ff.key = ""
            msg = (
                f"{side} cell={ff.cell} q_port={ff.q_name} d_port={ff.d_name} "
                f"aliases={aliases} candidates={','.join(cands) or '-'} "
                f"common={','.join(common) or '-'}"
            )
            errors.append(msg)
            print(f"equiv_ref REGPAIR FAIL(pairing) {msg}")

    resolve("gold", gold_flops, gate_all)
    resolve("gate", gate_flops, gold_all)
    return errors


def rematch_q_suffix(gold_flops: list[Flop], gate_flops: list[Flop]) -> None:
    """crc vs crc_q: leftover keys that differ only by a trailing _q."""
    gold_map, _ = group_by_key(gold_flops)
    gate_map, _ = group_by_key(gate_flops)
    g_left = [ff for ff in gold_flops if ff.key and ff.key not in gate_map]
    t_left = [ff for ff in gate_flops if ff.key and ff.key not in gold_map]
    g_by: dict[str, list[Flop]] = {}
    t_by: dict[str, list[Flop]] = {}
    for ff in g_left:
        g_by.setdefault(strip_q_key(ff.key), []).append(ff)
    for ff in t_left:
        t_by.setdefault(strip_q_key(ff.key), []).append(ff)
    for sk, gffs in g_by.items():
        tffs = t_by.get(sk) or []
        if len(gffs) == 1 and len(tffs) == 1:
            old = tffs[0].key
            tffs[0].key = gffs[0].key
            print(
                f"equiv_ref REGPAIR rematch q-suffix key={gffs[0].key} "
                f"gate_was={old} gold_cell={gffs[0].cell} gate_cell={tffs[0].cell}"
            )


def reset_port(mod: dict) -> tuple[str | None, int | None]:
    ports = mod.get("ports") or {}
    for name in ("rst_pyc", "rst", "reset"):
        if name in ports:
            return name, 1
    if "rst_n" in ports:
        return "rst_n", 0
    return None, None


def parse_eval_values(text: str, names: list[str]) -> dict[str, int]:
    got: dict[str, int] = {}
    # Longest name first so rp_d_crc does not steal rp_d_crc_word.
    ordered = sorted(names, key=len, reverse=True)
    for line in text.splitlines():
        if "Eval result:" not in line:
            continue
        for name in ordered:
            if name in got:
                continue
            if not re.search(rf"(\\?{re.escape(name)})\s*=", line):
                continue
            m = re.search(r"=\s*(\d+)'h([0-9a-fA-F]+)", line)
            if m:
                got[name] = int(m.group(2), 16)
                continue
            m = re.search(r"=\s*(\d+)'b([01]+)", line)
            if m:
                got[name] = int(m.group(2), 2)
                continue
            m = re.search(r"=\s*(\d+)'([01]+)", line)
            if m:
                got[name] = int(m.group(2), 2)
                continue
            m = re.search(r"=\s*(\d+)\.?\s*$", line)
            if m:
                got[name] = int(m.group(1), 10)
    return got


def _eval_lit(val: int) -> str:
    if val < 0:
        return str(val)
    if val <= 1:
        return str(val)
    bits = max(val.bit_length(), 1)
    return f"{bits}'h{val:x}"


def eval_signals(
    rtlil: Path,
    top: str,
    assigns: dict[str, int],
    show: list[str],
    widths: dict[str, int] | None = None,
) -> dict[str, int]:
    if not show:
        return {}
    widths = widths or {}
    sets = []
    for name, val in assigns.items():
        w = widths.get(name)
        lit = f"{w}'h{val:x}" if w else _eval_lit(val)
        sets.append(f"-set {name} {lit}")
    shows = " ".join(f"-show {n}" for n in show)
    script = (
        f"read_rtlil {rtlil}\n"
        f"cd {top}\n"
        f"eval {' '.join(sets)} {shows}\n"
    )
    proc = subprocess.run(
        ["yosys", "-p", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return parse_eval_values(proc.stdout or "", show)


def eval_d_under_reset(rtlil: Path, top: str, d_names: list[str], rst: str, active: int) -> dict[str, int]:
    return eval_signals(rtlil, top, {rst: active}, d_names)


def eval_directed_midblock(tmp: Path, gold_cut_mod: dict) -> None:
    """Design mid-block vector. Correct cut → both D_crc/D_word/D_done = 0."""
    ports = gold_cut_mod.get("ports") or {}
    assigns = {
        "rst_pyc": 0,
        "start": 0,
        "valid_in": 1,
        "last": 0,
        "data_in": MIDBLOCK_DATA,
        "rp_q_crc": MIDBLOCK_CRC,  # 30-bit remainder 0x0F3025FF
        "rp_q_crc_word": 0,
        "rp_q_done": 0,
    }
    use = {k: v for k, v in assigns.items() if k in ports}
    show = [n for n in ("rp_d_crc", "rp_d_crc_word", "rp_d_done") if n in ports]
    widths = {"data_in": 160, "rp_q_crc": 30, "rp_q_crc_word": 32}
    gvals = eval_signals(tmp / "gold_cut.il", "gold", use, show, widths)
    tvals = eval_signals(tmp / "gate_cut.il", "gate", use, show, widths)
    expect = {"rp_d_crc": 0, "rp_d_crc_word": 0, "rp_d_done": 0}
    equal = all(gvals.get(n) == tvals.get(n) for n in show)
    zeros = all(gvals.get(n) == expect.get(n, 0) for n in show)
    match = equal and zeros
    print(
        f"equiv_ref REGPAIR directed_midblock "
        f"Q_crc=0x{MIDBLOCK_CRC:x} start=0 valid=1 last=0 "
        f"data=0x{MIDBLOCK_DATA:x} "
        f"gold_D_crc={gvals.get('rp_d_crc')} gate_D_crc={tvals.get('rp_d_crc')} "
        f"gold_D_word={gvals.get('rp_d_crc_word')} gate_D_word={tvals.get('rp_d_crc_word')} "
        f"gold_D_done={gvals.get('rp_d_done')} gate_D_done={tvals.get('rp_d_done')} "
        f"result={'match' if match else 'differ'}"
    )


def abc_kind(log: str) -> str:
    if re.search(r"Networks are equivalent", log):
        return "equivalent"
    if re.search(r"\bUNSATISFIABLE\b", log) and not re.search(r"NOT EQUIVALENT", log, re.I):
        return "equivalent"
    if re.search(r"NOT EQUIVALENT|Verification failed|\bSATISFIABLE\b", log, re.I):
        return "not_equivalent"
    return "unproven"


def sat_kind(log: str) -> str:
    if re.search(r"time ?out|timed out", log, re.I):
        return "unproven"
    if re.search(r"SAT [Mm]odel|Assert failed|failed to prove|SATISFIABLE", log, re.I):
        return "not_equivalent"
    if re.search(r"proved|UNSAT|verified successfully|successful proof", log, re.I):
        return "equivalent"
    return "unproven"


def conclusion_line(log: str) -> str:
    pats = (
        r"Networks are equivalent",
        r"NOT EQUIVALENT",
        r"Verification failed",
        r"Assert failed",
        r"SAT [Mm]odel",
        r"successful proof",
        r"proved",
        r"UNSAT",
        r"SATISFIABLE",
        r"timeout",
    )
    for line in log.splitlines():
        if re.search("|".join(pats), line, re.I):
            return line.strip()
    tail = [ln.strip() for ln in log.splitlines() if ln.strip()]
    return tail[-1] if tail else "(no prove conclusion line)"


def port_sets(mod: dict) -> tuple[list[str], list[str]]:
    pi: list[str] = []
    po: list[str] = []
    for name, info in (mod.get("ports") or {}).items():
        direction = info.get("direction")
        if direction == "input":
            pi.append(name)
        elif direction == "output":
            po.append(name)
        elif direction == "inout":
            pi.append(name)
            po.append(name)
    return sorted(pi), sorted(po)


def strip_ports_for(flops: list[Flop], mod: dict) -> list[str]:
    """Clock + async-reset PIs used by the cut FFs. Original data ports stay."""
    ports = set(mod.get("ports") or {})
    drop: set[str] = set()
    for ff in flops:
        if ff.clk_name and ff.clk_name in ports:
            drop.add(ff.clk_name)
        for rst in ff.async_rst:
            if rst in ports:
                drop.add(rst)
    return sorted(drop)


def write_cut_script(
    path: Path,
    top: str,
    pairs: list[tuple[str, Flop]],
    src_il: Path,
    dst_il: Path,
    dst_json: Path,
    strip: list[str],
) -> None:
    lines = [
        f"read_rtlil {src_il}",
        f"cd {top}",
    ]
    for key, ff in pairs:
        if not ff.d_name:
            raise SystemExit(f"equiv_ref REGPAIR missing D net for key={key} q={ff.q_name}")
        q_pin = "Q" if ff.ftype in FF_TYPES else "q"
        q_nets: list[str] = []
        for nm in (ff.q_name, *ff.q_aliases):
            if nm and nm not in q_nets:
                q_nets.append(nm)
        lines += [
            f"add -input rp_q_{key} {ff.width}",
            f"add -output rp_d_{key} {ff.width}",
        ]
        # Drive every Q alias (pycc may keep crc_word and crc_word_2 on
        # the same bits; write_verilog would otherwise split an undriven PI).
        # Replace the FF Q driver, then assign every public alias onto
        # rp_q_* (-nounset) so a leftover `crc` wire cannot stay undriven
        # while crc_word's D still reads it.
        if ff.q_name:
            lines += [
                f"connect -unset {yosys_id(ff.q_name)}",
                f"connect -set {yosys_id(ff.q_name)} rp_q_{key}",
            ]
        for nm in q_nets:
            lines.append(f"connect -nounset -set {yosys_id(nm)} rp_q_{key}")
        lines += [
            # Export the cell D pin net, not a combo / output alias.
            f"connect -set rp_d_{key} {yosys_id(ff.d_name)}",
            f"# cut cell={ff.cell} type={ff.ftype} q_pin={q_pin} "
            f"q_net={ff.q_name} d_net={ff.d_name} aliases={'|'.join(q_nets)}",
        ]
    lines += [
        f"delete {DELETE_SEL}",
    ]
    for name in strip:
        lines.append(f"delete -input {yosys_id(name)}")
    lines += [
        "opt_clean",
        f"write_rtlil {dst_il}",
        f"write_json {dst_json}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_yosys_file(script: Path, tmo: int) -> subprocess.CompletedProcess[str]:
    argv = ["yosys", "-q", "-s", str(script)]
    if tmo > 0:
        argv = ["timeout", str(tmo), *argv]
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def run_yosys_p(script: str, tmo: int, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    argv = ["yosys", "-p", script]
    if quiet:
        argv = ["yosys", "-q", "-p", script]
    if tmo > 0:
        argv = ["timeout", str(tmo), *argv]
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def run_abc(cmd: str, tmo: int, abc: str) -> subprocess.CompletedProcess[str]:
    argv = [abc, "-c", cmd]
    if tmo > 0:
        argv = ["timeout", str(tmo), *argv]
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def omit_output(il: Path, top: str, port: str, dst_il: Path, dst_json: Path, tmo: int) -> subprocess.CompletedProcess[str]:
    ys = (
        f"read_rtlil {il}\n"
        f"cd {top}\n"
        f"delete -output {yosys_id(port)}\n"
        "opt_clean\n"
        f"write_rtlil {dst_il}\n"
        f"write_json {dst_json}\n"
    )
    return run_yosys_p(ys, tmo, quiet=True)


def print_port_tables(label: str, pi: list[str], po: list[str]) -> None:
    print(f"equiv_ref REGPAIR {label}_pi={' '.join(pi) if pi else '(none)'}")
    print(f"equiv_ref REGPAIR {label}_po={' '.join(po) if po else '(none)'}")


def report_port_diffs(gold_pi: list[str], gold_po: list[str], gate_pi: list[str], gate_po: list[str]) -> bool:
    """Return True if name sets match. On mismatch print FAIL + missing names."""
    g_pi, t_pi = set(gold_pi), set(gate_pi)
    g_po, t_po = set(gold_po), set(gate_po)
    ok = g_pi == t_pi and g_po == t_po
    if ok:
        print("equiv_ref REGPAIR ports=PASS")
        return True
    for name in sorted(g_pi - t_pi):
        print(f"equiv_ref REGPAIR port_missing side=gate dir=pi name={name}")
    for name in sorted(t_pi - g_pi):
        print(f"equiv_ref REGPAIR port_missing side=gold dir=pi name={name}")
    for name in sorted(g_po - t_po):
        print(f"equiv_ref REGPAIR port_missing side=gate dir=po name={name}")
    for name in sorted(t_po - g_po):
        print(f"equiv_ref REGPAIR port_missing side=gold dir=po name={name}")
    print(
        "equiv_ref REGPAIR ports=FAIL "
        f"gold_only_pi={','.join(sorted(g_pi - t_pi)) or '-'} "
        f"gate_only_pi={','.join(sorted(t_pi - g_pi)) or '-'} "
        f"gold_only_po={','.join(sorted(g_po - t_po)) or '-'} "
        f"gate_only_po={','.join(sorted(t_po - g_po)) or '-'}"
    )
    return False


def witnesses_from_log(log: str, po_names: list[str]) -> list[str]:
    found: list[str] = []
    for name in po_names:
        if re.search(rf"\b{re.escape(name)}\b", log):
            found.append(name)
    for m in re.finditer(r"\b(rp_d_[A-Za-z0-9_]+)\b", log):
        if m.group(1) not in found:
            found.append(m.group(1))
    return found


def witnesses_from_sat_json(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    names: list[str] = []

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            name = obj.get("name") or obj.get("net") or obj.get("signal")
            val = obj.get("wave") or obj.get("value") or obj.get("data")
            if isinstance(name, str) and val is not None:
                text = name if isinstance(val, str) else f"{name}={val}"
                if re.search(r"rp_d_|cmp_|trigger", name) and re.search(r"[1xX]", str(val)):
                    names.append(name)
                elif isinstance(val, str) and "1" in val and name.startswith("cmp_"):
                    names.append(name)
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)

    _walk(data)
    return names


def port_width(mod: dict, name: str) -> int:
    bits = ((mod.get("ports") or {}).get(name) or {}).get("bits") or []
    return len(bits) if bits else 1


def _verilog_id(name: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "\\" + name + " "


def write_named_aig(
    il: Path,
    top: str,
    aig: Path,
    pis: list[str],
    pos: list[str],
    widths: dict[str, int],
    tmp: Path,
    tmo: int,
) -> tuple[bool, str]:
    """Ordinary combo AIGER. Architectural ports only, shared name order.

    Never `write_aiger -miter`. Never dump the cut through `write_verilog`
    (that splits Q aliases and promotes leftover wires to extra PIs so
    `&cec` sees unequal CI counts). Instantiate the RTLIL cut from a
    wrapper whose ports are the sorted name list.
    """
    keep = set(pis) | set(pos)
    tag = re.sub(r"[^A-Za-z0-9_]", "_", aig.stem)
    js = tmp / f"{top}_{tag}_ports.json"
    cleaned = tmp / f"{top}_{tag}_clean.il"
    wrap = tmp / f"{top}_{tag}_wrap.v"
    dumped = run_yosys_p(
        f"read_rtlil {il}\ncd {top}\nwrite_json {js}\n",
        tmo,
        quiet=True,
    )
    if dumped.returncode != 0 or not js.is_file():
        return False, dumped.stdout or "write_json for AIGER ports failed"
    try:
        mod = json.loads(js.read_text(encoding="utf-8"))["modules"][top]
    except (json.JSONDecodeError, KeyError) as exc:
        return False, f"cut json: {exc}"
    dels: list[str] = []
    for name, info in (mod.get("ports") or {}).items():
        if name in keep:
            continue
        direction = info.get("direction")
        if direction == "output":
            dels.append(f"delete -output {yosys_id(name)}")
        else:
            dels.append(f"delete -input {yosys_id(name)}")
    wname = f"wrap_{top}_{tag}"
    decl: list[str] = []
    conns: list[str] = []
    for name in pis:
        w = max(int(widths.get(name, 1) or 1), 1)
        vid = _verilog_id(name)
        decl.append(f"  input wire [{w - 1}:0] {vid}" if w > 1 else f"  input wire {vid}")
        conns.append(f"    .{vid}({vid})")
    for name in pos:
        w = max(int(widths.get(name, 1) or 1), 1)
        vid = _verilog_id(name)
        decl.append(f"  output wire [{w - 1}:0] {vid}" if w > 1 else f"  output wire {vid}")
        conns.append(f"    .{vid}({vid})")
    wrap.write_text(
        f"module {wname} (\n" + ",\n".join(decl) + "\n);\n"
        f"  {top} u (\n" + ",\n".join(conns) + "\n  );\nendmodule\n",
        encoding="utf-8",
    )
    ys = (
        f"read_rtlil {il}\n"
        f"cd {top}\n"
        + ("\n".join(dels) + "\n" if dels else "")
        + "setundef -undriven -zero\n"
        "opt_clean\n"
        f"write_rtlil {cleaned}\n"
        "design -reset\n"
        f"read_rtlil {cleaned}\n"
        f"read_verilog {wrap}\n"
        f"hierarchy -check -top {wname}\n"
        "proc; flatten; opt_expr; opt_clean\n"
        "techmap; opt; aigmap; opt\n"
        "setundef -undriven -zero\n"
        "opt_clean\n"
        # Binary AIGER. ABC `&r` reads ASCII `aag` as 0 ANDs and then
        # `&cec` reports a false EQ. Never `-miter` (that is a property AIGER).
        f"write_aiger -map {aig}.map {aig}\n"
    )
    built = run_yosys_p(ys, tmo, quiet=True)
    if built.returncode != 0 or not aig.is_file():
        return False, built.stdout or "write_aiger failed"
    return True, ""


def aiger_map_names(path: Path) -> tuple[list[str], list[str]]:
    """Parse Yosys `write_aiger -map` into (pi_names, po_names) in file order."""
    mp = Path(str(path) + ".map")
    if not mp.is_file():
        return [], []
    pis: list[str] = []
    pos: list[str] = []
    for line in mp.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 2:
            continue
        kind, name = parts[0], parts[-1]
        if kind == "input":
            pis.append(name)
        elif kind == "output":
            pos.append(name)
    return pis, pos


def print_aiger_name_tables(
    g_aig: Path,
    t_aig: Path,
    pis: list[str],
    pos: list[str],
    widths: dict[str, int],
) -> None:
    """Print wrapper vs AIGER name order so a PI/PO shuffle is visible."""
    wrap_pi: list[str] = []
    wrap_po: list[str] = []
    for name in pis:
        w = max(int(widths.get(name, 1) or 1), 1)
        wrap_pi.extend([f"{name}[{i}]" if w > 1 else name for i in range(w)])
    for name in pos:
        w = max(int(widths.get(name, 1) or 1), 1)
        wrap_po.extend([f"{name}[{i}]" if w > 1 else name for i in range(w)])
    print(f"equiv_ref REGPAIR aiger_wrap_pi={' '.join(wrap_pi) if wrap_pi else '(none)'}")
    print(f"equiv_ref REGPAIR aiger_wrap_po={' '.join(wrap_po) if wrap_po else '(none)'}")
    for label, aig in (("gold", g_aig), ("gate", t_aig)):
        mpi, mpo = aiger_map_names(aig)
        print(f"equiv_ref REGPAIR aiger_{label}_pi={' '.join(mpi) if mpi else '(none)'}")
        print(f"equiv_ref REGPAIR aiger_{label}_po={' '.join(mpo) if mpo else '(none)'}")
    g_pi, g_po = aiger_map_names(g_aig)
    t_pi, t_po = aiger_map_names(t_aig)
    if g_pi and t_pi and g_pi != t_pi:
        print("equiv_ref REGPAIR aiger_pi_name_diff gold_vs_gate")
        for i, (a, b) in enumerate(zip(g_pi, t_pi)):
            if a != b:
                print(f"equiv_ref REGPAIR aiger_pi_diff i={i} gold={a} gate={b}")
    if g_po and t_po and g_po != t_po:
        print("equiv_ref REGPAIR aiger_po_name_diff gold_vs_gate")
        for i, (a, b) in enumerate(zip(g_po, t_po)):
            if a != b:
                print(f"equiv_ref REGPAIR aiger_po_diff i={i} gold={a} gate={b}")


def aiger_counts(path: Path) -> tuple[int, int, int]:
    """Return (pi, latch, po) from an ASCII AIGER header."""
    if not path.is_file():
        return 0, 0, 0
    head = path.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    if not head:
        return 0, 0, 0
    parts = head[0].split()
    if len(parts) >= 5 and parts[0] in {"aag", "aig"}:
        return int(parts[2]), int(parts[3]), int(parts[4])
    return 0, 0, 0


def parse_named_cex(path: Path) -> dict[str, int]:
    """Parse `write_cex -n` (`name@frame=bit` or `name[i]@frame=bit`)."""
    if not path.is_file():
        return {}
    bits: dict[str, int] = {}
    buses: dict[str, dict[int, int]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.search(r"([A-Za-z0-9_./]+)(?:\[(\d+)\])?@(\d+)=([01])", line)
        if not m:
            continue
        name, idx, _fr, bit = m.group(1), m.group(2), m.group(3), int(m.group(4))
        if idx is None:
            bits[name] = bit
        else:
            buses.setdefault(name, {})[int(idx)] = bit
    out = dict(bits)
    for name, idxmap in buses.items():
        acc = 0
        for i, b in idxmap.items():
            acc |= (b & 1) << i
        out[name] = acc
    return out


def parse_positional_cex(path: Path, pis: list[str], widths: dict[str, int]) -> dict[str, int]:
    """Map a nameless ABC bit-string onto the wrapper PI order (LSB first)."""
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    blob = ""
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("."):
            continue
        bits = re.sub(r"[^01]", "", s)
        if len(bits) > len(blob):
            blob = bits
    if not blob:
        m = re.search(r"[01]{8,}", text)
        blob = m.group(0) if m else ""
    if not blob:
        return {}
    out: dict[str, int] = {}
    cursor = 0
    for name in pis:
        w = max(int(widths.get(name, 1) or 1), 1)
        chunk = blob[cursor:cursor + w]
        if len(chunk) < w:
            break
        acc = 0
        for i, ch in enumerate(chunk):
            if ch == "1":
                acc |= 1 << i
        out[name] = acc
        cursor += w
    return out


def parse_pi_pattern(log: str, pis: list[str], widths: dict[str, int]) -> dict[str, int]:
    """Map `pi224=0 pi160=1 …` from ABC `cec` onto the wrapper PI order."""
    bits: dict[int, int] = {}
    for m in re.finditer(r"\bpi(\d+)=([01])", log):
        bits[int(m.group(1))] = int(m.group(2))
    if not bits:
        return {}
    out: dict[str, int] = {}
    cursor = 0
    for name in pis:
        w = max(int(widths.get(name, 1) or 1), 1)
        acc = 0
        for i in range(w):
            acc |= bits.get(cursor + i, 0) << i
        out[name] = acc
        cursor += w
    return out


def cex_model(
    path: Path,
    pis: list[str],
    widths: dict[str, int],
    log: str = "",
) -> dict[str, int]:
    named = parse_named_cex(path)
    if named:
        return named
    pos = parse_positional_cex(path, pis, widths)
    if pos:
        return pos
    return parse_pi_pattern(log, pis, widths)


def explain_cex_on_ports(
    tmp: Path,
    assigns: dict[str, int],
    pos: list[str],
    widths: dict[str, int],
) -> tuple[str | None, str]:
    """Eval both cut sides; return (first differing PO, detail)."""
    use = {k: v for k, v in assigns.items() if k}
    gvals = eval_signals(tmp / "gold_cut.il", "gold", use, pos, widths)
    tvals = eval_signals(tmp / "gate_cut.il", "gate", use, pos, widths)
    for po in pos:
        gv, tv = gvals.get(po), tvals.get(po)
        if gv is None or tv is None:
            continue
        if gv != tv:
            return po, f"port={po} gold=0x{gv:x} gate=0x{tv:x}"
    return None, "eval found no differing PO"


def cec_pair(
    tmp: Path,
    gold_il: Path,
    gate_il: Path,
    pis: list[str],
    pos: list[str],
    widths: dict[str, int],
    abc: str,
    tmo: int,
    label: str,
) -> tuple[str, str, str, dict[str, int]]:
    """Two ordinary AIGERs, name-aligned, ABC &cec. Never write_aiger -miter."""
    g_aig = tmp / f"{label}_gold.aig"
    t_aig = tmp / f"{label}_gate.aig"
    ok_g, err_g = write_named_aig(gold_il, "gold", g_aig, pis, pos, widths, tmp, tmo)
    ok_t, err_t = write_named_aig(gate_il, "gate", t_aig, pis, pos, widths, tmp, tmo)
    if not ok_g or not ok_t:
        print(err_g + err_t)
        return "unproven", "aiger-build", "named AIGER build failed", {}
    g_pi, g_l, g_po = aiger_counts(g_aig)
    t_pi, t_l, t_po = aiger_counts(t_aig)
    exp_pi = sum(max(int(widths.get(n, 1) or 1), 1) for n in pis)
    exp_po = sum(max(int(widths.get(n, 1) or 1), 1) for n in pos)
    print(
        f"equiv_ref REGPAIR aiger label={label} "
        f"gold_pi={g_pi} gold_ff={g_l} gold_po={g_po} "
        f"gate_pi={t_pi} gate_ff={t_l} gate_po={t_po} "
        f"expect_pi={exp_pi} expect_po={exp_po} write_aiger=binary (no -ascii -miter)"
    )
    if g_l or t_l:
        print(f"equiv_ref REGPAIR SCRIPT_ERROR aiger_has_latches label={label}")
        return "script_error", "abc-&cec", "cut AIGER is not combinational", {}
    if g_po == 0 or t_po == 0:
        print(f"equiv_ref REGPAIR SCRIPT_ERROR aiger_zero_po label={label} (property AIGER, not combo CEC)")
        return "script_error", "abc-&cec", "AIGER has 0 POs (write_aiger -miter shape)", {}
    print_aiger_name_tables(g_aig, t_aig, pis, pos, widths)
    if g_pi != t_pi or g_po != t_po or g_pi != exp_pi or g_po != exp_po:
        print(
            f"equiv_ref REGPAIR SCRIPT_ERROR aiger_pi_po_mismatch label={label} "
            f"gold={g_pi}/{g_po} gate={t_pi}/{t_po} expect={exp_pi}/{exp_po}"
        )
        return "script_error", "abc-&cec", "AIGER PI/PO not name-aligned", {}
    cex = tmp / f"{label}.cex"
    # -m means "current network is already a miter". Two named combo AIGERs
    # must be loaded as a pair: &r gold; &cec gate. Never write_aiger -miter.
    cmd = f"&r {g_aig}; &cec -v -T {tmo} {t_aig}"
    print(f"equiv_ref REGPAIR abc_cmd={cmd}")
    proc = run_abc(cmd, tmo + 5 if tmo > 0 else 0, abc)
    log = proc.stdout or ""
    print(log)
    if not log.strip():
        print(f"equiv_ref REGPAIR abc_empty rc={proc.returncode}")
    kind = abc_kind(log)
    # &cec on a large Gia can time out with no line. Regular `cec -n`
    # matches CIs by order (wrapper order) and often finishes.
    if kind == "unproven":
        cmd2 = f"read {g_aig}; cec -n -v -T {tmo} {t_aig}"
        print(f"equiv_ref REGPAIR abc_cmd={cmd2}")
        proc2 = run_abc(cmd2, tmo + 5 if tmo > 0 else 0, abc)
        log2 = proc2.stdout or ""
        print(log2)
        log = (log + "\n" + log2).strip()
        kind = abc_kind(log2) if log2.strip() else kind
    line = conclusion_line(log)
    model: dict[str, int] = {}
    if kind == "not_equivalent":
        # &cec sim-disproof does not populate write_cex. Rebuild a miter
        # and SAT-save the witness, then map bits onto the named PI order.
        cex_cmd = f"&r {g_aig}; &miter {t_aig}; &sat -m -a; &put; write_cex {cex}"
        print(f"equiv_ref REGPAIR abc_cex_cmd={cex_cmd}")
        cproc = run_abc(cex_cmd, min(tmo, 20) + 5 if tmo > 0 else 0, abc)
        clog = cproc.stdout or ""
        print(clog)
        model = cex_model(cex, pis, widths, log + "\n" + clog)
    return kind, "abc-&cec", line, model


def directed_cut_vectors(pis: list[str]) -> list[dict[str, int]]:
    """Named-port vectors to replay a NOT EQ. Includes RX eflag/ok/fail probes."""
    zeros = {n: 0 for n in pis}
    init = dict(zeros)
    if "rp_q_crc" in init:
        init["rp_q_crc"] = 0x3FFFFFFF
    last_beat = dict(init)
    last_beat.update({"valid_in": 1, "last": 1})
    start_valid_last = dict(last_beat)
    start_valid_last["start"] = 1
    start_valid = dict(init)
    start_valid.update({"start": 1, "valid_in": 1})
    mid = dict(init)
    mid.update({"valid_in": 1, "data_in": MIDBLOCK_DATA, "rp_q_crc": MIDBLOCK_CRC})
    rst = dict(zeros)
    if "rst_pyc" in rst:
        rst["rst_pyc"] = 1
    recv_last = dict(last_beat)
    if "crc_recv" in recv_last:
        recv_last["crc_recv"] = 0x155
    if "rp_q_recv_q" in recv_last:
        recv_last["rp_q_recv_q"] = 0x155
    # RX eflag_n = done_q ? recv_q[30] : eflag_q. These two should differ
    # if gold uses `done` (next) and gate uses `done_q` (cut PI), or vice versa.
    eflag_set = dict(zeros)
    if "rp_q_done" in eflag_set:
        eflag_set["rp_q_done"] = 1
    if "rp_q_recv_q" in eflag_set:
        eflag_set["rp_q_recv_q"] = 1 << 30
    eflag_hold = dict(zeros)
    if "rp_q_eflag_q" in eflag_hold:
        eflag_hold["rp_q_eflag_q"] = 1
    ok_match = dict(zeros)
    if "rp_q_done" in ok_match:
        ok_match["rp_q_done"] = 1
    if "crc_recv" in ok_match and "rp_q_crc" in ok_match:
        ok_match["crc_recv"] = 0x155
        ok_match["rp_q_crc"] = 0x155
    ok_mismatch = dict(ok_match)
    if "crc_recv" in ok_mismatch:
        ok_mismatch["crc_recv"] = 0x2AA
    return [rst, last_beat, start_valid_last, start_valid, mid, recv_last, eflag_set, eflag_hold, ok_match, ok_mismatch]


def run_affine_on_pos(
    tmp: Path,
    pis: list[str],
    rp_pos: list[str],
    widths: dict[str, int],
    tmo: int,
) -> tuple[str, str, str, list[str]]:
    """GATE-EQY-004 (5). Only after &cec timeout (or --affine-only)."""
    from affine_prove import prove_affine_po

    kinds: list[tuple[str, str]] = []
    wit: list[str] = []
    last_line = ""
    for po in rp_pos:
        akind, aline, _acex, _rows = prove_affine_po(
            tmp, tmp / "gold_cut.il", tmp / "gate_cut.il", pis, po, widths, tmo
        )
        shown = "unproven" if akind == "na" else akind
        print(f"equiv_ref REGPAIR po_cec name={po} result={shown} method=affine line={aline}")
        last_line = aline
        kinds.append((po, akind))
        if akind == "not_equivalent":
            wit.append(po)
    if any(k == "not_equivalent" for _po, k in kinds):
        return "not_equivalent", "affine", last_line, wit
    if any(k == "na" for _po, k in kinds):
        return "unproven", "affine", last_line, []
    return "equivalent", "affine", last_line, []


def prove_miter(
    tmp: Path,
    tmo: int,
    abc: str,
    po_names: list[str],
    affine_only: bool = False,
) -> tuple[str, str, str, list[str]]:
    """Name-aligned combo CEC of the two cut nets. Option (a): not property AIGER."""
    gold_mod = json.loads((tmp / "gold_cut.json").read_text(encoding="utf-8"))["modules"]["gold"]
    gate_mod = json.loads((tmp / "gate_cut.json").read_text(encoding="utf-8"))["modules"]["gate"]
    gold_pi, gold_po = port_sets(gold_mod)
    _t_pi, _t_po = port_sets(gate_mod)
    pis = sorted(gold_pi)
    # Next-state only. Leftover leaf outputs (crc_word/done) are Q
    # passthroughs after the cut; pycc may const-0 them and ABC then
    # reports a trivial "PI vs. constant" NOT EQ that is not a D mismatch.
    pos = sorted(n for n in gold_po if n in po_names and n.startswith("rp_d_"))
    if not pos:
        pos = sorted(n for n in gold_po if n in po_names)
    widths = {n: port_width(gold_mod, n) for n in pis + pos}
    for n in pis + pos:
        widths.setdefault(n, port_width(gate_mod, n))
    rp_pos = [po for po in pos if po.startswith("rp_d_")]

    if affine_only:
        print("equiv_ref REGPAIR affine_only=1 skip=&cec")
        return run_affine_on_pos(tmp, pis, rp_pos, widths, tmo)

    kind, used, line, model = cec_pair(
        tmp, tmp / "gold_cut.il", tmp / "gate_cut.il", pis, pos, widths, abc, tmo, "all"
    )
    if kind == "equivalent":
        # A subset of an equivalent PO set is equivalent. Do not rebuild a
        # 1-PO AIGER (opt after deleting the other POs can fool &cec).
        for po in rp_pos:
            print(f"equiv_ref REGPAIR po_cec name={po} result=equivalent line={line}")
        return kind, used, line, []
    if kind == "script_error":
        print("equiv_ref REGPAIR SCRIPT_ERROR not_eq_or_bad_aiger_without_combo_cec")
        for po in rp_pos:
            print(f"equiv_ref REGPAIR po_cec name={po} result=script_error line={line}")
        return "script_error", used, line, []
    if kind == "unproven":
        # GATE-EQY-004 (5): XOR next-state after &cec timeout.
        print("equiv_ref REGPAIR note=&cec timeout; trying method=affine")
        return run_affine_on_pos(tmp, pis, rp_pos, widths, tmo)

    # NOT EQ is only a verdict when write_cex produced a replayable model
    # that differs on a named port. Otherwise it is a script error.
    candidates: list[dict[str, int]] = []
    if model:
        candidates.append(model)
    candidates += directed_cut_vectors(pis)
    wit: list[str] = []
    used_model: dict[str, int] | None = None
    for cand in candidates:
        use = {k: v for k, v in cand.items() if k in pis}
        probe = rp_pos or pos
        diff, detail = explain_cex_on_ports(tmp, use, probe, widths)
        if diff is None:
            continue
        used_model = use
        break
    if used_model is None:
        # Per-PO &cec to name the differing output, then directed again.
        # 1-bit POs first (RX eflag/ok/fail/done).
        by_w = sorted(rp_pos, key=lambda n: widths.get(n, 1))
        for po in by_w:
            pk, _pu, pline, pmodel = cec_pair(
                tmp, tmp / "gold_cut.il", tmp / "gate_cut.il",
                pis, [po], widths, abc, min(max(tmo, 1), 20), f"po_{po}",
            )
            print(f"equiv_ref REGPAIR po_cec name={po} result={pk} line={pline}")
            if pk == "equivalent":
                continue
            if pk == "not_equivalent":
                more = [pmodel] if pmodel else []
                more += directed_cut_vectors(pis)
                for cand in more:
                    use = {k: v for k, v in cand.items() if k in pis}
                    diff, detail = explain_cex_on_ports(tmp, use, [po], widths)
                    if diff is None:
                        continue
                    print(
                        "equiv_ref REGPAIR cex_inputs "
                        + " ".join(f"{k}=0x{v:x}" for k, v in sorted(use.items()) if k in pis)
                    )
                    print(f"equiv_ref REGPAIR cex_ok=1 po={po} {detail}")
                    return "not_equivalent", used, pline, [po]
        print("equiv_ref REGPAIR SCRIPT_ERROR not_eq_without_cex")
        return "script_error", used, line, []
    print(
        "equiv_ref REGPAIR cex_inputs "
        + " ".join(f"{k}=0x{v:x}" for k, v in sorted(used_model.items()) if k in pis)
    )
    for po in rp_pos or pos:
        diff, detail = explain_cex_on_ports(tmp, used_model, [po], widths)
        if diff is None:
            print(f"equiv_ref REGPAIR po_cec name={po} result=equivalent line={line}")
            continue
        print(f"equiv_ref REGPAIR po_cec name={po} result=not_equivalent line={line}")
        print(f"equiv_ref REGPAIR cex_ok=1 po={po} {detail}")
        wit.append(po)
    if not wit:
        print("equiv_ref REGPAIR SCRIPT_ERROR cex_not_replayable eval found no differing PO")
        return "script_error", used, line, []
    return "not_equivalent", used, line, wit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leaf", required=True)
    ap.add_argument("--tmp", required=True, type=Path)
    ap.add_argument("--abc", default="yosys-abc")
    ap.add_argument("--tmo", type=int, default=90)
    ap.add_argument(
        "--omit-po",
        default="",
        help="Self-test: drop this output on --omit-side after the cut (e.g. rp_d_crc).",
    )
    ap.add_argument("--omit-side", default="gold", choices=("gold", "gate"))
    ap.add_argument(
        "--affine-only",
        action="store_true",
        help="Skip &cec; run GATE-EQY-004 (5) affine on each rp_d_* (self-test).",
    )
    args = ap.parse_args()
    tmp = args.tmp
    gold_json = json.loads((tmp / "gold.json").read_text(encoding="utf-8"))
    gate_json = json.loads((tmp / "gate.json").read_text(encoding="utf-8"))
    gold_mod = gold_json["modules"]["gold"]
    gate_mod = gate_json["modules"]["gate"]

    print(f"equiv_ref REGPAIR norm={NORM_HELP}")

    pyc_g = leftover_pyc_reg(gold_mod)
    pyc_t = leftover_pyc_reg(gate_mod)
    if pyc_g or pyc_t:
        print(f"equiv_ref REGPAIR FAIL leftover_pyc_reg gold={pyc_g or '-'} gate={pyc_t or '-'}")
        print("equiv_ref REGPAIR regpair=FAIL(flatten)")
        return 2

    gold_flops = extract_flops(gold_mod)
    gate_flops = extract_flops(gate_mod)
    premux = [
        (side, ff)
        for side, flops in (("gold", gold_flops), ("gate", gate_flops))
        for ff in flops
        if ff.d_name and "__next" in ff.d_name
    ]
    for side, ff in premux:
        print(
            f"equiv_ref REGPAIR FAIL pre-mux D {side} cell={ff.cell} d={ff.d_name} "
            "(must use flattened $dff D after reset/hold mux, not pyc_reg.d)"
        )
    if premux:
        print("equiv_ref REGPAIR regpair=FAIL(cut)")
        return 1
    print("equiv_ref REGPAIR csv side,cell,type,q_port,d_port,public_q_aliases,key_candidates")
    for side, flops in (("gold", gold_flops), ("gate", gate_flops)):
        for ff in flops:
            print(
                f"equiv_ref REGPAIR csv {side},{ff.cell},{ff.ftype},"
                f"{ff.q_name},{ff.d_name},{'|'.join(ff.q_aliases) or '-'},"
                f"{'|'.join(ff.key_candidates) or '-'}"
            )
    resolve_err = assign_pairing_keys(gold_flops, gate_flops)
    rematch_q_suffix(gold_flops, gate_flops)
    gold_map, gold_amb = group_by_key(gold_flops)
    gate_map, gate_amb = group_by_key(gate_flops)
    unresolved = [ff for ff in gold_flops + gate_flops if not ff.key]
    for msg in gold_amb + gate_amb:
        print(f"equiv_ref REGPAIR FAIL {msg}")

    keys = sorted(set(gold_map) | set(gate_map))
    pairs: list[tuple[str, Flop, Flop]] = []
    unmatched_gold: list[Flop] = []
    unmatched_gate: list[Flop] = []
    width_mismatch: list[str] = []

    for key in keys:
        g = gold_map.get(key)
        t = gate_map.get(key)
        if g and t:
            if g.width != t.width:
                width_mismatch.append(
                    f"key={key} gold_width={g.width} gate_width={t.width} "
                    f"gold={g.q_name} gate={t.q_name}"
                )
            else:
                pairs.append((key, g, t))
        elif g:
            unmatched_gold.append(g)
        else:
            unmatched_gate.append(t)  # type: ignore[arg-type]

    print(
        f"equiv_ref REGPAIR pairs={len(pairs)} unmatched={len(unmatched_gold) + len(unmatched_gate)} "
        f"unmatched_gold={len(unmatched_gold)} unmatched_gate={len(unmatched_gate)}"
    )
    for key, g, t in pairs:
        print(
            f"equiv_ref REGPAIR pair key={key} width={g.width} "
            f"gold_cell={g.cell} gate_cell={t.cell} "
            f"gold_q={g.q_name} gate_q={t.q_name} gold_d={g.d_name} gate_d={t.d_name} "
            f"gold_type={g.ftype} gate_type={t.ftype}"
        )
    for ff in unmatched_gold:
        print(
            f"equiv_ref REGPAIR unmatched gold key={ff.key} width={ff.width} "
            f"cell={ff.cell} q={ff.q_name} d={ff.d_name}"
        )
    for ff in unmatched_gate:
        print(
            f"equiv_ref REGPAIR unmatched gate key={ff.key} width={ff.width} "
            f"cell={ff.cell} q={ff.q_name} d={ff.d_name}"
        )
    for msg in width_mismatch:
        print(f"equiv_ref REGPAIR width_mismatch {msg}")

    set_mismatch = bool(
        gold_amb or gate_amb or unmatched_gold or unmatched_gate
        or width_mismatch or resolve_err or unresolved
    )
    exp = EXPECTED_KEYS.get(args.leaf)
    got = tuple(sorted({k for k, _g, _t in pairs}))
    if exp:
        print(f"equiv_ref REGPAIR expected_keys={','.join(exp)}")
        print(f"equiv_ref REGPAIR got_keys={','.join(got) if got else '-'}")
    if set_mismatch:
        print("equiv_ref REGPAIR pairing=FAIL")
        print("equiv_ref REGPAIR cec_line=skipped (set-mismatch extra/missing/width)")
        print("equiv_ref REGPAIR reset=skipped (set-mismatch)")
        print("equiv_ref REGPAIR method=regpair result=set_mismatch")
        print("equiv_ref REGPAIR regpair=FAIL(pairing)")
        print("equiv_ref REGPAIR set_mismatch=1")
        return 4
    print("equiv_ref REGPAIR pairing=PASS")

    rst_g, act_g = reset_port(gold_mod)
    rst_t, act_t = reset_port(gate_mod)
    eval_g: dict[str, int] = {}
    eval_t: dict[str, int] = {}
    if rst_g and act_g is not None:
        eval_g = eval_d_under_reset(
            tmp / "gold.il",
            "gold",
            [g.d_name for _k, g, _t in pairs if g.d_name],
            rst_g,
            act_g,
        )
    if rst_t and act_t is not None:
        eval_t = eval_d_under_reset(
            tmp / "gate.il",
            "gate",
            [t.d_name for _k, _g, t in pairs if t.d_name],
            rst_t,
            act_t,
        )

    reset_ok = True
    for key, g, t in pairs:
        g_kind, t_kind = g.kind, t.kind
        g_pol, t_pol = g.polarity, t.polarity
        g_val, t_val = g.value, t.value
        if g_val is None and g.d_name and g.d_name in eval_g:
            g_val = eval_g[g.d_name]
        if t_val is None and t.d_name and t.d_name in eval_t:
            t_val = eval_t[t.d_name]
        kind_m = g_kind == t_kind
        pol_m = True if g_kind == "none" else g_pol == t_pol
        val_m = g_val == t_val
        row = "match" if (kind_m and pol_m and val_m) else "mismatch"
        if row != "match":
            reset_ok = False
        print(
            f"equiv_ref REGPAIR reset key={key} "
            f"gold={g_kind}/pol={g_pol}/val={g_val} "
            f"gate={t_kind}/pol={t_pol}/val={t_val} result={row}"
        )
    if not pairs:
        print("equiv_ref REGPAIR reset=PASS (no registers)")
    elif reset_ok:
        print("equiv_ref REGPAIR reset=PASS")
    else:
        print("equiv_ref REGPAIR reset=FAIL")

    for key, g, t in pairs:
        g_val, t_val = g.value, t.value
        if g_val is None and g.d_name and g.d_name in eval_g:
            g_val = eval_g[g.d_name]
        if t_val is None and t.d_name and t.d_name in eval_t:
            t_val = eval_t[t.d_name]
        print(
            f"equiv_ref REGPAIR table key={key} width={g.width} "
            f"gold_cell={g.cell} gate_cell={t.cell} "
            f"rst_gold={g_val} rst_gate={t_val} "
            f"gold_q={g.q_name} gate_q={t.q_name} "
            f"gold_d={g.d_name} gate_d={t.d_name}"
        )

    gold_strip = strip_ports_for([g for _k, g, _t in pairs], gold_mod)
    gate_strip = strip_ports_for([t for _k, _g, t in pairs], gate_mod)
    print(f"equiv_ref REGPAIR strip_gold={' '.join(gold_strip) if gold_strip else '(none)'}")
    print(f"equiv_ref REGPAIR strip_gate={' '.join(gate_strip) if gate_strip else '(none)'}")

    gold_cut = tmp / "gold_cut.il"
    gate_cut = tmp / "gate_cut.il"
    gold_cut_json = tmp / "gold_cut.json"
    gate_cut_json = tmp / "gate_cut.json"
    write_cut_script(
        tmp / "cut_gold.ys",
        "gold",
        [(k, g) for k, g, _t in pairs],
        tmp / "gold.il",
        gold_cut,
        gold_cut_json,
        gold_strip,
    )
    write_cut_script(
        tmp / "cut_gate.ys",
        "gate",
        [(k, t) for k, _g, t in pairs],
        tmp / "gate.il",
        gate_cut,
        gate_cut_json,
        gate_strip,
    )
    gcut = run_yosys_file(tmp / "cut_gold.ys", args.tmo)
    tcut = run_yosys_file(tmp / "cut_gate.ys", args.tmo)
    if gcut.returncode == 0 and tcut.returncode == 0:
        # Re-assign Q aliases after opt_clean; pycc often leaves a second
        # `crc` wire whose bits are no longer rp_q_crc.
        for side, pairs_side in (
            ("gold", [(k, g) for k, g, _t in pairs]),
            ("gate", [(k, t) for k, _g, t in pairs]),
        ):
            cut_json = json.loads((tmp / f"{side}_cut.json").read_text(encoding="utf-8"))
            cmod = cut_json["modules"][side]
            nets = cmod.get("netnames") or {}
            rec = [f"read_rtlil {tmp / (side + '_cut.il')}", f"cd {side}"]
            for key, ff in pairs_side:
                qn = f"rp_q_{key}"
                qbits = _bits_tuple((nets.get(qn) or {}).get("bits") or [])
                for nm in (ff.q_name, *ff.q_aliases):
                    if not nm:
                        continue
                    abits = _bits_tuple((nets.get(nm) or {}).get("bits") or [])
                    if not abits or abits == qbits:
                        continue
                    rec.append(f"connect -nounset -set {yosys_id(nm)} {qn}")
            rec += [
                "opt_clean",
                f"write_rtlil {tmp / (side + '_cut.il')}",
                f"write_json {tmp / (side + '_cut.json')}",
            ]
            rec_ys = tmp / f"reconnect_{side}.ys"
            rec_ys.write_text("\n".join(rec) + "\n", encoding="utf-8")
            rproc = run_yosys_file(rec_ys, args.tmo)
            if rproc.returncode != 0:
                print(rproc.stdout or "")
                print("equiv_ref REGPAIR cec_line=reconnect aliases failed")
                print("equiv_ref REGPAIR method=regpair result=unproven")
                print("equiv_ref REGPAIR regpair=FAIL(cut)")
                return 1
    if gcut.returncode != 0 or tcut.returncode != 0:
        print((gcut.stdout or "") + (tcut.stdout or ""))
        print("equiv_ref REGPAIR cec_line=cut failed")
        print("equiv_ref REGPAIR method=regpair result=unproven")
        print("equiv_ref REGPAIR regpair=FAIL(cut)")
        return 1

    omit_po = (args.omit_po or "").strip()
    if omit_po:
        side = args.omit_side
        src = gold_cut if side == "gold" else gate_cut
        dst_il = tmp / f"{side}_cut.il"
        dst_js = tmp / f"{side}_cut.json"
        omitted = omit_output(src, side, omit_po, dst_il, dst_js, args.tmo)
        if omitted.returncode != 0:
            print(omitted.stdout or "")
            print(f"equiv_ref REGPAIR cec_line=omit-po {omit_po} failed")
            print("equiv_ref REGPAIR method=regpair result=unproven")
            print("equiv_ref REGPAIR regpair=FAIL(omit)")
            return 1
        print(f"equiv_ref REGPAIR omit_po={omit_po} side={side}")

    gold_cut_mod = json.loads(gold_cut_json.read_text(encoding="utf-8"))["modules"]["gold"]
    gate_cut_mod = json.loads(gate_cut_json.read_text(encoding="utf-8"))["modules"]["gate"]
    gold_pi, gold_po = port_sets(gold_cut_mod)
    gate_pi, gate_po = port_sets(gate_cut_mod)
    print_port_tables("gold", gold_pi, gold_po)
    print_port_tables("gate", gate_pi, gate_po)
    ports_ok = report_port_diffs(gold_pi, gold_po, gate_pi, gate_po)
    if not ports_ok:
        print("equiv_ref REGPAIR cec_line=skipped (port name sets differ)")
        print("equiv_ref REGPAIR method=regpair result=ports_fail")
        print("equiv_ref REGPAIR regpair=FAIL(ports)")
        return 2

    if {"crc", "crc_word", "done"} <= {k for k, _g, _t in pairs}:
        eval_directed_midblock(tmp, gold_cut_mod)

    po_names = sorted(set(gold_po) | set(gate_po))
    affine_only = bool(args.affine_only or os.environ.get("EQUIV_REGPAIR_AFFINE_ONLY") == "1")
    kind, used, line, wit = prove_miter(tmp, args.tmo, args.abc, po_names, affine_only=affine_only)
    if wit:
        print(f"equiv_ref REGPAIR witness={' '.join(wit)}")
    print(f"equiv_ref REGPAIR cec_line={line}")
    print(f"equiv_ref REGPAIR prove_method={used}")
    print(f"equiv_ref REGPAIR method={used} result={kind}")

    if not reset_ok:
        print("equiv_ref REGPAIR regpair=FAIL(reset)")
        return 2
    if kind == "equivalent":
        print("equiv_ref REGPAIR regpair=PASS")
        return 0
    if kind == "script_error":
        print("equiv_ref REGPAIR regpair=FAIL(script)")
        return 1
    if kind == "not_equivalent":
        # Same registers / ports / reset, different next-state encoding.
        # Only with a replayable write_cex. Do not judge RTL wrong and do not pass.
        print("equiv_ref REGPAIR regpair=INCONCLUSIVE(state-encoding)")
        return 3
    print("equiv_ref REGPAIR regpair=FAIL(unproven)")
    return 1



if __name__ == "__main__":
    raise SystemExit(main())
