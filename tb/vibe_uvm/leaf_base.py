"""Shared helpers for leaf TBs. Stimulus is ports or SPEC §10 hooks only (D13)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge, Timer
from uvm import UVMConfigDb, UVMTest, uvm_error, uvm_info, UVM_LOW

from tb.vibe_uvm.clk_rst import CORE_CLK_PERIOD_PS
from tb.vibe_uvm.coverage import export_functional
from tb.vibe_uvm.scoreboard import ScoreboardBase
from tb.vibe_uvm.seed_log import log_seed, resolve_seed

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "tb" / "reports"


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw, 0)


def hooks_from_dut(dut) -> int:
    return 1 if hasattr(dut, "tb_test_mode") else 0


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


class CaseRecorder:
    def __init__(self, tb_name: str, seed: int, hooks: int):
        self.tb_name = tb_name
        self.seed = seed
        self.hooks = hooks
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
        dest = REPORTS / "regress" / f"hooks{self.hooks}" / f"{self.tb_name}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        n_pass = sum(1 for r in self.rows if r["status"] == "PASS")
        n_fail = sum(1 for r in self.rows if r["status"] == "FAIL")
        payload = {
            "tb": self.tb_name,
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
        self.hooks = hooks_from_dut(self.dut)
        self.rec = CaseRecorder(self.TB_NAME, self.seed, self.hooks)

    async def run_phase(self, phase):
        phase.raise_objection(self)
        try:
            await self._setup()
            await self.run_cases()
        finally:
            cov_name = f"{self.COV_PREFIX}_hooks{self.hooks}.json"
            export_functional(REPORTS / "cov_func" / cov_name)
            if self.rec is not None:
                self.rec.write(cov_name)
            n_fail = sum(1 for r in (self.rec.rows if self.rec else []) if r["status"] == "FAIL")
            tag = "FAIL" if n_fail else "PASS"
            print(
                f"{tag} {self.TB_NAME}_suite TEST_HOOKS={self.hooks} SEED {self.seed}",
                flush=True,
            )
            phase.drop_objection(self)

    async def _setup(self) -> None:
        dut = self.dut
        self.clkgen = GatedClock(dut.core_clk)
        self.clkgen.start()
        if hasattr(dut, "rst_n"):
            dut.rst_n.value = 0
        await self.idle_hooks()
        await wait_ps(CORE_CLK_PERIOD_PS * 2)

    async def idle_hooks(self) -> None:
        dut = self.dut
        if not self.hooks:
            return
        dut.tb_test_mode.value = 0
        dut.tb_inj_am_lock.value = 0
        dut.tb_inj_lid_bad.value = 0
        dut.tb_inj_crd_cells.value = 0

    async def check_hooks_quiet(self, case: str, tps: list[str]) -> None:
        """TEST_HOOKS=1: inj must not reach these leaves; obs stay 0 (SPEC §10 / §11)."""
        if not self.hooks:
            return
        dut = self.dut
        if hasattr(dut, "start"):
            dut.start.value = 0
            dut.valid_in.value = 0
            dut.last.value = 0
        if hasattr(dut, "valid_in"):
            dut.valid_in.value = 0
        for _ in range(2):
            await RisingEdge(dut.core_clk)
        before = {}
        for name in ("rst_n_sync", "rst_pyc", "data_out", "valid_out", "crc_word", "done",
                     "crc_ok", "crc_fail", "error_flag_rx"):
            if hasattr(dut, name):
                before[name] = as_int(getattr(dut, name), name)
        dut.tb_test_mode.value = 1
        dut.tb_inj_am_lock.value = 0xF
        dut.tb_inj_lid_bad.value = 1
        dut.tb_inj_crd_cells.value = 0xABCD
        await RisingEdge(dut.core_clk)
        for name, exp in before.items():
            got = as_int(getattr(dut, name), name)
            if got != exp:
                self.rec.fail(case, tps, f"hook changed {name}: {exp} -> {got}")
                raise AssertionError(f"{case}: hook changed {name}")
        for name in (
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
        ):
            got = as_int(getattr(dut, name), name)
            if got != 0:
                self.rec.fail(case, tps, f"{name}={got} expected 0")
                raise AssertionError(f"{case}: {name} not held 0")
        await self.idle_hooks()
        self.rec.pass_(case, tps)

    async def run_cases(self) -> None:
        raise NotImplementedError


async def leaf_entry(dut, test_cls_name: str) -> None:
    from uvm import run_test

    seed = log_seed(resolve_seed())
    UVMConfigDb.set(None, "*", "vif", dut)
    UVMConfigDb.set(None, "*", "seed", seed)
    await run_test(test_cls_name)
    print(f"SEED {seed}", flush=True)
