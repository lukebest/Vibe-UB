"""One stub class per C-line decode leaf. Behaviour is in StubDecoderBase."""

from __future__ import annotations

from pathlib import Path

from .contract_encodings import EncodingTable
from .contract_yaml import ContractHeader, find_contracts_dir, load_contract_file
from .model import StubDecoderBase

LEAF_NAMES: tuple[str, ...] = (
    "ub_mem_ptw_desc_dec",
    "ub_mem_dec_ent_dec",
    "ub_mem_tecte_dec",
    "ub_mem_tcte_dec",
    "ub_mem_l1tct_dec",
    "ub_mem_mapte_dec",
)


def load_leaf_header(leaf: str, contracts_dir: Path | None = None) -> ContractHeader:
    root = contracts_dir or find_contracts_dir()
    return load_contract_file(root / f"{leaf}.md")


class UbMemPtwDescDecStub(StubDecoderBase):
    def __init__(self, header: ContractHeader | None = None, **kwargs) -> None:
        super().__init__(header or load_leaf_header("ub_mem_ptw_desc_dec"), **kwargs)


class UbMemDecEntDecStub(StubDecoderBase):
    def __init__(self, header: ContractHeader | None = None, **kwargs) -> None:
        super().__init__(header or load_leaf_header("ub_mem_dec_ent_dec"), **kwargs)


class UbMemTecteDecStub(StubDecoderBase):
    def __init__(self, header: ContractHeader | None = None, **kwargs) -> None:
        super().__init__(header or load_leaf_header("ub_mem_tecte_dec"), **kwargs)


class UbMemTcteDecStub(StubDecoderBase):
    def __init__(self, header: ContractHeader | None = None, **kwargs) -> None:
        super().__init__(header or load_leaf_header("ub_mem_tcte_dec"), **kwargs)


class UbMemL1tctDecStub(StubDecoderBase):
    def __init__(self, header: ContractHeader | None = None, **kwargs) -> None:
        super().__init__(header or load_leaf_header("ub_mem_l1tct_dec"), **kwargs)


class UbMemMapteDecStub(StubDecoderBase):
    def __init__(self, header: ContractHeader | None = None, **kwargs) -> None:
        super().__init__(header or load_leaf_header("ub_mem_mapte_dec"), **kwargs)


_CLASSES: dict[str, type[StubDecoderBase]] = {
    "ub_mem_ptw_desc_dec": UbMemPtwDescDecStub,
    "ub_mem_dec_ent_dec": UbMemDecEntDecStub,
    "ub_mem_tecte_dec": UbMemTecteDecStub,
    "ub_mem_tcte_dec": UbMemTcteDecStub,
    "ub_mem_l1tct_dec": UbMemL1tctDecStub,
    "ub_mem_mapte_dec": UbMemMapteDecStub,
}


def make_stub(
    leaf: str,
    header: ContractHeader | None = None,
    encoding: EncodingTable | None = None,
    seed: int = 0,
) -> StubDecoderBase:
    cls = _CLASSES[leaf]
    hdr = header or load_leaf_header(leaf)
    return cls(header=hdr, encoding=encoding, seed=seed)
