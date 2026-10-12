"""TP↔TA monitor / driver. Signal names: LAYER_CONTRACTS §3.

Submit (ta2tp_*) and complete (tp2ta_*) are scored against the model
on each side independently.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from tb.contracts.model import (
    FLIT_W,
    INI_TASSN_W,
    MODE_W,
    OPCODE_W,
    predict_flit,
    predict_op,
)
from tb.contracts.scoreboard import ContractScoreboard

OP_FIELDS = (
    "ta2tp_op_valid",
    "ta2tp_op_ready",
    "ta2tp_opcode",
    "ta2tp_tassn",
    "ta2tp_mode",
    "ta2tp_bypass",
)
DATA_TX = (
    "ta2tp_data",
    "ta2tp_valid",
    "ta2tp_ready",
    "ta2tp_sop",
    "ta2tp_eop",
)
DONE = ("tp2ta_done", "tp2ta_fail", "tp2ta_tassn", "tp2ta_err")
OP_RX = (
    "tp2ta_op_valid",
    "tp2ta_op_ready",
    "tp2ta_opcode",
    "tp2ta_op_tassn",
    "tp2ta_op_mode",
    "tp2ta_op_bypass",
)
DATA_RX = (
    "tp2ta_data",
    "tp2ta_data_valid",
    "tp2ta_data_ready",
    "tp2ta_data_sop",
    "tp2ta_data_eop",
)
CTRL = ("nw2tp_flush", "nw_link_up")

ALL_SIGNALS = OP_FIELDS + DATA_TX + DONE + OP_RX + DATA_RX + CTRL


class MockBit:
    def __init__(self, value: int = 0, width: int = 1):
        self.width = width
        self._value = int(value) & ((1 << width) - 1)

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, raw: int) -> None:
        self._value = int(raw) & ((1 << self.width) - 1)


def mock_bundle() -> dict[str, MockBit]:
    widths = {
        "ta2tp_data": FLIT_W,
        "tp2ta_data": FLIT_W,
        "ta2tp_opcode": OPCODE_W,
        "tp2ta_opcode": OPCODE_W,
        "ta2tp_tassn": INI_TASSN_W,
        "tp2ta_tassn": INI_TASSN_W,
        "tp2ta_op_tassn": INI_TASSN_W,
        "ta2tp_mode": MODE_W,
        "tp2ta_op_mode": MODE_W,
    }
    return {name: MockBit(0, widths.get(name, 1)) for name in ALL_SIGNALS}


class TpTaDriver:
    def __init__(self, sigs: Mapping[str, Any]):
        self.sigs = sigs

    def idle_submit(self) -> None:
        self.sigs["ta2tp_op_valid"].value = 0
        self.sigs["ta2tp_valid"].value = 0
        self.sigs["ta2tp_opcode"].value = 0
        self.sigs["ta2tp_tassn"].value = 0
        self.sigs["ta2tp_mode"].value = 0
        self.sigs["ta2tp_bypass"].value = 0
        self.sigs["ta2tp_data"].value = 0
        self.sigs["ta2tp_sop"].value = 0
        self.sigs["ta2tp_eop"].value = 0

    def idle_complete(self) -> None:
        self.sigs["tp2ta_done"].value = 0
        self.sigs["tp2ta_fail"].value = 0
        self.sigs["tp2ta_tassn"].value = 0
        self.sigs["tp2ta_err"].value = 0
        self.sigs["tp2ta_op_valid"].value = 0
        self.sigs["tp2ta_data_valid"].value = 0

    def present_op(
        self,
        *,
        opcode: int,
        tassn: int,
        mode: int = 0,
        bypass: int = 1,
    ) -> None:
        self.sigs["ta2tp_opcode"].value = opcode
        self.sigs["ta2tp_tassn"].value = tassn
        self.sigs["ta2tp_mode"].value = mode
        self.sigs["ta2tp_bypass"].value = bypass
        self.sigs["ta2tp_op_valid"].value = 1

    def present_payload(self, *, data: int, sop: int, eop: int) -> None:
        self.sigs["ta2tp_data"].value = data
        self.sigs["ta2tp_sop"].value = sop
        self.sigs["ta2tp_eop"].value = eop
        self.sigs["ta2tp_valid"].value = 1

    def set_op_ready(self, ready: int) -> None:
        self.sigs["ta2tp_op_ready"].value = ready

    def set_data_ready(self, ready: int) -> None:
        self.sigs["ta2tp_ready"].value = ready

    def pulse_done(self, tassn: int, fail: int = 0, err: int = 0) -> None:
        self.sigs["tp2ta_tassn"].value = tassn
        self.sigs["tp2ta_done"].value = 0 if fail else 1
        self.sigs["tp2ta_fail"].value = 1 if fail else 0
        self.sigs["tp2ta_err"].value = err

    def present_deliver_op(
        self,
        *,
        opcode: int,
        tassn: int,
        mode: int = 0,
        bypass: int = 1,
    ) -> None:
        self.sigs["tp2ta_opcode"].value = opcode
        self.sigs["tp2ta_op_tassn"].value = tassn
        self.sigs["tp2ta_op_mode"].value = mode
        self.sigs["tp2ta_op_bypass"].value = bypass
        self.sigs["tp2ta_op_valid"].value = 1

    def present_deliver_payload(self, *, data: int, sop: int, eop: int) -> None:
        self.sigs["tp2ta_data"].value = data
        self.sigs["tp2ta_data_sop"].value = sop
        self.sigs["tp2ta_data_eop"].value = eop
        self.sigs["tp2ta_data_valid"].value = 1

    def set_deliver_op_ready(self, ready: int) -> None:
        self.sigs["tp2ta_op_ready"].value = ready

    def set_deliver_data_ready(self, ready: int) -> None:
        self.sigs["tp2ta_data_ready"].value = ready

    def set_flush(self, flush: int) -> None:
        self.sigs["nw2tp_flush"].value = flush

    def set_link_up(self, up: int) -> None:
        self.sigs["nw_link_up"].value = up


class TpTaMonitor:
    def __init__(self, sigs: Mapping[str, Any]):
        self.sigs = sigs

    def sample_submit_op(self) -> dict[str, int] | None:
        if int(self.sigs["ta2tp_op_valid"].value) != 1:
            return None
        if int(self.sigs["ta2tp_op_ready"].value) != 1:
            return None
        return {
            "opcode": int(self.sigs["ta2tp_opcode"].value),
            "tassn": int(self.sigs["ta2tp_tassn"].value),
            "mode": int(self.sigs["ta2tp_mode"].value),
            "bypass": int(self.sigs["ta2tp_bypass"].value),
        }

    def sample_submit_data(self) -> dict[str, int] | None:
        if int(self.sigs["ta2tp_valid"].value) != 1:
            return None
        if int(self.sigs["ta2tp_ready"].value) != 1:
            return None
        return {
            "data": int(self.sigs["ta2tp_data"].value),
            "sop": int(self.sigs["ta2tp_sop"].value),
            "eop": int(self.sigs["ta2tp_eop"].value),
        }

    def sample_complete(self) -> dict[str, int] | None:
        done = int(self.sigs["tp2ta_done"].value)
        fail = int(self.sigs["tp2ta_fail"].value)
        if not (done or fail):
            return None
        return {
            "done": done,
            "fail": fail,
            "tassn": int(self.sigs["tp2ta_tassn"].value),
            "err": int(self.sigs["tp2ta_err"].value),
        }

    def sample_deliver_op(self) -> dict[str, int] | None:
        if int(self.sigs["tp2ta_op_valid"].value) != 1:
            return None
        if int(self.sigs["tp2ta_op_ready"].value) != 1:
            return None
        return {
            "opcode": int(self.sigs["tp2ta_opcode"].value),
            "tassn": int(self.sigs["tp2ta_op_tassn"].value),
            "mode": int(self.sigs["tp2ta_op_mode"].value),
            "bypass": int(self.sigs["tp2ta_op_bypass"].value),
        }

    def sample_deliver_data(self) -> dict[str, int] | None:
        if int(self.sigs["tp2ta_data_valid"].value) != 1:
            return None
        if int(self.sigs["tp2ta_data_ready"].value) != 1:
            return None
        return {
            "data": int(self.sigs["tp2ta_data"].value),
            "sop": int(self.sigs["tp2ta_data_sop"].value),
            "eop": int(self.sigs["tp2ta_data_eop"].value),
        }


class TpTaHook:
    def __init__(self, sb: ContractScoreboard, mon: TpTaMonitor):
        self.sb = sb
        self.mon = mon

    def check_submit(self, exp: Mapping[str, int], ctx: str = "") -> None:
        got = self.mon.sample_submit_op()
        self.sb.compare("submit", dict(exp), got, ctx)

    def check_submit_data(self, exp: Mapping[str, int], ctx: str = "") -> None:
        got = self.mon.sample_submit_data()
        self.sb.compare("submit", dict(exp), got, ctx)

    def check_complete(self, exp: Mapping[str, int], ctx: str = "") -> None:
        got = self.mon.sample_complete()
        self.sb.compare("complete", dict(exp), got, ctx)

    def check_deliver(self, exp: Mapping[str, int], ctx: str = "") -> None:
        got = self.mon.sample_deliver_op()
        self.sb.compare("complete", dict(exp), got, ctx)


def submit_expected(**kwargs: int) -> dict[str, int]:
    op = predict_op(**kwargs)
    return {k: op[k] for k in ("opcode", "tassn", "mode", "bypass")}


def payload_expected(**kwargs: int) -> dict[str, int]:
    beat = predict_flit(sl=0, nlp=0, bypass=0, err=0, **kwargs)
    return {k: beat[k] for k in ("data", "sop", "eop")}


async def drive_op_beat(
    driver: TpTaDriver,
    rising: Callable,
    **fields: int,
) -> None:
    driver.present_op(**fields)
    await rising()
    while int(driver.sigs["ta2tp_op_ready"].value) != 1:
        await rising()
    driver.idle_submit()
