# Formal

## Formula reference (verification)

Independent synthesizable SV references for A-line leaves. Ports match the
PRODUCT leaf contract used by the TB harnesses. Written from SPEC only —
not from `pycircuit/` or `rtl/`.

Xia: if a reference and `model/` / `tb/models` disagree bit-for-bit, **do not
edit either side**. Record the vector and bit in `formal/reports/ref_vs_model/`
and stop; Xia judges from SPEC.

`scripts/gate/equiv_ref.sh <leaf> <netlist.v>` compares a caller-supplied
netlist to the matching file under `formal/<layer>/ref/`. It does not look
up `rtl/` and does not require a design PR to be present.

`chparam` is applied to the gold (formula) side. The gate is chparam'd only
when the file itself declares `parameter NUM_LANES` / `PYC_RST_ACTIVE_HIGH`
(handwritten / older nets). pycc SPEC §2.2 nets have no Verilog parameter;
polarity and `NUM_LANES` come from the variant tag (`_x4`, `_pol0`) or env.

Gate `read_verilog` always uses `-I rtl/pyc_lib` (one copy of `pyc_reg.v` and
other pycc runtime primitives). If that directory is not in the tree yet,
the script falls back to `-I rtl/common` and prints
`WARN: rtl/pyc_lib/ missing; falling back to rtl/common for Yosys -I`.
The banner line includes `pyc_inc=rtl/pyc_lib` or `pyc_inc=rtl/common`.
The TB filelist (`tb/Makefile` `VERILOG_INCLUDE_DIRS`) uses the same pair.

Methods, in order. Exit 0 only if a method **proves** the compare.
Timeout of a method is unproven; try the next. BMC-only is not a pass.
Affine next-state basis is not a recognized pass.

1. `equiv_make` + `equiv_simple` + `equiv_induct` + `equiv_status -assert`
2. `miter -equiv -flatten -make_assert` + `sat -verify -tempinduct -prove-asserts -set-init-zero`
3. `write_aiger` of gold and gate, then Yosys `yosys-abc` `dsec`
   (combinational nets fall through to `cec`). If that cannot run:
   `miter -equiv -flatten -make_outputs` + `&r; &cec -m`.

The script prints `equiv_ref METHOD=...`, `equiv_ref TIME method=... sec=... result=...`,
`equiv_ref abc=... yosys=... yosys_pkg=...`, and `gate_chparam=none|...`.

Xia §2.6 BCRC `start`/`valid_in` (do not edit `tb/models`):

| Beat | Remainder |
| --- | --- |
| `start && valid_in` | `update(INIT, flit)` (MSB-first); last also emits `crc_word` next cycle |
| `start && valid_in && last` | `eat(flit, last=True)` — 16 data bytes, not the trailing BCRC word |
| `start && !valid_in` | load INIT, ignore `data_in` |
| `start` after a non-last block | abandon the partial remainder, reseed INIT |

Negative fixtures under `formal/dll/negative/` and `formal/pcs/negative/` must FAIL both the leaf TB (where applicable) and `equiv_ref.sh`. `bcrc_drop_start_flit.sv` loads INIT on `start` and drops a same-cycle flit.

| Leaf | Path | SPEC |
| --- | --- | --- |
| `ub_pcs_lane_dist` | `formal/pcs/ref/` | §2.3 / §2.4 `Lane<j,i>=CA<(NSYM-1)-i*N-j>` |
| `ub_pcs_lane_dedist` | `formal/pcs/ref/` | inverse of the same map |
| `ub_pcs_lane_collect` | `formal/pcs/ref/` | dist then dedist (no PRODUCT collect) |
| `ub_dll_bcrc` | `formal/dll/ref/` | §2.6 bit-serial CRC30 |
| `ub_dll_bcrc_check` | `formal/dll/ref/` | §2.6 CRC30 compare + flag passthrough |
| `ub_pyc_rst_adapt` | `formal/common/ref/` | §4.2 polarity adapter |

Cocotb self-check (no product netlist):

```bash
make -C tb leaf REF=1 LEAF=ub_pcs_lane_dist NUM_LANES=4 SIM=icarus
tb/scripts/run_ref_selfcheck.sh icarus
```

## Formal interface assertions

Architecture (Xia) owns the assertions. Path convention:

```
formal/<iface>/*.sv
formal/<iface>/*.sby
```

Each `<iface>` directory is self-contained: SystemVerilog assertions plus a
small stub so SymbiYosys can run the job **without product RTL**.

The gate (`scripts/gate/formal.sh`) walks `formal/*/*.sby` and runs
`sby -f` on each file. Any failure fails the job. When no `.sby` files
exist the job succeeds and prints `no assertions yet`.
