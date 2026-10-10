# OpenSTA recipe for impl quick-synth (Sky130 hd tt proxy).
# Driven by environment variables set by scripts/impl/quick_synth.py.
#
#   QS_TOP          linked top
#   QS_NETLIST      mapped verilog from Yosys
#   QS_LIBERTY      sky130_fd_sc_hd__tt_025C_1v80.lib
#   QS_OUTDIR       per-run output directory
#   QS_PERIOD_NS    clock period (liberty time_unit = 1ns)
#   QS_CLK_PORT     clock port name, or empty for a virtual clock
#   QS_CLK_NAME     clock name in SDC (always core_clk)

set top       $::env(QS_TOP)
set netlist   $::env(QS_NETLIST)
set liberty   $::env(QS_LIBERTY)
set outdir    $::env(QS_OUTDIR)
set period    $::env(QS_PERIOD_NS)
set clk_name  core_clk
if {[info exists ::env(QS_CLK_NAME)] && $::env(QS_CLK_NAME) ne ""} {
    set clk_name $::env(QS_CLK_NAME)
}
set clk_port ""
if {[info exists ::env(QS_CLK_PORT)]} {
    set clk_port $::env(QS_CLK_PORT)
}

read_liberty $liberty
read_verilog $netlist
link_design $top

if {$clk_port ne ""} {
    create_clock -name $clk_name -period $period [get_ports $clk_port]
} else {
    # Combinational leaf: virtual clock so I/O can be constrained.
    create_clock -name $clk_name -period $period
}

# Inputs/outputs 0 delay / ideal. Exclude the clock port from input delay.
if {$clk_port ne ""} {
    set clk_pins [get_ports $clk_port]
    set din [remove_from_collection [all_inputs] $clk_pins]
} else {
    set din [all_inputs]
}
if {[sizeof_collection $din] > 0} {
    set_input_delay 0 -clock $clk_name $din
}
set dout [all_outputs]
if {[sizeof_collection $dout] > 0} {
    set_output_delay 0 -clock $clk_name $dout
}

# No extra wire-load model: liberty default only.

set rpt [file join $outdir sta_worst_setup.rpt]
report_checks -path_delay max -group_count 1 -endpoint_count 1 \
    -unique_paths_to_endpoint \
    -format full -fields {slew cap input_pin net} -digits 4 \
    > $rpt

set slack_rpt [file join $outdir sta_worst_slack.rpt]
report_worst_slack -max > $slack_rpt

# Unconstrained combo fallback (no sequential endpoints).
set unc [file join $outdir sta_unconstrained.rpt]
report_checks -unconstrained -path_delay max -group_count 1 \
    -endpoint_count 1 -format full -fields {slew cap input_pin net} \
    -digits 4 > $unc

exit
