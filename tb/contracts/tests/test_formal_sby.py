"""GATE-PRIVATE-PARENT-FREE / GATE-FORMAL-DEPTH structure for formal/contracts."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FORMAL = REPO / "formal" / "contracts"
DEFAULT_TASKS = frozenset({"bmc", "cover", "prove"})
COVER_MARGIN = 6
PLANNED_COVER = 16


def _sections(text: str) -> dict[str, list[str]]:
    cur = ""
    out: dict[str, list[str]] = {}
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("[") and s.endswith("]") and len(s) > 2:
            cur = s[1:-1].strip().lower()
            out.setdefault(cur, [])
            continue
        if cur:
            out[cur].append(raw)
    return out


def _task_names(text: str) -> set[str]:
    names: set[str] = set()
    for raw in _sections(text).get("tasks", []):
        line = raw.split("#", 1)[0].strip()
        if line:
            names.add(line.split()[0].lower())
    return names


def _files(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in _sections(text).get("files", []):
        line = raw.split("#", 1)[0].strip()
        if line:
            tokens.append(line.split()[0].strip("\"'"))
    return tokens


def _bmc_depth(text: str) -> int | None:
    bmc = None
    generic = None
    for raw in _sections(text).get("options", []):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        prefix = ""
        rest = line
        if ":" in line:
            left, right = line.split(":", 1)
            if left.strip() and " " not in left.strip():
                prefix = left.strip().lower()
                rest = right.strip()
        parts = rest.split()
        if len(parts) >= 2 and parts[0] == "depth":
            n = int(parts[1])
            if prefix == "bmc" or prefix.endswith("_bmc"):
                bmc = n
            elif prefix == "":
                generic = n
    return bmc if bmc is not None else generic


def test_default_sby_have_no_assume_file():
    for name in ("nw_tp.sby", "tp_ta.sby"):
        text = (FORMAL / name).read_text(encoding="utf-8")
        tasks = _task_names(text)
        assert tasks == DEFAULT_TASKS, (name, tasks)
        files = _files(text)
        assert all("assume" not in f for f in files), (name, files)
        assert "assume" not in text.lower().split("[script]", 1)[-1].split("[files]", 1)[0]
    dll = (FORMAL.parent / "dll" / "dll.sby").read_text(encoding="utf-8")
    assert _task_names(dll) == DEFAULT_TASKS
    assert all("assume" not in f for f in _files(dll))


def test_assume_only_in_named_diag_sby():
    for name in ("nw_tp_assume_diag.sby", "tp_ta_assume_diag.sby"):
        text = (FORMAL / name).read_text(encoding="utf-8")
        tasks = _task_names(text)
        assert tasks == {"assume_diag"}, (name, tasks)
        assert tasks.isdisjoint(DEFAULT_TASKS)
        files = _files(text)
        assert any(f.endswith("_assume.sv") for f in files), files


def test_assert_sv_has_no_assume_property():
    for name in ("nw_tp_assert.sv", "tp_ta_assert.sv", "nw_tp_harness.sv", "tp_ta_harness.sv"):
        text = (FORMAL / name).read_text(encoding="utf-8")
        assert "assume property" not in text
        assert not any(
            line.split("//", 1)[0].replace(" ", "").startswith("assume(")
            for line in text.splitlines()
        )


def test_assume_sv_exists_and_uses_assume_property():
    for name in ("nw_tp_assume.sv", "tp_ta_assume.sv"):
        text = (FORMAL / name).read_text(encoding="utf-8")
        assert "assume (" in text or "assume(" in text.replace(" ", "")


def test_bmc_depth_meets_planned_cover_margin():
    need = PLANNED_COVER + COVER_MARGIN
    for name in ("nw_tp.sby", "tp_ta.sby"):
        depth = _bmc_depth((FORMAL / name).read_text(encoding="utf-8"))
        assert depth is not None and depth >= need, (name, depth, need)
    dll_depth = _bmc_depth((FORMAL.parent / "dll" / "dll.sby").read_text(encoding="utf-8"))
    assert dll_depth is not None and dll_depth >= 6 + COVER_MARGIN, dll_depth

def test_nw_tp_has_no_timeout_322_323_cover():
    text = (FORMAL / "nw_tp_assert.sv").read_text(encoding="utf-8")
    assert "c_timeout_322" not in text
    assert "c_timeout_323" not in text
    assert "c_rto" in text
    assert "c_ack_coal" in text
    dll = (FORMAL.parent / "dll" / "dll_timeout_assert.sv").read_text(encoding="utf-8")
    assert "c_timeout_322" in dll
    assert "c_timeout_323" in dll
