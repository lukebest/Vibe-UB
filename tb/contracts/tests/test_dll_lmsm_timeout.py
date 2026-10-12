"""DLL RETRY_WAIT / LMSM PROBE_WAIT 322/323. Not TP-owned.

LAYER_CONTRACTS §3: RETRY_WAIT_CYC (323-cycle) is DLL (§4.7.3.3);
PROBE_WAIT_CYC is LMSM (§3.4.3.2). TP uses RTO and ACK-coalescing
timers only (§6.4.2.1).
"""

from __future__ import annotations

import math

from tb.contracts.model import (
    F_CORE_HZ,
    TIMEOUT_DEFAULT_CYC,
    TIMEOUT_US,
    timed_out,
    timeout_cycles,
)


def test_dll_retry_wait_default_323():
    assert TIMEOUT_DEFAULT_CYC == 323
    assert math.ceil(TIMEOUT_US * 1e-6 * F_CORE_HZ) == 323
    assert timeout_cycles(None) == 323
    assert timeout_cycles(0) == 323
    assert timeout_cycles(323) == 323


def test_dll_retry_wait_322_not_fired():
    assert timed_out(322, 323) is False
    assert timed_out(322) is False


def test_dll_retry_wait_323_fired():
    assert timed_out(323, 323) is True
    assert timed_out(323) is True
    assert timed_out(324) is True


def test_lmsm_probe_wait_same_323_rule():
    assert timeout_cycles(None) == 323
    assert timed_out(322) is False
    assert timed_out(323) is True
