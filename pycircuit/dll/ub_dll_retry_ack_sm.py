"""ub_dll_retry_ack_sm — DLL RETRY_ACK_SM (real pyc4.0 leaf).

SPEC #41 / D20 §6.4 / §13 A-13.
Event names, pulse vs level, and fixed priority are from that head.
SPEC §10 lists no hooks: HOOKS ports match PRODUCT.

No SUB_SET / SUB_REPLAY: parent folds ack-set + replay into one
ub_dll_retry_ack_set_done pulse (#41 §6.4).
"""

from __future__ import annotations

from pathlib import Path

from pycircuit import Circuit, module, mux, u

# STATUS.RETRY_ACK_ST[14:13] (SPEC §6.4 / REGMAP). 2–3 reserved; never produced.
ST_NORMAL = 0
ST_ACK = 1

LEAF = "ub_dll_retry_ack_sm"
VARIANTS: dict[str, dict] = {
    "": {},
}

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRODUCT_V = REPO / "rtl" / "dll" / "ub_dll_retry_ack_sm.v"
HOOKS_V = REPO / "rtl" / "dll" / "hooks" / "ub_dll_retry_ack_sm.v"


def _build_body(m: Circuit) -> None:
    clk = m.clock("core_clk")
    rst = m.reset("rst_pyc")
    port_rst = m.input("port_rst", width=1)

    # SPEC §6.4 / A-13 event ports.
    req_set = m.input("ub_dll_retry_req_set", width=1)
    ack_set_done = m.input("ub_dll_retry_ack_set_done", width=1)

    st = m.out("st", clk=clk, rst=rst, width=2, init=u(2, ST_NORMAL))

    is_n = st == ST_NORMAL
    is_a = st == ST_ACK
    illegal = ~(is_n | is_a)

    # Priority (#41 §6.4): reset → NORMAL; req_set → ACK (covers same-cycle
    # ack_set_done); ack_set_done → NORMAL.
    st_n = mux(
        port_rst | illegal,
        u(2, ST_NORMAL),
        mux(req_set, u(2, ST_ACK), mux(is_a & ack_set_done, u(2, ST_NORMAL), st.out())),
    )

    st.set(st_n)
    m.output("retry_ack_st", st.out())


@module(name="ub_dll_retry_ack_sm")
def build(m: Circuit, test_hooks: int = 0) -> None:
    _ = int(test_hooks)
    _build_body(m)


build.__pycircuit_name__ = "ub_dll_retry_ack_sm"


def generate() -> tuple[Path, Path]:
    from lib.pycc_emit import compile_to_verilog

    product = compile_to_verilog(
        build,
        name=LEAF,
        params={},
        test_hooks=False,
    )
    hooks = compile_to_verilog(
        build,
        name=LEAF,
        params={},
        test_hooks=True,
    )
    PRODUCT_V.parent.mkdir(parents=True, exist_ok=True)
    HOOKS_V.parent.mkdir(parents=True, exist_ok=True)
    PRODUCT_V.write_text(product, encoding="utf-8")
    HOOKS_V.write_text(hooks, encoding="utf-8")
    return PRODUCT_V, HOOKS_V


if __name__ == "__main__":
    p, h = generate()
    print(f"wrote {p}")
    print(f"wrote {h}")
