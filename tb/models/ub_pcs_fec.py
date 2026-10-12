"""ub_pcs_fec_enc / ub_pcs_fec_dec (CODING_STYLE §5).

SPEC §2.4 rows ``ub_pcs_fec_enc`` / ``ub_pcs_fec_dec``
(UB-PHY §3.2.2.1 encoder, §3.2.3.5 decoder).

RTL-independent golden: symbol-by-symbol polynomial arithmetic over GF(2^8).
Not derived from ``rtl/pcs/ub_pcs_fec_*.v``.

Closed rules:

- RS(128, 120), eight parity symbols. Field GF(2^8), primitive polynomial
  ``x^8+x^4+x^3+x^2+1`` (0x11D); ``alpha`` is a root (0x02).
- ``g(x) = prod_{j=0}^{2T-1} (x - alpha^j)``. Coefficients g0..g8 equal
  Table 3-2: 24, 200, 173, 239, 54, 81, 11, 255, 1.
- ``m(x) = m_{K-1} x^{N-1} + ... + m_0 x^{2T}``. Input order m119..m0.
  Parity ``p(x) = m(x) mod g(x)``. Codeword order m119..m0, p7..p0.
- Symbol bits: ``m_i = sum_b m_{i,b} alpha^b`` (bit 0 = LSB coefficient).
- T=2 encoding uses the same eight parity symbols as T=4.
- Decoder: ``r(x) = r127 x^{127} + ... + r0``, r127 first.
  ``S_j = r(alpha^j)`` for ``0 <= j < 8``.
  T=4 corrects up to 4 symbol errors. T=2 uses ``S_0..S_3`` to correct up
  to 2 errors, then ``S_4..S_7`` on the corrected word must be zero.
  More than T errors that remain visible in the syndromes are failures,
  never a successful decode of a wrong word.
- Bypass: identity, no parity.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

N = 128
K = 120
TWO_T = 8
T_DEFAULT = 4
PRIM_POLY = 0x11D
ALPHA = 0x02
SYMBOL_BITS = 8
SYMBOL_MASK = 0xFF

# UB-PHY Table 3-2, g0 .. g8 (decimal). g8 = 1 (monic).
TABLE_3_2 = (24, 200, 173, 239, 54, 81, 11, 255, 1)

VECTOR_VERSION = 1
VECTOR_FILENAME = "ub_pcs_fec_vectors.json"


class FecMode(Enum):
    """Negotiated FEC mode (SPEC §2.4). T=4 is the default."""

    T4 = 4
    T2 = 2
    BYPASS = 0

    @property
    def t(self) -> int | None:
        if self is FecMode.BYPASS:
            return None
        return int(self.value)


@dataclass(frozen=True)
class UbPcsFecConfig:
    mode: FecMode = FecMode.T4
    n: int = N
    k: int = K

    def __post_init__(self) -> None:
        if self.n != N or self.k != K:
            raise ValueError(f"only RS({N},{K}) is specified, got RS({self.n},{self.k})")
        if self.n - self.k != TWO_T:
            raise ValueError("parity length must be 8")

    @property
    def t(self) -> int | None:
        return self.mode.t

    @property
    def two_t(self) -> int:
        return TWO_T

    @property
    def bypass(self) -> bool:
        return self.mode is FecMode.BYPASS


@dataclass(frozen=True)
class UbPcsFecDecodeResult:
    """Corrected 120 message symbols plus decode status."""

    message: tuple[int, ...]
    ok: bool
    uncorrectable: bool
    n_corrected: int
    syndromes: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.ok == self.uncorrectable:
            raise ValueError("ok and uncorrectable must be complementary")


def _build_gf_tables() -> tuple[list[int], list[int]]:
    """exp[i] = alpha^i, log[alpha^i] = i, for the 0x11D primitive field."""
    exp = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x <<= 1
        if x & 0x100:
            x ^= PRIM_POLY
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


_EXP, _LOG = _build_gf_tables()


def gf_mul(a: int, b: int) -> int:
    a &= SYMBOL_MASK
    b &= SYMBOL_MASK
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def gf_inv(a: int) -> int:
    a &= SYMBOL_MASK
    if a == 0:
        raise ZeroDivisionError("GF(256) inverse of 0")
    return _EXP[255 - _LOG[a]]


def gf_pow_alpha(e: int) -> int:
    """alpha^e with e taken modulo 255 (alpha^255 = 1)."""
    return _EXP[e % 255]


def _as_symbols(data: Sequence[int], n: int, *, name: str) -> list[int]:
    if len(data) != n:
        raise ValueError(f"{name} must have {n} symbols, got {len(data)}")
    out: list[int] = []
    for i, s in enumerate(data):
        v = int(s)
        if not 0 <= v <= SYMBOL_MASK:
            raise ValueError(f"{name}[{i}]={v} is not an 8-bit symbol")
        out.append(v)
    return out


def _poly_deg(p: Sequence[int]) -> int:
    deg = -1
    for i, c in enumerate(p):
        if c:
            deg = i
    return deg


def _poly_eval(coeffs: Sequence[int], x: int) -> int:
    """Evaluate coeffs[0] + coeffs[1] x + ... at x (Horner)."""
    acc = 0
    for c in reversed(coeffs):
        acc = gf_mul(acc, x) ^ c
    return acc


def _poly_mul_monic_linear(poly: list[int], root: int) -> list[int]:
    """poly(x) * (x - root) = poly(x) * (x + root) in characteristic 2."""
    out = [0] * (len(poly) + 1)
    for i, c in enumerate(poly):
        out[i] ^= gf_mul(c, root)
        out[i + 1] ^= c
    return out


def _poly_mod(dividend: Sequence[int], divisor: Sequence[int]) -> list[int]:
    """Remainder of dividend(x) / divisor(x). Coeffs are low-degree first."""
    ddeg = _poly_deg(divisor)
    if ddeg < 0:
        raise ZeroDivisionError("polynomial modulus is zero")
    num = list(dividend)
    inv_lead = gf_inv(divisor[ddeg])
    for deg in range(len(num) - 1, ddeg - 1, -1):
        if num[deg] == 0:
            continue
        factor = gf_mul(num[deg], inv_lead)
        shift = deg - ddeg
        for i, c in enumerate(divisor):
            num[shift + i] ^= gf_mul(factor, c)
    if ddeg == 0:
        return [0]
    return [(num[i] if i < len(num) else 0) for i in range(ddeg)]


def generator_coefficients() -> tuple[int, ...]:
    """g0..g8 from prod_{j=0}^{7} (x - alpha^j). Equals Table 3-2."""
    g = [1]
    for j in range(TWO_T):
        g = _poly_mul_monic_linear(g, gf_pow_alpha(j))
    return tuple(g)


def pack_symbols(symbols: Sequence[int]) -> int:
    """High-first pack: ``symbols[0]`` is the most-significant byte."""
    acc = 0
    for s in symbols:
        acc = (acc << SYMBOL_BITS) | (int(s) & SYMBOL_MASK)
    return acc


def unpack_symbols(word: int, n: int) -> list[int]:
    out = [0] * n
    for i in range(n - 1, -1, -1):
        out[i] = word & SYMBOL_MASK
        word >>= SYMBOL_BITS
    return out


def evaluate_syndromes(codeword: Sequence[int], nsynd: int = TWO_T) -> list[int]:
    """S_j = r(alpha^j) for j=0..nsynd-1. ``codeword[0]`` is r_{N-1}."""
    cw = _as_symbols(codeword, N, name="codeword")
    syn: list[int] = []
    for j in range(nsynd):
        aj = gf_pow_alpha(j)
        acc = 0
        for s in cw:
            acc = gf_mul(acc, aj) ^ s
        syn.append(acc)
    return syn


def _message_polynomial(message: Sequence[int]) -> list[int]:
    """m(x) = m119 x^{127} + ... + m0 x^8. Index is the power of x."""
    poly = [0] * N
    for i, s in enumerate(message):
        poly[N - 1 - i] = s
    return poly


def _encode_systematic(message: Sequence[int]) -> list[int]:
    """Parity = m(x) mod g(x); codeword = m119..m0, p7..p0."""
    g = generator_coefficients()
    rem = _poly_mod(_message_polynomial(message), g)
    # rem[i] is the coefficient of x^i = p_i. Wire order is p7..p0.
    parity_high_first = [rem[i] if i < len(rem) else 0 for i in range(TWO_T - 1, -1, -1)]
    return list(message) + parity_high_first


def _berlekamp_massey(syndromes: Sequence[int]) -> tuple[list[int], int]:
    """Locator λ(x) = 1 + λ1 x + ... with the (1 - X x) convention."""
    c = [1]
    b = [1]
    L = 0
    scale_b = 1
    m = 1
    for n, s_n in enumerate(syndromes):
        disc = s_n
        for i in range(1, min(L + 1, len(c))):
            disc ^= gf_mul(c[i], syndromes[n - i])
        if disc == 0:
            m += 1
            continue
        prev = c[:]
        factor = gf_mul(disc, gf_inv(scale_b))
        need = max(len(c), len(b) + m)
        c = c + [0] * (need - len(c))
        for i, coeff in enumerate(b):
            c[i + m] ^= gf_mul(factor, coeff)
        if 2 * L <= n:
            L = n + 1 - L
            b = prev
            scale_b = disc
            m = 1
        else:
            m += 1
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    return c, L


def _error_evaluator(syndromes: Sequence[int], lam: Sequence[int], nsynd: int) -> list[int]:
    """ω(x) = S(x) λ(x) mod x^{2T}."""
    omega = [0] * nsynd
    for i, s_i in enumerate(syndromes):
        for j, l_j in enumerate(lam):
            if i + j < nsynd:
                omega[i + j] ^= gf_mul(s_i, l_j)
    while len(omega) > 1 and omega[-1] == 0:
        omega.pop()
    return omega


def _formal_derivative(poly: Sequence[int]) -> list[int]:
    """d/dx in characteristic 2: even powers vanish."""
    deriv = [0] * max(len(poly) - 1, 1)
    for i in range(1, len(poly)):
        if i & 1:
            deriv[i - 1] = poly[i]
    return deriv


def _chien_forney(
    lam: Sequence[int],
    omega: Sequence[int],
    t: int,
) -> list[tuple[int, int]] | None:
    """Roots of λ at X^{-1}=alpha^{-i} → error at power i, magnitude via Forney.

    For syndromes S_j = r(alpha^j) (first root alpha^0) and λ(x)=∏(1-X_ℓ x):

        e_ℓ = X_ℓ · ω(X_ℓ^{-1}) / λ'(X_ℓ^{-1})
    """
    deg = _poly_deg(lam)
    if deg < 1 or deg > t:
        return None
    dlam = _formal_derivative(lam)
    a_inv = gf_pow_alpha(-1)
    xinv = 1  # alpha^{0} = alpha^{-0}
    found: list[tuple[int, int]] = []
    for power in range(N):
        if _poly_eval(lam, xinv) == 0:
            denom = _poly_eval(dlam, xinv)
            if denom == 0:
                return None
            x_loc = gf_pow_alpha(power)
            mag = gf_mul(x_loc, gf_mul(_poly_eval(omega, xinv), gf_inv(denom)))
            if mag == 0:
                return None
            found.append((power, mag))
        xinv = gf_mul(xinv, a_inv)
    if len(found) != deg:
        return None
    return found


def _fail(message: Sequence[int], syn: Sequence[int]) -> UbPcsFecDecodeResult:
    return UbPcsFecDecodeResult(
        message=tuple(message),
        ok=False,
        uncorrectable=True,
        n_corrected=0,
        syndromes=tuple(syn),
    )


def _ok(
    message: Sequence[int],
    syn: Sequence[int],
    n_corrected: int,
) -> UbPcsFecDecodeResult:
    return UbPcsFecDecodeResult(
        message=tuple(message),
        ok=True,
        uncorrectable=False,
        n_corrected=n_corrected,
        syndromes=tuple(syn),
    )


def _decode_rs(received: Sequence[int], t: int) -> UbPcsFecDecodeResult:
    rx = _as_symbols(received, N, name="received")
    syn = evaluate_syndromes(rx, TWO_T)
    msg_rx = rx[:K]
    if all(s == 0 for s in syn):
        return _ok(msg_rx, syn, 0)

    nsynd = 2 * t
    syn_use = syn[:nsynd]
    lam, L = _berlekamp_massey(syn_use)
    if L < 1 or L > t or _poly_deg(lam) != L or lam[0] != 1:
        return _fail(msg_rx, syn)

    omega = _error_evaluator(syn_use, lam, nsynd)
    located = _chien_forney(lam, omega, t)
    if located is None:
        return _fail(msg_rx, syn)

    corrected = list(rx)
    for power, mag in located:
        # r(x) power i sits at high-first index N-1-i.
        corrected[N - 1 - power] ^= mag

    syn_corr = evaluate_syndromes(corrected, TWO_T)
    # T=4: every syndrome of the corrected word must vanish.
    # T=2: correction used S0..S3; any residual (S4..S7, or leftover S0..S3)
    # is a failure.
    if any(syn_corr):
        return _fail(msg_rx, syn)
    return _ok(corrected[:K], syn, len(located))


def link_quality_delta(*, uncorrectable: bool, t: int) -> int:
    """Optional link-quality increment: +T+1 on a decode failure."""
    if t < 0:
        raise ValueError(f"t must be >= 0, got {t}")
    return (t + 1) if uncorrectable else 0


class UbPcsFecEnc:
    """Systematic RS(128,120) encoder. T=2 and T=4 share the same parity."""

    def __init__(self, cfg: UbPcsFecConfig | None = None) -> None:
        self.cfg = cfg or UbPcsFecConfig()

    def encode(self, message: Sequence[int]) -> list[int]:
        msg = _as_symbols(message, self.cfg.k, name="message")
        if self.cfg.bypass:
            return msg
        return _encode_systematic(msg)


class UbPcsFecDec:
    """Bounded-distance RS decoder (Berlekamp-Massey + Chien + Forney)."""

    def __init__(self, cfg: UbPcsFecConfig | None = None) -> None:
        self.cfg = cfg or UbPcsFecConfig()

    def syndromes(self, received: Sequence[int]) -> list[int]:
        return evaluate_syndromes(received, TWO_T)

    def decode(self, received: Sequence[int]) -> UbPcsFecDecodeResult:
        if self.cfg.bypass:
            if len(received) == self.cfg.k:
                msg = _as_symbols(received, self.cfg.k, name="received")
            elif len(received) == self.cfg.n:
                msg = _as_symbols(received[: self.cfg.k], self.cfg.k, name="received")
            else:
                raise ValueError(
                    f"bypass received must have {self.cfg.k} or {self.cfg.n} symbols"
                )
            return _ok(msg, (), 0)
        t = self.cfg.t
        if t is None:
            raise ValueError("decoder t is unset")
        return _decode_rs(received, t)


def encode(message: Sequence[int], cfg: UbPcsFecConfig | None = None) -> list[int]:
    return UbPcsFecEnc(cfg).encode(message)


def decode(received: Sequence[int], cfg: UbPcsFecConfig | None = None) -> UbPcsFecDecodeResult:
    return UbPcsFecDec(cfg).decode(received)


def reference_vectors(*, seed: int = 1, n_random: int = 4) -> dict:
    """Deterministic encode vectors for later testbenches."""
    import random

    enc = UbPcsFecEnc()
    vectors: list[dict] = []

    def add(name: str, message: list[int]) -> None:
        cw = enc.encode(message)
        vectors.append(
            {
                "name": name,
                "message": message,
                "codeword": cw,
                "parity": cw[K:],
            }
        )

    add("all_zero", [0] * K)
    add("all_0x55", [0x55] * K)
    add("incrementing", list(range(K)))
    rng = random.Random(seed)
    for i in range(n_random):
        add(f"random_{seed}_{i}", [rng.randrange(256) for _ in range(K)])

    # One directed error pattern so a decoder bench can load a received word.
    base = enc.encode(list(range(K)))
    received = list(base)
    received[0] ^= 0xA5
    received[N - 1] ^= 0x3C
    vectors.append(
        {
            "name": "two_errors_first_and_last",
            "message": list(range(K)),
            "codeword": base,
            "received": received,
            "error_positions": [0, N - 1],
            "error_magnitudes": [0xA5, 0x3C],
        }
    )
    return {
        "version": VECTOR_VERSION,
        "spec": "UB-PHY §3.2.2.1 / §3.2.3.5; SPEC §2.4 ub_pcs_fec_enc / ub_pcs_fec_dec",
        "n": N,
        "k": K,
        "prim_poly": hex(PRIM_POLY),
        "alpha": ALPHA,
        "generator_g0_to_g8": list(generator_coefficients()),
        "table_3_2": list(TABLE_3_2),
        "vectors": vectors,
    }


def write_reference_vectors(
    path: str | Path | None = None,
    *,
    seed: int = 1,
    n_random: int = 4,
) -> Path:
    dest = Path(path) if path is not None else Path(__file__).with_name(VECTOR_FILENAME)
    payload = reference_vectors(seed=seed, n_random=n_random)
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def default_vector_path() -> Path:
    return Path(__file__).with_name(VECTOR_FILENAME)
