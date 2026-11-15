#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARDUINO_CLI="${ARDUINO_CLI:-arduino-cli}"
STAGING_ROOT="$(mktemp -d)"
trap 'rm -rf "$STAGING_ROOT"' EXIT

# Arduino CLI requires the sketch directory and its primary .ino file to share
# a basename. Stage the nested firmware sketch and its local headers under that
# name so the surrounding project can keep its descriptive folder layout.
FIRMWARE_ROOT="$ROOT/alien-simon-says"
SKETCH_DIR="$STAGING_ROOT/alien-simon-says"
mkdir -p "$SKETCH_DIR" "$ROOT/build/physical" "$ROOT/build/wokwi"
cp "$FIRMWARE_ROOT/alien-simon-says.ino" "$FIRMWARE_ROOT"/*.h "$SKETCH_DIR/"

"$ARDUINO_CLI" compile \
  --fqbn arduino:avr:uno \
  --output-dir "$ROOT/build/physical" \
  "$SKETCH_DIR"

WOKWI_BUILD_SEED="${WOKWI_INITIAL_SEED:-}"
if [[ -z "$WOKWI_BUILD_SEED" ]]; then
  WOKWI_BUILD_SEED="$(python3 -c 'import secrets; print(secrets.randbelow(0xFFFFFFFF) + 1)')"
else
  if [[ ! "$WOKWI_BUILD_SEED" =~ ^[0-9]+$ ]] ||
     ! python3 -c 'import sys; n=int(sys.argv[1]); sys.exit(0 if 1 <= n <= 0xFFFFFFFF else 1)' "$WOKWI_BUILD_SEED"; then
    echo "WOKWI_INITIAL_SEED must be an integer from 1 to 4294967295" >&2
    exit 2
  fi
fi
printf 'Wokwi build seed: %s\n' "$WOKWI_BUILD_SEED"
WOKWI_CPPFLAGS="-DWOKWI_SIM -DWOKWI_INITIAL_SEED=${WOKWI_BUILD_SEED}UL"
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
