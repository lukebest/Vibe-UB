#!/usr/bin/env python3
"""synth-check fixtures: handwritten async-reset FF vs real latch / combo loop."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import handwritten_modules
from synth_check import deadreg_module, parse_yosys, synth_module


def _fail(name: str, detail: str) -> None:
    print(f"SELFTEST FAIL {name}: {detail}")
    raise SystemExit(1)


def _expect_rule(name: str, findings, rule: str) -> None:
    hits = [f for f in findings if f.rule == rule]
    if not hits:
        got = sorted({f.rule for f in findings}) or ["(none)"]
        _fail(name, f"expected rule {rule}, got {got}")
    print(f"SELFTEST PASS {name}: {rule} ({hits[0].message[:80]})")


def test_async_ff_not_latch_or_loop() -> None:
    """ub_rst_sync-style $adff must not be LATCH / COMBO_LOOP.

    Recognition is by $adff/$adffe/$dffsr cell type on every module, not a
    handwritten.yml skip and not a whole-module skip. SCC walks combo
    cells only; parse_yosys must not `continue` $adff lines.
    """
    listed = handwritten_modules()
    if "ub_rst_sync" not in listed:
        _fail("synth-async-ff", f"ub_rst_sync missing from handwritten.yml: {listed}")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ub_rst_sync.sv"
        path.write_text(
            "module ub_rst_sync (\n"
            "  input core_clk, input rst_n, output rst_n_sync\n"
            ");\n"
            "  reg r1, r2;\n"
            "  always @(posedge core_clk or negedge rst_n) begin\n"
            "    if (!rst_n) begin r1 <= 1'b0; r2 <= 1'b0; end\n"
            "    else begin r1 <= 1'b1; r2 <= r1; end\n"
            "  end\n"
            "  assign rst_n_sync = r2;\n"
            "endmodule\n",
            encoding="utf-8",
        )
        hits, _text = synth_module("ub_rst_sync", path, [path], [])
        bad = [h for h in hits if h.rule in {"LATCH", "COMBO_LOOP"}]
        if bad:
            _fail(
                "synth-async-ff",
                f"async-reset FF misclassified: "
                f"{[(h.rule, h.message[:80]) for h in bad]}",
            )
        print("SELFTEST PASS synth-async-ff: $adff/$adffe/$dffsr not LATCH/COMBO_LOOP")


def test_real_latch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad_latch.v"
        path.write_text(
            "module bad_latch(input en, input d, output reg q);\n"
            "  always @* if (en) q = d;\n"
            "endmodule\n",
            encoding="utf-8",
        )
        hits, _text = synth_module("bad_latch", path, [path], [])
        _expect_rule("synth-real-latch", hits, "LATCH")


def test_real_combo_loop() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad_combo_loop.v"
        path.write_text(
            "module bad_combo_loop(input a, output y);\n"
            "  assign y = ~y ^ a;\n"
            "endmodule\n",
            encoding="utf-8",
        )
        hits, _text = synth_module("bad_combo_loop", path, [path], [])
        _expect_rule("synth-real-combo-loop", hits, "COMBO_LOOP")


def test_async_ff_plus_real_combo_loop() -> None:
    """Async-reset FF in the same module must not hide a real combo loop."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad_async_and_loop.v"
        path.write_text(
            "module bad_async_and_loop(\n"
            "  input clk, input rst_n, input a, output q, output y\n"
            ");\n"
            "  reg r;\n"
            "  always @(posedge clk or negedge rst_n) begin\n"
            "    if (!rst_n) r <= 1'b0;\n"
            "    else r <= a;\n"
            "  end\n"
            "  assign q = r;\n"
            "  assign y = ~y ^ a;\n"
            "endmodule\n",
            encoding="utf-8",
        )
        hits, _text = synth_module("bad_async_and_loop", path, [path], [])
        _expect_rule("synth-async-plus-combo-loop", hits, "COMBO_LOOP")
        if any(h.rule == "LATCH" for h in hits):
            _fail("synth-async-plus-combo-loop", "async-reset FF also flagged LATCH")


def test_parse_does_not_skip_adff_line() -> None:
    """$adff on a line must not skip MULTI_DRIVE / COMBO_LOOP on that line."""
    text = "\n".join(
        [
            "Executing SCC pass (detecting logic loops).",
            "Found 0 SCCs in module ub_rst_sync.",
            "select -list t:$dlatch t:$adlatch t:$dlatchsr",
            "  created $adff cell `$procdff$3' with positive edge clock.",
            "  $_DFF_PN0_                      2",
            "Warning: found logic loop in module demo: $adff $xor",
            "multiple conflicting drivers for $adff.Q",
        ]
    )
    hits = parse_yosys(text, "demo", "demo.v")
    rules = {h.rule for h in hits}
    if "LATCH" in rules:
        _fail("synth-parse-no-skip", f"banner/select/$adff misclassified LATCH: {hits}")
    if "COMBO_LOOP" not in rules:
        _fail("synth-parse-no-skip", f"expected COMBO_LOOP on $adff line, got {rules}")
    if "MULTI_DRIVE" not in rules:
        _fail("synth-parse-no-skip", f"expected MULTI_DRIVE on $adff line, got {rules}")
    print("SELFTEST PASS synth-parse-no-skip: $adff line still MULTI_DRIVE+COMBO_LOOP")


def test_deadreg_catches_extra() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dead_extra.sv"
        path.write_text(
            "module dead_extra (input clk, input d, output reg q);\n"
            "  reg extra;\n"
            "  always @(posedge clk) begin q <= d; extra <= extra ^ d; end\n"
            "endmodule\n",
            encoding="utf-8",
        )
        findings = deadreg_module("dead_extra", path, [path], [])
        _expect_rule("synth-deadreg-extra", findings, "DEADREG")


def main() -> int:
    for fn in (
        test_deadreg_catches_extra,
        test_parse_does_not_skip_adff_line,
        test_async_ff_not_latch_or_loop,
        test_real_latch,
        test_real_combo_loop,
        test_async_ff_plus_real_combo_loop,
    ):
        fn()
    print(
        "gate synth-selftest: PASS "
        "(async-FF clean; latch + combo-loop + async+combo-loop fail)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
