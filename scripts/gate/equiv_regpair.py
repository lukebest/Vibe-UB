#!/usr/bin/env python3
"""Register-pair + ABC cec compare for scripts/gate/equiv_ref.sh.

After flatten, pair FFs by normalized Q net name (no hand-written map).
Each pair: Q is a shared PI, D is a PO. Then ABC cec / &cec on the
combinational remainder. Reset kind / polarity / value are checked
separately. All three must hold for PASS.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

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

DELETE_SEL = " ".join(f"t:{t}" for t in sorted(FF_TYPES))

NORM_HELP = (
    "strip leading '\\'; last hierarchy component ('.' or '/'); "
    "strip trailing bit-select; strip trailing '$...'; strip one trailing "
    "'_q' (case-insensitive); lowercase"
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


def normalize_reg_name(name: str) -> str:
    n = name.strip()
    if n.startswith("\\"):
        n = n[1:]
    n = n.replace("/", ".")
    n = n.split(".")[-1]
    n = re.sub(r"\[[^\]]+\]$", "", n)
    n = re.sub(r"\$[^./]*$", "", n)
    n = re.sub(r"_q$", "", n, flags=re.I)
    return n.lower()


def yosys_id(name: str) -> str:
    """Quote a Yosys identifier if it is not a plain id."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return name
    return "\\" + name + " "


def _bits_tuple(bits: list) -> tuple:
    return tuple(bits)


def _net_by_bits(mod: dict, bits: list) -> str | None:
    target = _bits_tuple(bits)
    scored: list[tuple[int, int, str]] = []
    for name, info in (mod.get("netnames") or {}).items():
        nb = _bits_tuple(info.get("bits") or [])
        if nb != target:
            continue
        hide = 1 if info.get("hide_name") else 0
        ugly = 1 if ("$" in name or "func" in name) else 0
        scored.append((hide, ugly, len(name), name))
    if scored:
        scored.sort()
        return scored[0][3]
    # Slice of a wider named net: keep the covering user name.
    for name, info in (mod.get("netnames") or {}).items():
        if info.get("hide_name"):
            continue
        nb = info.get("bits") or []
        if not nb:
            continue
        if all(b in nb for b in bits):
            return name
    return None


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
        if ftype not in FF_TYPES:
            continue
        params = cell.get("parameters") or {}
        conns = cell.get("connections") or {}
        width = _param_int(params.get("WIDTH")) or len(conns.get("Q") or []) or 1
        q_name = _net_by_bits(mod, conns.get("Q") or []) or cname
        d_name = _net_by_bits(mod, conns.get("D") or [])
        key = normalize_reg_name(q_name)
        if not key:
            key = normalize_reg_name(cname) or f"cell_{len(found)}"
        kind, pol, val = _ff_reset(ftype, params)
        found.append(
            Flop(
                cell=cname,
                ftype=ftype,
                width=width,
                q_name=q_name,
                d_name=d_name,
                key=key,
                kind=kind,
                polarity=pol,
                value=val,
                q_bits=_bits_tuple(conns.get("Q") or []),
            )
        )
    return found


def group_by_key(flops: list[Flop]) -> tuple[dict[str, Flop], list[str]]:
    """One flop per normalized key. Ambiguous keys are errors."""
    buckets: dict[str, list[Flop]] = {}
    for ff in flops:
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


def reset_port(mod: dict) -> tuple[str | None, int | None]:
    ports = mod.get("ports") or {}
    for name in ("rst_pyc", "rst", "reset"):
        if name in ports:
            return name, 1
    if "rst_n" in ports:
        return "rst_n", 0
    return None, None


def eval_d_under_reset(rtlil: Path, top: str, d_names: list[str], rst: str, active: int) -> dict[str, int]:
    if not d_names:
        return {}
    sets = [f"-set {rst} {active}"]
    shows = " ".join(f"-show {n}" for n in d_names)
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
    text = proc.stdout or ""
    got: dict[str, int] = {}
    for line in text.splitlines():
        if "Eval result:" not in line:
            continue
        for name in d_names:
            if f"\\{name}" in line or f" {name} " in line or line.endswith(name) or f"{name} =" in line:
                m = re.search(r"=\s*(\d+)'h([0-9a-fA-F]+)", line)
                if m:
                    got[name] = int(m.group(2), 16)
                    continue
                m = re.search(r"=\s*(\d+)'([01]+)", line)
                if m:
                    got[name] = int(m.group(2), 2)
                    continue
                m = re.search(r"=\s*(\d+)\.?\s*$", line)
                if m:
                    got[name] = int(m.group(1), 10)
    return got


def abc_kind(log: str) -> str:
    if re.search(r"Networks are equivalent", log):
        return "equivalent"
    if re.search(r"NOT EQUIVALENT|Verification failed", log, re.I):
        return "not_equivalent"
    return "unproven"


def cec_line(log: str) -> str:
    for line in log.splitlines():
        if re.search(r"Networks are equivalent|NOT EQUIVALENT|Verification failed", line, re.I):
            return line.strip()
    tail = [ln.strip() for ln in log.splitlines() if ln.strip()]
    return tail[-1] if tail else "(no abc conclusion line)"


def write_cut_script(path: Path, top: str, pairs: list[tuple[str, Flop]], src_il: Path, dst_il: Path) -> None:
    lines = [
        f"read_rtlil {src_il}",
        f"cd {top}",
    ]
    for key, ff in pairs:
        if not ff.d_name:
            raise SystemExit(f"equiv_ref REGPAIR missing D net for key={key} q={ff.q_name}")
        lines += [
            f"add -input rp_q_{key} {ff.width}",
            f"add -output rp_d_{key} {ff.width}",
            f"connect -unset {yosys_id(ff.q_name)}",
            f"connect -set {yosys_id(ff.q_name)} rp_q_{key}",
            f"connect -set rp_d_{key} {yosys_id(ff.d_name)}",
        ]
    lines += [
        f"delete {DELETE_SEL}",
        "opt_clean",
        f"write_rtlil {dst_il}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_yosys_file(script: Path, tmo: int) -> subprocess.CompletedProcess[str]:
    argv = ["yosys", "-q", "-s", str(script)]
    if tmo > 0:
        argv = ["timeout", str(tmo), *argv]
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def run_abc(cmd: str, tmo: int, abc: str) -> subprocess.CompletedProcess[str]:
    argv = [abc, "-c", cmd]
    if tmo > 0:
        argv = ["timeout", str(tmo), *argv]
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--leaf", required=True)
    ap.add_argument("--tmp", required=True, type=Path)
    ap.add_argument("--abc", default="yosys-abc")
    ap.add_argument("--tmo", type=int, default=90)
    args = ap.parse_args()
    tmp = args.tmp
    gold_json = json.loads((tmp / "gold.json").read_text(encoding="utf-8"))
    gate_json = json.loads((tmp / "gate.json").read_text(encoding="utf-8"))
    gold_mod = gold_json["modules"]["gold"]
    gate_mod = gate_json["modules"]["gate"]

    print(f"equiv_ref REGPAIR norm={NORM_HELP}")

    gold_flops = extract_flops(gold_mod)
    gate_flops = extract_flops(gate_mod)
    gold_map, gold_amb = group_by_key(gold_flops)
    gate_map, gate_amb = group_by_key(gate_flops)
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
            f"gold={g.q_name} gate={t.q_name} gold_type={g.ftype} gate_type={t.ftype}"
        )
    for ff in unmatched_gold:
        print(f"equiv_ref REGPAIR unmatched gold key={ff.key} width={ff.width} name={ff.q_name}")
    for ff in unmatched_gate:
        print(f"equiv_ref REGPAIR unmatched gate key={ff.key} width={ff.width} name={ff.q_name}")
    for msg in width_mismatch:
        print(f"equiv_ref REGPAIR width_mismatch {msg}")

    pair_ok = not (gold_amb or gate_amb or unmatched_gold or unmatched_gate or width_mismatch)
    if not pair_ok:
        print("equiv_ref REGPAIR pairing=FAIL")
        print("equiv_ref REGPAIR cec_line=skipped (pairing failed)")
        print("equiv_ref REGPAIR reset=skipped (pairing failed)")
        print("equiv_ref REGPAIR method=regpair result=pairing_fail")
        return 1
    print("equiv_ref REGPAIR pairing=PASS")

    # Reset check: cell kind/polarity/value, plus eval of D when kind is none.
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

    # Combinational cec after cutting paired FFs (Q=PI, D=PO).
    gold_cut = tmp / "gold_cut.il"
    gate_cut = tmp / "gate_cut.il"
    write_cut_script(tmp / "cut_gold.ys", "gold", [(k, g) for k, g, _t in pairs], tmp / "gold.il", gold_cut)
    write_cut_script(tmp / "cut_gate.ys", "gate", [(k, t) for k, _g, t in pairs], tmp / "gate.il", gate_cut)
    gcut = run_yosys_file(tmp / "cut_gold.ys", args.tmo)
    tcut = run_yosys_file(tmp / "cut_gate.ys", args.tmo)
    if gcut.returncode != 0 or tcut.returncode != 0:
        print((gcut.stdout or "") + (tcut.stdout or ""))
        print("equiv_ref REGPAIR cec_line=cut failed")
        print("equiv_ref REGPAIR method=regpair result=unproven")
        return 1

    def _write_aig(src: Path, top: str, dest: Path) -> subprocess.CompletedProcess[str]:
        ys = tmp / f"aig_{top}.ys"
        ys.write_text(
            f"read_rtlil {src}\nhierarchy -top {top}\n"
            f"techmap; opt; dffunmap; aigmap; opt\n"
            f"write_aiger -symbols {dest}\n",
            encoding="utf-8",
        )
        return run_yosys_file(ys, args.tmo)

    g_aig = _write_aig(gold_cut, "gold", tmp / "gold.aig")
    t_aig = _write_aig(gate_cut, "gate", tmp / "gate.aig")
    miter_ys = tmp / "miter.ys"
    miter_ys.write_text(
        f"read_rtlil {gold_cut}\nread_rtlil {gate_cut}\n"
        f"miter -equiv -flatten gold gate miter\n"
        f"hierarchy -top miter\n"
        f"techmap; opt; dffunmap; aigmap; opt\n"
        f"write_aiger -symbols -miter {tmp / 'miter.aig'}\n",
        encoding="utf-8",
    )
    aig = run_yosys_file(miter_ys, args.tmo)
    if g_aig.returncode != 0 or t_aig.returncode != 0:
        print((g_aig.stdout or "") + (t_aig.stdout or ""))
        print("equiv_ref REGPAIR cec_line=AIGER write failed")
        print("equiv_ref REGPAIR method=regpair result=unproven")
        return 1
    if aig.returncode != 0 or not (tmp / "gold.aig").is_file() or not (tmp / "gate.aig").is_file():
        print(aig.stdout or "")
        print("equiv_ref REGPAIR cec_line=AIGER write failed")
        print("equiv_ref REGPAIR method=regpair result=unproven")
        return 1

    abc_bin = args.abc
    used = "cec"
    proc = run_abc(f"cec -T {args.tmo} -v {tmp / 'gold.aig'} {tmp / 'gate.aig'}", args.tmo, abc_bin)
    log = proc.stdout or ""
    print(log)
    kind = abc_kind(log)
    if kind == "unproven":
        used = "&cec"
        proc = run_abc(f"&r {tmp / 'miter.aig'}; &cec -m -v -T {args.tmo}", args.tmo, abc_bin)
        log = proc.stdout or ""
        print(log)
        kind = abc_kind(log)

    line = cec_line(log)
    print(f"equiv_ref REGPAIR cec_line={line}")
    print(f"equiv_ref REGPAIR method={used} result={kind}")

    if kind != "equivalent":
        return 1
    if not reset_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
