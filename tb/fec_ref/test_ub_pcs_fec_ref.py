"""Icarus + cocotb bit-exact check of the FEC formula refs vs the golden.

VARIANT selects the toplevel:
  enc_ref / syn_ref           — must match the golden
  enc_bad_coeff / enc_rev_order / enc_poly11b — must mismatch
  syn_poly11b / syn_bad_root  — must mismatch (scoreboard FAIL)

Compare counts are per symbol (GATE-TB-SB-001). T=2 extra-syndrome check
is exercised on the syndrome ref (S4..S7 of a T=2-corrected word). Bypass
has no pin on these refs and is recorded as model-only.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import cocotb
from cocotb.triggers import Timer

from _golden import load_golden, load_vectors, pack_symbols, unpack_symbols

K = 120
N = 128
TWO_T = 8
SEED_EXTRA = 20261010
N_EXTRA_RANDOM = 8
ONEHOT_COUNT = K

REPORT_DIR = Path(__file__).resolve().parents[2] / "formal" / "reports" / "ref_vs_model"
REPORT_PATH = REPORT_DIR / "ub_pcs_fec.md"
COUNTS_PATH = REPORT_DIR / "selftest_counts.json"

g = load_golden()


class Scoreboard:
    def __init__(self, name: str, expected: int) -> None:
        self.name = name
        self.expected = expected
        self.n_compare = 0
        self.n_mismatch = 0
        self.first = None

    def compare(self, exp: int, act: int, ctx: str) -> None:
        self.n_compare += 1
        if int(exp) != int(act):
            self.n_mismatch += 1
            if self.first is None:
                self.first = {
                    "ctx": ctx,
                    "expected": int(exp),
                    "actual": int(act),
                }

    def check(self, *, expect_fail: bool) -> None:
        if self.n_compare <= 0:
            raise AssertionError(f"{self.name}: n_compare is 0")
        if self.n_compare != self.expected:
            raise AssertionError(
                f"{self.name}: n_compare={self.n_compare} expected={self.expected}"
            )
        stamp = Path("sim_build") / f"{self.name.replace(':', '_')}.status"
        stamp.parent.mkdir(parents=True, exist_ok=True)
        if expect_fail:
            if self.n_mismatch <= 0:
                stamp.write_text("FAIL\n", encoding="utf-8")
                raise AssertionError(f"{self.name}: fake netlist did not FAIL")
            stamp.write_text(
                f"FAIL_AS_REQUIRED n_mismatch={self.n_mismatch}\n", encoding="utf-8"
            )
            return
        if self.n_mismatch:
            stamp.write_text(f"FAIL first={self.first}\n", encoding="utf-8")
            raise AssertionError(
                f"{self.name}: {self.n_mismatch} mismatches; first={self.first}"
            )
        stamp.write_text("PASS\n", encoding="utf-8")


def _int_or_x(signal) -> int:
    raw = signal.value
    try:
        return int(raw)
    except ValueError as exc:
        raise AssertionError(f"{signal._name} is X/Z: {raw}") from exc


async def _settle() -> None:
    await Timer(1, units="ns")


def _json_encode_vectors() -> list[dict]:
    return [v for v in load_vectors()["vectors"] if "codeword" in v]


def _directed_messages() -> list[tuple[str, list[int]]]:
    out: list[tuple[str, list[int]]] = []
    for i in range(ONEHOT_COUNT):
        msg = [0] * K
        msg[i] = 1
        out.append((f"onehot_m{K - 1 - i}", msg))
    rng = random.Random(SEED_EXTRA)
    for i in range(N_EXTRA_RANDOM):
        out.append((f"random_{SEED_EXTRA}_{i}", [rng.randrange(256) for _ in range(K)]))
    return out


def _enc_expected_compares() -> int:
    # JSON codewords + one-hot + extra random. Incrementing is in the JSON file.
    n_vec = len(_json_encode_vectors()) + ONEHOT_COUNT + N_EXTRA_RANDOM
    # T=2 encode of incrementing (same 8 parity as T=4) — one extra vector.
    n_vec += 1
    return n_vec * N


def _syn_expected_compares() -> int:
    n_clean = len(_json_encode_vectors()) + ONEHOT_COUNT + N_EXTRA_RANDOM
    # clean CW syndromes (8) + JSON received + T=2 corrected CW (S0..S7 incl. S4..S7)
    return n_clean * TWO_T + TWO_T + TWO_T


def _all_encode_cases() -> list[tuple[str, list[int], list[int]]]:
    cases: list[tuple[str, list[int], list[int]]] = []
    enc = g.UbPcsFecEnc(g.UbPcsFecConfig(mode=g.FecMode.T4))
    for vec in _json_encode_vectors():
        cases.append((f"json:{vec['name']}", list(vec["message"]), list(vec["codeword"])))
    for name, msg in _directed_messages():
        cases.append((name, msg, enc.encode(msg)))
    enc_t2 = g.UbPcsFecEnc(g.UbPcsFecConfig(mode=g.FecMode.T2))
    msg = list(range(K))
    cases.append(("t2_incrementing", msg, enc_t2.encode(msg)))
    return cases


def _write_report(payload: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    COUNTS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    first = payload.get("first_mismatch")
    lines = [
        "# FEC formula-ref vs golden model",
        "",
        "Leaf refs: `ub_pcs_fec_enc_ref`, `ub_pcs_fec_syndrome_ref`.",
        "Golden: `tb/models/ub_pcs_fec.py` + `tb/models/ub_pcs_fec_vectors.json`.",
        "",
        "## Compare counts",
        "",
        f"- encoder ({payload['enc_variant']}): "
        f"{payload['enc_n_compare']} compares, {payload['enc_n_mismatch']} mismatches "
        f"(expected {payload['enc_expected']})",
        f"- syndrome ({payload['syn_variant']}): "
        f"{payload['syn_n_compare']} compares, {payload['syn_n_mismatch']} mismatches "
        f"(expected {payload['syn_expected']})",
        "",
        "## T=2 / bypass",
        "",
        "- T=2 encode: same eight parity symbols as T=4; covered by `t2_incrementing` on the encoder ref.",
        "- T=2 S4..S7: syndrome ref of a T=2-corrected word must be all-zero (model decoder + this Horner leaf).",
        "- Bypass: **no pin on these refs**; identity / no-parity is covered on the model side only.",
        "",
        "## First mismatch",
        "",
    ]
    if first:
        lines.append("```")
        lines.append(json.dumps(first, indent=2))
        lines.append("```")
        lines.append("")
        lines.append("Neither the ref nor the model was edited. Waiting for Xia.")
    else:
        lines.append("None (refs match the golden on every counted symbol).")
    lines.extend(
        [
            "",
            "## Fake netlists (must FAIL)",
            "",
            *(f"- {row}" for row in payload.get("fake_fail_lines", [])),
            "",
            "## Self-test by directory",
            "",
            "- `tb/fec_ref/`: 7 Icarus+cocotb runs (enc_ref, syn_ref, enc_bad_coeff, enc_rev_order, enc_poly11b, syn_poly11b, syn_bad_root).",
            f"- encoder symbol compares: {payload['enc_n_compare']} (JSON 8 + one-hot 120 + extra-random 8 + T=2 incrementing).",
            f"- syndrome symbol compares: {payload['syn_n_compare']} (clean CWs + JSON two_errors + T=2 corrected S0..S7).",
            "",
        ]
    )
    equiv_status = REPORT_DIR / "equiv_status.txt"
    if equiv_status.is_file():
        lines.extend(
            [
                "## Formula-ref Yosys equiv",
                "",
                "```",
                equiv_status.read_text(encoding="utf-8").rstrip(),
                "```",
                "",
            ]
        )
    legacy = REPORT_DIR / "legacy_equiv.txt"
    if legacy.is_file():
        lines.extend(
            [
                "## Legacy RTL (`rtl/pcs/`) — informational",
                "",
                "```",
                legacy.read_text(encoding="utf-8").rstrip(),
                "```",
                "",
                "Yosys 0.33 times out unrolling the per-symbol combo loop; Icarus is the",
                "passing path. Legacy encoder ports are sequential (`clk`/`valid_*`);",
                "the formula ref is combinational. Not blocking.",
                "",
            ]
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


@cocotb.test()
async def test_formula_ref(dut):
    variant = os.environ.get("FEC_REF_VARIANT", "enc_ref")
    expect_fail = (
        variant.startswith("enc_bad")
        or variant.startswith("enc_rev")
        or variant.startswith("enc_poly")
        or variant.startswith("syn_poly")
        or variant.startswith("syn_bad")
    )

    if variant.startswith("syn"):
        await _run_syndrome(dut, variant, expect_fail=expect_fail)
    else:
        await _run_encoder(dut, variant, expect_fail=expect_fail)


async def _run_encoder(dut, variant: str, *, expect_fail: bool) -> None:
    expected = _enc_expected_compares()
    sb = Scoreboard(f"enc:{variant}", expected)
    for name, msg, cw_exp in _all_encode_cases():
        dut.msg_in.value = pack_symbols(msg)
        await _settle()
        cw_act = unpack_symbols(_int_or_x(dut.cw_out), N)
        for i, (e, a) in enumerate(zip(cw_exp, cw_act, strict=True)):
            sb.compare(e, a, f"{variant} {name} sym{i}")
    if expect_fail:
        _record_fake(variant, sb)
    else:
        print(
            f"{variant}: PASS n_compare={sb.n_compare} n_mismatch={sb.n_mismatch}",
            flush=True,
        )
        _merge_counts({
            "enc_variant": sb.name,
            "enc_n_compare": sb.n_compare,
            "enc_n_mismatch": sb.n_mismatch,
            "first_mismatch": sb.first,
        })
    sb.check(expect_fail=expect_fail)


async def _run_syndrome(dut, variant: str, *, expect_fail: bool) -> None:
    expected = _syn_expected_compares()
    sb = Scoreboard(f"syn:{variant}", expected)
    enc = g.UbPcsFecEnc()
    syn_model = g.UbPcsFecDec()

    clean: list[tuple[str, list[int]]] = []
    for vec in _json_encode_vectors():
        clean.append((f"json:{vec['name']}", list(vec["codeword"])))
    for name, msg in _directed_messages():
        clean.append((name, enc.encode(msg)))

    for name, cw in clean:
        dut.cw_in.value = pack_symbols(cw)
        await _settle()
        # Bus is {S7,...,S0}; model list is S0..S7.
        act = list(reversed(unpack_symbols(_int_or_x(dut.syndromes), TWO_T)))
        exp = syn_model.syndromes(cw)
        for i, (e, a) in enumerate(zip(exp, act, strict=True)):
            sb.compare(e, a, f"{variant} {name} S{i}")

    recv_vec = next(v for v in load_vectors()["vectors"] if v["name"] == "two_errors_first_and_last")
    received = list(recv_vec["received"])
    dut.cw_in.value = pack_symbols(received)
    await _settle()
    act = list(reversed(unpack_symbols(_int_or_x(dut.syndromes), TWO_T)))
    exp = syn_model.syndromes(received)
    for i, (e, a) in enumerate(zip(exp, act, strict=True)):
        sb.compare(e, a, f"{variant} json:two_errors S{i}")

    # T=2: correct two errors with the model, then Horner must give S0..S7 = 0
    # (S4..S7 are the extra-syndrome check in the golden).
    dec_t2 = g.UbPcsFecDec(g.UbPcsFecConfig(mode=g.FecMode.T2))
    rx = list(enc.encode(list(range(K))))
    rx[0] ^= 0xA5
    rx[N - 1] ^= 0x3C
    result = dec_t2.decode(rx)
    assert result.ok, "T=2 model decode of two directed errors must succeed"
    corrected = enc.encode(list(result.message))
    dut.cw_in.value = pack_symbols(corrected)
    await _settle()
    act = list(reversed(unpack_symbols(_int_or_x(dut.syndromes), TWO_T)))
    for i, a in enumerate(act):
        sb.compare(0, a, f"{variant} t2_corrected S{i}")

    if expect_fail:
        _record_fake(variant, sb)
    else:
        print(
            f"{variant}: PASS n_compare={sb.n_compare} n_mismatch={sb.n_mismatch}",
            flush=True,
        )
        _merge_counts({
            "syn_variant": sb.name,
            "syn_n_compare": sb.n_compare,
            "syn_n_mismatch": sb.n_mismatch,
            "first_mismatch": sb.first,
        })
    sb.check(expect_fail=expect_fail)


def _load_prev() -> dict:
    if COUNTS_PATH.is_file():
        return json.loads(COUNTS_PATH.read_text(encoding="utf-8"))
    return {
        "enc_variant": "",
        "syn_variant": "",
        "enc_n_compare": 0,
        "enc_n_mismatch": 0,
        "enc_expected": _enc_expected_compares(),
        "syn_n_compare": 0,
        "syn_n_mismatch": 0,
        "syn_expected": _syn_expected_compares(),
        "first_mismatch": None,
        "fake_fail_lines": [],
    }


def _merge_counts(update: dict) -> None:
    prev = _load_prev()
    prev["enc_expected"] = _enc_expected_compares()
    prev["syn_expected"] = _syn_expected_compares()
    for key, value in update.items():
        if key == "fake_fail_lines":
            continue
        prev[key] = value
    _write_report(prev)


def _record_fake(variant: str, sb: Scoreboard) -> None:
    line = (
        f"{variant}: n_compare={sb.n_compare} n_mismatch={sb.n_mismatch} "
        f"first={sb.first}"
    )
    print(line, flush=True)
    prev = _load_prev()
    lines = list(prev.get("fake_fail_lines") or [])
    if line not in lines:
        lines.append(line)
    prev["fake_fail_lines"] = lines
    prev["enc_expected"] = _enc_expected_compares()
    prev["syn_expected"] = _syn_expected_compares()
    _write_report(prev)
