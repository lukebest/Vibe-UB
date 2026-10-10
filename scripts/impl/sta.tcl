# OpenSTA 2.0-compatible recipe for impl quick-synth (Sky130 hd tt proxy).
# Avoid collection commands that are missing from OpenSTA 2.0.17
# (no remove_from_collection / sizeof_collection / report_worst_slack).
#
#   QS_TOP QS_NETLIST QS_LIBERTY QS_OUTDIR QS_PERIOD_NS QS_CLK_PORT QS_CLK_NAME

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
    create_clock -name $clk_name -period $period
}

# Inputs/outputs 0 delay / ideal. Port names come from the driver
# (OpenSTA 2.0 get_name on a collection is not usable).
set ins ""
set outs ""
if {[info exists ::env(QS_INPUTS)]} { set ins $::env(QS_INPUTS) }
if {[info exists ::env(QS_OUTPUTS)]} { set outs $::env(QS_OUTPUTS) }
foreach n $ins {
    if {$n eq ""} { continue }
    set_input_delay 0 -clock $clk_name [get_ports $n]
}
foreach n $outs {
    if {$n eq ""} { continue }
    set_output_delay 0 -clock $clk_name [get_ports $n]
}

# Sequential reset *inputs* are not data. Do not include rst_n_sync —
# that name is the sync's output / the adapter's data input.
foreach rst {rst_n rst_pyc port_rst} {
    catch {set_false_path -from [get_ports $rst]}
}

# No extra wire-load model: liberty default only.

set rpt [file join $outdir sta_worst_setup.rpt]
report_checks -path_delay max -path_group $clk_name \
    -group_count 1 -endpoint_count 1 \
    -unique_paths_to_endpoint \
    -format full -fields {slew cap input_pin net} -digits 4 \
    > $rpt

set unc [file join $outdir sta_unconstrained.rpt]
report_checks -unconstrained -path_delay max -group_count 1 \
    -endpoint_count 1 -format full -fields {slew cap input_pin net} \
    -digits 4 > $unc

exit
