#!/usr/bin/env bash
# Wrapper: choose lumber house build (default) or beach lot build (BEACH_LOT=1 or BUILD_TARGET=beach).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TARGET="${BUILD_TARGET:-}"
if [[ "${BEACH_LOT:-0}" == "1" || "${TARGET}" == "beach" ]]; then
  exec "${SCRIPT_DIR}/BeachHouse/run_beach_house.sh" "$@"
else
  exec "${SCRIPT_DIR}/lumber/run_build_house.sh" "$@"
fi
