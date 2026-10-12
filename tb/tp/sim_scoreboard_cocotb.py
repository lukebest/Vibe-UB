"""Scoreboard cocotb test for ``ub_tp_bypass`` (new file; #65 owns sim_cocotb.py).

The architecture model is the oracle. Drive TA→NW and NW→TA packets
(1 flit / beat, valid/ready), including backpressure, flush, and
link-down. Compare each completed packet against ``UbTpBypass``.
"""

from __future__ import annotations

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import NextTimeStep, ReadOnly, RisingEdge

from model.tp.ub_tp_bypass import Flit
from tb.tp.items import ObservedRx, ObservedTx, RxSpec, TxSpec
from tb.tp.ports import CLK_PORT, PORTS, RST_PORT
from tb.tp.scoreboard import TpBypassScoreboard
from tb.tp.sequences import DUT_CASES, expected_compares, make_plan


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw, 0) if raw else default


def _sample_int(sig):
    val = sig.value
    is_res = getattr(val, "is_resolvable", None)
    if is_res is False:
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _require_ports(dut) -> None:
    missing = [n for n in PORTS if not hasattr(dut, n)]
    extra_tb = [n for n in dir(dut) if n.startswith("tb_")]
    if missing:
        raise AssertionError(f"DUT missing ports {missing}")
    if extra_tb:
        raise AssertionError(f"DUT has tb_* ports {extra_tb}; SPEC §10 lists none")


def _idle_inputs(dut) -> None:
    dut.ta2tp_valid.value = 0
    dut.ta2tp_op_valid.value = 0
    dut.ta2tp_sop.value = 0
    dut.ta2tp_eop.value = 0
    dut.ta2tp_data.value = 0
    dut.ta2tp_bypass.value = 1
    dut.ta2tp_dcna.value = 0
    dut.nw2tp_valid.value = 0
    dut.nw2tp_sop.value = 0
    dut.nw2tp_eop.value = 0
    dut.nw2tp_data.value = 0
    dut.nw2tp_err.value = 0


async def _reset(dut) -> None:
    getattr(dut, RST_PORT).value = 1
    dut.nw_link_up.value = 1
    dut.nw2tp_flush.value = 0
    dut.tp2nw_ready.value = 1
    dut.tp2ta_ready.value = 1
    _idle_inputs(dut)
    clk = getattr(dut, CLK_PORT)
    for _ in range(4):
        await RisingEdge(clk)
    getattr(dut, RST_PORT).value = 0
    await RisingEdge(clk)


class _Monitors:
    def __init__(self, dut) -> None:
        self.dut = dut
        self.clk = getattr(dut, CLK_PORT)
        self.tx: list[ObservedTx] = []
        self.rx: list[ObservedRx] = []
        self._tx_flits: list[Flit] = []
        self._tx_side: dict[str, int] | None = None
        self._rx_flits: list[Flit] = []
        self._rx_err = False
        self.cycle = 0
        self.running = True

    async def run(self) -> None:
        while self.running:
            await RisingEdge(self.clk)
            self.cycle += 1
            await ReadOnly()
            self._sample_tx()
            self._sample_rx()
            await NextTimeStep()

    def _sample_tx(self) -> None:
        valid = _sample_int(self.dut.tp2nw_valid)
        ready = _sample_int(self.dut.tp2nw_ready)
        if valid != 1 or ready != 1:
            return
        data = _sample_int(self.dut.tp2nw_data)
        sop = _sample_int(self.dut.tp2nw_sop)
        eop = _sample_int(self.dut.tp2nw_eop)
        if data is None or sop is None or eop is None:
            raise AssertionError(f"cycle {self.cycle}: TX beat has X/Z")
        side = {
            "bypass": _sample_int(self.dut.tp2nw_bypass),
            "dcna": _sample_int(self.dut.tp2nw_dcna),
            "sl": _sample_int(self.dut.tp2nw_sl),
            "nlp": _sample_int(self.dut.tp2nw_nlp),
            "lbf": _sample_int(self.dut.tp2nw_lbf),
            "rt": _sample_int(self.dut.tp2nw_rt),
            "cci": _sample_int(self.dut.tp2nw_cci),
        }
        if any(v is None for v in side.values()):
            raise AssertionError(f"cycle {self.cycle}: TX sideband X/Z {side}")
        flit = Flit(data, sop=bool(sop), eop=bool(eop))
        if flit.sop:
            self._tx_flits = [flit]
            self._tx_side = side
        else:
            if self._tx_side is None:
                raise AssertionError(f"cycle {self.cycle}: TX flit without sop")
            if side != self._tx_side:
                raise AssertionError(
                    f"cycle {self.cycle}: TX sideband changed mid-packet "
                    f"{self._tx_side} -> {side}"
                )
            self._tx_flits.append(flit)
        if flit.eop:
            assert self._tx_side is not None
            self.tx.append(
                ObservedTx(flits=tuple(self._tx_flits), **self._tx_side)
            )
            self._tx_flits = []
            self._tx_side = None

    def _sample_rx(self) -> None:
        valid = _sample_int(self.dut.tp2ta_valid)
        ready = _sample_int(self.dut.tp2ta_ready)
        if valid != 1 or ready != 1:
            return
        data = _sample_int(self.dut.tp2ta_data)
        sop = _sample_int(self.dut.tp2ta_sop)
        eop = _sample_int(self.dut.tp2ta_eop)
        err = _sample_int(self.dut.tp2ta_err)
        if None in (data, sop, eop, err):
            raise AssertionError(f"cycle {self.cycle}: RX beat has X/Z")
        flit = Flit(data, sop=bool(sop), eop=bool(eop))
        if flit.sop:
            self._rx_flits = [flit]
            self._rx_err = False
        else:
            if not self._rx_flits:
                raise AssertionError(f"cycle {self.cycle}: RX flit without sop")
            self._rx_flits.append(flit)
        if flit.eop:
            # err is meaningful on eop (LAYER_CONTRACTS §2).
            self.rx.append(
                ObservedRx(flits=tuple(self._rx_flits), err=bool(err))
            )
            self._rx_flits = []


async def _send_tx(dut, spec: TxSpec, mon: _Monitors, rng=None) -> None:
    clk = getattr(dut, CLK_PORT)
    remaining = list(spec.data)
    op_pending = True
    total = len(remaining)
    timeout = 256
    stall = 0
    while remaining or op_pending:
        # 1-deep TX register: hold dest ready some beats, but unblock
        # after two stalls so a multi-flit packet cannot deadlock.
        if rng is not None and stall == 0:
            dut.tp2nw_ready.value = int(rng.random() > 0.35)
        elif stall >= 2:
            dut.tp2nw_ready.value = 1
        if op_pending:
            dut.ta2tp_op_valid.value = 1
            dut.ta2tp_bypass.value = 1
            dut.ta2tp_dcna.value = spec.dcna
        if remaining:
            idx = total - len(remaining)
            dut.ta2tp_valid.value = 1
            dut.ta2tp_data.value = remaining[0]
            dut.ta2tp_sop.value = int(idx == 0)
            dut.ta2tp_eop.value = int(len(remaining) == 1)
        # Sample combo ready in this cycle, then take the edge that
        # captures the handshake. Post-edge ready already sees busy_q.
        await NextTimeStep()
        await ReadOnly()
        op_hs = op_pending and _sample_int(dut.ta2tp_op_ready) == 1 and _sample_int(
            dut.ta2tp_op_valid
        ) == 1
        data_hs = bool(remaining) and _sample_int(dut.ta2tp_ready) == 1 and _sample_int(
            dut.ta2tp_valid
        ) == 1
        op_rdy = _sample_int(dut.ta2tp_op_ready)
        data_rdy = _sample_int(dut.ta2tp_ready)
        nw_valid = _sample_int(dut.tp2nw_valid)
        await RisingEdge(clk)
        if op_hs:
            op_pending = False
            dut.ta2tp_op_valid.value = 0
        if data_hs:
            remaining.pop(0)
            if not remaining:
                dut.ta2tp_valid.value = 0
                dut.ta2tp_sop.value = 0
                dut.ta2tp_eop.value = 0
        stall = 0 if (op_hs or data_hs) else stall + 1
        timeout -= 1
        if timeout <= 0:
            raise AssertionError(
                f"cycle {mon.cycle}: TX handshake timeout tassn={spec.tassn} "
                f"op_pending={op_pending} nflit_left={len(remaining)} "
                f"op_ready={op_rdy} ta2tp_ready={data_rdy} "
                f"tp2nw_valid={nw_valid}. "
                "expected: DUT accepts TA submit (UbTpBypass.submit); "
                "actual: no valid/ready handshake. "
                "If op_ready stays 0 after a finished packet, busy_q did not "
                "clear on same-cycle op+eop "
                "(busy_next = op_hs | (busy & ~data_eop_hs))."
            )
    _idle_inputs(dut)


async def _send_rx(dut, spec: RxSpec, mon: _Monitors, rng=None) -> None:
    clk = getattr(dut, CLK_PORT)
    remaining = list(spec.data)
    total = len(remaining)
    timeout = 256
    stall = 0
    while remaining:
        if rng is not None and stall == 0:
            dut.tp2ta_ready.value = int(rng.random() > 0.35)
        elif stall >= 2:
            dut.tp2ta_ready.value = 1
        idx = total - len(remaining)
        dut.nw2tp_valid.value = 1
        dut.nw2tp_data.value = remaining[0]
        dut.nw2tp_sop.value = int(idx == 0)
        dut.nw2tp_eop.value = int(len(remaining) == 1)
        # err only presented on the eop beat (LAYER_CONTRACTS §2).
        dut.nw2tp_err.value = int(bool(spec.err) and len(remaining) == 1)
        await NextTimeStep()
        await ReadOnly()
        hs = _sample_int(dut.nw2tp_ready) == 1 and _sample_int(dut.nw2tp_valid) == 1
        await RisingEdge(clk)
        if hs:
            remaining.pop(0)
            if not remaining:
                dut.nw2tp_valid.value = 0
                dut.nw2tp_sop.value = 0
                dut.nw2tp_eop.value = 0
                dut.nw2tp_err.value = 0
            stall = 0
        else:
            stall += 1
        timeout -= 1
        if timeout <= 0:
            raise AssertionError(f"cycle {mon.cycle}: RX handshake timeout")
    _idle_inputs(dut)


async def _wait_tx(mon: _Monitors, before: int, *, timeout: int = 64) -> ObservedTx:
    clk = mon.clk
    for _ in range(timeout):
        if len(mon.tx) > before:
            return mon.tx[before]
        await RisingEdge(clk)
    raise AssertionError(
        f"cycle {mon.cycle}: DUT TX packet never completed "
        f"(have={len(mon.tx)} want>{before})"
    )


async def _wait_rx(mon: _Monitors, before: int, *, timeout: int = 64) -> ObservedRx:
    clk = mon.clk
    for _ in range(timeout):
        if len(mon.rx) > before:
            return mon.rx[before]
        await RisingEdge(clk)
    raise AssertionError(
        f"cycle {mon.cycle}: DUT RX packet never completed "
        f"(have={len(mon.rx)} want>{before})"
    )


async def _assert_no_tx(dut, mon: _Monitors, beats: int = 8) -> None:
    clk = getattr(dut, CLK_PORT)
    dut.ta2tp_op_valid.value = 1
    dut.ta2tp_bypass.value = 1
    dut.ta2tp_dcna.value = 0x00DE
    dut.ta2tp_valid.value = 1
    dut.ta2tp_sop.value = 1
    dut.ta2tp_eop.value = 1
    dut.ta2tp_data.value = 0xDEAD
    before = len(mon.tx)
    for _ in range(beats):
        await NextTimeStep()
        await ReadOnly()
        op_hs = _sample_int(dut.ta2tp_op_valid) == 1 and _sample_int(dut.ta2tp_op_ready) == 1
        data_hs = _sample_int(dut.ta2tp_valid) == 1 and _sample_int(dut.ta2tp_ready) == 1
        await RisingEdge(clk)
        if op_hs or data_hs:
            raise AssertionError(
                f"cycle {mon.cycle}: TX handshake while flush/link-down "
                f"op_hs={op_hs} data_hs={data_hs}"
            )
    if len(mon.tx) != before:
        raise AssertionError(f"cycle {mon.cycle}: unexpected TX packet during flush")
    _idle_inputs(dut)


async def _set_ready_pattern(dut, rng, enable: bool) -> None:
    if not enable:
        dut.tp2nw_ready.value = 1
        dut.tp2ta_ready.value = 1
        return
    dut.tp2nw_ready.value = int(rng.random() > 0.35)
    dut.tp2ta_ready.value = int(rng.random() > 0.35)


@cocotb.test()
async def test_ub_tp_bypass(dut):
    seed = _env_int("TP_SEED", 1)
    case = os.environ.get("TP_CASE", "all")
    print(f"SEED {seed}", flush=True)
    print(
        f"TP case={case} netlist={os.environ.get('TP_NETLIST', '?')}",
        flush=True,
    )
    _require_ports(dut)
    clk = getattr(dut, CLK_PORT)
    cocotb.start_soon(Clock(clk, 10, units="ns").start())
    await _reset(dut)
    assert _sample_int(dut.tp2nw_valid) == 0
    assert _sample_int(dut.tp2ta_valid) == 0

    mon = _Monitors(dut)
    cocotb.start_soon(mon.run())
    sb = TpBypassScoreboard()
    cases = list(DUT_CASES) if case == "all" else [case]
    total_want = 0
    rng = __import__("random").Random(seed)

    for name in cases:
        plan = make_plan(name, seed=seed)
        want = expected_compares(plan)
        total_want += want
        before = sb.n_compare
        wobble = name == "backpressure"
        for kind, payload in plan:
            await _set_ready_pattern(dut, rng, wobble)
            if kind == "tx":
                sb.expect_tx(payload)
                n_tx = len(mon.tx)
                await _send_tx(dut, payload, mon, rng if wobble else None)
                dut.tp2nw_ready.value = 1
                actual = await _wait_tx(mon, n_tx)
                if not sb.compare_tx(actual, f"{name} tx@{mon.cycle}"):
                    raise AssertionError(
                        f"seed={seed} cycle={mon.cycle} case={name}: "
                        + "; ".join(sb.mismatches)
                    )
            elif kind == "rx":
                if payload.drop:
                    raise AssertionError("DUT has no nw2tp_drop pin")
                sb.expect_rx(payload)
                n_rx = len(mon.rx)
                await _send_rx(dut, payload, mon, rng if wobble else None)
                dut.tp2ta_ready.value = 1
                actual = await _wait_rx(mon, n_rx)
                if not sb.compare_rx(actual, f"{name} rx@{mon.cycle}"):
                    raise AssertionError(
                        f"seed={seed} cycle={mon.cycle} case={name}: "
                        + "; ".join(sb.mismatches)
                    )
            elif kind == "flush":
                sb.apply_flush()
                dut.nw2tp_flush.value = 1
                await RisingEdge(clk)
                await _assert_no_tx(dut, mon)
            elif kind == "end_flush":
                sb.end_flush()
                dut.nw2tp_flush.value = 0
                await RisingEdge(clk)
            elif kind == "link_down":
                sb.apply_link_down()
                dut.nw_link_up.value = 0
                dut.tp2nw_ready.value = 0
                await RisingEdge(clk)
                await _assert_no_tx(dut, mon)
            elif kind == "link_up":
                sb.ref.nw_link_up = True
                sb.end_flush()
                dut.nw_link_up.value = 1
                dut.tp2nw_ready.value = 1
                dut.nw2tp_flush.value = 0
                await RisingEdge(clk)
            else:
                raise AssertionError(f"unknown step {kind}")
        got = sb.n_compare - before
        if got != want:
            raise AssertionError(
                f"case={name} n_compare {got} != expected {want}"
            )
        print(f"n_compare {name}={got}", flush=True)

    mon.running = False
    sb.assert_done(total_want)
    print(
        f"PASS ub_tp_bypass case={case} n_compare={sb.n_compare} "
        f"n_skip={sb.n_skip} n_mismatch={sb.n_mismatch}",
        flush=True,
    )
