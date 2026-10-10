#!/usr/bin/env bash
# Impl quick-synth wrapper (Sky130 hd tt proxy). Informational; not a merge gate.
# See docs/rules/impl_quick_synth.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# OpenROAD-flow-scripts redistributes the SkyWater hd tt liberty.
# Do NOT commit the PDK. Override with SKY130_HD_LIB.
ORFS_COMMIT="${SKY130_HD_LIB_COMMIT:-5a76f84edc02baf49b75ccbd1a3a9e6a458a8d90}"
ORFS_LIB_REL="flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
ORFS_LIB_URL="${SKY130_HD_LIB_URL:-https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/${ORFS_COMMIT}/${ORFS_LIB_REL}}"

usage() {
  cat <<'EOF'
Usage: scripts/impl/quick_synth.sh [--ref GIT_REF | --work-tree DIR] [options]

  --ref REF                 synthesize this git ref (git archive; does not checkout)
  --work-tree DIR           synthesize this tree instead
  --base REF                diff base for default tops (default: origin/main)
  --tops m1,m2              top modules (default: rtl/<block>/*.v leaves touched vs --base)
  --out DIR                 output directory (required unless --self-check)
  --chparam KEY=VAL         optional Yosys chparam override (repeatable; TOP:KEY=VAL)
  --baseline-json FILE      prior results.json for QoR compare
  --baseline-report FILE    prior markdown report for QoR compare
  --baseline-map NEW=OLD    map a §2.2 tagged leaf to a legacy module[:VARIANT]
  --sram-bit-threshold N    blackbox mem instances with depth×width > N bits (default 4096)
  --incdir DIR              extra Yosys -I (repeatable; default is rtl/pyc_lib)
  --self-check              parser / mapping / include-read checks (no design synth)
  --help                    this text

Env:
  SKY130_HD_LIB           path to sky130_fd_sc_hd__tt_025C_1v80.lib
  SKY130_HD_LIB_COMMIT    OpenROAD-flow-scripts commit used to fetch liberty
  QS_SRAM_BIT_THRESHOLD   default for --sram-bit-threshold
  QS_INCDIRS              extra Yosys -I dirs (colon / comma / space separated)
  YOSYS / STA             tool binaries (default: yosys, sta)

Default clock: core_clk at F_CORE from docs/SPEC.md (§4.1 / §9, ≈80.57 MHz).
If SPEC states no frequency, period is 2.0 ns (500 MHz) labelled placeholder.

SPEC §2.2: each rtl/<block>/<leaf>_<tag>.v is a fixed netlist (no required chparam).
HOOKS are rtl/<block>/hooks/ with the same name. `_placeholder` is lint/TB only.
EOF
}

OUT=""
REF=""
WORK_TREE=""
BASE="origin/main"
TOPS=""
CHPARAMS=()
BASELINE_JSON=""
BASELINE_REPORT=""
BASELINE_MAPS=()
SRAM_THRESH=""
INCDIRS=()
SELF_CHECK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) REF="${2:-}"; shift 2 ;;
    --work-tree) WORK_TREE="${2:-}"; shift 2 ;;
    --base) BASE="${2:-}"; shift 2 ;;
    --tops) TOPS="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    --chparam) CHPARAMS+=("${2:-}"); shift 2 ;;
    --baseline-json) BASELINE_JSON="${2:-}"; shift 2 ;;
    --baseline-report) BASELINE_REPORT="${2:-}"; shift 2 ;;
    --baseline-map) BASELINE_MAPS+=("${2:-}"); shift 2 ;;
    --sram-bit-threshold) SRAM_THRESH="${2:-}"; shift 2 ;;
    --incdir) INCDIRS+=("${2:-}"); shift 2 ;;
    --self-check) SELF_CHECK=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "$SELF_CHECK" -eq 1 ]]; then
  exec python3 "${SCRIPT_DIR}/quick_synth.py" --self-check
fi

if [[ -z "$OUT" ]]; then
  echo "quick_synth.sh: --out is required" >&2
  usage >&2
  exit 2
fi

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "quick_synth.sh: missing tool '$1'" >&2
    echo "  install yosys (apt/oss-cad-suite) and OpenSTA (sta) or OpenROAD." >&2
    exit 3
  fi
}
need yosys
if command -v sta >/dev/null 2>&1; then
  :
elif command -v opensta >/dev/null 2>&1; then
  # Some packages install the binary as opensta; Python driver calls `sta`.
  export PATH="$(dirname "$(command -v opensta)"):$PATH"
else
  echo "quick_synth.sh: missing OpenSTA binary 'sta' (or 'opensta')" >&2
  exit 3
fi

cache_dir="${XDG_CACHE_HOME:-${HOME}/.cache}/vibe-ub/sky130"
mkdir -p "$cache_dir"
lib_name="sky130_fd_sc_hd__tt_025C_1v80.lib"
cached="${cache_dir}/${ORFS_COMMIT}_${lib_name}"

if [[ -n "${SKY130_HD_LIB:-}" && -f "${SKY130_HD_LIB}" ]]; then
  :
elif [[ -f "$cached" ]]; then
  export SKY130_HD_LIB="$cached"
else
  echo "quick_synth.sh: fetching Sky130 hd liberty from OpenROAD-flow-scripts ${ORFS_COMMIT}" >&2
  tmp="${cached}.part"
  if ! curl -fsSL "$ORFS_LIB_URL" -o "$tmp"; then
    echo "quick_synth.sh: liberty download failed: $ORFS_LIB_URL" >&2
    echo "  set SKY130_HD_LIB to a local sky130_fd_sc_hd__tt_025C_1v80.lib" >&2
    exit 4
  fi
  if ! grep -q 'library ("sky130_fd_sc_hd__tt_025C_1v80")' "$tmp"; then
    echo "quick_synth.sh: downloaded file is not the expected liberty" >&2
    exit 4
  fi
  mv "$tmp" "$cached"
  export SKY130_HD_LIB="$cached"
fi

export SKY130_HD_LIB_SOURCE="${SKY130_HD_LIB_SOURCE:-OpenROAD-flow-scripts ${ORFS_LIB_REL} (SkyWater hd tt; not committed)}"
export SKY130_HD_LIB_COMMIT="${ORFS_COMMIT}"

py=(python3 "${SCRIPT_DIR}/quick_synth.py" --repo "$REPO_ROOT" --out "$OUT" --base "$BASE")
if [[ -n "$REF" ]]; then
  py+=(--ref "$REF")
fi
if [[ -n "$WORK_TREE" ]]; then
  py+=(--work-tree "$WORK_TREE")
fi
if [[ -n "$TOPS" ]]; then
  py+=(--tops "$TOPS")
fi
for c in "${CHPARAMS[@]+"${CHPARAMS[@]}"}"; do
  py+=(--chparam "$c")
done
if [[ -n "$BASELINE_JSON" ]]; then
  py+=(--baseline-json "$BASELINE_JSON")
fi
if [[ -n "$BASELINE_REPORT" ]]; then
  py+=(--baseline-report "$BASELINE_REPORT")
fi
for m in "${BASELINE_MAPS[@]+"${BASELINE_MAPS[@]}"}"; do
  py+=(--baseline-map "$m")
done
if [[ -n "$SRAM_THRESH" ]]; then
  py+=(--sram-bit-threshold "$SRAM_THRESH")
fi
for d in "${INCDIRS[@]+"${INCDIRS[@]}"}"; do
  py+=(--incdir "$d")
done
py+=(--liberty "$SKY130_HD_LIB")

exec "${py[@]}"
