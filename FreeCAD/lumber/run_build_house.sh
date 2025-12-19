#!/usr/bin/env bash
# Helper: rebuild the 16x24 house in a fresh FreeCAD document with one command.
# Usage: ./run_build_house.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
MACRO="${SCRIPT_DIR}/Build_House_16x24_From_Modules.FCMacro"

if [[ ! -f "${MACRO}" ]]; then
  echo "Macro not found at ${MACRO}" >&2
  exit 1
fi

# Prefer user-provided FreeCAD command; default to headless FreeCADCmd for reliability
DEFAULT_FCCMD="/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd"
FREECAD_CMD="${FREECAD_CMD:-$DEFAULT_FCCMD}"

echo "Running FreeCAD macro with LUMBER_FORCE_NEW_DOC=1 ..."
# Default to a timestamped FCStd so runs don't clobber each other; override with OUT_PATH if desired.
TIMESTAMP="$(date +"%Y%m%d-%H%M%S")"
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/FreeCAD/builds}"
mkdir -p "${BUILD_DIR}"
OUT_PATH="${OUT_PATH:-${BUILD_DIR}/House_16x24_from_modules.${TIMESTAMP}.fcstd}"
echo "Output will be saved to ${OUT_PATH}"
echo "Using FreeCAD at: ${FREECAD_CMD}"
echo "Executing build macro headless ..."
FREECAD_LOAD_3DCONNEXION=0 \
  LUMBER_RUN_BOM=1 \
  LUMBER_FORCE_NEW_DOC=1 \
  LUMBER_SAVE_FCSTD="${OUT_PATH}" \
  QT_QPA_PLATFORM=offscreen \
  "${FREECAD_CMD}" -c "${MACRO}" <<'EOF'
exit()
EOF

if [[ "${NO_OPEN:-1}" != "1" ]]; then
  echo "Closing existing FreeCAD documents and opening ${OUT_PATH} ..."
  /usr/bin/osascript <<OSA >/dev/null 2>&1
tell application "System Events"
  set fcRunning to (name of processes) contains "FreeCAD"
end tell
if fcRunning then
  tell application "FreeCAD"
    try
      repeat with d in (documents as list)
        close d saving no
      end repeat
    end try
    open POSIX file "${OUT_PATH}"
    activate
  end tell
else
  tell application "FreeCAD"
    open POSIX file "${OUT_PATH}"
    activate
  end tell
end if
OSA
else
  echo "NO_OPEN=1 set; skipping GUI open."
fi
