"""RS(128,120) FEC properties against UB-PHY §3.2.2.1 / §3.2.3.5 and SPEC §2.4."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from tb.models.ub_pcs_fec import (
    ALPHA,
    K,
    N,
    PRIM_POLY,
    TABLE_3_2,
    TWO_T,
    FecMode,
    UbPcsFecConfig,
    UbPcsFecDec,
    UbPcsFecEnc,
    decode,
    default_vector_path,
    encode,
    evaluate_syndromes,
    generator_coefficients,
    link_quality_delta,
    pack_symbols,
    reference_vectors,
    unpack_symbols,
    write_reference_vectors,
)

SEED_ENC = 0xFEC0128
SEED_DEC_T4 = 0xFEC4004
SEED_DEC_T2 = 0xFEC2002
SEED_FAIL_T4 = 0xFEC4005
SEED_FAIL_T2 = 0xFEC2003
N_RANDOM_CW = 24
N_TRIALS_OK = 16
N_TRIALS_FAIL = 80


def _gf_mul_shift(a: int, b: int) -> int:
    """Independent schoolbook GF(2^8) mul (not the model tables)."""
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi:
            a ^= PRIM_POLY & 0xFF
        b >>= 1
    return p


def _product_generator() -> list[int]:
    """g(x) = prod_{j=0}^{7} (x - alpha^j), low-degree first."""
    g = [1]
    x = 1
    for _j in range(TWO_T):
        root = x
        ng = [0] * (len(g) + 1)
        for i, c in enumerate(g):
            ng[i] ^= _gf_mul_shift(c, root)
            ng[i + 1] ^= c
        g = ng
        x = _gf_mul_shift(x, ALPHA)
    return g


def _alpha_pow(e: int) -> int:
    x = 1
    e %= 255
    for _ in range(e):
        x = _gf_mul_shift(x, ALPHA)
    return x


def _syndromes_def(cw: list[int]) -> list[int]:
    syn = []
    for j in range(TWO_T):
        aj = _alpha_pow(j)
        acc = 0
        xpow = 1
        for power in range(N):
            acc ^= _gf_mul_shift(cw[N - 1 - power], xpow)
            xpow = _gf_mul_shift(xpow, aj)
        syn.append(acc)
    return syn


def _rand_msg(rng: random.Random) -> list[int]:
    return [rng.randrange(256) for _ in range(K)]


def _inject(cw: list[int], rng: random.Random, nerr: int) -> list[int]:
    rx = list(cw)
    if nerr == 0:
        return rx
    for pos in rng.sample(range(N), nerr):
        rx[pos] ^= rng.randrange(1, 256)
    return rx


def test_generator_matches_table_3_2():
    g_model = generator_coefficients()
    g_prod = tuple(_product_generator())
    assert g_model == TABLE_3_2
    assert g_prod == TABLE_3_2
    assert g_model[-1] == 1


def test_all_zero_encodes_to_zero_and_has_zero_syndromes():
    cw = encode([0] * K)
    assert cw == [0] * N
    assert _syndromes_def(cw) == [0] * TWO_T
    assert evaluate_syndromes(cw) == [0] * TWO_T
    got = decode(cw)
    assert got.ok and not got.uncorrectable
    assert got.message == (0,) * K
    assert got.n_corrected == 0


@pytest.mark.parametrize("seed", [SEED_ENC, SEED_ENC + 1, 7])
def test_random_messages_encode_with_zero_syndromes(seed):
    rng = random.Random(seed)
    enc = UbPcsFecEnc()
    for _ in range(N_RANDOM_CW):
        msg = _rand_msg(rng)
        cw = enc.encode(msg)
        assert cw[:K] == msg
        assert len(cw) == N
        assert _syndromes_def(cw) == [0] * TWO_T
        assert evaluate_syndromes(cw) == [0] * TWO_T


def test_t2_encoding_matches_t4():
    rng = random.Random(SEED_ENC)
    msg = _rand_msg(rng)
    t4 = UbPcsFecEnc(UbPcsFecConfig(mode=FecMode.T4)).encode(msg)
    t2 = UbPcsFecEnc(UbPcsFecConfig(mode=FecMode.T2)).encode(msg)
    assert t4 == t2
    assert t4[K:] != [0] * TWO_T or msg == [0] * K


@pytest.mark.parametrize("mode,seed", [(FecMode.T4, SEED_DEC_T4), (FecMode.T2, SEED_DEC_T2)])
def test_zero_to_t_errors_are_fully_corrected(mode, seed):
    t = mode.value
    cfg = UbPcsFecConfig(mode=mode)
    enc = UbPcsFecEnc(cfg)
    dec = UbPcsFecDec(cfg)
    rng = random.Random(seed)
    for nerr in range(t + 1):
        for _ in range(N_TRIALS_OK):
            msg = _rand_msg(rng)
            cw = enc.encode(msg)
            rx = _inject(cw, rng, nerr)
            got = dec.decode(rx)
            assert got.ok, (nerr, got)
            assert not got.uncorrectable
            assert got.message == tuple(msg)
            assert got.n_corrected == nerr


@pytest.mark.parametrize(
    "idx,label",
    [
        (0, "first_symbol"),
        (K - 1, "last_message_symbol"),
        (K, "first_parity_symbol"),
        (N - 1, "last_symbol"),
        (N - 8, "parity_p7"),
        (N - 1, "parity_p0"),
    ],
)
def test_directed_error_positions(idx, label):
    del label
    msg = list(range(K))
    cw = encode(msg)
    for mode in (FecMode.T4, FecMode.T2):
        rx = list(cw)
        rx[idx] ^= 0x5A
        got = decode(rx, UbPcsFecConfig(mode=mode))
        assert got.ok
        assert got.message == tuple(msg)
        assert got.n_corrected == 1


def test_parity_symbol_errors_only():
    msg = [0xA5] * K
    cw = encode(msg)
    rx = list(cw)
    rx[K] ^= 0x11
    rx[K + 3] ^= 0x22
    rx[N - 1] ^= 0x33
    got = decode(rx)
    assert got.ok
    assert got.message == tuple(msg)
    assert got.n_corrected == 3


def _decode_failure_stats(mode: FecMode, nerr: int, seed: int, n_trials: int) -> dict:
    cfg = UbPcsFecConfig(mode=mode)
    enc = UbPcsFecEnc(cfg)
    dec = UbPcsFecDec(cfg)
    rng = random.Random(seed)
    fail = 0
    recovered = 0
    wrong_success = 0
    detectable_wrong = 0
    for _ in range(n_trials):
        msg = _rand_msg(rng)
        cw = enc.encode(msg)
        rx = _inject(cw, rng, nerr)
        got = dec.decode(rx)
        if not got.ok:
            fail += 1
            continue
        if got.message == tuple(msg):
            recovered += 1
            continue
        wrong_success += 1
        # Re-encode the delivered message. Residual syndromes mean the decoder
        # accepted a non-codeword — forbidden when the syndromes can detect it.
        delivered = enc.encode(list(got.message))
        if any(_syndromes_def(delivered)):
            detectable_wrong += 1
    return {
        "fail": fail,
        "recovered": recovered,
        "wrong_success": wrong_success,
        "detectable_wrong": detectable_wrong,
        "fail_rate": fail / n_trials,
    }


@pytest.mark.parametrize(
    "mode,nerr,seed",
    [
        (FecMode.T4, 5, SEED_FAIL_T4),
        (FecMode.T4, 8, SEED_FAIL_T4 + 8),
        (FecMode.T2, 3, SEED_FAIL_T2),
        (FecMode.T2, 6, SEED_FAIL_T2 + 6),
    ],
)
def test_more_than_t_errors_are_uncorrectable_when_detectable(mode, nerr, seed):
    stats = _decode_failure_stats(mode, nerr, seed, N_TRIALS_FAIL)
    assert stats["detectable_wrong"] == 0
    assert stats["fail_rate"] >= 0.75
    # A bounded-distance decoder cannot return the original message after T+1
    # symbol errors: that would require flipping T+1 positions.
    assert stats["recovered"] == 0


def test_bypass_is_identity():
    rng = random.Random(9)
    msg = _rand_msg(rng)
    cfg = UbPcsFecConfig(mode=FecMode.BYPASS)
    assert UbPcsFecEnc(cfg).encode(msg) == msg
    got = UbPcsFecDec(cfg).decode(msg)
    assert got.ok and not got.uncorrectable
    assert got.message == tuple(msg)
    assert got.n_corrected == 0
    # 128-symbol input: pass the leading 120 through, ignore a fake tail.
    padded = msg + [0xFF] * TWO_T
    got_n = UbPcsFecDec(cfg).decode(padded)
    assert got_n.message == tuple(msg)
    assert got_n.ok


def test_link_quality_helper_adds_t_plus_one_on_failure():
    assert link_quality_delta(uncorrectable=True, t=4) == 5
    assert link_quality_delta(uncorrectable=True, t=2) == 3
    assert link_quality_delta(uncorrectable=False, t=4) == 0
    cfg = UbPcsFecConfig(mode=FecMode.T4)
    msg = [1] * K
    cw = encode(msg, cfg)
    rx = list(cw)
    for i in range(5):
        rx[i] ^= 0x10 + i
    got = decode(rx, cfg)
    assert got.uncorrectable
    assert link_quality_delta(uncorrectable=got.uncorrectable, t=4) == 5


def test_pack_high_first_roundtrip():
    msg = list(range(K))
    cw = encode(msg)
    word = pack_symbols(cw)
    assert unpack_symbols(word, N) == cw
    assert (word >> (8 * (N - 1))) & 0xFF == cw[0]
    assert word & 0xFF == cw[-1]


def test_reference_vectors_file_matches_helper():
    payload = reference_vectors(seed=1, n_random=4)
    assert payload["generator_g0_to_g8"] == list(TABLE_3_2)
    path = default_vector_path()
    assert path.is_file()
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == payload
    enc = UbPcsFecEnc()
    dec = UbPcsFecDec()
    for vec in payload["vectors"]:
        assert enc.encode(vec["message"]) == vec["codeword"]
        if "received" in vec:
            got = dec.decode(vec["received"])
            assert got.ok
            assert list(got.message) == vec["message"]
        else:
            assert _syndromes_def(vec["codeword"]) == [0] * TWO_T


def test_write_reference_vectors_roundtrip(tmp_path: Path):
    dest = tmp_path / "ub_pcs_fec_vectors.json"
    write_reference_vectors(dest, seed=1, n_random=4)
    assert json.loads(dest.read_text(encoding="utf-8")) == reference_vectors(seed=1, n_random=4)


def test_rejects_bad_lengths_and_symbols():
    with pytest.raises(ValueError):
        encode([0] * (K - 1))
    with pytest.raises(ValueError):
        encode([256] + [0] * (K - 1))
    with pytest.raises(ValueError):
        decode([0] * 10)
    with pytest.raises(ValueError):
        UbPcsFecConfig(n=255, k=239)
