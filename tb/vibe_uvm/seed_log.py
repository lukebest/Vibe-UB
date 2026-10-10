"""Log the run seed (D8). Print to the sim log so a fail can be replayed."""

from __future__ import annotations

import os
import random

from uvm import UVM_LOW, uvm_info


def resolve_seed(explicit: int | None = None) -> int:
    if explicit is not None:
        return int(explicit) & 0xFFFFFFFF
    for key in ("COCOTB_RANDOM_SEED", "RANDOM_SEED", "UVM_SEED"):
        raw = os.environ.get(key)
        if raw:
            return int(raw, 0) & 0xFFFFFFFF
    return random.SystemRandom().randrange(0, 2**32)


def log_seed(seed: int, where: str = "TB") -> int:
    """Print `SEED <n>` (VERIF_PLAN §10.3) and return it."""
    random.seed(seed)
    line = f"SEED {seed}"
    print(line, flush=True)
    try:
        uvm_info(where, line, UVM_LOW)
    except Exception:
        pass
    return seed
