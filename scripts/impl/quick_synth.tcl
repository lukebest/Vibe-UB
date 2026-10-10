# Yosys recipe for impl quick-synth (Sky130 hd tt proxy).
# Use `yosys {cmd}` (not `yosys -import`) so Tcl builtins (proc/eval) are not shadowed.
#
#   QS_TOP          synthesis top
#   QS_FILES        space-separated Verilog/SV sources
#   QS_LIB_FILES    optional blackbox memories (read_verilog -lib)
#   QS_LIBERTY      sky130_fd_sc_hd__tt_025C_1v80.lib
#   QS_OUTDIR       per-run output directory
#   QS_CHPARAM      optional Yosys chparam override (SPEC §2.2: not required)
#   QS_READ_SV      1 to pass -sv to read_verilog

set top     $::env(QS_TOP)
set files   $::env(QS_FILES)
set liberty $::env(QS_LIBERTY)
set outdir  $::env(QS_OUTDIR)

set sv 0
if {[info exists ::env(QS_READ_SV)] && $::env(QS_READ_SV) eq "1"} {
    set sv 1
}

# Large SRAM primitives: interface only (blackbox). Body never enters the design.
if {[info exists ::env(QS_LIB_FILES)] && $::env(QS_LIB_FILES) ne ""} {
    foreach f $::env(QS_LIB_FILES) {
        if {$f eq ""} { continue }
        if {$sv || [string match *.sv $f]} {
            yosys "read_verilog -lib -sv $f"
        } else {
            yosys "read_verilog -lib $f"
        }
    }
}

foreach f $files {
    if {$sv || [string match *.sv $f]} {
        yosys "read_verilog -sv $f"
    } else {
        yosys "read_verilog $f"
    }
}

if {[info exists ::env(QS_CHPARAM)] && $::env(QS_CHPARAM) ne ""} {
    yosys $::env(QS_CHPARAM)
}

yosys "hierarchy -check -top $top"
yosys {proc}
yosys {opt}
yosys "tee -o [file join $outdir designer_stat.txt] stat"
yosys "tee -o [file join $outdir scc_proc.txt] scc"

# Latch / memory probe on the generic netlist (before flatten/map).
yosys "tee -o [file join $outdir latch_generic.txt] select -list t:\$_DLATCH* t:\$_DLATCHSR* t:\$dlatch"
yosys "tee -o [file join $outdir mem_generic.txt] select -list t:\$mem t:\$mem_v2 t:\$memrd t:\$memwr t:\$meminit"

yosys "synth -top $top -flatten"
yosys "tee -o [file join $outdir generic_synth_stat.txt] stat"
yosys "tee -o [file join $outdir ltp.txt] ltp"
yosys "tee -o [file join $outdir scc_synth.txt] scc"

yosys "dfflibmap -liberty $liberty"
yosys "abc -liberty $liberty"
yosys {opt_clean -purge}
yosys "tee -o [file join $outdir mapped_stat.txt] stat -liberty $liberty"
yosys "tee -o [file join $outdir latch_mapped.txt] select -list t:*dlatch* t:*DLATCH* t:sky130_fd_sc_hd__dl*"

# -noexpr avoids concat-LHS assigns that OpenSTA 2.0 cannot parse.
yosys "write_verilog -noattr -noexpr [file join $outdir mapped.v]"
