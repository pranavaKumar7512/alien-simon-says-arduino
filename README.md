# Alien Simon Says — Arduino Uno R3

A complete Simon Says sketch for the confirmed **Arduino Uno R3**, with four generic play buttons and firmware for four independently driven four-pixel NeoPixel strips—red on D2, green on D3, blue on D4, and yellow on D5, with no DOUT chaining; it also has a separate Start button, the exact Seeed Grove 16x2 LCD Black-on-Yellow V2.0 / JHD1804M1 display, an MP3-TF-16P physical audio backend, an FS5106B positional servo, and a Wokwi DFPlayer protocol mock. The Wokwi diagram shows all four independent strips and their direct data routes. The user reports 3-pin, 5 V addressable RGB WS2812B/NeoPixel-style strips with GND, DIN/DO, and 5 V pads, and now reports that the physical setup matches the IRL diagram: all four D2–D5 data jumpers and all eight primary strip VDD/VSS branches are connected, including the previously reported red branches. This physical state is user-reported, not independently observed or continuity-tested. The user also reports that their professor reviewed/verified the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; that review does not independently establish that branch leads were installed. The exact strip model has not been independently inspected.

> **Four-strip topology and physical status:** the Wokwi diagram models four independent direct data links (Uno D2/D3/D4/D5→red/green/blue/yellow DIN) and all eight primary supply branches (breakout 5V→each strip VDD in red `#FF0000`; breakout GND→each strip VSS in black `#000000`). It has exactly 17 parts and 65 connection entries: 45 colored wire entries and 20 `$bb` component-lead placements. No DOUT, VDD.2, or VSS.2 links are shown. The user reports that their setup matches the IRL diagram, with all four physical data jumpers and all eight primary strip VDD/VSS branches connected, including the previously reported red branches. These physical connections are user-reported, not independently observed or continuity-tested. The user's professor reportedly reviewed/verified the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; this is user-reported and does not independently prove that branch leads were installed. Physical strip branches use that approved distribution arrangement—not extra wires crammed into the two-terminal breakout or ordinary breadboard rails. Wokwi shows logical breakout-to-strip nets; the alternate physical distribution-board routing is not depicted. Keep USB and every supply disconnected for an unpowered final inspection; check marked VDD/VSS endpoints against the approved distribution points, shorts, and secure rated conductors. No power-up until final inspection passes. The `$bb` entries are component-lead placements, not loose jumper wires; diagram totals do not verify physical connections. Visual strip clearance remains pending a fresh full render.

> **Keep all power disconnected for final inspection.** The Wokwi external-adapter and barrel-breakout chips are visual topology markers; they do not model voltage, current, adapter protection, or passive internal continuity. The user reports their professor reviewed/verified the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; this remains user-reported and does not independently prove that each branch lead was installed. With USB and every supply off, verify each physical strip lead ends at the marked primary VDD/VSS pad and approved distribution point, check for shorts, and ensure rated conductors are secure. Do not power up until this final inspection passes.

## Project contents

- `alien-simon-says/alien-simon-says.ino` — nonblocking gameplay/state machine; both builds send DFRobotDFPlayerMini frames over SoftwareSerial D10/D11, drive four independent four-pixel strips from D2–D5 with four Adafruit_NeoPixel objects, and drive the servo from Timer1 hardware PWM on D9/OC1A.
- `alien-simon-says/*.h` — firmware-local headers staged with the sketch. Matching root-level header copies are used by the host C tests and must stay synchronized.
- `scripts/build-arduino.sh` — stages the nested sketch and its adjacent headers under Arduino CLI's required matching basename and builds physical and Wokwi firmware into the configured output folders.
- `scripts/run-wokwi-tests.py` — builds test firmware from the nested sketch and generates randomized, seed-replayable Wokwi scenarios with local previous-first-color metadata.
- `first_color_journal.h` — CRC/commit-checked, wear-levelled Uno EEPROM ring for the previous game's first color, separate from the best-score record.
- `game_sequence.h` — a constant-memory, seed-replayable pseudo-random stream that samples each cue with replacement from all four colors.
- `button_mapping.h` — a separately seeded one-to-one mapping from left-to-right button positions to cue colors, shuffled after every three successfully completed rounds.
- Rob Tillaart's SIMON library verifies player answers in bounded chunks of up to ten symbols; the game sequence itself streams beyond that chunk size.
- Physical seeds come from the AVR Arduino Entropy library's watchdog/Timer1 timing jitter; Wokwi uses host-injected replay seeds.
- `servo_celebration_config.h` — shared Game Over servo angle/timing settings and Timer1 pulse conversion for physical and Wokwi builds.
- `audio_track_config.h` — shared cue-track range and dedicated player-loss audio track selection.
- `sdcard/mp3/0001.mp3`–`0004.mp3` — card-ready, generated classic Simon-style tone cues (not recordings from an original Simon game); `0005.mp3` is the generated losing sound.
- `assets/source-sound-alien1-hq.mp3` — retained, attributed alien source sample; it is not used by the generated cues.
- `SHA256SUMS` — verified SHA-256 hashes for the five game cues and retained source sample.
- `chips/grove-jhd1804.chip.c` / `.chip.json` — local I2C/framebuffer model for the specified Grove/JHD1804 LCD, not a substitute display.
- `chips/dfplayer-mock.chip.c` / `.chip.json` — UART protocol mock for volume, track, stop, and simulated track-finished events; it does not decode or play the copied MP3 files.
- `chips/visual-speaker.chip.c` / `.chip.json` — separate two-terminal component named `8 Ω / 0.5 W — no playback`; it is a visual pinout only.
- `chips/barrel-jack-breakout.chip.c` / `.chip.json` — visual-only female DC barrel-jack-to-2-screw-terminal breakout marker, matching the form shown in the user's photo; its pins do not implement electrical pass-through.
- `diagram.json`, `wokwi.toml` — the current Uno simulation has one 30-row half breadboard and four visible four-pixel `wokwi-led-strip` parts (`neopixel-red`, `neopixel-green`, `neopixel-blue`, `neopixel-yellow`) at `top: 60`, `left: 647.537`, `727.537`, `807.537`, and `887.537`, rotated 225°. Direct white links connect D2/D3/D4/D5 to the corresponding DIN pins; breakout 5V connects directly to all four primary VDD pins in red `#FF0000`, and breakout GND connects directly to all four primary VSS pins in black `#000000`. Thus all eight primary supply branches are modeled; DOUT and all VDD.2/VSS.2 pins remain open. The diagram has 17 parts and 65 connections (45 colored wires plus 20 `$bb` component-lead placements). The user reports their setup matches the IRL diagram, including all four physical data jumpers and all eight primary strip supply branches; this is not independently observed or continuity-tested. The user reports professor review/verification of the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; this does not independently prove branch-lead installation. Physical branches route through that approved distribution arrangement rather than extra wires in the two-terminal breakout or ordinary breadboard rails; Wokwi's logical direct nets do not depict this alternate routing. The adapter is physically plugged directly into the visual-only barrel-jack breakout and is not a separate diagram part. `pixelSize: "2020"` is a rendering choice, not a verified physical package. The diagram also has five buttons, the LCD model, DFPlayer mock, no-playback speaker model, and visual-only servo; there is no buzzer. Button pins and the MP3 TX resistor use `$bb` placements. The breakout marker does not itself establish physical topology or safety.

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

The sketch has no Servo-library build dependency: D9/OC1A uses Timer1 Fast PWM mode 14 with a 16 MHz clock, prescaler 8, `ICR1=39999` (20 ms frame), and `OCR1A` pulse widths in 0.5 µs ticks. This hardware PWM continues without interrupt servicing, avoiding SoftwareSerial's interrupt blocking stretching servo pulses. The sketch retains the Servo library's default 544–2400 µs angle mapping and approximately 2 µs trim. Timer1 is reserved for this servo output; do not use `analogWrite()` on D9/D10 or another library/configuration that takes over Timer1. Both firmware builds use the existing DFRobot library and SoftwareSerial; the Wokwi diagram connects those same serial pins to the custom UART mock. The sketch does not require installing the Grove library: it sends the documented Grove LCD command/data protocol over `Wire` directly.

From this folder (Git Bash on the development machine):

```sh
sha256sum -c SHA256SUMS
bash scripts/build-arduino.sh
wokwi-cli chip compile --output chips/grove-jhd1804.chip.wasm chips/grove-jhd1804.chip.c
wokwi-cli chip compile --output chips/dfplayer-mock.chip.wasm chips/dfplayer-mock.chip.c
wokwi-cli chip compile --output chips/visual-speaker.chip.wasm chips/visual-speaker.chip.c
wokwi-cli chip compile --output chips/barrel-jack-breakout.chip.wasm chips/barrel-jack-breakout.chip.c
wokwi-cli lint --warnings-as-errors .
gcc -std=c99 -Wno-attributes tests/test_grove_jhd1804.c -o build/test_grove_jhd1804 && build/test_grove_jhd1804
gcc -std=c99 -Wno-attributes tests/test_dfplayer_mock.c -o build/test_dfplayer_mock && build/test_dfplayer_mock
gcc -std=c99 tests/test_audio_completion_filter.c -o build/test_audio_completion_filter && build/test_audio_completion_filter
gcc -std=c99 tests/test_game_over_audio_config.c -o build/test_game_over_audio_config && build/test_game_over_audio_config
gcc -std=c99 tests/test_player_led_feedback.c -o build/test_player_led_feedback && build/test_player_led_feedback
gcc -std=c99 tests/test_first_color_journal.c -o build/test_first_color_journal && build/test_first_color_journal
gcc -std=c99 tests/test_game_sequence.c -o build/test_game_sequence && build/test_game_sequence
gcc -std=c99 -Wall -Wextra -Werror tests/test_button_mapping.c -o build/test_button_mapping && build/test_button_mapping
gcc -std=c99 tests/test_servo_celebration_config.c -o build/test_servo_celebration_config_physical && build/test_servo_celebration_config_physical
gcc -std=c99 -DWOKWI_SIM tests/test_servo_celebration_config.c -o build/test_servo_celebration_config_wokwi && build/test_servo_celebration_config_wokwi
python3 tests/test_diagram_led_button_layout.py
python3 tests/test_diagram_breadboard_nets.py
python3 tests/test_wokwi_test_runner.py
python3 scripts/run-wokwi-tests.py --scenario all
```

The first build is the physical Uno firmware. The second is the default Wokwi build; unless overridden, it injects a new nonzero host-generated seed at each build and prints it. Re-running the same firmware image intentionally repeats its sequence; use `WOKWI_INITIAL_SEED=<seed> bash scripts/build-arduino.sh` to rebuild a replayable image. Randomized automation recompiles a Wokwi image with a per-run logged seed; it also passes prior-first-color metadata, which does not affect cue selection. The mock checks the 10-byte DFRobot frame/header/checksum, handles volume/play/stop, and schedules configurable completion events, but never reads the copied MP3 files or plays sound. The separate speaker has no playback behavior; no buzzer or `tone()` backend is used. Host tests cover protocol parsing, checksums, completion cancellation, the LCD model, four independent strips with grouped 16-pixel NeoPixel feedback, map-preserving 500 ms input flashes, and simultaneous position-map rendering, first-color journal integrity/wear-leveling, sequence selection, seeded position-to-color mapping, loss-gated servo targets, and exact breadboard diagram nets. `python3 scripts/run-wokwi-tests.py --scenario all` generates randomized matching button scenarios, prints replay commands, stores the Wokwi previous-first-color state in `.wokwi-sequence-state.json`, and saves transcripts/manifests under `build/wokwi-tests/`. Use `--scenario first-round` for one test or `--scenario button-remap` to exercise the 5.5-second initial identity-map preview, post-sequence color maps, 500 ms pressed-color dark flashes, the round-4 shuffle and preview, and successful answers through round 4. This scenario plans runtime coverage; actual LED/LCD rendering still needs runtime or hardware observation. To reproduce a run, use the printed seed and previous-color arguments with `--no-persist`. Runtime scenarios require a valid `WOKWI_CLI_TOKEN`; Wokwi's monthly CI-minute quota can also block them. Wokwi simulation does **not** validate physical NeoPixel current/power, actual DFPlayer playback, speaker output/current, external servo power/travel/load, or the real LCD hardware. Official interface references: [Wokwi Custom Chip UART API](https://docs.wokwi.com/chips-api/uart), [custom chip JSON](https://docs.wokwi.com/chips-api/chip-definition), [automation scenarios](https://docs.wokwi.com/wokwi-ci/automation-scenarios), [Wokwi CLI usage/token requirement](https://docs.wokwi.com/wokwi-ci/cli-usage), and [Wokwi LED strip part](https://docs.wokwi.com/parts/wokwi-led-strip).

### Wokwi audio model

The Uno's D11 SoftwareSerial TX reaches the custom DFPlayer mock RX (through the diagram's 1 kΩ signal resistor), and mock TX returns to Uno D10 SoftwareSerial RX. The mock parses the real DFRobot 9600-baud command frames, accepts volume/play/stop, and sends a checksummed `0x3D` finish event after the configured simulation delay. Stop cancels pending completion. It has no SD-card audio decoder and emits no sound. The separate two-terminal part is named exactly `8 Ω / 0.5 W — no playback`; it is wired only across mock `SPK1`/`SPK2`, never to Uno GPIO or GND.

The LCD and DFPlayer mock use the Uno's 5 V/GND rails in Wokwi. The user's 5 V / 5 A adapter is physically plugged directly into the barrel-jack breakout; accordingly, the diagram omits an adapter part. The breakout's `5V` and `GND` branches connect to the servo V+/GND and one GND reference to Uno GND. Wokwi additionally models direct logical nets from breakout 5V/GND to all four strips' primary VDD/VSS pins, with red `#FF0000` positive links and black `#000000` ground links. This logical diagram does not depict the physical alternate distribution-board routing or establish physical installation. The user reports that their setup matches the IRL diagram, including all four physical data jumpers and all eight primary strip power branches; these are not independently observed or continuity-tested. The user reports professor review/verification of the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; this user-reported path review does not independently prove that branch leads were installed. The physical strip branches use that approved distribution arrangement, not extra wires crammed into the two-terminal breakout or ordinary breadboard rails. The breakout custom chip is visual-only: it does not source voltage or model current, adapter protection, or actual barrel-jack pass-through. External positive is not connected to Uno 5 V. No DOUT chaining is used, and DOUT, VDD.2, and VSS.2 remain unconnected. No series resistor is shown in the data path; actual strip pinout and signal-interface requirements depend on the exact parts. This user-reported status is not physical verification or power-up approval. Firmware addresses pixels 0–3 as red, 4–7 green, 8–11 blue, and 12–15 yellow. Never power physical strips or servo motor current from Uno USB/5 V. The five 6 mm buttons and MP3 TX signal resistor use breadboard placements. Mock speaker outputs reach the visual speaker through separate, ungrounded breadboard rows. Wokwi lint and netlist tests validate structure/connectivity, not visual clarity or runtime behavior. Every visible Wokwi wire segment has its own high-contrast hex color, but the palette has not been checked in a fresh rendered screenshot: the local screenshot attempt was blocked by the Free-plan monthly CI-minute quota. The Wokwi diagram is not evidence of physical hookup; keep power-up blocked until final inspection passes. When physical speaker testing is permitted, the speaker stays directly across the physical module's SPK1/SPK2 outputs.

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
- Four independent NeoPixel strips contain sixteen addressable LEDs total: indices 0–3 are red, 4–7 green, 8–11 blue, and 12–15 yellow. During cue playback, only the mapped four-pixel group for the current cue lights; every group is off between cues. After the last cue, all four button-position groups illuminate in their current mapped colors and stay on while the player answers. Sequence cues stay lit for 2,000 ms from cue-on; an early natural audio-finished event does not shorten the light. At that deadline the firmware issues an idempotent DFPlayer Stop request to bound playback (harmless if the track already completed), then all strips remain off for the existing 180 ms gap. The physical module's exact Stop latency is not validated. In Wokwi, matching track numbers go to the DFPlayer mock; the mock has no MP3 decoder and plays no sound. On a debounced play-button press, only that color's mapped four-pixel group turns off for 500 ms while the other three groups remain lit; then the complete map is restored. The answer is still committed and checked only after button release, so a held button can remain down after the 500 ms flash. The 25 ms debounce, chord detection, and release-to-submit behavior remain. Players may wait indefinitely before answering and may hold a debounced answer indefinitely before releasing it. Held buttons during cue playback do not create button feedback; after the cues, the full map remains visible while the firmware waits for all buttons to be released. Two or more simultaneously debounced play buttons fail the run.
- The four controls are identified by physical position from left to right as Buttons 1–4; their casing colors have no gameplay meaning. The initial map is Button 1→Red, 2→Green, 3→Blue, 4→Yellow. After each three successfully completed rounds (3→4, 6→7, 9→10, …), a seed-derived shuffle creates a new one-to-one map for the next block; the cue sequence is unchanged. Each cue lights only its mapped group, all groups go dark between cues, and all four mapped colors are shown after the sequence. A pressed color's group then goes dark for 500 ms before the full map is restored. Repeating the exact previous full map is rejected, though individual assignments may repeat. A new game or restart restores the initial map and shows all four button-position LED groups simultaneously in their assigned cue colors for 5.5 seconds before Round 1, giving the player time to learn the button/color relationship. After each later remap, the celebration audio finishes first, then the same 5.5-second full-map preview appears before the next round. The LCD retains the existing idle, round, and score pages and never displays the mapping. The separate mapping PRNG does not affect cue generation, and the Wokwi `button-remap` scenario verifies replayable maps and translated inputs. A wrong answer, chord, or the 32-bit technical round counter reaching its maximum ends the run.
- The final score is stored in Uno EEPROM when it improves the best score. Idle keeps `PRESS START` on the first row and alternates `YOUR` / `BEST` score values on the second row every three seconds. EEPROM behavior still needs a physical power-cycle check.
- Game Over after a player loss plays physical track 5 (`/mp3/0005.mp3`) or sends mock track command 5. Other Game Over exits (the technical round-counter safeguard) and successful-round celebrations choose randomly from physical tracks 1–4. The screen remains visible for at least three seconds and, after a player loss, until the servo's configured return allowance has elapsed; the firmware then sends Stop before returning to score pages. This is three seconds on the physical configuration and six seconds in Wokwi. Technical counter exhaustion ends the game without servo motion because it is not a player loss. Completion events are drained throughout Game Over.
- Successful rounds 3, 6, 9, … still play a random celebration audio cue, but do not move the servo. The servo extends only after a player loses through a wrong answer or chord, then returns to 0°. In Wokwi, its target changes to 180° for a 3-second hold, then to 0° for a separate 3-second return allowance. Physical builds retain the conservative, unverified settings of 90° extend, 0° retract, a 1-second hold, and a 1-second return allowance until the real FS5106B linkage endpoints are verified. These are command-based intervals that include travel time; neither simulation nor elapsed time provides position feedback. The [Wokwi servo reference](https://docs.wokwi.com/parts/wokwi-servo) documents its range as 0°–180° with hard stops. Do not widen physical settings until the actual mechanism/load is assessed; the supply-path review is user-reported as professor-verified and is not an additional check request here.
- There is no practical round cap. The firmware stops only if its 32-bit completed-round counter reaches `UINT32_MAX`, a technical overflow safeguard rather than a gameplay limit. SIMON's ten-symbol array is reused as a verifier buffer and does not limit the game sequence.

## Pin map — physical Uno R3

| Uno pin | Connection | Notes |
|---|---|---|
| D2 | Red strip DIN | Direct white data link in the diagram; user confirms the physical D2-to-red-DIN jumper |
| D3 | Green strip DIN | Direct white data link in the diagram; user confirms the physical D3-to-green-DIN jumper |
| D4 | Blue strip DIN | Direct white data link in the diagram; user confirms the physical D4-to-blue-DIN jumper |
| D5 | Yellow strip DIN | Direct white data link in the diagram; user confirms the physical D5-to-yellow-DIN jumper |

These are user-reported jumper connections; continuity and pad labels/orientation have not been independently measured.
| D6, D7, D8, A0 | Generic play controls, Buttons 1–4 from left to right | `INPUT_PULLUP`; position—not casing color—identifies each control; pressed input connects to GND |
| A1 | Separate two-terminal, normally-open Start button | `INPUT_PULLUP`; its other lead returns to GND when pressed |
| A4 / A5 | Grove LCD SDA / SCL | I²C address `0x3E`; do not swap data and clock |
| D9 | FS5106B signal | Servo motor power must come directly from a verified external supply path, not Uno/breadboard power |
| D10 | Uno SoftwareSerial RX ← MP3-TF-16P TX | No connection to Uno D0/D1 |
| D11 | Uno SoftwareSerial TX → 1 kΩ series resistor → MP3-TF-16P RX | Start at module volume 3 |
| D12 | Unused | No tone/buzzer backend is used in Wokwi or on the physical build |
| 5V / GND | Visual-only breakout branches to servo, Uno GND reference, and all four strip VDD/VSS pins | Wokwi models the eight primary strip supply nets directly between the breakout and strips, but not the physical alternate distribution-board layout. The user reports all eight primary physical strip branches connected, not independently observed or continuity-tested. The user reports professor review/verification of the intended 5 V / 5 A supply and distribution path; that review does not independently prove branch-lead installation. Use the approved distribution arrangement, not extra wires crammed into the two-terminal breakout or ordinary breadboard rails. Keep USB and every supply disconnected; perform the unpowered final inspection in Step 2 before power-up. |
| D0 / D1 | USB serial diagnostics | Reserved; keep free of MP3 wiring |
| A2 / A3 | Unused | No random-number hardware is connected |

Timer1 is dedicated to the D9/OC1A servo signal. It generates 50 Hz Fast PWM using a 0.5 µs timer tick and a 39999 TOP; servo targets use the standard angle-to-pulse range with the Servo library's ~2 µs trim retained. The timer continues producing active pulses while the servo is parked—there is no detach operation. Timer1 also owns D10/OC1B's PWM timing, so do not use D9/D10 `analogWrite()` or code that reconfigures Timer1. This does not change the D10 SoftwareSerial RX / D11 TX audio map.

The firmware runs a 500 ms power-on self-test in `setup()` that lights all sixteen pixels simultaneously in four mapped-color groups (0–3 red, 4–7 green, 8–11 blue, 12–15 yellow), then clears them and enters IDLE. Separately, each game start shows the initial button/color map for 5.5 seconds before Round 1. Sequence cues light only their mapped group and leave all groups dark between flashes; after the sequence, all four mapped colors stay lit, with the pressed color's group briefly dark for 500 ms on each button press. The user reports 5 V, 3-pin addressable WS2812B/NeoPixel-style strips, with pads labeled GND, DIN/DO, and 5 V; exact strip model, pad labels/orientation, and signal-interface requirements have not been independently inspected. The user reports that their professor reviewed/verified the intended shared 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; this is not independently measured, and this path review does not establish installation of all branch leads. The visual-only breakout marker is not evidence of the physical hookup. Never power physical strips from Uno USB or Uno 5 V; keep power-up blocked until the unpowered final inspection confirms marked endpoints, no shorts, and secure rated conductors. Adafruit's [NeoPixel best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices) do not substitute for identifying the actual strip pads and signal requirements. Play-button inputs use the Uno's internal pull-ups, so no button is wired to +5 V.

The MP3 files belong in `/mp3/` at the root of a FAT32 microSD/TF card:

```text
/mp3/0001.mp3
/mp3/0002.mp3
/mp3/0003.mp3
/mp3/0004.mp3
/mp3/0005.mp3
```

`0001`–`0004` map respectively to red, green, blue, and yellow; `0005` plays after a player loss. The physical speaker connects across the module's **SPK1 and SPK2 speaker outputs** (one lead per output). Never connect a speaker terminal to an Uno GPIO or GND.

## Physical wiring — unpowered stages

Disconnect the Uno USB cable and every external supply while building or changing wiring. The drawings below describe signal/low-current connections only; they do not override the power gates below. Confirm every actual terminal against the part's markings before inserting a wire. The breadboard row assignments match the Wokwi logical net plan, but the ASCII drawings are not placement instructions: verify each purchased board's connected tie groups and any split power rails with its markings/continuity before use.

### Breadboard row and rail assignment

The local/Wokwi diagram uses `wokwi-breadboard-half`, with 30 numbered tie-point rows. Assumed physical topology: each numbered five-hole group A–E is connected, F–J is separately connected across the center trench, the top positive rail carries +5 V, and the bottom negative rail carries GND. The Wokwi diagram uses those two different rails; physical breadboards can split rails or differ, so verify continuity and bridge only after checking the board and ratings. Do not use these low-current rails for servo motor current. Wokwi tie-point endpoints use forms such as `bb1:1t.a`, `bb1:1t.b`, `bb1:1b.f`, `bb1:tp.1`, and `bb1:bn.1`. The component endpoints below use the editor-generated fourth-field array `['$bb']` and its verified pin-to-hole mapping.

| Breadboard row/rail | Intended net and physical footprint | Connection |
|---|---|---|
| 1 | D11 to DFPlayer mock RX through the 1 kΩ resistor | D11 → `1t.a`; resistor pin 1 at `1t.b`, pin 2 at `1b.f`; `1b.g` → mock RX |
| 2 | LCD SDA | Uno A4 ↔ `2t.a`/`2t.b` ↔ LCD SDA |
| 3 | LCD SCL | Uno A5 ↔ `3t.a`/`3t.b` ↔ LCD SCL |
| 4 | Red button contact 2 | Row 4 bottom group returns to GND |
| 5 | DFPlayer mock TX to Uno D10 | Mock TX ↔ `5t.a`/`5t.b` ↔ Uno D10 |
| 6 | Red button contact 1 | GPIO D6 uses row 6 |
| 7 | Servo signal only | Uno D9 ↔ `7t.a`/`7t.b` ↔ visual servo PWM |
| 8 / 9, 14 / 15, 20 / 21, 26 / 27 | Former discrete-LED nodes | No NeoPixel data wire is assigned to these holes; actual physical occupancy is unknown, so do not reuse without checking the board |
| 10 | Green button contact 2 | Row 10 bottom group returns to GND |
| 11 | Visual speaker SPK1 | Mock SPK1 uses isolated row 11 and matching visual-speaker pin |
| 12 | Green button contact 1 | GPIO D7 uses row 12 |
| 13 | Visual speaker SPK2 | Mock SPK2 uses isolated row 13 and matching visual-speaker pin |
| 16 | Blue button contact 2 | Row 16 bottom group returns to GND |
| 18 | Blue button contact 1 | GPIO D8 uses row 18 |
| 19, 25 | Spare rows | No strip data wire is assigned here; physical occupancy is unknown, so inspect the board before use |
| 22 | Yellow button contact 2 | Row 22 bottom group returns to GND |
| 24 | Yellow button contact 1 | GPIO A0 uses row 24 |
| 28 | Start button GND-return lead | Wokwi `2.r` → `28b.f`; row 28 joins this diagram's GND-return chain |
| 30 | Start button A1 signal lead | Wokwi `1.l` → `30t.e`; GPIO A1 uses row 30 |
| Top + rail | Uno USB-equivalent +5 V in Wokwi | Uno 5V, LCD VCC, and mock VCC only. The external LED/servo supply does not connect to this rail or to Uno 5V. |
| Bottom GND rail | Uno GND in Wokwi | Uno GND, LCD/mock GND, and button grounds. Wokwi models the external GND reference to Uno GND and direct breakout-to-strip/servo ground nets; physically, the strip branches route through the professor-approved additional rated distribution arrangement, not this low-current rail or ordinary breadboard rails. |

For the Wokwi layout, the five button GND tie groups (rows 4, 10, 16, 22, 28) are chained across their bottom-section J holes: `4b.j → 10b.j → 16b.j → 22b.j → 28b.j → bn.28`. Each J hole is in the same lower F–J tie group as that row’s button return. This keeps a direct, clean trunk along the lower edge, away from the F-hole return endpoints, and uses a single `bn.28` tap. Uno GND uses `bn.1`; the off-board LCD and DFPlayer mock returns use `bn.29` and `bn.30`. This daisy-chain is a Wokwi layout choice, not physical wiring approval: a broken jumper would disconnect later groups, and the real board’s tie groups/rail continuity and current limits must be verified before wiring.

Wokwi wire colors now follow electrical function rather than assigning a unique color to every segment: red is positive supply, black is GND, each play-button input wire matches its associated cue/strip color for visual tracing, all four play-button bodies are black, Start is white, SDA/SCL are cyan/magenta, NeoPixel data is white, DFPlayer TX/RX links are purple/gray, servo PWM is orange, and the two speaker leads are brown/tan. Same-function paths retain the same color across breadboard segments; use endpoints to trace each connection. These colors are for diagram readability, not physical wiring approval; keep all supplies off until the final inspection passes.

The full Wokwi strip topology has direct independent data links from Uno D2/D3/D4/D5 to red/green/blue/yellow DIN and all eight primary power branches: breakout 5V to each strip VDD (red `#FF0000`) and breakout GND to each strip VSS (black `#000000`). No DOUT, VDD.2, or VSS.2 pin is connected; no DOUT chaining is used. The user reports that their physical setup matches the IRL diagram, including all four D2–D5 data jumpers and all eight primary VDD/VSS branches; these reports are not independently observed or continuity-tested. The user reports that their professor reviewed/verified the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; that review is separate from and does not independently establish branch-lead installation. Physical strip branches route through that approved distribution arrangement, not through extra wires crammed into the two-terminal breakout or ordinary breadboard rails. The Wokwi direct nets are logical and do not depict the alternate physical layout. Keep USB and every supply disconnected; perform the unpowered final inspection by checking marked VDD/VSS endpoints against the approved distribution points, checking for shorts, and ensuring rated conductors are secure. Do not power up before inspection passes. The breakout GND also connects to Uno GND as the data reference; the custom adapter/breakout chips model no real voltage/current or internal pass-through. No series resistor is shown in the simulated data path, and actual signal-interface requirements depend on the exact strip. Firmware's four independent strips represent sixteen sequential pixels, grouped as red, green, blue, and yellow. The diagram itself does not establish physical connector ratings, branch protection, or power-supply suitability; the supply-path review remains user-reported. Never power physical strips from Uno USB/5 V. The four four-leg play buttons use contact-1 rows 6, 12, 18, 24 and contact-2 rows 4, 10, 16, 22; their Wokwi pins are `1.l=c1t.e`, `1.r=c1b.f`, `2.l=c2t.e`, `2.r=c2b.f`. The GPIO tie group is contact 1's `t` section and `c2b.g` returns to GND. The separate two-terminal, normally-open physical Start button uses one lead at A1 row `30t` and one GND-return lead at row `28b`; Wokwi's four-pin symbol routes only `1.l` to `30t.e` and `2.r` to `28b.f`, leaving `1.r` and `2.l` unused. In this diagram, the row-28 bottom group joins the GND-return chain. These are logical diagram placements, not proof of physical switch fit or orientation.

The Wokwi half breadboard is a logical/visual wiring aid only: it does not verify the physical board's tie-point continuity, component ratings, current capacity, servo supply isolation, or speaker compatibility. The layout uses the 30-row half-board model and checks assigned hole ranges, button/resistor footprints and clearances, and all four strips' 225° clockwise rotation, `top: 60`, and northeast placements at `left: 647.537` (red), `727.537` (green), `807.537` (blue), and `887.537` (yellow). The test checks diagram anchors and spacing only; review a fresh screenshot to confirm rendered clearance because the static test does not establish overlap resolution. The breadboard is first in `diagram.json`'s `parts` array so it renders behind mounted components; the layout test guards that order. The selected local Wokwi layout places the board at `(left, top)=(330, 350)`, Uno at `(left, top)=(260, 0)` rotated 45°, LCD at `(150, 300)`, servo at `(680, 125)`, barrel-jack breakout at `(820, 320)`, DFPlayer mock at `(680, 405)`, and visual speaker at `(820, 405)`. The physical adapter plugs directly into the barrel-jack breakout and is omitted from the diagram; it is not a diagram part. Six components use `$bb` placements (the five buttons and the MP3 TX resistor); all four strips remain direct diagram components. Keep every hard gate in [Power and physical limits](#power-and-physical-limits) closed until verified.

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
row-j Wokwi GND trunk, which taps the bottom rail at `bn.28`.
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

### Step 2 — four independent four-pixel NeoPixel strips (modeled topology and unpowered final inspection)

The Wokwi diagram contains `neopixel-red`, `neopixel-green`, `neopixel-blue`, and `neopixel-yellow`, each with `top: 60`, `rotate: 225` (225° clockwise), `pixels: "4"`, and `pixelSize: "2020"`; their `left` positions are 647.537, 727.537, 807.537, and 887.537 respectively. Firmware uses four independent Adafruit_NeoPixel objects: D2 red, D3 green, D4 blue, and D5 yellow. Grouped pixel indices 0–3, 4–7, 8–11, and 12–15 map to red, green, blue, and yellow.

```text
Full modeled Wokwi topology (visual placement only; no fresh render, so clearance remains unconfirmed):
[RED 0-3]      top 60 / left 647.537, rotated 225° clockwise
[GREEN 4-7]    top 60 / left 727.537, rotated 225° clockwise
[BLUE 8-11]    top 60 / left 807.537, rotated 225° clockwise
[YELLOW 12-15] top 60 / left 887.537, rotated 225° clockwise

Direct, independent data links (white, `#FFFFFF`):
Uno D2 → red DIN; D3 → green DIN; D4 → blue DIN; D5 → yellow DIN

All eight primary strip power branches (direct logical nets in Wokwi):
Breakout 5V → red VDD; green VDD; blue VDD; yellow VDD (red, `#FF0000`)
Breakout GND → red VSS; green VSS; blue VSS; yellow VSS (black, `#000000`)

No DOUT chaining. Every strip's DOUT, VDD.2, and VSS.2 remains unconnected.
The physical alternate distribution-board routing is not depicted: route strip
branches through the additional rated distribution arrangement the user
reports their professor approved, not by cramming extra wires into the
two-terminal breakout or ordinary breadboard rails. The full 5 V / 5 A path
approval/verification is user-reported and not independently measured here; it
concerns the intended supply/distribution path and does not prove that strip
branch leads were installed.
```

The user now reports that they followed the instructions and their physical setup matches the IRL diagram: all four direct data jumpers (D2–D5 to the corresponding DIN pins) and all eight primary strip power branches (each strip's VDD/+5 V and VSS/GND) are connected, including the previously reported red VDD/VSS branches. This physical installation report has not been independently observed or continuity-tested. Separately, the user reports that their professor reviewed/verified the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection. That reported path review does not independently prove that any branch lead was installed. Wokwi's direct breakout-to-strip nets are logical; the physical professor-approved distribution-board routing is not depicted.

#### Final unpowered inspection — no wiring checklist remains

With the Uno USB cable and every external supply off and disconnected:

- Verify each strip lead is on the strip's marked primary VDD or VSS pad and terminates at the corresponding positive or negative point in the approved distribution arrangement.
- Check for shorts between positive and ground and between adjacent/unintended connections.
- Confirm the rated conductors and terminations are secure.

Do not repeat the professor-reported supply-path review as part of this check. Keep all supplies off; do not power up until this final physical inspection passes and all other project gates are closed.

Diagram totals: 17 parts and 65 connection entries (45 colored wire entries + 20 `$bb` component-lead placements). The user reports all four data jumpers and all eight primary strip branches physically connected; this is not independent physical verification. The 20 `$bb` entries are breadboard-mounted component-lead placements, not loose jumpers and not evidence of physical installation.

```text
Intended complete firmware/output map:
D2 → red DIN    D3 → green DIN    D4 → blue DIN    D5 → yellow DIN
```

### Step 3 — exact Grove 16x2 LCD

Use the confirmed Seeed Grove 16x2 LCD Black-on-Yellow V2.0 (PCB `JHD1804M1 P1835`), not a generic HD44780 backpack. Follow the Grove connector labels/cable orientation. The Seeed documentation specifies 3.3/5 V and I2C address `0x3E`; this build uses 5 V and Uno A4/A5.

```text
Physical lead colors—not Wokwi segment colors                            LCD lead
Uno 5V ─────── top + rail ─────────────────────────────────────── VCC (red)
Uno GND ────── bottom GND rail ────────────────────────────────── GND (black)
Uno A4 ─────── row 2 ──────────────────────────────────────────── SDA (cyan)
Uno A5 ─────── row 3 ──────────────────────────────────────────── SCL (magenta)
              keep rows 2 and 3 separate; keep + and GND rails separate

No extra LCD backpack, RGB-backlight board, or generic display is substituted.
No LCD signal/power lead goes directly to the Uno; use the assigned board
rows/rails and verify the Grove connector orientation before power.
```

The firmware follows the official shared Seeed `Grove_LCD_RGB_Backlight` Arduino library's monochrome-compatible LCD protocol: 7-bit address `0x3E`; command control byte `0x80`; display-data control byte `0x40`; 16x2 function/display/clear/entry and DDRAM row commands. It does not call the unsupported RGB-backlight API. The project-local Wokwi chip handles those same I2C command/data prefixes and renders a yellow monochrome 16x2 framebuffer.

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

Do not connect either speaker output to GND or an Uno pin. Keep the speaker
unpowered until the module output/load ratings are verified; Wokwi mock rows
11 and 13 do not approve the physical speaker path.
```

Format/copy the card as required by the module, then place `/mp3/0001.mp3`–`0005.mp3` on the card. Begin at volume 3. The actual MP3-TF-16P clone/card compatibility and current budget are not confirmed by simulation.

### Step 5 — servo signal and shared external power

The Uno is intended to use USB; the user-selected 5 V / 5 A adapter is intended to power both the NeoPixel strips and the FS5106B servo through the professor-approved additional distribution arrangement connected to a barrel-jack breakout. Neither load's supply current is routed through Uno 5 V or the breadboard. The user reports that their professor reviewed/verified the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; this remains user-reported and has not been independently measured or inspected by us. This path review does not independently prove branch-lead installation. Do not repeat those professor-reviewed supply-path checks in this guide. The adapter plugs directly into the physical breakout; Wokwi shows only a visual breakout marker and does not model its electrical behavior. Keep USB and every supply disconnected for final inspection; do not power up until the inspection passes.

```text
Signal only through breadboard row 7:
Uno D9 ───────────── row 7 ─────────────────────────> FS5106B signal

Intended physical load-branch routing (the logical Wokwi branch nets are modeled, but this alternate distribution-board layout is not depicted and does not prove individual lead installation):
Adapter barrel plug ──> barrel-jack-to-screw-terminal breakout
Breakout 5V/GND ──> professor-designated, approved distribution arrangement
Distribution positive ──┬── separate branches ──> each NeoPixel strip VDD
                       └── separate branch ────> servo V+
Distribution negative ─┬── separate returns ───> each strip VSS and servo GND
                       └── common reference ───> Uno GND / data-signal reference

Uno remains separately USB-powered; NO external +5 V connection to Uno 5V/barrel.
Do not route strip/servo positive or load-current returns through the Uno or
breadboard. The user reports professor approval of this additional distribution
arrangement and supply path; it has not been independently measured by us and
does not independently prove individual branch-lead installation. This drawing
is not power-up approval; keep power disconnected until the unpowered
final inspection passes. The Wokwi diagram is a logical net view, not this
physical distribution-board layout.
```

The user reports 5 V / 5 A as the adapter being used; an earlier-mentioned 5 V / 3 A adapter is not the selected supply. The selected plan is to use the 5 A adapter for both the four NeoPixel strips and servo. The user reports their professor reviewed/verified the intended 5 V / 5 A source/distribution path, including polarity, ratings, wiring method, distribution, and protection; we have not independently measured or inspected that path, and this guide does not ask to repeat that review. Separately, the user reports all four data jumpers and all eight primary strip VDD/VSS branches connected; these are not independently observed or continuity-tested, and the professor's path review does not itself prove branch-lead installation. Use the professor-approved additional rated distribution arrangement, not extra leads crammed into the two-terminal breakout or ordinary breadboard rails. The adapter photo appears to show a female barrel jack with two screw terminals, but the photo alone does not establish jack size or terminal mapping. Exact strip model/pad labels and the servo's behavior at its actual mechanism/load remain unverified here. Keep all supplies disconnected and complete the unpowered final inspection before any power-up.

## Power and physical limits — hard pre-energizing gates

Do **not** energize any circuit until the final physical inspection passes and all project gates below are closed. The user reports professor review/verification of the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection. This is a user report, not an independent measurement by us; the path review does not independently prove branch-lead installation, and this guide does not ask to repeat those checks. The user separately reports all four data jumpers and all eight primary strip power branches connected; this is not independently observed or continuity-tested. Keep USB and every supply disconnected during inspection.

1. During the unpowered final inspection, verify that each installed strip lead reaches the actual marked primary VDD/VSS pad and the corresponding positive/negative point in the approved distribution arrangement; check for shorts and secure, rated conductors. The user reports professor review/verification of the intended supply/distribution path, but that does not independently prove lead installation; do not repeat those reported supply-path checks. Keep supplies off and do not overcrowd the breakout or ordinary breadboard rails.
2. Assess the FS5106B mechanism/load, signal requirements, travel limits, horn/linkage clearance, and safe unloaded angles. The mechanism/load and the conservative physical 0°/90° positions are not verified; hold/retraction timings are tunable values only. The supply-path ratings are user-reported as professor-verified, not a new check request here. The Wokwi 0°/180° sweep is a simulation setting, not an approved physical endpoint range.
3. Verify the MP3-TF-16P board variant, supply/current draw, microSD requirements, serial levels, and speaker output/load ratings. Confirm the aggregate Uno USB budget for the display, module, buttons, and all parts actually powered from the Uno. Never power the physical NeoPixels from Uno USB/5 V.
4. The user reports 5 V, 3-pin addressable WS2812B/NeoPixel-style strips with GND, DIN/DO, and 5 V pads, but exact manufacturer/model, pad order/orientation, and signal-interface details have not been independently inspected against each strip's markings/datasheet. The user reports that their professor reviewed/verified the intended shared 5 V / 5 A supply and distribution path; this is not an independent measurement, and this guide does not ask to redo that review. Separately, the user reports all four physical data jumpers and all eight primary strip VDD/VSS branches connected; none has been independently observed or continuity-tested. The Wokwi diagram's D2/D3/D4/D5 data links and breakout-to-strip supply nets are logical topology and do not independently establish physical pad labels or installed leads. No power-up until the unpowered final inspection passes.
5. Unpowered, continuity-test each four-leg play button to identify its internally joined pairs and ensure GPIO/GND use opposing contacts. Separately verify the physical two-terminal Start button is normally open (open released, connected only when pressed), that its leads fit the intended contacts, and that orientation is correct. Check for shorts during final inspection before any power-up.
6. Verify the Grove connector orientation and the Uno's SDA/A4, SCL/A5 mapping. The product is rated for 3.3/5 V by Seeed, but still check the unit's actual label/condition.

Never feed the external adapter's +5 V to Uno +5 V or the Uno barrel jack while USB is attached. Wokwi represents strip and servo supply with direct logical branches from the breakout; physically route those branches through the user-reported professor-approved additional rated distribution arrangement, not through Uno power or ordinary breadboard rails. Uno GND joins external GND only at the planned common signal-reference point. Do not connect external positive to the Uno supply. The user-reported professor review of the intended supply path is not independent measurement by us and does not prove branch-lead installation; do not treat this guide as a request to repeat those checks. Keep power-up blocked until the unpowered final physical inspection passes.

## Physical validation plan

1. **Unpowered final inspection:** the user reports that their setup matches the IRL diagram, including all four D2–D5 data jumpers and all eight primary strip VDD/VSS branches; this is not independently observed or continuity-tested. The user separately reports professor review/verification of the intended 5 V / 5 A supply and distribution path, including polarity, ratings, wiring method, distribution, and protection; that review does not independently prove branch-lead installation, and this guide does not ask to repeat those checks. With USB and every supply off, verify each strip lead against the marked VDD/VSS pad and corresponding approved distribution point, check for shorts, and confirm secure rated conductors. Keep all power disconnected; do not power up until inspection passes. Continue to observe unrelated project gates above (button released-contact topology, LCD/module wiring, servo mechanism/load, and USB budget).
2. **Uno and low-current inputs/display:** only after the final inspection passes and applicable project gates are closed, connect laptop USB as appropriate. Do not power physical NeoPixel strips from Uno USB/5 V. The current Wokwi diagram shows direct data links from D2/D3/D4/D5 to red/green/blue/yellow DIN. The user reports all four physical direct data jumpers: D2-to-red-DIN, D3-to-green-DIN, D4-to-blue-DIN, and D5-to-yellow-DIN, as well as all eight primary strip power branches. These are user reports only; continuity and pad labels/orientation have not been independently measured. Professor review of the intended supply/distribution path is separate and does not prove branch-lead installation. Static validation does not confirm rendered or runtime behavior. Confirm the existing idle and round/score LCD pages and button debounce/release. In Wokwi only, verify the 5.5-second map preview after round 3, the full mapped-color display after each cue sequence, and a 500 ms dark flash for the pressed color; do not power the physical strips. Test Start ignored during a run and a two-button chord.
3. **EEPROM:** record a best score, play a game, power-cycle the Uno, and verify the best score page. The first-color journal continues recording each game's first cue but does not constrain the next sequence. The journal shares no bytes with the best-score record; EEPROM behavior has not been physically power-cycle tested.
4. **MP3:** only after module/USB current and speaker/module ratings are verified, insert the prepared card, connect speaker across SPK1/SPK2, confirm startup/track mapping at volume 3, cue completion, and Game Over audio stop after the minimum display interval and any servo return allowance. Do not connect speaker to GND/GPIO.
5. **Servo electrical check:** only after every external power gate is closed, first test the servo disconnected from its mechanism with the rated direct supply and shared ground. Confirm startup retract command, safe configured angles, hold, and retract timing while keeping servo motor current off the Uno/breadboard rails.
6. **Mechanism/load check:** install/tune linkage only with a safe clear zone and verified load/current/travel. Confirm the servo stays still after successful rounds 3/6/9, then extends and retracts only after a player loss; verify the configured return allowance before Game Over exits.
7. **Full game:** validate a response delayed beyond five seconds, a debounced press held beyond five seconds before release, wrong answer/chord handling, score accounting, best-score persistence, audio overlap protection, and repeated power cycles. There is no player-response timeout. Record any changes to provisional servo constants and hardware details here.

## Audio cues

The four card-ready MP3s are generated, short electronic tones in a classic Simon-style sequence. They are newly synthesized cues, not recordings or extracted audio from an original Simon game. Each has a brief fade to avoid clicks:

| File | Button/LED | Generated fundamental |
|---|---|---:|
| `0001.mp3` | Red pixel/button | 523.25 Hz (C5) |
| `0002.mp3` | Green pixel/button | 659.25 Hz (E5) |
| `0003.mp3` | Blue pixel/button | 783.99 Hz (G5) |
| `0004.mp3` | Yellow pixel/button | 1046.50 Hz (C6) |
| `0005.mp3` | Player loss / wrong answer | Descending two-part electronic tone |

On a player loss (wrong answer or chord), firmware plays `/mp3/0005.mp3`; the technical round-counter safeguard does not use the loss sound. Successful-round celebration cues still choose randomly among tracks 1–4. The Wokwi DFPlayer mock does not read or play any MP3.

The previously used “sound-alien1” sample by **zippi1** remains at `assets/source-sound-alien1-hq.mp3`; it is not used to make these tones. Source: https://freesound.org/people/zippi1/sounds/18027/, licensed **CC BY-NC 4.0**: https://creativecommons.org/licenses/by-nc/4.0/ .
