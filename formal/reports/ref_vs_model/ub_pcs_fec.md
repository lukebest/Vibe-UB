# FEC formula-ref vs golden model

Leaf refs: `ub_pcs_fec_enc_ref`, `ub_pcs_fec_syndrome_ref`.
Golden: `tb/models/ub_pcs_fec.py` + `tb/models/ub_pcs_fec_vectors.json`.

## Compare counts

- encoder (enc:enc_ref): 17536 compares, 0 mismatches (expected 17536)
- syndrome (syn:syn_ref): 1104 compares, 0 mismatches (expected 1104)

## T=2 / bypass

- T=2 encode: same eight parity symbols as T=4; covered by `t2_incrementing` on the encoder ref.
- T=2 S4..S7: syndrome ref of a T=2-corrected word must be all-zero (model decoder + this Horner leaf).
- Bypass: **no pin on these refs**; identity / no-parity is covered on the model side only.

## First mismatch

None (refs match the golden on every counted symbol).

## Fake netlists (must FAIL)

- enc_bad_coeff: n_compare=17536 n_mismatch=1049 first={'ctx': 'enc_bad_coeff json:all_0x55 sym120', 'expected': 220, 'actual': 140}
- enc_rev_order: n_compare=17536 n_mismatch=1078 first={'ctx': 'enc_rev_order json:incrementing sym120', 'expected': 40, 'actual': 7}
- enc_poly11b: n_compare=17536 n_mismatch=1078 first={'ctx': 'enc_poly11b json:all_0x55 sym120', 'expected': 220, 'actual': 229}
- syn_poly11b: n_compare=1104 n_mismatch=954 first={'ctx': 'syn_poly11b json:all_0x55 S1', 'expected': 0, 'actual': 246}
- syn_bad_root: n_compare=1104 n_mismatch=144 first={'ctx': 'syn_bad_root json:all_0x55 S7', 'expected': 0, 'actual': 97}

## Self-test by directory

- `tb/fec_ref/`: 7 Icarus+cocotb runs (enc_ref, syn_ref, enc_bad_coeff, enc_rev_order, enc_poly11b, syn_poly11b, syn_bad_root).
- encoder symbol compares: 17536 (JSON 8 + one-hot 120 + extra-random 8 + T=2 incrementing).
- syndrome symbol compares: 1104 (clean CWs + JSON two_errors + T=2 corrected S0..S7).

## Formula-ref Yosys equiv

```
equiv: not run (timeout)
equiv: not run (timeout) [ub_pcs_fec_enc_self]
equiv: not run (timeout) [ub_pcs_fec_enc_false_ub_pcs_fec_enc_ref_bad_coeff]
equiv: not run (timeout) [ub_pcs_fec_enc_false_ub_pcs_fec_enc_ref_poly11b]
equiv: not run (timeout) [ub_pcs_fec_enc_false_ub_pcs_fec_enc_ref_rev_order]
equiv: not run (timeout) [ub_pcs_fec_syndrome_self]
equiv: not run (timeout) [ub_pcs_fec_syndrome_false_ub_pcs_fec_syndrome_ref_bad_root]
equiv: not run (timeout) [ub_pcs_fec_syndrome_false_ub_pcs_fec_syndrome_ref_poly11b]
```

## Legacy RTL (`rtl/pcs/`) — informational

```
legacy ub_pcs_fec_enc: TIMEOUT loading rtl (legacy; not blocking)
legacy ub_pcs_fec_syndrome: TIMEOUT loading rtl (legacy; not blocking)
```

Yosys 0.33 times out unrolling the per-symbol combo loop; Icarus is the
passing path. Legacy encoder ports are sequential (`clk`/`valid_*`);
the formula ref is combinational. Not blocking.

