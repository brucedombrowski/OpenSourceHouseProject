#!/usr/bin/env bash
# Build the 950 Surf beach house model
# Usage: cd 950_Surf && ./build.sh

set -euo pipefail

# Get the directory where this script lives
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESIGN_HOUSE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Set config path and build directory
export BEACH_CONFIG="${SCRIPT_DIR}/config.py"
export BUILD_DIR="${SCRIPT_DIR}/builds"

# Call the parent design_house.sh script
cd "${DESIGN_HOUSE_DIR}"
exec ./design_house.sh
