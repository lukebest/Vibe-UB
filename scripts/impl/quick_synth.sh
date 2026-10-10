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

  --ref REF           synthesize this git ref (git archive; does not checkout)
  --work-tree DIR     synthesize this tree instead
  --base REF          diff base for default tops (default: origin/main)
  --tops m1,m2        top modules (default: rtl/ leaves touched vs --base)
  --out DIR           output directory (required)
  --extra-num-lanes N also chparam NUM_LANES for lane dist/dedist (default: 8)
  --help              this text

Env:
  SKY130_HD_LIB         path to sky130_fd_sc_hd__tt_025C_1v80.lib
  SKY130_HD_LIB_COMMIT  OpenROAD-flow-scripts commit used to fetch liberty
  YOSYS / STA           tool binaries (default: yosys, sta)

Default clock: core_clk at F_CORE from docs/SPEC.md (§4.1 / §9, ≈80.57 MHz).
If SPEC states no frequency, period is 2.0 ns (500 MHz) labelled placeholder.
EOF
}

OUT=""
REF=""
WORK_TREE=""
BASE="origin/main"
TOPS=""
EXTRA_LANES="8"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref) REF="${2:-}"; shift 2 ;;
    --work-tree) WORK_TREE="${2:-}"; shift 2 ;;
    --base) BASE="${2:-}"; shift 2 ;;
    --tops) TOPS="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    --extra-num-lanes) EXTRA_LANES="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

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
py+=(--extra-num-lanes "$EXTRA_LANES")
py+=(--liberty "$SKY130_HD_LIB")

exec "${py[@]}"
