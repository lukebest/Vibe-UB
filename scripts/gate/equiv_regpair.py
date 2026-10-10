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
their names. Name-set mismatch is FAIL. Prove with a single Yosys
`miter -equiv` (pairs by port name, not order) plus combo
`sat -prove-asserts` or ABC on that miter. Reset kind / polarity / value
are checked separately (mismatch is FAIL). All must hold.
"""

from __future__ import annotations

import argparse
import json
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
    for line in text.splitlines():
        if "Eval result:" not in line:
            continue
        for name in names:
            if name in got:
                continue
            if not (
                f"\\{name}" in line
                or f" {name} " in line
                or line.endswith(name)
                or f"{name} =" in line
            ):
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
        lines += [
            f"add -input rp_q_{key} {ff.width}",
            f"add -output rp_d_{key} {ff.width}",
            # Drive every reader of the FF Q from the cut PI (same net as cell Q).
            f"connect -unset {yosys_id(ff.q_name)}",
            f"connect -set {yosys_id(ff.q_name)} rp_q_{key}",
            # Export the cell D pin net, not a combo / output alias.
            f"connect -set rp_d_{key} {yosys_id(ff.d_name)}",
            f"# cut cell={ff.cell} type={ff.ftype} q_pin={q_pin} q_net={ff.q_name} d_net={ff.d_name}",
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


def find_sat_witness(tmp: Path, tmo: int, abc: str, po_names: list[str]) -> list[str]:
    """Name-paired per-PO trigger miter + ABC: which POs / rp_d_* differ."""
    found: list[str] = []
    for po in po_names:
        others = [n for n in po_names if n != po]
        drop_g = "\n".join(f"delete -output {yosys_id(n)}" for n in others)
        ys = tmp / f"wit_{po}.ys"
        aig = tmp / f"wit_{po}.aig"
        g1 = tmp / f"wit_{po}_gold.il"
        t1 = tmp / f"wit_{po}_gate.il"
        ys.write_text(
            f"read_rtlil {tmp / 'gold_cut.il'}\n"
            "hierarchy -top gold\n"
            f"cd gold\n{drop_g}\n"
            f"write_rtlil {g1}\n"
            "design -reset\n"
            f"read_rtlil {tmp / 'gate_cut.il'}\n"
            "hierarchy -top gate\n"
            f"cd gate\n{drop_g}\n"
            f"write_rtlil {t1}\n"
            "design -reset\n"
            f"read_rtlil {g1}\n"
            f"read_rtlil {t1}\n"
            "miter -equiv -flatten -make_assert gold gate wit\n"
            "hierarchy -top wit\n"
            "delete t:$assert t:$assume t:$live t:$fair\n"
            "techmap; opt; aigmap; opt\n"
            f"write_aiger -symbols -miter {aig}\n",
            encoding="utf-8",
        )
        built = run_yosys_file(ys, tmo)
        if built.returncode != 0 or not aig.is_file():
            print(built.stdout or "")
            continue
        proc = run_abc(f"&r {aig}; &cec -m -v -T {min(tmo, 15) if tmo else 15}", tmo, abc)
        log = proc.stdout or ""
        kind = abc_kind(log)
        print(f"equiv_ref REGPAIR po_cec name={po} result={kind} line={conclusion_line(log)}")
        if kind != "equivalent":
            found.append(po)
    return found


def prove_miter(tmp: Path, tmo: int, abc: str, po_names: list[str]) -> tuple[str, str, str, list[str]]:
    """Name-paired miter, then ABC / sat on that single miter. No order-cec."""
    build = tmp / "miter_build.ys"
    build.write_text(
        f"read_rtlil {tmp / 'gold_cut.il'}\n"
        f"read_rtlil {tmp / 'gate_cut.il'}\n"
        "miter -equiv -flatten -make_assert gold gate miter\n"
        "hierarchy -top miter\n"
        f"write_rtlil {tmp / 'miter.il'}\n"
        f"write_json {tmp / 'miter.json'}\n",
        encoding="utf-8",
    )
    built = run_yosys_file(build, tmo)
    if built.returncode != 0 or not (tmp / "miter.il").is_file():
        print(built.stdout or "")
        return "unproven", "miter-build", "miter build failed", []
    # write_aiger -miter rejects $assert; keep them for sat, strip for ABC.
    aig_ys = tmp / "miter_aig.ys"
    aig_ys.write_text(
        f"read_rtlil {tmp / 'miter.il'}\n"
        "hierarchy -top miter\n"
        "delete t:$assert t:$assume t:$live t:$fair\n"
        "techmap; opt; aigmap; opt\n"
        f"write_aiger -symbols -miter {tmp / 'miter.aig'}\n",
        encoding="utf-8",
    )
    aig = run_yosys_file(aig_ys, tmo)
    if aig.returncode != 0:
        print(aig.stdout or "")

    last_log = ""
    last_used = "miter-build"
    if (tmp / "miter.aig").is_file():
        abc_cmds = [
            ("abc-&cec", f"&r {tmp / 'miter.aig'}; &cec -m -v -T {tmo}"),
            ("abc-iprove", f"read {tmp / 'miter.aig'}; iprove"),
            ("abc-dprove", f"read {tmp / 'miter.aig'}; dprove"),
        ]
        for used, cmd in abc_cmds:
            proc = run_abc(cmd, tmo, abc)
            log = proc.stdout or ""
            print(log)
            last_log = log
            last_used = used
            kind = abc_kind(log)
            if kind == "unproven" and re.search(r"SATISFIABLE", log, re.I):
                kind = "not_equivalent"
            if kind == "equivalent":
                return kind, used, conclusion_line(log), []
            if kind == "not_equivalent":
                wit = witnesses_from_log(log, po_names) or find_sat_witness(tmp, tmo, abc, po_names)
                return kind, used, conclusion_line(log), wit

    sat_script = (
        f"read_rtlil {tmp / 'miter.il'}\n"
        "hierarchy -top miter\n"
        f"sat -verify -prove-asserts -timeout {tmo} "
        f"-dump_json {tmp / 'sat_cex.json'}\n"
    )
    sat = run_yosys_p(sat_script, tmo + 5 if tmo > 0 else 0)
    sat_log = sat.stdout or ""
    print(sat_log)
    kind = sat_kind(sat_log)
    if sat.returncode == 124 or re.search(r"time ?out|timed out", sat_log, re.I):
        kind = "unproven"
    elif sat.returncode == 0 and kind == "unproven":
        kind = "equivalent"
    elif sat.returncode != 0 and kind == "unproven":
        kind = "not_equivalent"
    last_log = sat_log
    last_used = "sat-prove-asserts"
    if kind == "equivalent":
        return kind, last_used, conclusion_line(sat_log), []
    if kind == "not_equivalent":
        wit = witnesses_from_sat_json(tmp / "sat_cex.json") or find_sat_witness(tmp, tmo, abc, po_names)
        if not wit:
            wit = witnesses_from_log(sat_log, po_names)
        return kind, last_used, conclusion_line(sat_log), wit
    return "unproven", last_used, conclusion_line(last_log), witnesses_from_log(last_log, po_names)


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
    kind, used, line, wit = prove_miter(tmp, args.tmo, args.abc, po_names)
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
    if kind == "not_equivalent":
        # Same registers / ports / reset, different next-state encoding.
        # Do not judge RTL wrong and do not pass; caller switches method.
        print("equiv_ref REGPAIR regpair=INCONCLUSIVE(state-encoding)")
        return 3
    print("equiv_ref REGPAIR regpair=FAIL(unproven)")
    return 1



if __name__ == "__main__":
    raise SystemExit(main())
