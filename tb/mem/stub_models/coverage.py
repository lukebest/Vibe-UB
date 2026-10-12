"""Functional samples for stub models.

Existing ``tb/vibe_uvm/coverage.py`` CoverPoints are DUT / harness TPs.
This sampler is category ``stub_model`` so stub hits never mix with DUT
bins. Suggestion for the coverage rollup: key on ``category`` (or a
``stub_model.*`` name prefix) and keep ``reports/cov_func/`` DUT-only.

The PTW functional cross is exactly ``desc_lvl`` ×
``ENC_INVALID`` / ``ENC_TBL_PG`` / ``ENC_BLOCK`` (12 cells).
"""

from __future__ import annotations

from collections import Counter

from .contract_encodings import ENC_CLASSES, EncClassTable

STUB_MODEL_CATEGORY = "stub_model"


class StubModelCoverage:
    category = STUB_MODEL_CATEGORY

    def __init__(self, leaf: str, enc_table: EncClassTable | None = None) -> None:
        self.leaf = leaf
        self.enc_table = enc_table
        self.hits: Counter[str] = Counter()
        self.cross: Counter[tuple[int, str]] = Counter()

    def sample(self, event: str) -> None:
        self.hits[f"{STUB_MODEL_CATEGORY}.{self.leaf}.{event}"] += 1

    def sample_lvl_x_enc(self, level: int, enc_class: str) -> None:
        """CoverCross: walk level × input encoding class. Stub-model only."""
        key = (int(level), str(enc_class))
        self.cross[key] += 1
        self.hits[f"{STUB_MODEL_CATEGORY}.{self.leaf}.lvl_x_enc.{level}.{enc_class}"] += 1

    def expected_cells(self) -> frozenset[tuple[int, str]]:
        if self.enc_table is not None:
            return frozenset(self.enc_table.keys())
        return frozenset((level, enc) for level in range(4) for enc in ENC_CLASSES)

    def missing_cells(self) -> frozenset[tuple[int, str]]:
        return self.expected_cells() - frozenset(self.cross)

    def as_dict(self) -> dict[str, int]:
        payload = dict(self.hits)
        for (level, enc), count in self.cross.items():
            payload[f"{STUB_MODEL_CATEGORY}.{self.leaf}.cross.lvl_x_enc.{level}x{enc}"] = count
        return payload
