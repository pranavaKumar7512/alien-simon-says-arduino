# Alien Simon Says — Arduino Uno R3

A complete Simon Says sketch for the confirmed **Arduino Uno R3**, with four generic play buttons and four independently driven **six-pixel** NeoPixel strips—red on D2, green on D3, blue on D4, and yellow on D12, with no DOUT chaining. The game also has a separate Start button, the Seeed Grove 16x2 LCD Black-on-Yellow V2.0 / JHD1804M1 display, an MP3-TF-16P physical audio backend, an FS5106B positional servo, and a Wokwi DFPlayer protocol mock. The physical strips are reported by the user as 3-pin, 5 V addressable WS2812B/NeoPixel-style parts with GND, DIN/DO, and 5 V pads. The user currently confirms a yellow-colored physical data jumper from Uno D12 to yellow DIN; this is not independently observed or continuity-tested.

> **Diagram and physical-build status:** at the user's request, this project's `diagram.json` now matches the separate `../alien-simon-says-build/diagram.json` build canvas. It models direct D2/D3/D4/D12 data links and the user-reported strip/servo rail routing through the breadboard. This is a Wokwi topology record, not independent confirmation of physical connections, pad labels, continuity, ratings, current, or rendered clearance. The user reports that the first breadboard rails were verified for the combined strip-plus-servo load; the exact board model, continuous-current rating, wiring, and aggregate draw remain unverified here. This report is not a safety certification or approval to energize.

> **Power and signal safety gates remain closed:** keep Uno USB and every external source disconnected during wiring and inspection. Never connect the external supply's +5 V to Uno 5V or the Uno barrel jack; keep the external positive path separate, establish only the required common ground/signal reference, and check signal-powered/backfeed paths and the actual power-up/shutdown sequence. Verify exact strip pad labels, signal compatibility/interface, wiring, protection, board/rail ratings, combined strip-plus-servo current, servo supply/signaling, and every other gate in [Power and physical limits](#power-and-physical-limits) before any physical energization. The reports above do not authorize power-up.

> **Single supply (user-directed, supersedes the "never connect external +5 V to Uno 5V" wording below):** the barrel breakout's 5V now has two wires: one to the `bp` rail (strips, servo, motor driver) and one directly to the Uno `5V` pin (which feeds LCD and DFPlayer via `tp`). Breakout GND stays common with Uno GND via `tn`. Never connect Uno USB or the Uno barrel/VIN while the supply feeds the 5V pin (back-feed). Feeding the 5V pin bypasses the Uno regulator/fuse, so the supply must be regulated 5 V and fused/current-limited and sized for Uno + LCD + DFPlayer + servo + motor + strips. The user reports the breadboard is rated for the load; that is unverified. All other gates below remain open.

## Project contents

- `alien-simon-says/alien-simon-says.ino` — nonblocking gameplay/state machine; both builds send DFRobotDFPlayerMini frames over SoftwareSerial D10/D11, drive four independent six-pixel strips from D2, D3, D4, and D12 with four Adafruit_NeoPixel objects, and drive the servo from Timer1 hardware PWM on D9/OC1A.
- `alien-simon-says/game_settings.h` — the one file to edit to tune the game: motor power and timing, player LED brightness, servo travel and timing, MP3 volume, and cue/Game Over/score-page timing. See "Changing game settings" below. Pins, wiring, EEPROM layout, track numbers and LCD text are deliberately not exposed.
- `alien-simon-says/*.h` — firmware-local headers staged with the sketch. Matching root-level header copies are used by the host C tests and must stay synchronized.
- `scripts/build-arduino.sh` — stages the nested sketch and its adjacent headers under Arduino CLI's required matching basename and builds physical and Wokwi firmware into the configured output folders.
- `scripts/run-wokwi-tests.py` — builds test firmware from the nested sketch and generates randomized, seed-replayable Wokwi scenarios with local previous-first-color metadata.
- `game_count_store.h` — persistent, saturating 32-bit total-games counter in EEPROM bytes 12–15; erased EEPROM reads as zero.
- `score_stats_store.h` — two-copy CRC/commit-checked aggregate score samples in EEPROM bytes 16–47.
- `first_color_journal.h` — CRC/commit-checked, wear-levelled Uno EEPROM ring for the previous game's first color, starting at byte 48.
- `game_sequence.h` — a constant-memory, seed-replayable pseudo-random stream that samples each cue with replacement from all four colors.
- `button_mapping.h` — a separately seeded one-to-one mapping from left-to-right button positions to cue colors, shuffled after every three successfully completed rounds.
- Rob Tillaart's SIMON library verifies player answers in bounded chunks of up to ten symbols; the game sequence itself streams beyond that chunk size.
- Physical seeds come from the AVR Arduino Entropy library's watchdog/Timer1 timing jitter; Wokwi uses host-injected replay seeds.
- `servo_celebration_config.h` — shared Game Over servo angle/timing settings and Timer1 pulse conversion for physical and Wokwi builds.
- `audio_track_config.h` — shared cue-track range plus dedicated celebration and player-loss track selection.
- `sdcard/card-mp3/` — the seven audio files as they are on the physical SD card (`/mp3/`), named `0001-button1.mp3`–`0004-button4.mp3`, `0005-spare.mp3`, `0006-celebration.mp3` and `0007-losing.mp3`. The firmware plays them by track number with `playMp3Folder(n)`, which matches the leading four digits, so the label after the digits is free text. Hashes are in `SHA256SUMS`.
- `sdcard/mp3/0001.mp3`–`0005.mp3` — older repository audio files, different recordings from the card, kept unchanged (tracks 1–4 are color cues; track 5 is retained but unused by full-game events). Full-game celebration/loss request user-provided physical tracks 6/7; the user reports these are already at `D:/mp3`, but their contents were not accessed or verified here.
- `assets/source-sound-alien1-hq.mp3` — retained, attributed alien source sample; it is not used by the generated cues.
- `SHA256SUMS` — verified SHA-256 hashes for the five repository MP3 assets and retained source sample.
- `chips/grove-jhd1804.chip.c` / `.chip.json` — local I2C/framebuffer model for the specified Grove/JHD1804 LCD, not a substitute display.
- `chips/dfplayer-mock.chip.c` / `.chip.json` — UART protocol mock for volume, tracks 1–7, stop, and simulated finish events; its default 2,000 ms delay approximates tracks 6/7 while it still does not decode or play MP3 files.
- `chips/visual-speaker.chip.c` / `.chip.json` — separate two-terminal component named `8 Ω / 0.5 W — no playback`; it is a visual pinout only.
- `chips/barrel-jack-breakout.chip.c` / `.chip.json` — visual-only female DC barrel-jack-to-2-screw-terminal breakout marker, matching the form shown in the user's photo; its pins do not implement electrical pass-through.
- `diagram.json`, `wokwi.toml` — the Wokwi canvas now matches the separate build variant's one-board layout: 17 parts, 63 connection entries (43 colored wires plus 20 `$bb` component-lead placements), four six-pixel strips, direct data pins D2/D3/D4/D12, and separate modeled Uno-logic and external-load breadboard rails. Strip DOUT and secondary power pins are open. This logical canvas reflects user-reported routing only; it does not verify physical connections, rail continuity/rating, current, safety, or rendered clearance.

## Build and run

Host-tool prerequisites: install [Arduino CLI](https://docs.arduino.cc/arduino-cli/installation/) for firmware builds; [Wokwi CLI](https://docs.wokwi.com/wokwi-ci/cli-installation) is needed for diagram lint, custom-chip builds, and runtime scenarios. The validation commands below also assume Bash, GCC (`gcc`), Python 3.8 or newer, and `sha256sum` are on `PATH` (for example, Git Bash plus a GCC toolchain). Runtime scenarios additionally require a valid `WOKWI_CLI_TOKEN`.

This project was built with Arduino CLI, Arduino AVR Boards 1.8.8, `DFRobotDFPlayerMini` 1.0.6, and `Adafruit NeoPixel` 1.15.5. Install any missing AVR core/libraries once after installing Arduino CLI:

```sh
arduino-cli core update-index
arduino-cli core install arduino:avr@1.8.8
arduino-cli lib install "DFRobotDFPlayerMini@1.0.6"
arduino-cli lib install "Adafruit NeoPixel@1.15.5"
arduino-cli lib install "SIMON@0.1.5"
ARDUINO_LIBRARY_ENABLE_UNSAFE_INSTALL=true arduino-cli lib install --git-url https://github.com/pmjdebruijn/Arduino-Entropy-Library.git#401537e3d6c413b7812e0aa3323d25b1b754938a
```

The sketch has no Servo-library build dependency: D9/OC1A uses Timer1 Fast PWM mode 14 with a 16 MHz clock, prescaler 8, `ICR1=39999` (20 ms frame), and `OCR1A` pulse widths in 0.5 µs ticks. This hardware PWM continues without interrupt servicing, avoiding SoftwareSerial's interrupt blocking stretching servo pulses. Servo targets map 0° to 700 µs, 90° to 1500 µs, and 180° to 2300 µs with no trim offset. Timer1 is reserved for this servo output; do not use `analogWrite()` on D9/D10 or another library/configuration that takes over Timer1. Both firmware builds use the existing DFRobot library and SoftwareSerial; the Wokwi diagram connects those same serial pins to the custom UART mock. The sketch does not require installing the Grove library: it sends the documented Grove LCD command/data protocol over `Wire` directly.

From this folder (Git Bash on the development machine):

```sh
sha256sum -c SHA256SUMS
bash scripts/build-arduino.sh
wokwi-cli chip compile --output chips/grove-jhd1804.chip.wasm chips/grove-jhd1804.chip.c
wokwi-cli chip compile --output chips/dfplayer-mock.chip.wasm chips/dfplayer-mock.chip.c
wokwi-cli chip compile --output chips/visual-speaker.chip.wasm chips/visual-speaker.chip.c
wokwi-cli chip compile --output chips/barrel-jack-breakout.chip.wasm chips/barrel-jack-breakout.chip.c
wokwi-cli chip compile --output chips/mdd3a-board-visual.chip.wasm chips/mdd3a-board-visual.chip.c
wokwi-cli chip compile --output chips/fit0458-motor-visual.chip.wasm chips/fit0458-motor-visual.chip.c
wokwi-cli lint --warnings-as-errors .
gcc -std=c99 -Wno-attributes tests/test_grove_jhd1804.c -o build/test_grove_jhd1804 && build/test_grove_jhd1804
gcc -std=c99 -Wno-attributes tests/test_dfplayer_mock.c -o build/test_dfplayer_mock && build/test_dfplayer_mock
gcc -std=c99 tests/test_audio_completion_filter.c -o build/test_audio_completion_filter && build/test_audio_completion_filter
gcc -std=c99 tests/test_game_over_audio_config.c -o build/test_game_over_audio_config && build/test_game_over_audio_config
gcc -std=c99 tests/test_player_led_feedback.c -o build/test_player_led_feedback && build/test_player_led_feedback
gcc -std=c99 -Wall -Wextra -Werror tests/test_motor_loss_reaction.c -o build/test_motor_loss_reaction && build/test_motor_loss_reaction
gcc -std=c99 -Wall -Wextra -Werror tests/test_motor_drive_config.c -o build/test_motor_drive_config && build/test_motor_drive_config
gcc -std=c99 tests/test_first_color_journal.c -o build/test_first_color_journal && build/test_first_color_journal
gcc -std=c99 -Wall -Wextra -Werror tests/test_game_count_store.c -o build/test_game_count_store && build/test_game_count_store
gcc -std=c99 -Wall -Wextra -Werror tests/test_score_stats_store.c -o build/test_score_stats_store && build/test_score_stats_store
gcc -std=c99 tests/test_game_sequence.c -o build/test_game_sequence && build/test_game_sequence
gcc -std=c99 -Wall -Wextra -Werror tests/test_button_mapping.c -o build/test_button_mapping && build/test_button_mapping
gcc -std=c99 tests/test_servo_celebration_config.c -o build/test_servo_celebration_config_physical && build/test_servo_celebration_config_physical
gcc -std=c99 -DWOKWI_SIM tests/test_servo_celebration_config.c -o build/test_servo_celebration_config_wokwi && build/test_servo_celebration_config_wokwi
python3 tests/test_game_count_integration.py
python3 tests/test_score_stats_integration.py
python3 tests/test_active_score_lcd_integration.py
python3 tests/test_diagram_led_button_layout.py
python3 tests/test_diagram_breadboard_nets.py
python3 tests/test_wokwi_test_runner.py
python3 tests/test_game_settings.py
python3 tests/test_card_track_files.py
python3 scripts/run-wokwi-tests.py --scenario all
```

The first build is the physical Uno firmware. The second is the default Wokwi build; unless overridden, it injects a new nonzero host-generated seed at each build and prints it. Re-running the same firmware image intentionally repeats its sequence; use `WOKWI_INITIAL_SEED=<seed> bash scripts/build-arduino.sh` to rebuild a replayable image. Randomized automation recompiles a Wokwi image with a per-run logged seed; it also passes prior-first-color metadata, which does not affect cue selection. The mock checks the 10-byte DFRobot frame/header/checksum, handles volume/play/stop, and schedules configurable completion events, but never reads the copied MP3 files or plays sound. The separate speaker has no playback behavior; no buzzer or `tone()` backend is used. Host tests cover protocol parsing, checksums, completion cancellation, the LCD model, four independent strips with grouped 24-pixel NeoPixel feedback, map-preserving 500 ms input flashes, and simultaneous position-map rendering, first-color journal integrity/wear-leveling, game-count initialization/persistence/saturation and isolation, score-stats aggregation/CRC/torn-write recovery/saturation, sequence selection, seeded position-to-color mapping, loss-gated servo targets, and exact breadboard diagram nets. `python3 scripts/run-wokwi-tests.py --scenario all` generates randomized matching button scenarios, prints replay commands, stores the Wokwi previous-first-color state in `.wokwi-sequence-state.json`, and saves transcripts/manifests under `build/wokwi-tests/`. Use `--scenario first-round` for one test or `--scenario button-remap` to exercise the 2.75-second initial identity-map preview, post-sequence color maps, 500 ms pressed-color dark flashes, the round-4 shuffle and preview, and successful answers through round 4. This scenario plans runtime coverage; actual LED/LCD rendering still needs runtime or hardware observation. To reproduce a run, use the printed seed and previous-color arguments with `--no-persist`. Runtime scenarios require a valid `WOKWI_CLI_TOKEN`; Wokwi's monthly CI-minute quota can also block them. Wokwi simulation does **not** validate physical NeoPixel current/power, actual DFPlayer playback, speaker output/current, external servo power/travel/load, or the real LCD hardware. Official interface references: [Wokwi Custom Chip UART API](https://docs.wokwi.com/chips-api/uart), [custom chip JSON](https://docs.wokwi.com/chips-api/chip-definition), [automation scenarios](https://docs.wokwi.com/wokwi-ci/automation-scenarios), [Wokwi CLI usage/token requirement](https://docs.wokwi.com/wokwi-ci/cli-usage), and [Wokwi LED strip part](https://docs.wokwi.com/parts/wokwi-led-strip).

#### Uno SRAM notes for the six-pixel game

The current clean Uno builds report 1,075 bytes of static global memory (of 2,048 bytes) for physical firmware and 974 bytes for `WOKWI_SIM`. Adafruit NeoPixel 1.15.5 allocates each RGB strip's pixel buffer with `malloc()` from `updateLength()` during object construction: six pixels x three bytes x four strips = 72 bytes of dynamic heap payload (24 bytes more than the former four-pixel groups). `begin()` configures the pins; it does not allocate these buffers. Subtracting only that payload leaves nominal upper bounds of 901 bytes physical and 1,002 bytes Wokwi for allocator bookkeeping, any other allocations, and stack; these are not measured runtime stack margins or proof of safe heap/stack separation. The Uno SRAM budget is therefore tighter than the CLI static-global line alone suggests.

### Wokwi audio model

The Uno's D11 SoftwareSerial TX reaches the custom DFPlayer mock RX (through the diagram's 1 kΩ signal resistor), and mock TX returns to Uno D10 SoftwareSerial RX. The mock parses the real DFRobot 9600-baud command frames, accepts volume/play/stop, and sends a checksummed `0x3D` finish event after the configured simulation delay. Stop cancels pending completion. It has no SD-card audio decoder and emits no sound. The separate two-terminal part is named exactly `8 Ω / 0.5 W — no playback`; it is wired only across mock `SPK1`/`SPK2`, never to Uno GPIO or GND.

The LCD and DFPlayer mock use the Uno logic rails in Wokwi; the strips and servo use separately modeled external-load rails. `diagram.json` matches the sibling build canvas, but neither diagram nor the user's report independently verifies physical continuity, board/rail ratings, aggregate current, branch installation, or approval to energize. Keep external positive isolated from Uno 5V/barrel and USB, establish only the intended common ground, verify strip/servo signal backfeed and power sequencing, and keep all sources off until all gates close.

### Randomized Wokwi automation

Run the generated scenarios with a valid `WOKWI_CLI_TOKEN`:
```sh
python3 scripts/run-wokwi-tests.py --scenario all
# Or run one scenario:
python3 scripts/run-wokwi-tests.py --scenario first-round
```

By default, each randomized test launch gets a nonzero seed from the host OS random source; the runner logs the seed plus prior-color metadata. The runner generates each scenario cue/button from the same xorshift32 sequence as firmware, so randomized colors do not break correct-answer tests. `first-round` checks that early audio completion does not shorten the 2 s light and that the player can wait 5.2 s before pressing and hold the debounced answer for 5.2 s before release; `chunk-boundary` uses a Wokwi-only test build to start at round 11, enter all eleven cues, and verify a correct answer across the SIMON ten-symbol chunk boundary. The other scenarios use a longer mock completion delay to verify Game Over event draining, successful rounds without servo extension, and loss-triggered servo motion. The runner checks cue-on/off/Stop/gap timestamps and input/event ordering, stores per-run YAML/diagram/transcript/manifests under `build/wokwi-tests/`, and builds scenario firmware separately under `build/wokwi-tests/firmware/<scenario>-<seed>-prev-<color|none>` (selected with `--elf`) so test images never replace the interactive `build/wokwi` firmware. Cross-launch Wokwi previous-color state lives in the local `.wokwi-sequence-state.json`; running `wokwi-cli` directly bypasses this persistence wrapper. Use the printed replay command, which uses the script's absolute path, to reproduce a failure. A Wokwi CI-minute quota error can prevent runtime verification; only a successful scenario completion counts as runtime evidence.

### SIMON library and uncapped rounds

Both builds use Rob Tillaart's [SIMON library 0.1.5](https://github.com/RobTillaart/SIMON) for answer storage and verification. Its default `SIMON_MAXSIZE` is ten, so the sketch uses one library object as a rolling verifier: it loads at most ten expected symbols, calls `add()` for each released button, and calls `verify()` against the submitted prefix. After ten inputs, it clears the answer buffer and loads the next chunk. The full game sequence is not stored in SIMON's fixed array; `game_sequence.h` regenerates it from a small stream state, so round length is not capped at ten.

Physical sequence seeds are collected from the AVR Arduino Entropy library's watchdog/Timer1 timing jitter when Start is pressed. The sketch waits up to 1.2 seconds for one 32-bit pool value and then disables the watchdog to avoid gameplay-time ISR interference with SoftwareSerial. If acquisition times out, it displays `RANDOM NOT READY`; no extra RNG module is needed. This jitter-derived source is not certified or cryptographic, and it has not been measured on the physical Uno. The library's `generateSequence()` method is intentionally not used for the whole game: it produces at most ten symbols and reseeds from `micros()`. The sketch instead streams its own sequence and uses SIMON only for bounded answer verification.

Both physical and Wokwi builds use the same with-replacement pseudo-random sequence. The bounded mapper rejects the top three xorshift32 states before modulo mapping. Although the accepted first-draw values divide evenly among four colors, xorshift32 cycles only its nonzero states and a rejection advances the same deterministic stream; a one-state-scale seed-space skew remains, so strict IID or exact 25.000...% probability is not claimed. Repeats are allowed; neither a four-color bag nor the EEPROM first-color journal constrains a draw. The journal still records each game's first cue. Physical games use the entropy-library seed; Wokwi uses logged host-injected seeds. Ordinary Wokwi builds get a fresh host seed at build time, while test runs inject explicit replayable seeds. The SIMON library handles answer checking only; LEDs, buttons, round progression, audio, scoring, LCD, and servo behavior remain in the sketch.

### Simulation/physical behavior

- Start begins a game while idle. During an active run, a fresh debounced Start press immediately abandons the run and starts a new round 1 with a new sequence; the current score resets, while best score and EEPROM journal remain. During Game Over, Start queues a restart until the audio minimum and servo return allowance finish, so it cannot interrupt servo retraction. Release Start before requesting another reset.
- Both builds stream with-replacement pseudo-random cues; every color remains eligible on each draw, and repeats are permitted. Prior-color metadata and the EEPROM journal never constrain a choice. Physical starts use the Entropy library seed; Wokwi uses the host seed. SIMON checks answers in chunks of up to ten symbols, allowing the game sequence to continue beyond the library's fixed capacity. The first cue is still stored in the wear-levelled, CRC/commit-checked EEPROM journal. Wokwi's previous-first-color metadata is still stored by the CLI wrapper in `.wokwi-sequence-state.json` and logged for replay/debugging, but does not affect cue generation. Direct Wokwi CLI launches do not update that file.
- Four independent NeoPixel strips contain twenty-four addressable LEDs total: indices 0–5 are red, 6–11 green, 12–17 blue, and 18–23 yellow. During cue playback, only the mapped six-pixel group for the current cue lights; every group is off between cues. After the last cue, all four button-position groups illuminate in their current mapped colors and stay on while the player answers. Sequence cues stay lit for 2,000 ms from cue-on; an early natural audio-finished event does not shorten the light. At that deadline the firmware issues an idempotent DFPlayer Stop request to bound playback (harmless if the track already completed), then all strips remain off for the existing 180 ms gap. The physical module's exact Stop latency is not validated. In Wokwi, matching track numbers go to the DFPlayer mock; the mock has no MP3 decoder and plays no sound. On a debounced play-button press, only that color's mapped six-pixel group turns off for 500 ms while the other three groups remain lit; then the complete map is restored. The answer is still committed and checked only after button release, so a held button can remain down after the 500 ms flash. The 25 ms debounce, chord detection, and release-to-submit behavior remain. Players may wait indefinitely before answering and may hold a debounced answer indefinitely before releasing it. Held buttons during cue playback do not create button feedback; after the cues, the full map remains visible while the firmware waits for all buttons to be released. Two or more simultaneously debounced play buttons fail the run.
- The four controls are identified by physical position from left to right as Buttons 1–4; their casing colors have no gameplay meaning. The initial map is Button 1→Red, 2→Green, 3→Blue, 4→Yellow. After each three successfully completed rounds (3→4, 6→7, 9→10, …), a seed-derived shuffle creates a new one-to-one map for the next block; the cue sequence is unchanged. Each cue lights only its mapped group, all groups go dark between cues, and all four mapped colors are shown after the sequence. A pressed color's group then goes dark for 500 ms before the full map is restored. Repeating the exact previous full map is rejected, though individual assignments may repeat. A new game or restart restores the initial map and shows all four button-position LED groups simultaneously in their assigned cue colors for 2.75 seconds before Round 1, giving the player time to learn the button/color relationship. After each later remap, the celebration audio finishes first, then the same 2.75-second full-map preview appears before the next round. During an active game the LCD continuously shows `SCORE:<10-digit zero-padded completed-round count>` on row 1 and `BEST:<10-digit zero-padded best score>` on row 2, including the initial mapping preview, cue playback, answer waits, and round celebrations; it does not display the round number, session count, or button mapping. Idle cycles only the `YOUR` and `BEST` score pages; Game Over/error screens may use their own messages. The separate mapping PRNG does not affect cue generation, and the Wokwi `button-remap` scenario verifies replayable maps and translated inputs. A wrong answer, chord, or the 32-bit technical round counter reaching its maximum ends the run.
- EEPROM statistics keep the best score in bytes 0–11 and count lifetime game sessions in bytes 12–15; a session is counted only after seed acquisition succeeds. The saturating session counter is not wear-levelled, and interruption during its multi-byte update can corrupt it. Bytes 16–47 now hold a two-copy, CRC/commit-checked score summary (sample count plus exact score sum); the alternating copies protect against a torn update but are not full wear-leveling. Byte 48 onward holds the wear-levelled first-color journal with 122 slots. Repurposing bytes 16–47 makes the four overlapped older journal slots unavailable; that history never constrains cue selection. The score average is derived from score samples recorded after this firmware update, so old scores cannot be included. A Game Over and a manual restart each record the run's completed-round score once; a power cut mid-game still counts as a started session but cannot save an ending score. Players see only the `YOUR` and `BEST` idle pages; the session count is hidden from the LCD. To retrieve the requested summary, connect USB, open Serial Monitor at 115200 baud with a newline ending, and send `STATS`; the board prints only best rounds and average rounds in a CSV header and row (`N/A` before the first score sample). The lifetime session count remains stored in EEPROM but is omitted from this report and the player LCD. EEPROM power-cycle and serial-report behavior still need physical verification.
- Game Over after a player loss plays physical track 7 (`/mp3/0007.mp3`) or sends mock track command 7. Other Game Over exits (the technical round-counter safeguard) retain random tracks 1–4. The screen remains visible for at least three seconds and, after a player loss, until the servo's configured return allowance has elapsed; the firmware then sends Stop before returning to score pages. This is three seconds on the physical configuration and six seconds in Wokwi. Technical counter exhaustion ends the game without servo motion because it is not a player loss. Completion events are drained throughout Game Over.
- Successful rounds 3, 6, 9, … play the dedicated physical/mock track 6 (`/mp3/0006.mp3`) and block the next round until completion or the existing 2.5-second fail-closed timeout; they do not move the servo. Track 6's reported duration (~1.714 s) is within that bound. The servo extends only after a player loses through a wrong answer or chord, then returns to 0°. In Wokwi, its target changes to 180° for a 3-second hold, then to 0° for a separate 3-second return allowance. Physical builds retain the conservative, unverified settings of 90° extend, 0° retract, a 1-second hold, and a 1-second return allowance until the real FS5106B linkage endpoints are verified. These are command-based intervals that include travel time; neither simulation nor elapsed time provides position feedback. Do not widen physical settings until the actual mechanism/load and safe travel are assessed.
- There is no practical round cap. The firmware stops only if its 32-bit completed-round counter reaches `UINT32_MAX`, a technical overflow safeguard rather than a gameplay limit. SIMON's ten-symbol array is reused as a verifier buffer and does not limit the game sequence.
- Full-game NeoPixel software brightness is 255/255 (maximum), above the standalone all-components test's 32/255 setting. This is only a software setting—not a current limit or safety rating. Keep physical power disconnected until the strip-plus-servo current and every other power gate are verified.

## Changing game settings

Edit `alien-simon-says/alien-simon-says/game_settings.h`, save it, then compile and upload the sketch again. The Uno cannot read the file while running, so nothing changes until you re-upload. Every value has a comment with its unit and allowed range, and an out-of-range value stops the compile with an error instead of misbehaving. Settings cover the motor (start lead, ramp, max run, power), player LED brightness, servo extend angle and timing (real rig only), MP3 volume, and cue, Game Over and score-page timing.

The defaults equal the previous hard-coded behaviour. `tests/test_game_settings.py` checks that the defaults in `game_settings.h` match the headers' own defaults and that edits and range errors take effect. The Wokwi runner scenarios assume the default timings, so restore the defaults before running `scripts/run-wokwi-tests.py`. Motor power and run time share the 5 V supply with the strips and servo: raise them only after the physical gates below are met.

## Pin map — physical Uno R3

| Uno pin | Connection | Notes |
|---|---|---|
| D2 | Red strip DIN | Direct yellow Wokwi data link; the physical jumper's continuity is not independently verified |
| D3 | Green strip DIN | Direct yellow Wokwi data link; the physical jumper's continuity is not independently verified |
| D4 | Blue strip DIN | Direct yellow Wokwi data link; the physical jumper's continuity is not independently verified |
| D5 | MDD3A `M1A` signal input (PWM forward drive) | Motor feature; see Step 6 |

These are user-reported jumper connections; continuity and pad labels/orientation have not been independently measured.
| D6, D7, D8, A0 | Generic play controls, Buttons 1–4 from left to right | `INPUT_PULLUP`; position—not casing color—identifies each control; pressed input connects to GND |
| A1 | Separate two-terminal, normally-open Start button | `INPUT_PULLUP`; its other lead returns to GND when pressed |
| A4 / A5 | Grove LCD SDA / SCL | I²C address `0x3E`; do not swap data and clock |
| D9 | FS5106B signal | Routed through row 7 to the servo PWM pin in the matching main/build Wokwi canvases; actual supply/rail capacity and signal-off behavior remain unverified. |
| D10 | Uno SoftwareSerial RX ← MP3-TF-16P TX | No connection to Uno D0/D1 |
| D11 | Uno SoftwareSerial TX → 1 kΩ series resistor → MP3-TF-16P RX | Start at module volume 3 |
| D12 | Yellow strip DIN | Yellow Wokwi data link; user confirms a yellow-colored physical D12-to-yellow-DIN jumper, not independently continuity-tested |
| 5V / GND | Uno 5V/GND serve logic; the visual breakout routes external load positive/return through the separate `bp`/`tn` breadboard rails to servo and strips | The user reports those rails were professor-checked for the combined strip-plus-servo load, but exact board/rating, continuity, aggregate current, and installed branch state are not independently verified. The diagram is not power-up approval. Keep external +5 V isolated from Uno 5V/barrel and USB; verify common-ground, backfeed, and power sequencing before any authorized energization. |
| D0 / D1 | USB serial diagnostics | Reserved; keep free of MP3 wiring |
| A2 | MDD3A `M1B` signal input (held LOW) | Motor feature; digital only, no PWM |
| A3 | Unused | No random-number hardware is connected |

Timer1 is dedicated to the D9/OC1A servo signal. It generates 50 Hz Fast PWM using a 0.5 µs timer tick and a 39999 TOP; servo targets map 0°/90°/180° to 700/1500/2300 µs with no trim offset. The timer continues producing active pulses while the servo is parked—there is no detach operation. Timer1 also owns D10/OC1B's PWM timing, so do not use D9/D10 `analogWrite()` or code that reconfigures Timer1. This does not change the D10 SoftwareSerial RX / D11 TX audio map.

The firmware runs a 500 ms power-on self-test in `setup()` that lights all twenty-four pixels simultaneously in four mapped-color groups (0-5 red, 6-11 green, 12-17 blue, 18-23 yellow), then clears them and enters IDLE. Separately, each game start shows the initial button/color map for 2.75 seconds before Round 1. Sequence cues light only their mapped group and leave all groups dark between flashes; after the sequence, all four mapped colors stay lit, with the pressed color's group briefly dark for 500 ms on each button press. The user reports 5 V, 3-pin addressable WS2812B/NeoPixel-style strips, but exact model, pad labels/orientation, signal-interface requirements, and wiring are not independently inspected. The user reports first-breadboard rails verified for combined strip-plus-servo load; exact rating, actual current, branch state, and physical safety are not independently verified. Never power strips from Uno USB/5V. Verify data signal compatibility, common ground, no backfeed, and safe power sequencing before any separately authorized energization.

The game firmware requests MP3 files from `/mp3/` at the root of a FAT32 microSD/TF card:

```text
/mp3/0001.mp3
/mp3/0002.mp3
/mp3/0003.mp3
/mp3/0004.mp3
/mp3/0005.mp3  (existing file retained; unused by full-game events)
/mp3/0006.mp3  (completed-round celebration)
/mp3/0007.mp3  (player loss)
```

`0001`–`0004` map respectively to red, green, blue, and yellow; `0006` plays after each successfully completed third round, and `0007` plays after a player loss. Existing track 5 is left untouched and is not selected by the full game. The user reports tracks 6/7 already exist on `D:/mp3`; no SD/card files were accessed or changed for this mapping. The physical speaker connects across the module's **SPK1 and SPK2 speaker outputs** (one lead per output). Never connect a speaker terminal to an Uno GPIO or GND.

## Physical wiring — unpowered stages

Disconnect the Uno USB cable and every external supply while building or changing wiring. `diagram.json` now matches the build variant's breadboard routes; it remains a topology aid, not an independently verified physical wiring record. The user reports that the first breadboard rails were verified for the combined strip-plus-servo load, but that report does not independently verify the board model/rating, wiring, tie groups, split rails, or actual aggregate current. Keep all sources disconnected and verify markings, continuity, protection, and every power gate before use.

### Breadboard row and rail assignment

The copied Wokwi canvas uses a `wokwi-breadboard-half` with 30 numbered tie-point rows and four modeled rails. Its `tp`/`bn` rails serve Uno logic; `bp`/`tn` route the external load positive/return. Wokwi's tie-group/rail behavior is a model; physical boards may have split rails or different continuity. The user reports the first board rails were verified for the combined strip-plus-servo load, but exact model, current rating, actual load, and physical continuity are not independently verified. Never use a rail for load current without verifying the actual board/path ratings, and keep external positive off Uno power.

| Breadboard row/rail | Intended net and physical footprint | Connection |
|---|---|---|
| 1 | D11 to DFPlayer mock RX through the 1 kΩ resistor | D11 → `1t.a`; resistor pin 1 at `1t.b`, pin 2 at `1b.f`; `1b.g` → mock RX |
| 2 | Unused for LCD in this canvas | LCD SDA connects directly to Uno A4 |
| 3 | Unused for LCD in this canvas | LCD SCL connects directly to Uno A5 |
| 4 | Red button contact 2 | Row 4 bottom group returns to GND |
| 5 | DFPlayer mock TX to Uno D10 | Mock TX ↔ `5t.a`/`5t.b` ↔ Uno D10 |
| 6 | Red button contact 1 | GPIO D6 uses row 6 |
| 7 | Servo signal only | Uno D9 ↔ `7t.a`/`7t.b` ↔ visual servo PWM |
| 8 / 9, 14 / 15, 20 / 21, 26 / 27 | Former discrete-LED nodes | No NeoPixel data wire is assigned to these holes; actual physical occupancy is unknown, so do not reuse without checking the board |
| 10 | Green button contact 2 | Row 10 bottom group returns to GND |
| 11 | Unused in this canvas | Speaker terminals connect directly mock-to-visual speaker |
| 12 | Green button contact 1 | GPIO D7 uses row 12 |
| 13 | Unused in this canvas | Speaker terminals connect directly mock-to-visual speaker |
| 16 | Blue button contact 2 | Row 16 bottom group returns to GND |
| 18 | Blue button contact 1 | GPIO D8 uses row 18 |
| 19, 25 | Spare rows | No strip data wire is assigned here; physical occupancy is unknown, so inspect the board before use |
| 22 | Yellow button contact 2 | Row 22 bottom group returns to GND |
| 24 | Yellow button contact 1 | GPIO A0 uses row 24 |
| 28 | Start button GND-return lead | Wokwi `2.r` → `28b.f`; row 28 joins this diagram's GND-return chain |
| 30 | Start button A1 signal lead | Wokwi `1.l` → `30t.e`; GPIO A1 uses row 30 |
| Top positive rail (`tp`) | Uno logic +5 V in Wokwi | Uno 5V, LCD VCC, and mock VCC only; isolated from external load positive |
| Top negative rail (`bn`) | Uno logic GND in Wokwi | Uno GND.1, LCD/mock GND, and button-return chain |
| Bottom positive rail (`bp`) | External load positive in Wokwi | Breakout 5V to servo V+ and each strip VDD; never join to Uno 5V |
| Bottom negative rail (`tn`) | External load return in Wokwi | Breakout GND, servo GND, strip VSS, and Uno GND.2 as the intended common signal reference; the Uno GND pins are internally common. Verify the real board rails and sequencing before power. |

In the copied build layout, the five button GND tie groups (rows 4, 10, 16, 22, 28) are chained across their bottom-section J holes: `4b.j → 10b.j → 16b.j → 22b.j → 28b.j → bn.25`. Each J hole is in the same lower F–J tie group as that row's button return. Uno logic GND uses `bn.1`; LCD and DFPlayer mock returns use `bn.22` and `bn.24`. The external-load negative rail is separate (`tn`) and references Uno GND through `GND.2`. These are modeled routes, not proof of physical continuity or approval to energize.

The copied build canvas uses the reported jumper colors for strip power/return, and yellow for all four NeoPixel data links. Other wire colors are visual aids; consult exact endpoints in `diagram.json` rather than inferring electrical function from color alone. Canvas colors do not establish physical jumper colors, continuity, or power-up approval.

The main Wokwi diagram now matches the sibling build canvas: direct D2/D3/D4/D12 data links and separate modeled `bp` positive / `tn` return rails for strip and servo loads, with Uno logic power on separate `tp`/`bn` rails and a common ground reference through Uno GND. No DOUT chaining or secondary strip power pins are shown. The user confirms a yellow-colored physical D12-to-yellow-DIN jumper, but it has not been independently continuity-tested. The user reports professor verification of the first-breadboard rails for combined strip-plus-servo load; exact rating, actual current, wiring, and branch state are not independently verified and this is not energization approval. Verify actual strip pads/signal compatibility, common ground, power sequencing, and backfeed behavior. Firmware groups pixels 0–5 red, 6–11 green, 12–17 blue, and 18–23 yellow. Wokwi structure does not prove physical wiring, ratings, rendered clearance, or runtime behavior.

The Wokwi half breadboard is a logical/visual wiring aid only: it does not verify physical tie-point continuity, component ratings, current capacity, servo supply isolation, or speaker compatibility. The canvas uses the 30-row half-board, four strips at the listed 225° positions, five mounted buttons, and the MP3 TX resistor. The layout tests check anchors, coordinates, footprints, and modeled nets, not visual overlap; inspect it in the user's Wokwi VS Code view for rendered clearance. The breadboard is at `(left, top)=(330, 350)`, Uno at `(260, 0)` rotated 45°, LCD at `(150, 300)`, servo at `(680, 125)`, breakout at `(820, 320)`, DFPlayer mock at `(680, 405)`, and visual speaker at `(820, 405)`. Twenty component-lead placements use `$bb`; the four strips are separate components with direct data wires and rail-routed supply. The physical adapter is omitted; the breakout remains visual-only. Keep every hard gate in [Power and physical limits](#power-and-physical-limits) closed until verified.

### Step 1 — four four-leg play buttons and one two-terminal Start button

The four play controls are four-leg tactile buttons. With each unpowered and removed from the circuit, use a continuity meter to identify its two permanently joined pin pairs and verify that the separate pairs connect only when pressed. Their physical package orientation is **not verified here**; do not assume the orientation from the generic drawing.

Start is a separate physical two-terminal, normally-open button. While it is unpowered and disconnected, verify that its two leads are open when released and connected only while pressed. Verify that its leads fit the intended breadboard contacts and that the contact orientation matches the button's behavior; do not infer this from Wokwi's symbol.

Place each four-leg play button across the breadboard's center trench. Connect one internally joined pair to its GPIO row and the other pair to its GND-return row. Pressing should bridge those two contacts; released must remain open. Repeat the continuity check after placement. For Start, connect one physical lead to the A1 row-30 signal group and the other to the row-28 GND-return group.

```text
Wokwi/editor pin placement example — play Button 1 (black in Wokwi), contact 1 on row 6, contact 2 on row 4
Verify the actual physical switch contact pairs and board tie strips with a meter.

columns     A   B   C   D   E       trench       F   G   H   I   J
row 6t      D6 ───────●──────────────● 1.l  ||  1.r ●──────────────●
row 6b                                     ||
row 4t      ──────────● 2.l───────────────||────────────────────────
row 4b                                     ||  2.r ● at 4b.f (same F–J group as 4b.j)
                         pins straddle trench at each contact row

The play-button editor links are 1.l=6t.e, 1.r=6b.f, 2.l=4t.e, and 2.r=4b.f.
D6 is tied to contact 1's row-6 top group; the row-4 bottom group joins the
row-j Wokwi GND trunk, which taps the logic return rail at `bn.25`.
Repeat only for the other play buttons at contact rows (12,10), (18,16), and
(24,22) for D7, D8, and A0. Released GPIO and GND contacts stay separate;
pressing bridges them. The sketch uses INPUT_PULLUP, not external +5 V.

Start is physical 2-terminal normally-open: one lead → A1 / `30t`; the other → GND return / `28b`.
Wokwi still draws four symbol pins, but routes only `1.l` → `30t.e` and `2.r` → `28b.f`;
`1.r` and `2.l` are intentionally unused. In the current diagram, row 28 joins GND through the row-j return chain.
```

| Control | Uno input | Other contact |
|---|---:|---|
| Button 1 (leftmost) | D6 | GND |
| Button 2 | D7 | GND |
| Button 3 | D8 | GND |
| Button 4 (rightmost play button) | A0 | GND |
| Start | A1 | GND |

### Step 2 — four independent six-pixel NeoPixel strips (build-derived Wokwi topology and unpowered inspection)

Both main and build-variant Wokwi diagrams contain four six-pixel strips. Firmware drives them independently on D2, D3, D4, and D12 with no DOUT chaining; pixel groups are 0–5 red, 6–11 green, 12–17 blue, and 18–23 yellow.

```text
Build-derived Wokwi topology (not a verified physical wiring record):
[RED 0-5]      top 60 / left 647.537, rotated 225 degrees
[GREEN 6-11]   top 60 / left 727.537, rotated 225 degrees
[BLUE 12-17]   top 60 / left 807.537, rotated 225 degrees
[YELLOW 18-23] top 60 / left 887.537, rotated 225 degrees

Independent data links:
Uno D2 -> red DIN; D3 -> green DIN; D4 -> blue DIN; D12 -> yellow DIN

Build-derived modeled supply routes:
Breakout 5V -> `bp` positive rail -> strips/servo; breakout GND -> `tn` return rail -> strips/servo
Every strip DOUT, VDD.2, and VSS.2 remains unconnected in this diagram.
```

The main diagram now matches the build variant's modeled routes; neither diagram independently verifies the physical wiring. The sibling `../alien-simon-says-build/diagram.json` currently retains a separate copy of the same canvas. The user reports that the first breadboard rails were verified for the combined strip-plus-servo load. That is a user report only, not independent verification of the board model, continuous-current rating, wiring/continuity, actual aggregate draw, or the state of any/all eight strip power branches. It is not power-up approval. The user also confirms the yellow-colored D12-to-yellow-DIN data jumper; continuity and actual strip pad labels remain unverified.

With USB and all external supplies disconnected, verify strip markings/direction, actual rail continuity/splits, wire/connector protection and ratings, combined strip-plus-servo current, common ground, signal/backfeed behavior, and power sequencing. Keep external +5 V isolated from Uno 5V/barrel. The user-reported rail check does not independently verify these conditions or authorize energization.

The copied diagram has 17 parts and 63 connection entries (43 colored wires plus 20 `$bb` component-lead placements). These counts are logical structure only, not evidence of present physical wiring, ratings, or rendered clearance. The breakout marker is visual-only. A fresh full render in Wokwi VS Code is still needed to verify appearance and clearance.

### Step 3 — exact Grove 16x2 LCD

Use the confirmed Seeed Grove 16x2 LCD Black-on-Yellow V2.0 (PCB `JHD1804M1 P1835`), not a generic HD44780 backpack. Follow the Grove connector labels/cable orientation. The Seeed documentation specifies 3.3/5 V and I2C address `0x3E`; this build uses 5 V and Uno A4/A5.

```text
Physical lead colors—not Wokwi segment colors                            LCD lead
Uno 5V ─────── top `tp` rail ──────────────────────────────────── LCD VCC
Uno GND ────── top `bn` rail ──────────────────────────────────── LCD GND
Uno A4 ────────────────────────────────────────────────────────── LCD SDA
Uno A5 ────────────────────────────────────────────────────────── LCD SCL
              LCD logic power stays separate from external load rails

No extra LCD backpack, RGB-backlight board, or generic display is substituted.
The diagram routes SDA/SCL directly and VCC/GND through the Uno logic rails.
Verify the real Grove connector orientation and wiring before any power.
```

The firmware follows the official shared Seeed `Grove_LCD_RGB_Backlight` Arduino library's monochrome-compatible LCD protocol: 7-bit address `0x3E`; command control byte `0x80`; display-data control byte `0x40`; 16x2 function/display/clear/entry and DDRAM row commands. It does not call the unsupported RGB-backlight API. In this diagram SDA/SCL route directly from Uno A4/A5; LCD VCC/GND use the Uno logic rails. The project-local Wokwi chip handles those same I2C command/data prefixes and renders a yellow monochrome 16x2 framebuffer.

Official references:

- [Seeed Grove 16x2 LCD series guide](https://wiki.seeedstudio.com/Grove-16x2_LCD_Series/)
- [Seeed Grove_LCD_RGB_Backlight source](https://github.com/Seeed-Studio/Grove_LCD_RGB_Backlight) (`rgb_lcd.cpp` / `rgb_lcd.h`)
- [JHD1804 data sheet linked by Seeed](https://files.seeedstudio.com/wiki/Grove-16x2_LCD_Series/res/JDH_1804_Datasheet.pdf)
- [Wokwi Custom Chip I2C API](https://docs.wokwi.com/chips-api/i2c), [Framebuffer API](https://docs.wokwi.com/chips-api/framebuffer), and [chip JSON](https://docs.wokwi.com/chips-api/chip-definition)

### Step 4 — MP3-TF-16P and speaker

Make these signal/audio connections with power disconnected. The D11-to-RX series resistor is required by this pin plan. Keep the module's own two speaker terminals isolated from Uno ground/GPIO.

```text
Signal tie rows (keep TX and RX nets separate)
Uno D10 RX <──────── row 5 <──────── mock/module TX
Uno D11 TX ────────> 1t.a / 1t.b ── [1 kΩ] ── 1b.f / 1b.g ──> mock RX
                        pin 1            pin 2  (1b.g to RX)

Shared power rails are not automatic permission to power this module:
module VCC/GND ──> only to the verified, current-rated path after the USB
                   budget and board/wire ratings are closed (see hard gates).

Physical speaker wiring is direct across module outputs, not via breadboard:
MP3-TF-16P SPK1 ───────────────────────────── speaker lead 1
MP3-TF-16P SPK2 ───────────────────────────── speaker lead 2

Do not connect either speaker output to GND or an Uno pin. The copied diagram routes each speaker terminal directly to its matching mock terminal; this visual connection does not verify the physical speaker path. Keep the speaker unpowered until module output/load ratings are verified.
```

The full-game firmware expects `/mp3/0001-…mp3`–`0007-…mp3` (see `sdcard/card-mp3/`); this repository contains existing files 1–5, while the user reports 6/7 already at `D:/mp3`. Do not overwrite existing card files. No SD/card access or file replacement is part of this change. Begin at volume 3 only after the physical gates are closed. The actual MP3-TF-16P clone/card compatibility and current budget are not confirmed by simulation.

### Step 5 — servo signal and separate external load supply

The main Wokwi diagram now matches the build-variant canvas and models the reported physical routing only. The user reports the first breadboard rails verified for the combined strip-plus-servo load, but the exact board model/rating, wiring, continuity, protective path, and real combined current have not been independently verified. This report is not a safety certification or permission to energize. No current connection state is asserted here for any individual strip power branch.

```text
Servo signal path modeled in both matching Wokwi canvases:
Uno D9 / OC1A -> assigned signal row -> servo PWM

External load-power route shown in that separate canvas:
External supply positive -> separate positive rail(s) -> strip VDD and servo V+
External supply negative -> separate return rail(s) -> strip VSS and servo GND
External ground -> the planned common signal reference to Uno GND

External +5 V must not connect to Uno 5V or the Uno barrel jack.
Do not power the strips or servo motor current from Uno USB/5V.
```

Before any physical energization, identify the adapter/breakout terminals and polarity, inspect the actual board/rail split and all connections, and verify the board, rail, wire, connector, protection, supply, and combined strip-plus-servo continuous/peak current limits. Confirm the actual servo interface/supply and FS5106B signal range. Check whether D9 PWM or NeoPixel DIN can backfeed an unpowered load or Uno, establish a safe power-off signal state and manufacturer-compatible sequencing, and confirm common ground without joining external positive to Uno power. Verify the exact strip model, pad labels, data-voltage compatibility and any required series resistor/level shifter. Keep all sources disconnected until every gate in [Power and physical limits](#power-and-physical-limits) passes; this reference guide grants no power-up approval.

### Step 6 — FIT0458 motor through the Seeed MAKER MDD3A (loss reaction)

On a player loss the sketch extends the servo, waits `MOTOR_START_LEAD_MS` (150 ms), then ramps the motor on D5 up to `MOTOR_DUTY_MAX` (128/255, about 50%) over `MOTOR_RAMP_MS` (300 ms). The motor always stops at `MOTOR_MAX_RUN_MS` (2.5 s) regardless of audio, and also on the loss track finishing, a DFPlayer error, Start pressed during the loss, or the 7 s loss watchdog. Stop is both inputs LOW. The loss audio is track `0007.mp3`, the file already on the physical SD card. The limits live in `alien-simon-says/motor_drive_config.h`; they bound current and are not a verified safety rating.

```text
Uno D5  -> MDD3A M1A input (signal header)
Uno A2  -> MDD3A M1B input (signal header)
Uno GND rail -> MDD3A logic GND
MDD3A VB+ -> bb1 bp.4 (external +5 V rail, next to the barrel breakout 5V wire at bp.3)
MDD3A VB- -> bb1 tn.7 (external GND rail, yellow wire as built)
MDD3A motor-1 output terminals -> FIT0458 motor power leads (swap only reverses direction)
MDD3A 5VO: leave unconnected      FIT0458 encoder leads: leave unconnected and insulated
```

The Wokwi diagram uses behaviour-free labelled stand-in boards (`chip-mdd3a-board-visual`, `chip-fit0458-motor-visual`) because Wokwi has no MDD3A or FIT0458 part. They model no motion, current or driver logic. Pin names come from the project's earlier motor simulation and the DFRobot FIT0458 page; the MDD3A datasheet was not readable, so check the real board's silkscreen and truth table (High/Low forward, Low/Low stop) before wiring.

Physical gates, all still open: the motor current (up to 2.8 A stall) now runs through the half-breadboard rails: the user reports their professor verified the board for this (no rating figure recorded, not independently checked); still confirm the rail jumpers and combined strips + servo + motor load before power-up; fit a fuse (about 3–5 A) and a 470–1000 µF capacitor at the driver VB+/VB-; measure the shared 5 V / 5 A supply under strips + servo + motor before trusting it; never connect motor VB+ to Uno 5V, USB or Vin, and never use the 9 V battery (FIT0458 is rated 3–7.5 V, 2.8 A stall); D5 and A2 float while the Uno resets or uploads, and no external pull-downs are fitted: with the motor disconnected, power the driver, hold the Uno in reset, and meter M1A/M1B to GND, and add 10 kΩ pull-downs from each input to GND if they do not read near 0 V; first run with the motor disconnected while watching M1A/M1B, then unloaded, then loaded. Do not run full-white strips and the motor together until the current is measured. This section is not energization approval.

## Power and physical limits

Do **not** energize any circuit based on a diagram, user report, host build, or this README. The main Wokwi diagram now matches the build variant's modeled routes but does not independently verify the physical assembly. The user reports that its first breadboard rails were verified for the combined strip-plus-servo load. This remains user-reported only: exact rail/board rating, continuity, aggregate current, branch installation, and component requirements are not independently verified. The report does not authorize energization. No claim is made here that all eight strip power branches are currently connected or disconnected.

1. **Supply and distribution:** identify the actual adapter, barrel breakout, polarity, protection, rail continuity/splits, board and conductor ratings, and combined continuous/peak current for four six-pixel strips plus servo. User-reported rail verification is not an independent rating/current certification. Keep external positive separate from Uno 5V/barrel and USB power. Verify that the current canvas' positive and return rails remain electrically separate and that no unintended path backfeeds Uno or a load.
2. **Strips and data path:** identify each strip's manufacturer/model, marked VDD/VSS/DIN/DOUT pads and orientation, voltage/current limits, signal-level requirements, and any required resistor/level-shifter. Verify each independent data route (D2/D3/D4/D12), actual ground reference, and signal behavior when either side is unpowered. The main Wokwi nets do not verify these physical properties.
3. **Servo:** identify the actual servo/interface and rated supply/current, evaluate FS5106B mechanism/load, horn/linkage clearance, safe travel limits, power-off signal/backfeed behavior, and safe sequencing. Firmware commands 700/1500/2300 microseconds at 0/90/180 degrees; physical game settings remain 90-degree extend, 0-degree retract, and one-second timing, but mechanism travel/safety is unverified. Wokwi's 180-degree command is simulation-only. Do not widen physical motion settings without separate safe mechanism assessment.
4. **Uno and low-current components:** verify the actual button contacts/orientation, Grove connector and SDA/A4/SCL/A5 mapping, DFPlayer variant/serial levels, aggregate Uno USB budget, microSD requirements, and speaker/module output ratings. Never power physical NeoPixels or servo motor current from Uno USB/5V.
5. **Isolation and sequencing:** never feed external +5 V to Uno +5 V or the Uno barrel jack, especially while USB is attached. Confirm a shared signal ground only where intended, no positive rail crossover, no signal-line backfeed when a supply is off, and safe startup/shutdown order for Uno, strips, and servo using their actual interfaces. Keep USB and every external source disconnected until all applicable checks pass. This document and the user-reported breadboard check are not energization approval.

## Physical validation plan

1. **Unpowered inspection:** use the main Wokwi diagram as a route reference, check all marked terminals/polarities, verify rail continuity/splits and conductor/connector protection, inspect for shorts, and confirm signal/common-ground/backfeed paths. A matching build canvas is not independent physical verification. Do not energize until all gates above pass and separate authorization exists.
2. **Uno and low-current inputs/display:** only after applicable gates and authorization are closed, validate buttons, LCD pages and debounce/release behavior. The user reports a yellow-colored physical D12-to-yellow-DIN jumper; this is not independently observed. Host/static checks do not establish physical continuity, rendered behavior, or electrical safety.
3. **EEPROM and stats:** play and end a game, power-cycle the Uno, then query `STATS` over USB Serial at 115200 baud with newline line-ending. Verify best score and average update on Game Over and manual restart, failed entropy does not increment the stored session count, and neither session count nor average appears on the player LCD. Verify the shifted first-color journal still records first cues without constraining sequence selection. EEPROM and serial behavior are not physically verified.
4. **Audio:** only after module/USB current and speaker/module ratings are verified, validate startup/track mapping at volume 3, cue completion, and Game Over audio stop. Audio SD files currently contain test voices; this is user-reported context and not audio-content verification in this build task.
5. **Servo electrical check:** only after all external-power gates and authorization are closed, test disconnected from its mechanism with the identified rated supply and shared ground. Verify startup retract, safe configured commands, hold/retract timing, and power sequencing while keeping servo motor current off Uno/breadboard logic power.
6. **Mechanism/load and full game:** only after the servo path is separately cleared, verify safe travel/load, loss-only motion, input handling, scoring, audio overlap, and repeated power cycles. No physical test or power-up is performed as part of these documentation/code changes.

## Audio cues

The repository's generated cue files are short electronic tones in a classic Simon-style sequence, not recordings or extracted audio from an original Simon game. The physical SD card is currently user-reported to contain test voices; its contents were not inspected or changed in this task, and the repository files do not establish what is on the card. Each repository cue has a brief fade to avoid clicks:

| File | Button/LED | Generated fundamental |
|---|---|---:|
| `0001.mp3` | Red pixel/button | 523.25 Hz (C5) |
| `0002.mp3` | Green pixel/button | 659.25 Hz (E5) |
| `0003.mp3` | Blue pixel/button | 783.99 Hz (G5) |
| `0004.mp3` | Yellow pixel/button | 1046.50 Hz (C6) |
| `0005.mp3` | Existing repository file retained; unused by full-game events | Descending two-part electronic tone |
| `0006.mp3` | Completed-round celebration (user-provided physical track) | Reported duration ~1.714 s; content not accessed here |
| `0007.mp3` | Player loss / wrong answer (user-provided physical track) | Reported duration ~1.790 s; content not accessed here |

On a player loss (wrong answer or chord), firmware plays `/mp3/0007.mp3`; the technical round-counter safeguard does not use the loss sound. Successful rounds 3, 6, 9, … play `/mp3/0006.mp3`. The Wokwi DFPlayer mock does not read or play any MP3.

The previously used “sound-alien1” sample by **zippi1** remains at `assets/source-sound-alien1-hq.mp3`; it is not used to make these tones. Source: https://freesound.org/people/zippi1/sounds/18027/, licensed **CC BY-NC 4.0**: https://creativecommons.org/licenses/by-nc/4.0/ .
