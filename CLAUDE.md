# alien-simon-says

NeoPixel Simon-says game on an Arduino Uno R3. Read `../AGENTS.md` (shared rules, graphify second-brain) and `README.md` (authoritative wiring, power gates, full command list) before substantial work. Not a git repo.

## Hardware / firmware summary
- Four 6-pixel WS2812B strips on D2/D3/D4/D12 (Adafruit NeoPixel 1.15.5).
- DFPlayer (MP3-TF-16P) via SoftwareSerial D10(RX)/D11(TX); Timer1 servo PWM on D9. **Timer1 is reserved for the servo: never `analogWrite` D9/D10.**
- Grove JHD1804 LCD over I2C. Wokwi custom chips in `chips/`.
- Core arduino:avr@1.8.8, DFRobotDFPlayerMini@1.0.6, SIMON@0.1.5, Entropy (pinned git commit).

## Map
- `alien-simon-says/alien-simon-says.ino` — the sketch (nested folder) plus firmware-local headers.
- Root-level `*.h` — host-test copies; **must stay byte-synchronized with the firmware-local copies** in `alien-simon-says/alien-simon-says/`.
- `game_settings.h` — the one file for tuning the game.
- EEPROM layout: `game_count_store.h` bytes 12-15; `score_stats_store.h` 16-47; `first_color_journal.h` from 48. Don't overlap.
- Other headers: `game_sequence.h`, `button_mapping.h`, `servo_celebration_config.h`, `audio_track_config.h`, `motor_*`, `player_led_feedback.h`.
- `diagram.json` (Wokwi) mirrors `../alien-simon-says-build/diagram.json`; keep both in sync.
- `tests/` Python + C host tests; `scripts/build-arduino.sh`, `scripts/run-wokwi-tests.py`; `sdcard/card-mp3/` tracks 1-7 (`sdcard/mp3/` older); `SHA256SUMS`; `wokwi.toml`.
- Siblings `lcd-only-test/`, `led-button-test/`, `red-strip-button-test/` are standalone; pick the right dir before editing. `../alien-simon-says-irl/` and `../alien-simon-says-sound-test/` are different projects.

## Commands (run from this dir)
- Tests: `python -m pytest tests -q` (62 tests expected passing)
- Checksums: `sha256sum -c SHA256SUMS`
- Build: `bash scripts/build-arduino.sh`
- Lint diagram: `wokwi-cli lint --warnings-as-errors .`
- Chip: `wokwi-cli chip compile --output chips/<name>.chip.wasm chips/<name>.chip.c`
- C host tests: see README `gcc -std=c99 ... tests/test_*.c` list (output into `build/`).
- Wokwi scenarios: `python3 scripts/run-wokwi-tests.py --scenario all` (needs `WOKWI_CLI_TOKEN`).

## Conventions
- After changing supported code, refresh the graph per `../AGENTS.md` (`GRAPHIFY_OUT=../second-brain/graphify-out graphify update .`). Never create another `graphify-out`.
- Diagram wire colors: red=5V/positive, black=GND/SPK2, white=buttons, orange=UART/servo PWM, blue=SDA, yellow=SCL, purple=motor control, gray=SPK1. **Strip wires (DIN/VDD/VSS) keep the user's reported physical jumper colors** (tests + README pin them).
- Diagram endpoints are pinned by tests (`test_diagram_breadboard_nets.py`, `test_diagram_led_button_layout.py`); recolor only, don't rewire.
- Changing the diagram's wire count means updating README (line ~33 counts).

## Security / safety
- Secrets only in `.env` (git-ignored); never echo `WOKWI_CLI_TOKEN` or read `.env` aloud.
- No power-up approval exists. Follow README physical-power gates before energizing; simulations/notes don't prove hardware state.
- bb2 rail routing for strip/servo loads is scoped to this project only; its rating is unverified. Verify board/rail rating and combined current before powering. Never generalize to the irl or sound-test variants.

## Lab notes — what not to do
- Don't "standardize" NeoPixel strip wire colors in diagram.json (and ../alien-simon-says-build/diagram.json): tests and README pin them to the user's reported physical jumper colors. Recolor other signals only; check tests/README for pinned colors first.
