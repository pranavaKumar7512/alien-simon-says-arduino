#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARDUINO_CLI="${ARDUINO_CLI:-arduino-cli}"
STAGING_ROOT="$(mktemp -d)"
trap 'rm -rf "$STAGING_ROOT"' EXIT

# Arduino CLI requires the sketch directory and its primary .ino file to share
# a basename. Stage only the firmware and its local headers under that name so
# this project can keep its descriptive parent-folder name.
SKETCH_DIR="$STAGING_ROOT/alien-simon-says"
mkdir -p "$SKETCH_DIR" "$ROOT/build/physical" "$ROOT/build/wokwi"
cp "$ROOT/alien-simon-says.ino" "$ROOT"/*.h "$SKETCH_DIR/"

"$ARDUINO_CLI" compile \
  --fqbn arduino:avr:uno \
  --output-dir "$ROOT/build/physical" \
  "$SKETCH_DIR"

WOKWI_CPPFLAGS="-DWOKWI_SIM"
if [[ -n "${WOKWI_INITIAL_SEED:-}" ]]; then
  if [[ ! "$WOKWI_INITIAL_SEED" =~ ^[0-9]+$ ]]; then
    echo "WOKWI_INITIAL_SEED must be a decimal integer" >&2
    exit 2
  fi
  WOKWI_CPPFLAGS+=" -DWOKWI_INITIAL_SEED=${WOKWI_INITIAL_SEED}UL"
fi
if [[ -n "${WOKWI_PREVIOUS_FIRST_COLOR:-}" ]]; then
  if [[ ! "$WOKWI_PREVIOUS_FIRST_COLOR" =~ ^([0-3]|255)$ ]]; then
    echo "WOKWI_PREVIOUS_FIRST_COLOR must be 0..3 or 255 (none)" >&2
    exit 2
  fi
  WOKWI_CPPFLAGS+=" -DWOKWI_PREVIOUS_FIRST_COLOR=${WOKWI_PREVIOUS_FIRST_COLOR}"
fi

"$ARDUINO_CLI" compile \
  --fqbn arduino:avr:uno \
  --build-property "compiler.cpp.extra_flags=$WOKWI_CPPFLAGS" \
  --output-dir "$ROOT/build/wokwi" \
  "$SKETCH_DIR"
