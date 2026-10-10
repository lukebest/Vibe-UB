# Yosys recipe for impl quick-synth (Sky130 hd tt proxy).
# Driven by environment variables set by scripts/impl/quick_synth.py.
#
#   QS_TOP          synthesis top
#   QS_FILES        space-separated Verilog/SV sources
#   QS_LIBERTY      sky130_fd_sc_hd__tt_025C_1v80.lib
#   QS_OUTDIR       per-run output directory
#   QS_CHPARAM      optional Yosys chparam command (already includes module)
#   QS_READ_SV      1 to pass -sv to read_verilog

yosys -import

set top     $::env(QS_TOP)
set files   $::env(QS_FILES)
set liberty $::env(QS_LIBERTY)
set outdir  $::env(QS_OUTDIR)

set sv 0
if {[info exists ::env(QS_READ_SV)] && $::env(QS_READ_SV) eq "1"} {
    set sv 1
}

foreach f $files {
    if {$sv || [string match *.sv $f]} {
        read_verilog -sv $f
    } else {
        read_verilog $f
    }
}

if {[info exists ::env(QS_CHPARAM)] && $::env(QS_CHPARAM) ne ""} {
    eval $::env(QS_CHPARAM)
}

hierarchy -check -top $top
proc
opt
tee -o [file join $outdir designer_stat.txt] stat
tee -o [file join $outdir scc_proc.txt] scc

# Latch / memory probe on the generic netlist (before flatten/map).
tee -o [file join $outdir latch_generic.txt] select -list t:\$_DLATCH* t:\$_DLATCHSR* t:\$dlatch
tee -o [file join $outdir mem_generic.txt] select -list t:\$mem t:\$mem_v2 t:\$memrd t:\$memwr t:\$meminit

synth -top $top -flatten
tee -o [file join $outdir generic_synth_stat.txt] stat
tee -o [file join $outdir ltp.txt] ltp
tee -o [file join $outdir scc_synth.txt] scc

dfflibmap -liberty $liberty
abc -liberty $liberty
opt_clean
tee -o [file join $outdir mapped_stat.txt] stat -liberty $liberty
tee -o [file join $outdir latch_mapped.txt] select -list t:*dlatch* t:*DLATCH* t:sky130_fd_sc_hd__dl*

write_verilog -noattr [file join $outdir mapped.v]
