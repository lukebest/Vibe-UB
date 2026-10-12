"""NW↔TP monitor / driver. Signal names: LAYER_CONTRACTS §2.

Handles expose ``.value`` (cocotb DUT signals or pytest mocks).
TX (tp2nw_*) and RX (nw2tp_*) are scored against the model separately.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

from tb.contracts.model import FLIT_W, NLP_W, SL_W, predict_flit
from tb.contracts.scoreboard import ContractScoreboard

TX_DATA = (
    "tp2nw_data",
    "tp2nw_sop",
    "tp2nw_eop",
    "tp2nw_sl",
    "tp2nw_nlp",
    "tp2nw_bypass",
)
RX_DATA = (
    "nw2tp_data",
    "nw2tp_sop",
    "nw2tp_eop",
    "nw2tp_err",
)
TX_HS = ("tp2nw_valid", "tp2nw_ready")
RX_HS = ("nw2tp_valid", "nw2tp_ready")
CTRL = ("nw2tp_flush", "nw2tp_drop", "nw_link_up", "nw2tp_icrc_err")

ALL_SIGNALS = TX_DATA + RX_DATA + TX_HS + RX_HS + CTRL


class MockBit:
    """Minimal cocotb-shaped handle for RTL-free pytest."""

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
        "tp2nw_data": FLIT_W,
        "nw2tp_data": FLIT_W,
        "tp2nw_sl": SL_W,
        "tp2nw_nlp": NLP_W,
    }
    return {name: MockBit(0, widths.get(name, 1)) for name in ALL_SIGNALS}


class NwTpDriver:
    """Drive one direction. Master drives valid+data; slave drives ready."""

    def __init__(self, sigs: Mapping[str, Any]):
        self.sigs = sigs

    def idle_tx(self) -> None:
        self.sigs["tp2nw_valid"].value = 0
        self.sigs["tp2nw_data"].value = 0
        self.sigs["tp2nw_sop"].value = 0
        self.sigs["tp2nw_eop"].value = 0
        self.sigs["tp2nw_sl"].value = 0
        self.sigs["tp2nw_nlp"].value = 0
        self.sigs["tp2nw_bypass"].value = 0

    def idle_rx(self) -> None:
        self.sigs["nw2tp_valid"].value = 0
        self.sigs["nw2tp_data"].value = 0
        self.sigs["nw2tp_sop"].value = 0
        self.sigs["nw2tp_eop"].value = 0
        self.sigs["nw2tp_err"].value = 0

    def present_tx(
        self,
        *,
        data: int,
        sop: int,
        eop: int,
        sl: int = 0,
        nlp: int = 0,
        bypass: int = 0,
    ) -> None:
        self.sigs["tp2nw_data"].value = data
        self.sigs["tp2nw_sop"].value = sop
        self.sigs["tp2nw_eop"].value = eop
        self.sigs["tp2nw_sl"].value = sl
        self.sigs["tp2nw_nlp"].value = nlp
        self.sigs["tp2nw_bypass"].value = bypass
        self.sigs["tp2nw_valid"].value = 1

    def present_rx(
        self,
        *,
        data: int,
        sop: int,
        eop: int,
        err: int = 0,
    ) -> None:
        self.sigs["nw2tp_data"].value = data
        self.sigs["nw2tp_sop"].value = sop
        self.sigs["nw2tp_eop"].value = eop
        self.sigs["nw2tp_err"].value = err
        self.sigs["nw2tp_valid"].value = 1

    def set_tx_ready(self, ready: int) -> None:
        self.sigs["tp2nw_ready"].value = ready

    def set_rx_ready(self, ready: int) -> None:
        self.sigs["nw2tp_ready"].value = ready

    def set_link_up(self, up: int) -> None:
        self.sigs["nw_link_up"].value = up

    def set_flush(self, flush: int) -> None:
        self.sigs["nw2tp_flush"].value = flush

    def pulse_drop(self) -> None:
        self.sigs["nw2tp_drop"].value = 1

    def clear_drop(self) -> None:
        self.sigs["nw2tp_drop"].value = 0


class NwTpMonitor:
    def __init__(self, sigs: Mapping[str, Any]):
        self.sigs = sigs

    def _fired(self, valid: str, ready: str) -> bool:
        return int(self.sigs[valid].value) == 1 and int(self.sigs[ready].value) == 1

    def sample_tx(self) -> dict[str, int] | None:
        if not self._fired("tp2nw_valid", "tp2nw_ready"):
            return None
        return {
            "data": int(self.sigs["tp2nw_data"].value),
            "sop": int(self.sigs["tp2nw_sop"].value),
            "eop": int(self.sigs["tp2nw_eop"].value),
            "sl": int(self.sigs["tp2nw_sl"].value),
            "nlp": int(self.sigs["tp2nw_nlp"].value),
            "bypass": int(self.sigs["tp2nw_bypass"].value),
        }

    def sample_rx(self) -> dict[str, int] | None:
        if not self._fired("nw2tp_valid", "nw2tp_ready"):
            return None
        return {
            "data": int(self.sigs["nw2tp_data"].value),
            "sop": int(self.sigs["nw2tp_sop"].value),
            "eop": int(self.sigs["nw2tp_eop"].value),
            "err": int(self.sigs["nw2tp_err"].value),
        }

    def link_up(self) -> int:
        return int(self.sigs["nw_link_up"].value)

    def flush(self) -> int:
        return int(self.sigs["nw2tp_flush"].value)


class NwTpHook:
    """Scoreboard hook: each fired beat vs model, sides independent."""

    def __init__(self, sb: ContractScoreboard, mon: NwTpMonitor):
        self.sb = sb
        self.mon = mon

    def check_tx(self, exp: Mapping[str, int], ctx: str = "") -> None:
        got = self.mon.sample_tx()
        self.sb.compare("tx", dict(exp), got, ctx)

    def check_rx(self, exp: Mapping[str, int], ctx: str = "") -> None:
        got = self.mon.sample_rx()
        self.sb.compare("rx", dict(exp), got, ctx)


def tx_expected(**kwargs: int) -> dict[str, int]:
    beat = predict_flit(**kwargs)
    return {k: beat[k] for k in ("data", "sop", "eop", "sl", "nlp", "bypass")}


def rx_expected(**kwargs: int) -> dict[str, int]:
    beat = predict_flit(sl=0, nlp=0, bypass=0, **kwargs)
    return {k: beat[k] for k in ("data", "sop", "eop", "err")}


async def drive_tx_beat(
    driver: NwTpDriver,
    rising: Callable,
    **fields: int,
) -> None:
    """Cocotb-shaped helper: hold valid until ready, one fire."""
    driver.present_tx(**fields)
    await rising()
    while int(driver.sigs["tp2nw_ready"].value) != 1:
        await rising()
    driver.idle_tx()
