# `formal/` — architecture-owned interface assertions (PHY first)

| Item | Value |
| --- | --- |
| Owner | Architecture (Xia). See [docs/TEAM.md](../docs/TEAM.md) §2 |
| Role | Interface contract, bindable by design self-checks and verification |
| Tool | SymbiYosys (`.sby`) + Yosys-compatible SVA subset |
| Companion | [model/](../model/) Python goldens |

Property modules contain **asserts / assumes / covers only** — no RTL
datapath. Each property cites the SPEC (or REGMAP) section it comes from.
Stubs under each `formal/<iface>/` are **not** product RTL; they exist so the
`.sby` job can pass standalone (BMC + cover) before the real leaf exists.

Do not copy UB Base Spec text. Cite section numbers only.

## Layout

| Directory | Interface | Property module | `.sby` |
| --- | --- | --- | --- |
| `reset/` | `rst_n` / `ub_rst_sync` | `ub_rst_if_props.sv` | `reset.sby` |
| `pma_pcs/` | PMA↔PCS data | `ub_pma_pcs_if_props.sv` | `pma_pcs.sby` |
| `lmsm_pcs/` | LMSM→PCS control | `ub_lmsm_pcs_if_props.sv` | `lmsm_pcs.sby` |
| `csr/` | CSR bus + TEST window | `ub_csr_if_props.sv` | `csr.sby` |
| `status/` | STATUS / PARAM reserved encodings | `ub_status_if_props.sv` | `status.sby` |
| `irq/` | `irq` + reset mask | `ub_irq_if_props.sv` | `irq.sby` |

## Properties (by interface)

### `reset` — SPEC §4.2, CODING_STYLE §2

| Property | What |
| --- | --- |
| `a_rst_async_assert` | `rst_n==0` ⇒ `rst_n_sync==0` combinationally (async assert) |
| `a_rst_sync_deassert_2flop` | two sampled `rst_n==1` ⇒ `rst_n_sync==1` next edge (2-flop) |
| `a_rst_held_after_assert` | sampled `rst_n==0` ⇒ next `rst_n_sync==0` |
| covers | output rise / fall, pin asserted / released |

### `pma_pcs` — SPEC §3.1, §3.2.4, §3.3, §9

| Property | What |
| --- | --- |
| `a_pma_w_m1` | `PMA_W==32` (M1) |
| `a_nlanes_*_legal` | `NUM_LANES_{TX,RX}` ∈ {1,2,4,8} |
| `a_pma_tx_hold` | TX valid/ready: hold valid+data until ready |
| (structural) | **no** `pma_rx_ready` port — RX is valid-only; sink must take every beat |
| covers | RX valid beat, TX handshake, TX backpressure, lane0 LSB, elec_idle |

### `lmsm_pcs` — SPEC §3.3.4, §5

| Property | What |
| --- | --- |
| `a_pattern_in_0_3` | `lmsm2pcs_pattern` 0..3 (all legal) |
| `a_lane_id_mode_ne3` | `lmsm2pcs_lane_id_mode` ≠ 3 (RESERVED; LMSM never drives) |
| `a_latch_*` | pattern / mode / `ltb_valid` / `ltb_type` latch at `lmb_start` |
| `a_hold_*` | latched copies stable between LMB starts |
| covers | each pattern 0..3, modes 0/1/2, LMB start, `ltb_valid` pulse, mid-frame change |

`lmb_start` is the PCS insertion-boundary strobe. It is **not** a SPEC
top-level pin; design and TB bind it to that pulse.

### `csr` — SPEC §3.2.3, §5, §7, §10, §11; REGMAP §2.4

| Property | What |
| --- | --- |
| `a_csr_ready_hi` | `csr_ready` always 1 (M1) |
| `a_csr_read_1cycle` | accepted read ⇒ `csr_rvalid` next cycle |
| `a_csr_write_no_rvalid` | accepted write ⇒ `csr_rvalid==0` next cycle |
| `a_csr_err_unmapped` | unmapped / unaligned ⇒ `csr_err` next cycle |
| `a_csr_err_mapped` | mapped ⇒ `csr_err==0` |
| `a_csr_unmap_rdata0` | unmapped read data is 0 |
| `a_csr_test_quiet_*` | TEST `0x0300–0x03FF` mapped; quiet ⇒ read 0 / write ignore / `csr_err==0` |
| (structural) | no `csr_wstrb` (full-word write only) |

### `status` — SPEC §6.3, §6.4, §9; REGMAP §2.1 / §2.2

| Property | What |
| --- | --- |
| `a_retry_req_st_legal` | `RETRY_REQ_ST` not in {5,6,7} |
| `a_retry_ack_st_legal` | `RETRY_ACK_ST` not in {2,3} |
| `a_num_lanes_*_legal` | `NUM_LANES_*` ∈ {1,2,4,8} |
| covers | every legal REQ / ACK code; lane counts 1/2/4/8 |

### `irq` — SPEC §3.2.6; REGMAP §2.1

| Property | What |
| --- | --- |
| `a_irq_formula` | `irq == IRQ_EN & \|(IRQ_STATUS & ~IRQ_MASK)` (active-high) |
| `a_irq_reset_mask` | while `rst_n==0`: `IRQ_EN==0`, `IRQ_MASK==0x7F`, `irq==0` |
| `a_irq_release_masked` | first cycle after release still fully masked |
| covers | masked-quiet, unmasked fire, `IRQ_EN==0` with sticky status |

## How design and verification bind them

Assertion modules are plain SV with input-only ports. Two inclusion styles:

**1. `bind` (preferred once the leaf exists)**

```systemverilog
bind ub_rst_sync ub_rst_if_props u_if (
  .core_clk(core_clk), .rst_n(rst_n), .rst_n_sync(rst_n_sync)
);
bind ub_controller ub_pma_pcs_if_props #(.NUM_LANES_TX(NUM_LANES_TX),
                                         .NUM_LANES_RX(NUM_LANES_RX)) u_pma (.*);
```

**2. Instantiate or `` `include ``** next to a TB wrapper / design self-check
harness (same ports). The standalone `.sby` jobs use instantiation so they
do not depend on Yosys `bind` support.

Design owns module-internal assertions. These files are the **interface**
slice only. Verification may also instantiate them in uvm-python / cocotb
wrappers; do not `force` internals (D13).

PRODUCT vs HOOKS: `ub_csr_if_props` takes `TEST_HOOKS`. PRODUCT ties
`tb_test_mode` unused and elaborates `TEST_HOOKS=0` (TEST window always quiet).

## Running the `.sby` jobs

```bash
make -C formal            # all ifaces, bmc + cover
make -C formal reset      # one iface
# or, from the iface directory:
sby -f reset.sby
```

Each job uses a stub/harness in the same directory. Depth is small (16–20).
Engine: `smtbmc z3`. Workdirs (`*_bmc/`, `*_cover/`) are gitignored.

If `sby` / `yosys` are not on PATH, say so — do not pretend the jobs ran.
