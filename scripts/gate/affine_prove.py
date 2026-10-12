#!/usr/bin/env python3
"""GATE-EQY-004 (5): affine next-state, only after &cec timeout.

Coarse-grain Yosys cells (after proc/flatten/opt, no techmap/abc).
Control bits start/valid_in/last: all 8 assignments; rst_pyc fixed 0.
Then opt_expr; opt_clean. Allowed cone cells:

  $xor $xnor $not $reduce_xor $reduce_xnor $pos  and constants
  (bit-select / concat are wires; $buf is treated as $pos)

A leftover $mux/$pmux that did not degenerate, or any other cell,
makes the method N/A. A $mux degenerates only when its two data arms
differ by a constant (identical GF(2) support); that is the POLY
`s ? (x^C) : x` identity. A data-bit select between two distinct
variables does not degenerate.

Both cut sides are checked. A constant cone (e.g. INIT) is affine.
Then compare all-0 and each unit vector on the remaining PI bits.
"""

from __future__ import annotations

import itertools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CONTROL = ("start", "valid_in", "last")
# GATE-EQY-004 (5) allowed set. $buf is a wire alias of $pos.
AFFINE_OK = {"$xor", "$xnor", "$not", "$reduce_xor", "$reduce_xnor", "$pos", "$buf"}


@dataclass
class AffineBits:
    """Each PO bit: const in GF(2) plus the set of PI bit names `port[i]`."""

    const: list[int]
    support: list[frozenset[str]]


@dataclass
class ComboResult:
    start: int
    valid_in: int
    last: int
    gold_ok: bool
    gate_ok: bool
    gold_why: str
    gate_why: str
    n_points: int = 0
    equal: bool | None = None
    cex: dict[str, int] = field(default_factory=dict)
    cex_detail: str = ""


def _eq():
    """Lazy import: affine_prove is loaded from equiv_regpair."""
    import equiv_regpair as eq

    return eq


def _norm_type(t: str) -> str:
    return t.lstrip("\\")


def _bit_key(port: str, idx: int, width: int) -> str:
    return port if width <= 1 else f"{port}[{idx}]"


def flatten_pi_bits(pis: list[str], widths: dict[str, int]) -> list[tuple[str, int, str]]:
    """(port, bit_index, key) for variable PIs (not controls, not rst_pyc)."""
    skip = set(CONTROL) | {"rst_pyc"}
    out: list[tuple[str, int, str]] = []
    for name in pis:
        if name in skip:
            continue
        w = max(int(widths.get(name, 1) or 1), 1)
        for i in range(w):
            out.append((name, i, _bit_key(name, i, w)))
    return out


def _cell_output_bits(cell: dict) -> list[int]:
    conns = cell.get("connections") or {}
    for pin in ("Y", "Q", "y"):
        if pin in conns:
            return list(conns[pin] or [])
    return []


def cone_cells(mod: dict, po: str) -> tuple[list[str], str]:
    """Cells in the TFI of `po`. Empty cell list + ok if the PO is a PI/const."""
    ports = mod.get("ports") or {}
    if po not in ports:
        return [], f"missing port {po}"
    target = set(ports[po].get("bits") or [])
    if not target:
        return [], "empty po bits"
    bit_driver: dict[int, str] = {}
    cells = mod.get("cells") or {}
    for cname, cell in cells.items():
        for b in _cell_output_bits(cell):
            if isinstance(b, int) and b not in (0, 1):
                bit_driver[b] = cname
    seen: set[str] = set()
    wait = list(target)
    while wait:
        b = wait.pop()
        if not isinstance(b, int) or b in (0, 1):
            continue
        cname = bit_driver.get(b)
        if not cname or cname in seen:
            continue
        seen.add(cname)
        for bits in (cells[cname].get("connections") or {}).values():
            for x in bits or []:
                if isinstance(x, int) and x not in (0, 1):
                    wait.append(x)
    return sorted(seen), ""


def _pi_bit_lookup(mod: dict, pis: list[str]) -> dict[int, str]:
    ports = mod.get("ports") or {}
    out: dict[int, str] = {}
    for name in pis:
        info = ports.get(name) or {}
        bits = info.get("bits") or []
        w = len(bits) if bits else 1
        for i, b in enumerate(bits):
            if isinstance(b, int) and b not in (0, 1):
                out[b] = _bit_key(name, i, w)
    return out


def _pin_bits(conns: dict, pin: str) -> list:
    return list(conns.get(pin) or conns.get(pin.lower()) or [])


def _bit_at(bits: list, idx: int):
    if idx < len(bits):
        return bits[idx]
    return 0


def _const_bit(bit: object) -> int | None:
    """Yosys JSON writes GND/VCC as 0/1 or the strings '0'/'1'."""
    if bit in (0, 1):
        return int(bit)
    if bit in ("0", "1"):
        return int(bit)
    return None


def _affine_of_bit(
    bit: object,
    memo: dict[int, tuple[int, frozenset[str]] | None],
    cells: dict,
    bit_driver: dict[int, str],
    pi_bits: dict[int, str],
) -> tuple[int, frozenset[str]] | None:
    c = _const_bit(bit)
    if c is not None:
        return c, frozenset()
    if not isinstance(bit, int):
        return None
    if bit in memo:
        return memo[bit]
    if bit in pi_bits:
        memo[bit] = (0, frozenset({pi_bits[bit]}))
        return memo[bit]
    cname = bit_driver.get(bit)
    if not cname:
        memo[bit] = None
        return None
    cell = cells[cname]
    t = _norm_type(cell.get("type") or "")
    conns = cell.get("connections") or {}
    ybits = _pin_bits(conns, "Y")
    try:
        yidx = ybits.index(bit)
    except ValueError:
        memo[bit] = None
        return None

    got: tuple[int, frozenset[str]] | None = None
    if t in {"$buf", "$pos"}:
        got = _affine_of_bit(_bit_at(_pin_bits(conns, "A"), yidx), memo, cells, bit_driver, pi_bits)
    elif t == "$not":
        inner = _affine_of_bit(_bit_at(_pin_bits(conns, "A"), yidx), memo, cells, bit_driver, pi_bits)
        got = None if inner is None else (1 - inner[0], inner[1])
    elif t in {"$xor", "$xnor"}:
        ga = _affine_of_bit(_bit_at(_pin_bits(conns, "A"), yidx), memo, cells, bit_driver, pi_bits)
        gb = _affine_of_bit(_bit_at(_pin_bits(conns, "B"), yidx), memo, cells, bit_driver, pi_bits)
        if ga is not None and gb is not None:
            const = ga[0] ^ gb[0]
            supp = ga[1] ^ gb[1]
            if t == "$xnor":
                const = 1 - const
            got = (const, supp)
    elif t in {"$reduce_xor", "$reduce_xnor"}:
        acc: tuple[int, frozenset[str]] | None = (0, frozenset())
        for src in _pin_bits(conns, "A"):
            inner = _affine_of_bit(src, memo, cells, bit_driver, pi_bits)
            if inner is None or acc is None:
                acc = None
                break
            acc = (acc[0] ^ inner[0], acc[1] ^ inner[1])
        if acc is not None:
            const, supp = acc
            if t == "$reduce_xnor":
                const = 1 - const
            got = (const, supp)
    elif t == "$mux":
        # Y = S ? A : B. Affine iff A and B differ by a constant
        # (identical support): Y = B xor S when they differ, else B.
        # Any leftover data-select mux (distinct supports) is N/A.
        gs = _affine_of_bit(_bit_at(_pin_bits(conns, "S"), 0), memo, cells, bit_driver, pi_bits)
        ga = _affine_of_bit(_bit_at(_pin_bits(conns, "A"), yidx), memo, cells, bit_driver, pi_bits)
        gb = _affine_of_bit(_bit_at(_pin_bits(conns, "B"), yidx), memo, cells, bit_driver, pi_bits)
        if gs is not None and ga is not None and gb is not None:
            if ga[1] == gb[1]:
                if ga[0] == gb[0]:
                    got = gb
                else:
                    got = (gb[0] ^ gs[0], gb[1] ^ gs[1])
    # $pmux and every other type stay None → leftover / non-affine.

    memo[bit] = got
    return got


def extract_affine(mod: dict, po: str, pis: list[str]) -> AffineBits | None:
    ports = mod.get("ports") or {}
    pbits = (ports.get(po) or {}).get("bits") or []
    cells = mod.get("cells") or {}
    bit_driver: dict[int, str] = {}
    for cname, cell in cells.items():
        for b in _cell_output_bits(cell):
            if isinstance(b, int) and b not in (0, 1):
                bit_driver[b] = cname
    pi_bits = _pi_bit_lookup(mod, pis)
    memo: dict[int, tuple[int, frozenset[str]] | None] = {}
    const: list[int] = []
    support: list[frozenset[str]] = []
    for b in pbits:
        got = _affine_of_bit(b, memo, cells, bit_driver, pi_bits)
        if got is None:
            return None
        const.append(got[0])
        support.append(got[1])
    return AffineBits(const=const, support=support)


def classify_cone(mod: dict, po: str, pis: list[str]) -> tuple[bool, str]:
    names, err = cone_cells(mod, po)
    if err:
        return False, err
    cells = mod.get("cells") or {}
    types: list[str] = []
    leftover_mux = 0
    folded_mux = 0
    bad: list[str] = []
    bit_driver: dict[int, str] = {}
    for cname, cell in cells.items():
        for b in _cell_output_bits(cell):
            if isinstance(b, int) and b not in (0, 1):
                bit_driver[b] = cname
    pi_bits = _pi_bit_lookup(mod, pis)
    memo: dict[int, tuple[int, frozenset[str]] | None] = {}
    for n in names:
        t = _norm_type(cells[n].get("type") or "")
        types.append(t)
        if t in AFFINE_OK:
            continue
        if t == "$mux":
            conns = cells[n].get("connections") or {}
            ybits = _pin_bits(conns, "Y")
            ok_bits = 0
            for i, yb in enumerate(ybits):
                got = _affine_of_bit(yb, memo, cells, bit_driver, pi_bits)
                if got is None:
                    leftover_mux += 1
                    break
                ok_bits += 1
            else:
                folded_mux += 1
            continue
        if t == "$pmux":
            leftover_mux += 1
            continue
        bad.append(t)
    if leftover_mux:
        return False, f"leftover $mux/$pmux (method N/A) n={leftover_mux}"
    if bad:
        uniq = ",".join(sorted(set(bad)))
        return False, f"non-affine cell {uniq}"
    extra = f" mux_folded={folded_mux}" if folded_mux else ""
    if not names:
        return True, "constant-or-wire"
    return True, "xor-only cells=" + ",".join(sorted(set(types))) + extra


def fold_controls(
    il: Path,
    top: str,
    po: str,
    assigns: dict[str, int],
    tmp: Path,
    tag: str,
    tmo: int,
) -> tuple[dict | None, str]:
    eq = _eq()
    js = tmp / f"affine_{top}_{tag}.json"
    pre = tmp / f"affine_{top}_ports.json"
    if not pre.is_file():
        dump = eq.run_yosys_p(f"read_rtlil {il}\ncd {top}\nwrite_json {pre}\n", tmo, quiet=True)
        if dump.returncode != 0 or not pre.is_file():
            return None, "fold: cannot read cut"
    try:
        pmod = json.loads(pre.read_text(encoding="utf-8"))["modules"][top]
    except (json.JSONDecodeError, KeyError) as exc:
        return None, f"fold pre json: {exc}"
    ys = [f"read_rtlil {il}", f"cd {top}"]
    for name, info in (pmod.get("ports") or {}).items():
        if info.get("direction") == "output" and name != po:
            ys.append(f"delete -output {eq.yosys_id(name)}")
    for name, val in assigns.items():
        if name not in (pmod.get("ports") or {}):
            continue
        ys.append(f"connect -set {eq.yosys_id(name)} {int(val)}")
    ys += ["opt_expr", "opt_clean", f"write_json {js}"]
    built = eq.run_yosys_p("\n".join(ys) + "\n", tmo, quiet=True)
    if built.returncode != 0 or not js.is_file():
        return None, "fold: opt_expr failed"
    try:
        return json.loads(js.read_text(encoding="utf-8"))["modules"][top], ""
    except (json.JSONDecodeError, KeyError) as exc:
        return None, f"fold json: {exc}"


def eval_affine(bits: AffineBits, assignment: dict[str, int], widths: dict[str, int]) -> int:
    acc = 0
    for i, (c, supp) in enumerate(zip(bits.const, bits.support)):
        v = c
        for key in supp:
            m = re.fullmatch(r"([A-Za-z0-9_]+)(?:\[(\d+)\])?", key)
            if not m:
                continue
            name, idx = m.group(1), m.group(2)
            word = int(assignment.get(name, 0))
            bit = word if idx is None else ((word >> int(idx)) & 1)
            v ^= bit
        acc |= (v & 1) << i
    return acc


def unit_points(pis: list[str], widths: dict[str, int]) -> list[dict[str, int]]:
    """All-0 plus one-hot on every variable PI bit (not controls / rst_pyc)."""
    skip = set(CONTROL) | {"rst_pyc"}
    var_pis = [n for n in pis if n not in skip]
    pts = [{n: 0 for n in var_pis}]
    for name, idx, _key in flatten_pi_bits(pis, widths):
        vec = {n: 0 for n in var_pis}
        vec[name] = 1 << idx
        pts.append(vec)
    return pts


def compare_affine(
    gold: AffineBits,
    gate: AffineBits,
    pis: list[str],
    widths: dict[str, int],
    base: dict[str, int],
) -> tuple[bool, int, dict[str, int], str]:
    """Compare all-0 and unit vectors. Returns (equal, n_points, cex, detail)."""
    pts = unit_points(pis, widths)
    for vec in pts:
        # Controls from `base` must win: the folded cone already assumed them,
        # and the unfolder cut replay has to use the same assignment.
        use = dict(vec)
        use.update(base)
        gv = eval_affine(gold, use, widths)
        tv = eval_affine(gate, use, widths)
        if gv != tv:
            return False, len(pts), use, f"gold=0x{gv:x} gate=0x{tv:x}"
    return True, len(pts), {}, ""


def prove_affine_po(
    tmp: Path,
    gold_il: Path,
    gate_il: Path,
    pis: list[str],
    po: str,
    widths: dict[str, int],
    tmo: int,
) -> tuple[str, str, dict[str, int], list[ComboResult]]:
    """Return (kind, line, cex, per-combo). kind=equivalent|not_equivalent|na."""
    combos = list(itertools.product((0, 1), repeat=3))
    rows: list[ComboResult] = []
    any_na = False
    first_cex: dict[str, int] = {}
    first_detail = ""
    total_pts = 0
    for start, valid, last in combos:
        assigns = {"rst_pyc": 0, "start": start, "valid_in": valid, "last": last}
        tag = f"s{start}v{valid}l{last}_{po}"
        gmod, gerr = fold_controls(gold_il, "gold", po, assigns, tmp, tag, tmo)
        tmod, terr = fold_controls(gate_il, "gate", po, assigns, tmp, tag + "t", tmo)
        if gmod is None or tmod is None:
            row = ComboResult(start, valid, last, False, False, gerr or "gold fold", terr or "gate fold")
            rows.append(row)
            any_na = True
            print(
                f"equiv_ref REGPAIR affine_prereq po={po} start={start} "
                f"valid_in={valid} last={last} rst_pyc=0 gold=FAIL({row.gold_why}) "
                f"gate=FAIL({row.gate_why})"
            )
            continue
        gok, gwhy = classify_cone(gmod, po, pis)
        tok, twhy = classify_cone(tmod, po, pis)
        print(
            f"equiv_ref REGPAIR affine_prereq po={po} start={start} "
            f"valid_in={valid} last={last} rst_pyc=0 gold={'PASS' if gok else 'FAIL'}({gwhy}) "
            f"gate={'PASS' if tok else 'FAIL'}({twhy})"
        )
        if not gok or not tok:
            rows.append(ComboResult(start, valid, last, gok, tok, gwhy, twhy))
            any_na = True
            continue
        gaff = extract_affine(gmod, po, pis)
        taff = extract_affine(tmod, po, pis)
        if gaff is None or taff is None:
            rows.append(
                ComboResult(
                    start,
                    valid,
                    last,
                    False,
                    False,
                    "extract failed" if gaff is None else gwhy,
                    "extract failed" if taff is None else twhy,
                )
            )
            any_na = True
            print(
                f"equiv_ref REGPAIR affine_prereq po={po} extract=FAIL "
                f"start={start} valid_in={valid} last={last}"
            )
            continue
        pts = unit_points(pis, widths)
        total_pts += len(pts)
        combo_eq = True
        cex, detail = {}, ""
        for vec in pts:
            use = dict(vec)
            use.update(assigns)
            gv = eval_affine(gaff, use, widths)
            tv = eval_affine(taff, use, widths)
            if gv == tv:
                continue
            diff, replay = _replay(tmp, use, po, widths)
            if diff is None:
                print(
                    f"equiv_ref REGPAIR affine_eval_match po={po} start={start} "
                    f"valid_in={valid} last={last} symbolic=gold=0x{gv:x} gate=0x{tv:x}"
                )
                continue
            combo_eq = False
            cex, detail = use, replay
            if not first_cex:
                first_cex = use
                first_detail = replay
            break
        row = ComboResult(
            start, valid, last, True, True, gwhy, twhy, len(pts), combo_eq, cex, detail
        )
        rows.append(row)
    n_combo = len(combos)
    print(
        f"equiv_ref REGPAIR affine po={po} method=affine combos={n_combo} "
        f"points={total_pts} na={int(any_na)}"
    )
    if any_na:
        return "na", f"affine N/A (non-XOR cone) combos={n_combo}", {}, rows
    if first_cex:
        print(f"equiv_ref REGPAIR cex_ok=1 po={po} method=affine {first_detail}")
        return "not_equivalent", f"affine NOT EQ {first_detail}", first_cex, rows
    return "equivalent", f"affine EQ combos={n_combo} points={total_pts}", {}, rows


def _replay(tmp: Path, assigns: dict[str, int], po: str, widths: dict[str, int]) -> tuple[str | None, str]:
    eq = _eq()
    skip = {po} | {n for n in widths if n.startswith("rp_d_")}
    use = {k: 0 for k in widths if k not in skip}
    use.update({k: v for k, v in assigns.items() if k and k not in skip})
    gvals = eq.eval_signals(tmp / "gold_cut.il", "gold", use, [po], widths)
    tvals = eq.eval_signals(tmp / "gate_cut.il", "gate", use, [po], widths)
    gv, tv = gvals.get(po), tvals.get(po)
    if gv is None or tv is None or gv == tv:
        return None, f"eval gold={gv} gate={tv}"
    return po, f"port={po} gold=0x{gv:x} gate=0x{tv:x}"
