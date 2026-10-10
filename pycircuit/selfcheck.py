#!/usr/bin/env python3
"""Minimal generator + golden self-check (not a verification TB).

Proves emit() runs. Lane dist is UB-PHY §3.2.2.3 (involutive + TB cosim). CRC30 golden uses SPEC
§2.6 byte-0 / MSB-first-per-byte and skips the last-flit BCRC field.
Scrambler involution uses *explicit* elaboration-only OPEN tokens
(SPEC §13) — not Switch, not product defaults.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from emit import emit_all
from lib import params as P
from lib.elab_open import ELAB_LFSR_INIT, ELAB_SCR_TAPS, elab_seed_map


def lfsr_step(s: int, taps: int, scr_w: int = P.SCR_W) -> int:
    fb = 0
    for k in range(scr_w):
        if (taps >> k) & 1:
            fb ^= (s >> k) & 1
    return ((s << 1) | fb) & ((1 << scr_w) - 1)


def xmask(state: int, taps: int, data_w: int, scr_w: int = P.SCR_W) -> int:
    """LSB-first data; each PRBS bit is the current MSB (Fibonacci)."""
    t = state
    acc = 0
    for i in range(data_w):
        acc |= ((t >> (scr_w - 1)) & 1) << i
        t = lfsr_step(t, taps, scr_w)
    return acc


def crc_step(c: int, b: int, poly: int = P.BCRC_POLY, crc_w: int = P.BCRC_W) -> int:
    fb = ((c >> (crc_w - 1)) & 1) ^ (b & 1)
    shl = (c << 1) & ((1 << crc_w) - 1)
    return shl ^ (poly if fb else 0)


def crc_bytes(c: int, data: bytes) -> int:
    """SPEC §2.6: Byte 0 upward, MSB first inside each byte. No invert."""
    t = c
    for byte in data:
        for bi in range(7, -1, -1):
            t = crc_step(t, (byte >> bi) & 1)
    return t


def flit_bytes(flit: int, flit_w: int = P.FLIT_W) -> bytes:
    nbytes = flit_w // 8
    return bytes((flit >> (8 * i)) & 0xFF for i in range(nbytes))


def crc_flit(c: int, flit: int, *, last: bool = False) -> int:
    raw = flit_bytes(flit)
    body = raw[: -P.BCRC_BYTES] if last else raw
    return crc_bytes(c, body)


def lane_dist(data: int, num_lanes: int, pma_w: int, sym_w: int) -> int:
    """UB-PHY §3.2.2.3 CodecNum=1 on this cycle's NSYM-symbol window."""
    nsym = num_lanes * (pma_w // sym_w)
    out = 0
    mask = (1 << sym_w) - 1
    spl = pma_w // sym_w
    for i in range(spl):
        for j in range(num_lanes):
            src = (nsym - 1) - i * num_lanes - j
            sym = (data >> (src * sym_w)) & mask
            out |= sym << (j * pma_w + i * sym_w)
    return out


def lane_dedist(data: int, num_lanes: int, pma_w: int, sym_w: int) -> int:
    nsym = num_lanes * (pma_w // sym_w)
    out = 0
    mask = (1 << sym_w) - 1
    spl = pma_w // sym_w
    for i in range(spl):
        for j in range(num_lanes):
            src = (nsym - 1) - i * num_lanes - j
            sym = (data >> (j * pma_w + i * sym_w)) & mask
            out |= sym << (src * sym_w)
    return out


def _pack_symbol_major(symbols: list[int], sym_w: int) -> int:
    word = 0
    for s, val in enumerate(symbols):
        word |= (val & ((1 << sym_w) - 1)) << (s * sym_w)
    return word


def _cosim_vs_tb_model() -> None:
    """Bit-exact vs tb.models.ub_pcs_lane_dist (tb/ not modified)."""
    root = HERE.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from tb.models.ub_pcs_lane_dist import UbPcsLaneDist, UbPcsLaneDistConfig

    for nlane in (1, 2, 4, 8):
        nsym = nlane * (P.PMA_W // P.SYM_W)
        ca = [(s * 17 + nlane) & 0xFF for s in range(nsym)]
        cfg = UbPcsLaneDistConfig(n_symbols=nsym)
        tb = UbPcsLaneDist(nlane, cfg)
        lanes = tb.distribute(ca)
        words = tb.pack_lane_words(lanes)
        tb_out = 0
        for j, lane_words in enumerate(words):
            tb_out |= lane_words[0] << (j * P.PMA_W)
        rtl_in = _pack_symbol_major(ca, P.SYM_W)
        rtl_out = lane_dist(rtl_in, nlane, P.PMA_W, P.SYM_W)
        assert rtl_out == tb_out, f"window cosim mismatch x{nlane}"
        back = lane_dedist(rtl_out, nlane, P.PMA_W, P.SYM_W)
        assert back == rtl_in

    # Full RS(128) codeword vs TB, high-end windows (first-on-wire first).
    nlane = 4
    n = 128
    win = nlane * (P.PMA_W // P.SYM_W)
    ca = list(range(n))
    tb = UbPcsLaneDist(nlane)
    packed = tb.pack_lane_words(tb.distribute(ca))
    nwords = n // win
    for k in range(nwords):
        window = ca[n - win * (k + 1) : n - win * k]
        rtl_out = lane_dist(_pack_symbol_major(window, P.SYM_W), nlane, P.PMA_W, P.SYM_W)
        tb_out = 0
        for j in range(nlane):
            tb_out |= packed[j][k] << (j * P.PMA_W)
        assert rtl_out == tb_out, f"RS128 cosim mismatch word {k}"
    assert packed[0][0] & 0xFF == 127
    assert (packed[1][0] & 0xFF) == 126
    assert (packed[2][0] & 0xFF) == 125
    assert (packed[3][0] & 0xFF) == 124


def _ports_block(text: str) -> str:
    return text.split("module", 1)[1].split(");", 1)[0]


def main() -> int:
    paths = emit_all()
    assert paths, "emit wrote nothing"
    products = [p for p in paths if "/hooks/" not in p.as_posix()]
    hooks = [p for p in paths if "/hooks/" in p.as_posix()]
    assert len(products) == 7, products
    assert len(hooks) == 7, hooks
    for p in paths:
        assert "gen/" not in p.as_posix()
        text = p.read_text(encoding="utf-8")
        assert "module " in text
        assert "`ifdef" not in text
        assert "$display" not in text
        assert "force " not in text
        if p.name != "ub_rst_sync.sv":
            assert "negedge rst_n" not in text
        # DECLFILENAME: file stem == module name
        mod = text.split("module ", 1)[1].split("(", 1)[0].split("#", 1)[0].strip()
        assert p.stem == mod, f"DECLFILENAME {p.name} vs {mod}"
        ports = _ports_block(text)
        assert "tb_test_mode" not in ports
        assert "tb_inj_" not in ports
        assert "tb_obs_" not in ports
        if "/hooks/" in p.as_posix():
            assert "TEST_HOOKS=1" in text
        else:
            assert "TEST_HOOKS=0" in text
    # Xia: no §10 hooks → HOOKS ports identical to PRODUCT (no tb_test_mode).
    for prod in products:
        hook = prod.parent / "hooks" / prod.name
        assert hook in hooks, hook
        assert _ports_block(prod.read_text(encoding="utf-8")) == _ports_block(
            hook.read_text(encoding="utf-8")
        )
    rst_hooks = HERE.parent / "rtl/common/hooks/ub_rst_sync.sv"
    assert not rst_hooks.exists(), "whitelist ub_rst_sync must not get a hooks copy"

    rtl = HERE.parent / "rtl"
    scr = (rtl / "pcs/ub_pcs_scrambler.v").read_text(encoding="utf-8")
    ports = _ports_block(scr)
    assert "amctl_lid" in ports
    assert "seed_load" in ports
    assert "lane_id" not in ports
    assert "SCR_TAPS" in scr
    assert "SEED_MAP" in scr
    assert "LFSR_INIT" in scr
    assert "t_mask[SCR_W-1]" in scr  # MSB-out Fibonacci
    assert "parameter integer SCR_TAP" not in scr
    assert "2'b01" not in scr
    assert "{SCR_W{1'b0}}" in scr
    assert "{SEED_MAP_W{1'b0}}" in scr
    assert "amctl_edf" in scr  # documented parent decode, not a port
    assert "amctl_edf" not in ports

    desc = (rtl / "pcs/ub_pcs_descrambler.v").read_text(encoding="utf-8")
    assert "amctl_lid" in _ports_block(desc)
    assert "lane_id" not in _ports_block(desc)
    assert "2'b01" not in desc

    bcrc = (rtl / "dll/ub_dll_bcrc.v").read_text(encoding="utf-8")
    assert "error_flag" not in _ports_block(bcrc)
    assert "1'b0, 1'b0, t" in bcrc
    assert "bi = 7" in bcrc
    assert "15A94AD5" in bcrc
    assert "NBYTE - BCRC_BYTES" in bcrc
    assert "n_eat" not in bcrc

    chk = (rtl / "dll/ub_dll_bcrc_check.v").read_text(encoding="utf-8")
    chk_ports = _ports_block(chk)
    assert "error_flag_rx" in chk_ports
    assert "input  wire                 error_flag" not in chk_ports

    for nlane in (1, 4, 8):
        width = nlane * P.PMA_W
        nsym = nlane * (P.PMA_W // P.SYM_W)
        sample = (0x0123456789ABCDEF0123456789ABCDEF) & ((1 << width) - 1)
        striped = lane_dist(sample, nlane, P.PMA_W, P.SYM_W)
        back = lane_dedist(striped, nlane, P.PMA_W, P.SYM_W)
        assert back == sample, f"lane dist/dedist failed for x{nlane}"
        # First-on-wire Lane<j,0> = CA<(NSYM-1)-j>
        for j in range(nlane):
            exp = (sample >> (((nsym - 1) - j) * P.SYM_W)) & 0xFF
            got = (striped >> (j * P.PMA_W)) & 0xFF
            assert got == exp, f"first-on-wire x{nlane} lane{j}"

    _cosim_vs_tb_model()

    taps = ELAB_SCR_TAPS
    st = ELAB_LFSR_INIT
    word = 0xA5A5A5A5 & ((1 << P.DATA_W_SCR) - 1)
    m = xmask(st, taps, P.DATA_W_SCR)
    assert (word ^ m) ^ m == word
    assert taps != 17
    assert st != 0x1

    smap = elab_seed_map()
    assert (smap & ((1 << P.SCR_W) - 1)) == 3

    c0 = P.BCRC_INIT
    c1 = crc_flit(c0, 0)
    c2 = crc_flit(c0, 1)
    assert c1 != c2
    assert crc_flit(c0, 0) == c1
    assert crc_flit(c0, 0x80) != crc_flit(c0, 0x01)
    # last flit skips the trailing BCRC word (4 bytes)
    last_full = crc_flit(c0, 0x80, last=False)
    last_skip = crc_flit(c0, 0x80, last=True)
    assert last_full != last_skip
    packed = c1 & ((1 << P.BCRC_W) - 1)
    assert packed == c1
    assert (packed >> 30) == 0

    print(
        "selfcheck ok: "
        f"{len(paths)} leaves @ rtl/<block>/, lane UB-PHY+TB cosim, "
        f"CRC30 byte-MSB-first + last-flit skip, scramble involution "
        f"(ELAB_SCR_TAPS={ELAB_SCR_TAPS:#x} ELAB_LFSR_INIT={ELAB_LFSR_INIT:#x})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
