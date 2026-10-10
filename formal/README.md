# Formula reference (verification)

Independent synthesizable SV references for A-line leaves. Ports match the
PRODUCT leaf contract used by the TB harnesses. Written from SPEC only —
not from `pycircuit/` or `rtl/`.

Xia: if a reference and `model/` / `tb/models` disagree bit-for-bit, **do not
edit either side**. Record the vector and bit in `formal/reports/ref_vs_model/`
and stop; Xia judges from SPEC.

`scripts/gate/equiv_ref.sh <leaf> <netlist.v>` compares a caller-supplied
netlist to the matching file under `formal/<layer>/ref/`. It does not look
up `rtl/` and does not require a design PR to be present.

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
