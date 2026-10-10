#!/usr/bin/env python3
"""synth-check fixtures: handwritten async-reset FF vs real latch / combo loop."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gatelib import handwritten_modules
from synth_check import synth_module


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

    handwritten.yml lists the cell; recognition is by $adff/$adffe/$dffsr,
    not a whole-module skip.
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


def main() -> int:
    for fn in (
        test_async_ff_not_latch_or_loop,
        test_real_latch,
        test_real_combo_loop,
    ):
        fn()
    print("gate synth-selftest: PASS (async-FF clean; latch + combo-loop fail)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
