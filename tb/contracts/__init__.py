"""B-line contract monitors, drivers, and scoreboard hooks.

NW↔TP and TP↔TA signal names follow docs/arch/LAYER_CONTRACTS.md §2 / §3.
These objects are cocotb-shaped (``.value`` handles) but do not import
cocotb, so pytest can self-test with mock signals when RTL is absent.
"""
