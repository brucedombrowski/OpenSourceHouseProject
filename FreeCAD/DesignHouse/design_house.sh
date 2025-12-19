#!/usr/bin/env bash
# Build the 950 Surf lot (lines + buildable area) and write a timestamped FCStd.

set -euo pipefail

if [[ -t 1 ]]; then
  clear
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MACROS_DIR="${SCRIPT_DIR}/macros"
# Template macro (generates timestamped copy for each build)
TEMPLATE_MACRO="${SCRIPT_DIR}/BeachHouse Template.FCMacro"
SNAP_MACRO="${MACROS_DIR}/snapshot_pile_spacing.FCMacro"
SNAP_JOIST_MACRO="${MACROS_DIR}/snapshot_joists.FCMacro"

# Prefer user-provided FreeCADCmd; default to headless CLI
DEFAULT_FCCMD="/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd"
FREECAD_CMD="${FREECAD_CMD:-$DEFAULT_FCCMD}"
DEFAULT_FC_GUI="/Applications/FreeCAD.app/Contents/MacOS/FreeCAD"
FREECAD_GUI_CMD="${FREECAD_GUI_CMD:-$DEFAULT_FC_GUI}"

# Ensure no stale FreeCAD processes are running
pkill -f "FreeCAD.app" 2>/dev/null || true
pkill -f "FreeCADCmd" 2>/dev/null || true

if [[ ! -f "${TEMPLATE_MACRO}" ]]; then
  echo "Template macro not found at ${TEMPLATE_MACRO}" >&2
  exit 1
fi

echo "Generating 950 Surf model (lot + piles) ..."
TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
BUILD_DIR="${BUILD_DIR:-${SCRIPT_DIR}/builds}"
ADDRESS="950_Surf"

# Clear previous builds to keep folder lean
if [[ -d "${BUILD_DIR}" ]]; then
  rm -rf "${BUILD_DIR:?}/"* 2>/dev/null || true
fi
mkdir -p "${BUILD_DIR}"

# Output files with address + timestamp
MACRO_OUT="${BUILD_DIR}/${ADDRESS}.${TIMESTAMP}.FCMacro"
OUT_PATH="${OUT_PATH:-${BUILD_DIR}/${ADDRESS}.${TIMESTAMP}.fcstd}"

echo "Creating timestamped macro: ${MACRO_OUT}"
cp "${TEMPLATE_MACRO}" "${MACRO_OUT}"

echo "Output will be saved to ${OUT_PATH}"
echo "Using FreeCADCmd at: ${FREECAD_CMD}"

PYTHONINSPECT=0 PYTHONSTARTUP= \
FREECAD_LOAD_3DCONNEXION=0 \
BEACH_BOM_PATH="${BUILD_DIR}/beach_bom.${TIMESTAMP}.csv" \
LUMBER_SAVE_FCSTD="${OUT_PATH}" \
  "${FREECAD_CMD}" -c "${MACRO_OUT}" </dev/null

# Optional snapshot (top view with dimensions) using GUI-capable FreeCAD (default on)
SNAPSHOT_DEFAULT="${SNAPSHOT:-1}"
if [[ "${SNAPSHOT_DEFAULT}" == "1" ]]; then
  SNAP_PATH="${BUILD_DIR}/${ADDRESS}_snapshot.${TIMESTAMP}.png"
  SNAP_INPUT="${BUILD_DIR}/snapshot_input.fcstd"
  echo "Generating snapshot at ${SNAP_PATH} ..."
  cp "${OUT_PATH}" "${SNAP_INPUT}"
  SNAPSHOT_INPUT="${SNAP_INPUT}" SNAPSHOT_IMAGE="${SNAP_PATH}" \
    PYTHONINSPECT=0 PYTHONSTARTUP= \
    FREECAD_LOAD_3DCONNEXION=0 \
    "${FREECAD_CMD}" -c "${SNAP_MACRO}" </dev/null

  # Joist spacing snapshot
  JOIST_SNAPSHOT="${BUILD_DIR}/${ADDRESS}_joists.${TIMESTAMP}.png"
  echo "Generating joist snapshot at ${JOIST_SNAPSHOT} ..."
  SNAPSHOT_INPUT="${SNAP_INPUT}" SNAPSHOT_IMAGE="${JOIST_SNAPSHOT}" \
    PYTHONINSPECT=0 PYTHONSTARTUP= \
    FREECAD_LOAD_3DCONNEXION=0 \
    "${FREECAD_CMD}" -c "${SNAP_JOIST_MACRO}" </dev/null

  # Floor plan snapshot (top-down view) - DISABLED (hangs on large models)
  # To generate manually: SNAPSHOT_INPUT="builds/950_Surf.*.fcstd" SNAPSHOT_IMAGE="builds/floor_plan.png" FreeCADCmd macros/snapshot_floor_plan.FCMacro
  # FLOOR_PLAN_MACRO="${MACROS_DIR}/snapshot_floor_plan.FCMacro"
  # if [[ -f "${FLOOR_PLAN_MACRO}" ]]; then
  #   FLOOR_PLAN_SNAPSHOT="${BUILD_DIR}/${ADDRESS}_floor_plan.${TIMESTAMP}.png"
  #   echo "Generating floor plan snapshot at ${FLOOR_PLAN_SNAPSHOT} ..."
  #   SNAPSHOT_INPUT="${SNAP_INPUT}" SNAPSHOT_IMAGE="${FLOOR_PLAN_SNAPSHOT}" \
  #     PYTHONINSPECT=0 PYTHONSTARTUP= \
  #     FREECAD_LOAD_3DCONNEXION=0 \
  #     "${FREECAD_CMD}" -c "${FLOOR_PLAN_MACRO}" </dev/null
  # fi

  rm -f "${SNAP_INPUT}"
fi

if [[ "${NO_OPEN:-0}" != "1" ]]; then
  echo "Closing existing FreeCAD documents and opening ${OUT_PATH} ..."
  /usr/bin/osascript <<OSA
tell application "FreeCAD"
  try
    repeat with d in (documents as list)
      close d saving no
    end repeat
  end try
  open POSIX file "${OUT_PATH}"
  activate
end tell
OSA
else
  echo "NO_OPEN=1 set; skipping GUI open."
fi
