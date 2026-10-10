"""Shared helpers for leaf TBs. Stimulus is ports or SPEC §10 hooks only (D13)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import cocotb
from cocotb.triggers import Timer
from uvm import UVMConfigDb, UVMTest, uvm_error, uvm_info, UVM_LOW

from tb.vibe_uvm.clk_rst import CORE_CLK_PERIOD_PS
from tb.vibe_uvm.coverage import export_functional
from tb.vibe_uvm.ref_mismatch import record as record_ref_mismatch
from tb.vibe_uvm.ref_mismatch import ref_mode
from tb.vibe_uvm.scoreboard import ScoreboardBase, scoreboard_tally
from tb.vibe_uvm.seed_log import log_seed, resolve_seed

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "tb" / "reports"


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw, 0)


_TB_PORTS = (
    "tb_test_mode",
    "tb_inj_am_lock",
    "tb_inj_lid_bad",
    "tb_inj_crd_cells",
    "tb_obs_link_ready",
    "tb_obs_link_up",
    "tb_obs_lmsm_st",
    "tb_obs_crd_cells",
    "tb_obs_crd_pend",
    "tb_obs_crd_low",
    "tb_obs_crd_bp",
    "tb_obs_crd_to",
    "tb_obs_dll_sm_st",
    "tb_obs_consume_flits",
)


def hooks_netlist() -> int:
    """Compile-time netlist select (TEST_HOOKS env). These leaves have no tb_* ports."""
    return 1 if env_int("TEST_HOOKS", 0) else 0


def assert_no_tb_ports(dut) -> None:
    extra = [n for n in _TB_PORTS if hasattr(dut, n)]
    if extra:
        raise AssertionError(f"leaf wrapper must not expose {extra} (SPEC §10 / Xia)")


def as_int(sig, ctx: str) -> int:
    try:
        return int(sig.value)
    except ValueError as exc:
        raise AssertionError(f"{ctx} is X/Z ({sig.value})") from exc


async def wait_ps(ps: int) -> None:
    await Timer(max(1, int(ps)), units="ps")


class GatedClock:
    """50% core_clk that can stop and restart (no force of DUT internals)."""

    def __init__(self, clk, period_ps: int = CORE_CLK_PERIOD_PS):
        self.clk = clk
        self.period_ps = period_ps
        self.enabled = True
        self._task = None

    def start(self) -> None:
        self.clk.value = 0
        self._task = cocotb.start_soon(self._run())

    async def _run(self) -> None:
        half = self.period_ps // 2
        while True:
            if not self.enabled:
                await wait_ps(half)
                continue
            self.clk.value = 1
            await wait_ps(half)
            self.clk.value = 0
            await wait_ps(half)

    async def stop(self) -> None:
        self.enabled = False
        self.clk.value = 0
        await wait_ps(self.period_ps)

    async def resume(self) -> None:
        self.enabled = True
        await wait_ps(self.period_ps)


def run_tag() -> str:
    """Keep per-param JSON distinct so x4 / polarity runs are not overwritten."""
    leaf = os.environ.get("LEAF", "")
    parts: list[str] = []
    if leaf in ("ub_pcs_lane_dist", "ub_pcs_lane_dedist", "ub_pcs_lane_collect"):
        parts.append(f"x{env_int('NUM_LANES', 4)}")
    if leaf == "ub_pyc_rst_adapt":
        parts.append(f"pol{env_int('PYC_RST_ACTIVE_HIGH', 1)}")
    if ref_mode():
        parts.append("ref")
    return "_".join(parts)


def _sim_name() -> str:
    return os.environ.get("SIM", "icarus")


class CaseRecorder:
    def __init__(self, tb_name: str, seed: int, hooks: int, tag: str = ""):
        self.tb_name = tb_name
        self.seed = seed
        self.hooks = hooks
        self.tag = tag
        self.rows: list[dict] = []

    def pass_(self, name: str, tps: list[str], detail: str = "") -> None:
        self._emit("PASS", name, tps, detail)

    def fail(self, name: str, tps: list[str], detail: str) -> None:
        self._emit("FAIL", name, tps, detail)

    def _emit(self, status: str, name: str, tps: list[str], detail: str) -> None:
        rec = {
            "status": status,
            "test": name,
            "tp": tps,
            "seed": self.seed,
            "test_hooks": self.hooks,
            "detail": detail,
        }
        self.rows.append(rec)
        extra = f" {detail}" if detail else ""
        line = (
            f"{status} {name} TP={','.join(tps)} "
            f"SEED {self.seed} TEST_HOOKS={self.hooks}{extra}"
        )
        print(line, flush=True)
        uvm_info("LEAF", line, UVM_LOW)

    def write(self, cov_name: str) -> Path:
        stem = self.tb_name if not self.tag else f"{self.tb_name}_{self.tag}"
        dest = (
            REPORTS / "regress" / _sim_name() / f"hooks{self.hooks}" / f"{stem}.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        n_pass = sum(1 for r in self.rows if r["status"] == "PASS")
        n_fail = sum(1 for r in self.rows if r["status"] == "FAIL")
        payload = {
            "tb": self.tb_name,
            "tag": self.tag,
            "sim": _sim_name(),
            "seed": self.seed,
            "test_hooks": self.hooks,
            "pass": n_pass,
            "fail": n_fail,
            "tests": self.rows,
            "coverage_json": cov_name,
        }
        dest.write_text(json.dumps(payload, indent=2) + "\n")
        return dest


class LeafUvmTest(UVMTest):
    """One UVM test per leaf MODULE; run_phase walks named cases."""

    TB_NAME = "leaf"
    COV_PREFIX = "leaf"

    def __init__(self, name, parent):
        super().__init__(name, parent)
        self.dut = None
        self.seed = 0
        self.hooks = 0
        self.sb = ScoreboardBase("scoreboard", self)
        self.rec = None
        self.clkgen = None

    def build_phase(self, phase):
        super().build_phase(phase)
        arr = []
        if not UVMConfigDb.get(self, "", "vif", arr):
            uvm_error("LEAF", "vif not in config DB")
            return
        self.dut = arr[0]
        seed_arr = []
        if UVMConfigDb.get(self, "", "seed", seed_arr):
            self.seed = int(seed_arr[0])
        else:
            self.seed = resolve_seed()
        self.hooks = hooks_netlist()
        self.rec = CaseRecorder(self.TB_NAME, self.seed, self.hooks, tag=run_tag())

    def check(self, expected, actual, ctx: str) -> None:
        if not self.sb.check(expected, actual, ctx):
            if ref_mode():
                record_ref_mismatch(
                    leaf=self.TB_NAME, ctx=ctx, expected=expected, actual=actual
                )
            raise AssertionError(f"{ctx}: expected={expected!r} actual={actual!r}")

    def check_word(self, got: int, exp: int, num_lanes: int, ctx: str) -> None:
        from tb.vibe_uvm.lane_util import PMA_W, first_mismatch, mismatch_msg

        width = num_lanes * PMA_W
        self.sb.expect(width)
        for pos in range(width):
            self.sb.compare((exp >> pos) & 1, (got >> pos) & 1, f"{ctx}[{pos}]")
        if got != exp:
            if ref_mode():
                hit = first_mismatch(got, exp, num_lanes) or {}
                record_ref_mismatch(
                    leaf=self.TB_NAME,
                    ctx=ctx,
                    expected=exp,
                    actual=got,
                    extra={"num_lanes": num_lanes, **hit},
                )
            raise AssertionError(mismatch_msg(got, exp, num_lanes, ctx))

    async def run_phase(self, phase):
        phase.raise_objection(self)
        try:
            await self._setup()
            await self.run_cases()
            self.sb.finalize()
        except Exception:
            if self.rec is not None and not any(
                r["status"] == "FAIL" for r in self.rec.rows
            ):
                self.rec.fail("scoreboard", [], "scoreboard tally or uncaught error")
            raise
        finally:
            tag = run_tag()
            parts = [self.COV_PREFIX, _sim_name(), f"hooks{self.hooks}"]
            if tag:
                parts.append(tag)
            cov_name = "_".join(parts) + ".json"
            export_functional(REPORTS / "cov_func" / cov_name)
            if self.rec is not None:
                self.rec.write(cov_name)
            n_fail = sum(1 for r in (self.rec.rows if self.rec else []) if r["status"] == "FAIL")
            if self.sb.n_mismatch or scoreboard_tally(
                self.sb.n_compare, self.sb.n_expect, self.sb.n_mismatch
            ):
                n_fail += 1
            tag = "FAIL" if n_fail else "PASS"
            print(
                f"{tag} {self.TB_NAME}_suite TEST_HOOKS={self.hooks} SEED {self.seed} "
                f"SB {self.sb.n_compare}/{self.sb.n_expect}",
                flush=True,
            )
            phase.drop_objection(self)

    async def _setup(self) -> None:
        dut = self.dut
        self.clkgen = GatedClock(dut.core_clk)
        self.clkgen.start()
        if hasattr(dut, "rst_n"):
            dut.rst_n.value = 0
        assert_no_tb_ports(dut)
        await wait_ps(CORE_CLK_PERIOD_PS * 2)

    async def run_cases(self) -> None:
        raise NotImplementedError


async def leaf_entry(dut, test_cls_name: str) -> None:
    from uvm import run_test

    seed = log_seed(resolve_seed())
    UVMConfigDb.set(None, "*", "vif", dut)
    UVMConfigDb.set(None, "*", "seed", seed)
    await run_test(test_cls_name)
    print(f"SEED {seed}", flush=True)
