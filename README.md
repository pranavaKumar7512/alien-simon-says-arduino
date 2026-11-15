# Alien Simon Says — Arduino Uno R3

A complete Simon Says sketch for the confirmed **Arduino Uno R3**, with four generic play buttons and four independently driven four-pixel NeoPixel strips—one strip per red, green, blue, and yellow cue color—a separate Start button, the exact Seeed Grove 16x2 LCD Black-on-Yellow V2.0 / JHD1804M1 display, an MP3-TF-16P physical audio backend, an FS5106B positional servo, and a Wokwi DFPlayer protocol mock. The user reports the physical strips are 3-pin, 5 V addressable RGB WS2812B/NeoPixel-style strips with GND, DIN/DO, and 5 V pads; the exact brand/model, current draw, connectors, and supply suitability remain unverified.

> **Staged rewiring:** Uno D2–D5 connect directly to independent red/green/blue/yellow DIN; D9 directly drives servo PWM; no strip DOUT is connected. bb1 retains buttons, LCD, DFPlayer/resistor/speaker, and Uno logic GND. The physical 5 V / 5 A adapter is assumed plugged into the barrel jack and is omitted from Wokwi. The breakout's two visible `VCC` (+5V)/`GND` screw-terminal pins connect directly to bb2's separate rails at `tp.30`/`bn.30`; individual load taps and the single common-GND reference remain. External +5V stays isolated from Uno 5V. Physical polarity, ratings, and safety remain unverified; full-render clearance is unconfirmed.

> **Physical power is not approved by this README.** Wokwi shows only the visual breakout with `VCC` (+5V)/`GND` pins connected to distribution rails; it omits the physical adapter. The diagram does not verify plug fit, polarity, voltage/current, protection, physical continuity, or ratings. Keep everything unpowered until every hard gate in [Power and physical limits](#power-and-physical-limits) is closed.

## Project contents

- `alien-simon-says.ino` — nonblocking gameplay/state machine; both builds send DFRobotDFPlayerMini frames over SoftwareSerial D10/D11, drive sixteen NeoPixels on four independent four-pixel strips from D2–D5 with four Adafruit_NeoPixel objects, and drive the servo from Timer1 hardware PWM on D9/OC1A.
- `scripts/build-arduino.sh` — stages the sketch under Arduino CLI's required matching basename and builds physical and Wokwi firmware into the configured output folders.
- `scripts/run-wokwi-tests.py` — generates randomized, seed-replayable Wokwi scenarios and manages local previous-first-color metadata.
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
- `chips/barrel-jack-breakout.chip.c` / `.chip.json` — visual-only female DC barrel-jack-to-2-screw-terminal breakout; its only pins are `VCC` (+5V) and `GND`. The physical adapter plugs into the barrel jack but is omitted from the Wokwi diagram.
- `diagram.json`, `wokwi.toml` — Uno simulation with bb1 for buttons/LCD/DFPlayer and bb2 for external-load distribution/common GND. The diagram has 18 parts and 66 entries (46 colored wires plus 20 `$bb` placements). D2–D5 and D9 connect directly to their signal pins; no DOUT chaining. Teal from breakout `VCC` (+5V) and black from breakout `GND` run directly to bb2 `tp.30`/`bn.30`; individual load taps remain separate. The physical adapter is assumed plugged into the barrel jack and is not a Wokwi part. bb1 is at `(330, 350)`, bb2 at `(330, 590)`, Uno at `(260, 0)`, and breakout at `(820, 320)`. Rendered clearance remains unreviewed; no diagram or test establishes physical safety.

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

The LCD and DFPlayer mock use the Uno's 5 V/GND rails in Wokwi. The physical 5 V / 5 A adapter is assumed plugged directly into the barrel jack and is omitted from the diagram. The breakout's visible `VCC` (+5V) terminal connects directly to bb2 `tp.30`; its visible `GND` terminal connects directly to bb2 `bn.30`. The five separate load tap pairs use indices red `.25`, servo `.26`, green `.27`, blue `.28`, yellow `.29`; `bb1:bn.2` connects to `bb2:bn.2` as the single common-GND reference. bb1 remains the low-current button/LCD/DFPlayer and logic-ground board. External positive is not connected to Uno 5 V. D2–D5 directly drive their matching independent DIN pins and D9 directly drives servo PWM; no DOUT is chained. Physical signal compatibility, strip pinouts, power, current, and suitability remain unverified; this is not wiring approval. The visual breakout is not an electrical source or protection device. Never power physical strips or servo motor current from Uno USB/5 V. Wokwi lint and netlist tests validate structure/connectivity, not visual clarity, runtime behavior, or physical suitability. Review a fresh render for wire/component clearance. The shared adapter's combined load, connector polarity, breakout, branch wiring, protection, and all physical power paths remain subject to the hard gates below.

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
- Four independently driven NeoPixel strips contain sixteen addressable LEDs total: indices 0–3 are red, 4–7 green, 8–11 blue, and 12–15 yellow. During cue playback, only the mapped four-pixel group for the current cue lights; every group is off between cues. After the last cue, all four button-position groups illuminate in their current mapped colors and stay on while the player answers. Sequence cues stay lit for 2,000 ms from cue-on; an early natural audio-finished event does not shorten the light. At that deadline the firmware issues an idempotent DFPlayer Stop request to bound playback (harmless if the track already completed), then all strips remain off for the existing 180 ms gap. The physical module's exact Stop latency is not validated. In Wokwi, matching track numbers go to the DFPlayer mock; the mock has no MP3 decoder and plays no sound. On a debounced play-button press, only that color's mapped four-pixel group turns off for 500 ms while the other three groups remain lit; then the complete map is restored. The answer is still committed and checked only after button release, so a held button can remain down after the 500 ms flash. The 25 ms debounce, chord detection, and release-to-submit behavior remain. Players may wait indefinitely before answering and may hold a debounced answer indefinitely before releasing it. Held buttons during cue playback do not create button feedback; after the cues, the full map remains visible while the firmware waits for all buttons to be released. Two or more simultaneously debounced play buttons fail the run.
- The four controls are identified by physical position from left to right as Buttons 1–4; their casing colors have no gameplay meaning. The initial map is Button 1→Red, 2→Green, 3→Blue, 4→Yellow. After each three successfully completed rounds (3→4, 6→7, 9→10, …), a seed-derived shuffle creates a new one-to-one map for the next block; the cue sequence is unchanged. Each cue lights only its mapped group, all groups go dark between cues, and all four mapped colors are shown after the sequence. A pressed color's group then goes dark for 500 ms before the full map is restored. Repeating the exact previous full map is rejected, though individual assignments may repeat. A new game or restart restores the initial map and shows all four button-position LED groups simultaneously in their assigned cue colors for 5.5 seconds before Round 1, giving the player time to learn the button/color relationship. After each later remap, the celebration audio finishes first, then the same 5.5-second full-map preview appears before the next round. The LCD retains the existing main-branch pages and never displays the mapping. The separate mapping PRNG does not affect cue generation, and the Wokwi `button-remap` scenario verifies replayable maps and translated inputs. A wrong answer, chord, or the 32-bit technical round counter reaching its maximum ends the run.
- The final score is stored in Uno EEPROM when it improves the best score. Idle keeps `PRESS START` on the first row and alternates `YOUR` / `BEST` score values on the second row every three seconds. EEPROM behavior still needs a physical power-cycle check.
- Game Over after a player loss plays physical track 5 (`/mp3/0005.mp3`) or sends mock track command 5. Other Game Over exits (the technical round-counter safeguard) and successful-round celebrations choose randomly from physical tracks 1–4. The screen remains visible for at least three seconds and, after a player loss, until the servo's configured return allowance has elapsed; the firmware then sends Stop before returning to score pages. This is three seconds on the physical configuration and six seconds in Wokwi. Technical counter exhaustion ends the game without servo motion because it is not a player loss. Completion events are drained throughout Game Over.
- Successful rounds 3, 6, 9, … still play a random celebration audio cue, but do not move the servo. The servo extends only after a player loses through a wrong answer or chord, then returns to 0°. In Wokwi, its target changes to 180° for a 3-second hold, then to 0° for a separate 3-second return allowance. Physical builds retain the conservative, unverified settings of 90° extend, 0° retract, a 1-second hold, and a 1-second return allowance until the real FS5106B linkage endpoints and supply are verified. These are command-based intervals that include travel time; neither simulation nor elapsed time provides position feedback. The [Wokwi servo reference](https://docs.wokwi.com/parts/wokwi-servo) documents its range as 0°–180° with hard stops. Do not widen physical settings until the actual mechanism/load and supply are checked.
- There is no practical round cap. The firmware stops only if its 32-bit completed-round counter reaches `UINT32_MAX`, a technical overflow safeguard rather than a gameplay limit. SIMON's ten-symbol array is reused as a verifier buffer and does not limit the game sequence.

## Pin map — physical Uno R3

| Uno pin | Connection | Notes |
|---|---|---|
| D2 | Red NeoPixel strip data | Direct to red DIN; no series resistor or DOUT chaining. Physical signal compatibility remains unverified. |
| D3 | Green NeoPixel strip data | Direct to green DIN; no series resistor or DOUT chaining. Physical signal compatibility remains unverified. |
| D4 | Blue NeoPixel strip data | Direct to blue DIN; no series resistor or DOUT chaining. Physical signal compatibility remains unverified. |
| D5 | Yellow NeoPixel strip data | Direct to yellow DIN; no series resistor or DOUT chaining. Physical signal compatibility remains unverified. |
| D6, D7, D8, A0 | Generic play controls, Buttons 1–4 from left to right | `INPUT_PULLUP`; position—not casing color—identifies each control; pressed input connects to GND |
| A1 | Separate two-terminal, normally-open Start button | `INPUT_PULLUP`; its other lead returns to GND when pressed |
| A4 / A5 | Grove LCD SDA / SCL | I²C address `0x3E`; do not swap data and clock |
| D9 | FS5106B signal | Direct to servo PWM. Servo motor power uses its own bb2 rail-hole taps only after bb2 capacity and all power-path ratings are verified; never use Uno 5V or logic-only bb1 rails for servo motor current. If the actual bb2 is unsuitable, use an approved, rated distribution point instead. |
| D10 | Uno SoftwareSerial RX ← MP3-TF-16P TX | No connection to Uno D0/D1 |
| D11 | Uno SoftwareSerial TX → 1 kΩ series resistor → MP3-TF-16P RX | Start at module volume 3 |
| D12 | Unused | No tone/buzzer backend is used in Wokwi or on the physical build |
| 5V / GND | Visual-only breakout supply branches | The visible breakout `VCC` (+5V)/`GND` terminals connect directly to bb2 `tp.30`/`bn.30`; red/servo/green/blue/yellow load taps use matching separate positive/negative rail holes 25–29. The bb1-to-bb2 common-GND reference is `bb1:bn.2`→`bb2:bn.2`. External +5 V stays isolated from Uno 5V. The physical adapter is omitted from Wokwi; verify its output, connector polarity, and all ratings before power. |
| D0 / D1 | USB serial diagnostics | Reserved; keep free of MP3 wiring |
| A2 / A3 | Unused | No random-number hardware is connected |

Timer1 is dedicated to the D9/OC1A servo signal. It generates 50 Hz Fast PWM using a 0.5 µs timer tick and a 39999 TOP; servo targets use the standard angle-to-pulse range with the Servo library's ~2 µs trim retained. The timer continues producing active pulses while the servo is parked—there is no detach operation. Timer1 also owns D10/OC1B's PWM timing, so do not use D9/D10 `analogWrite()` or code that reconfigures Timer1. This does not change the D10 SoftwareSerial RX / D11 TX audio map.

The firmware runs a 500 ms power-on self-test in `setup()` that lights all sixteen pixels simultaneously in four mapped-color groups (0–3 red, 4–7 green, 8–11 blue, 12–15 yellow), then clears them and enters IDLE. Separately, each game start shows the initial button/color map for 5.5 seconds before Round 1. Sequence cues light only their mapped group and leave all groups dark between flashes; after the sequence, all four mapped colors stay lit, with the pressed color's group briefly dark for 500 ms on each button press. The user reports 5 V, 3-pin addressable WS2812B/NeoPixel-style strips, with pads labeled GND, DIN/DO, and 5 V; confirm each actual strip's model, pin labels, and datasheet before wiring. The selected 5 V / 5 A adapter is planned to be shared between strips and servo, but its combined load/current limit, connector polarity, breakout, branch distribution, protection, and wire ratings remain unverified. The visual-only breakout marker is not evidence that the physical topology is safe. Never power physical strips from Uno USB or Uno 5 V; physical power-up remains blocked until every applicable electrical requirement is verified. Adafruit's [NeoPixel best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices) do not substitute for checking the actual strips' ratings. Play-button inputs use the Uno's internal pull-ups, so no button is wired to +5 V.

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

Disconnect the Uno USB cable and every external supply while building or changing wiring. The drawings below show the planned signal and power topology, but do not override the power gates below or certify physical suitability. Confirm every actual terminal against the part's markings before inserting a wire. The breadboard row assignments match the Wokwi logical net plan, but the ASCII drawings are not placement instructions: verify each purchased board's connected tie groups and any split power rails with its markings/continuity before use.

### Breadboard row and rail assignment

The local/Wokwi diagram uses `wokwi-breadboard-half`, with 30 numbered tie-point rows. Assumed physical topology: each numbered five-hole group A–E is connected, F–J is separately connected across the center trench, the top positive rail carries +5 V, and the bottom negative rail carries GND. In the canonical diagram, the breakout `VCC` (+5V)/`GND` feed bb2's separate positive/negative rails, and each strip and servo has its own rail-hole tap. bb1 remains the button/LCD/DFPlayer low-current logic and logic-ground reference board; the planned bb1-to-bb2 GND link is a reference, not a load-current route. Physical breadboards can split rails or differ, so verify continuity and ratings first. The user-reported bb2 rating is not independently verified: identify the exact board/rail rating and confirm combined current capacity before any physical power. If bb2 is unsuitable, use an approved, rated distribution point instead. Wokwi tie-point endpoints use forms such as `bb1:1t.a`, `bb1:1t.b`, `bb1:1b.f`, `bb1:tp.1`, and `bb1:bn.1`. The component endpoints below use the editor-generated fourth-field array `['$bb']` and its verified pin-to-hole mapping.
Unless explicitly prefixed `bb2:`, row numbers below refer to bb1. bb1 row 7 is unused. bb2 numbered tie-point rows carry no data or PWM nets; signal pins connect directly between the Uno and their loads. bb2 is reserved for external-load distribution rails and the single common-GND reference.

| Breadboard row/rail | Intended net and physical footprint | Connection |
|---|---|---|
| 1 | D11 to DFPlayer mock RX through the 1 kΩ resistor | D11 → `1t.a`; resistor pin 1 at `1t.b`, pin 2 at `1b.f`; `1b.g` → mock RX |
| 2 | LCD SDA | Uno A4 ↔ `2t.a`/`2t.b` ↔ LCD SDA |
| 3 | LCD SCL | Uno A5 ↔ `3t.a`/`3t.b` ↔ LCD SCL |
| 4 | Red button contact 2 | Row 4 bottom group returns to GND |
| 5 | DFPlayer mock TX to Uno D10 | Mock TX ↔ `5t.a`/`5t.b` ↔ Uno D10 |
| 6 | Red button contact 1 | GPIO D6 uses row 6 |
| `bb1:7` | Spare row | No servo PWM; D9 connects directly to the servo signal pin. |
| 8 / 9, 14 / 15, 20 / 21, 26 / 27 | Former discrete-LED nodes | No NeoPixel data wire is assigned to these holes; actual physical occupancy is unknown, so do not reuse without checking the board |
| 10 | Green button contact 2 | Row 10 bottom group returns to GND |
| 11 | Visual speaker SPK1 | Mock SPK1 uses isolated row 11 and matching visual-speaker pin |
| 12 | Green button contact 1 | GPIO D7 uses row 12 |
| 13 | Visual speaker SPK2 | Mock SPK2 uses isolated row 13 and matching visual-speaker pin |
| 16 | Blue button contact 2 | Row 16 bottom group returns to GND |
| 18 | Blue button contact 1 | GPIO D8 uses row 18 |
| `bb1:19`, `bb1:25` | Spare rows | Unused; D9 does not route through a breadboard row. |
| `bb2` tie-point rows 1–30 | No signal nets | bb2 is reserved for the external load distribution rails and common-GND reference; data/PWM bypasses bb2. |
| 22 | Yellow button contact 2 | Row 22 bottom group returns to GND |
| 24 | Yellow button contact 1 | GPIO A0 uses row 24 |
| 28 | Start button GND-return lead | Wokwi `2.r` → `28b.f`; row 28 returns separately to `bb1:bn.7`. |
| 30 | Start button A1 signal lead | Wokwi `1.l` → `30t.e`; GPIO A1 uses row 30 |
| Top + rail | Uno USB-equivalent +5 V in Wokwi | Uno 5V, LCD VCC, and mock VCC only. External +5 V stays isolated from Uno 5V and bb1. |
| Bottom GND rail | Uno GND in Wokwi | Uno GND and existing LCD/mock/button returns. One `bb1:bn.2` → `bb2:bn.2` wire references external GND; bb2 carries the separate load returns. |

Each button GND-return row separately taps bb1's bottom rail (`4b.j`→`bn.3`, `10b.j`→`bn.4`, `16b.j`→`bn.5`, `22b.j`→`bn.6`, `28b.j`→`bn.7`), so each individual breadboard hole endpoint has at most one diagram wire. Start's row-28 GND return taps `bb1:bn.7`; Uno GND uses `bb1:bn.1`; the off-board LCD and DFPlayer mock returns use `bn.29` and `bn.30`. `bb1:bn.2`→`bb2:bn.2` is the single common-ground reference between bb1 and bb2. Rail taps and board continuity still require physical verification.

Wokwi wire colors identify electrical function: red marks positive load distribution, teal marks the external breakout `VCC` (+5V) feed to bb2, and black is GND. Play-button input wires match their associated cue/strip color; all four play-button bodies are black; Start is white; SDA/SCL are cyan/magenta; NeoPixel data is white; DFPlayer TX/RX links are purple/gray; servo PWM is orange; speaker leads are brown/tan. Use endpoints to trace connections. Colors are for diagram readability, not physical wiring approval; verify actual connections and keep power-up blocked until physical ratings and supply paths are confirmed.

The Wokwi data topology connects Uno D2/D3/D4/D5 directly to red/green/blue/yellow DIN, respectively, and connects D9 directly to servo PWM. No strip DOUT is connected to another strip's DIN; the selected path uses no series resistors. bb2 carries only the external load distribution and common-GND reference: breakout `VCC` (+5V) → `bb2:tp.30`; red/servo/green/blue/yellow VDD/V+ taps → `bb2:tp.25/.26/.27/.28/.29`; breakout GND → `bb2:bn.30`; matching VSS/GND taps → `bb2:bn.25/.26/.27/.28/.29`; `bb1:bn.2` → `bb2:bn.2` is the sole Uno/external-GND reference. External +5 V remains isolated from Uno 5V and positive/negative rails remain separate. The user reports bb2 is rated, but exact physical board/rail rating and combined current capacity remain unverified; verify these and all load/connector/wire ratings before power. If bb2 is unsuitable, use an approved, rated distribution point. This is not power-up approval. Wokwi topology does not prove physical pin fit, continuity, signal compatibility, or safety.

The Wokwi breadboards are logical/visual wiring aids only: they do not verify physical tie-point continuity, component ratings, current capacity, servo supply isolation, or speaker compatibility. The layout test checks the 30-row half-board model, assigned hole ranges, button/resistor footprints and clearances, strip rotations and spacing, component anchors, and part order only; review a fresh screenshot for rendered clearance. The layout places bb1 at `(330, 350)`, bb2 at `(330, 590)`, Uno at `(260, 0)`, LCD at `(150, 300)`, servo at `(680, 125)`, breakout at `(820, 320)`, DFPlayer mock at `(680, 405)`, and speaker at `(820, 405)`; the physical adapter is omitted. Six components use `$bb` placements (the five buttons and MP3 TX resistor); four strips remain direct components. Keep every hard gate in [Power and physical limits](#power-and-physical-limits) closed until verified.

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
D6 is tied to contact 1's row-6 top group; the row-4 bottom group connects separately to bb1 GND rail tap `bb1:bn.3`.
Repeat only for the other play buttons at contact rows (12,10), (18,16), and
(24,22) for D7, D8, and A0. Released GPIO and GND contacts stay separate;
pressing bridges them. The sketch uses INPUT_PULLUP, not external +5 V.

Start is physical 2-terminal normally-open: one lead → A1 / `30t`; the other → GND return / `28b`.
Wokwi still draws four symbol pins, but routes only `1.l` → `30t.e` and `2.r` → `28b.f`; `1.r` and `2.l` are intentionally unused. Row 28 returns separately to bb1:bn.7. Each button GND row separately taps bb1:bn.3–.6; bb1:bn.2 → bb2:bn.2 is the one bb1-to-bb2 common-ground reference. Verify physical rail continuity before use.
```

| Control | Uno input | Other contact |
|---|---:|---|
| Button 1 (leftmost) | D6 | GND |
| Button 2 | D7 | GND |
| Button 3 | D8 | GND |
| Button 4 (rightmost play button) | A0 | GND |
| Start | A1 | GND |

### Step 2 — four independent four-pixel NeoPixel outputs (Wokwi preview only)

This describes the simulation, not physical build instructions. Each `wokwi-led-strip` has `pixels: "4"`, `rotate: 225` (225° clockwise), and the `pixelSize: "2020"` rendering option. Four Adafruit_NeoPixel instances each drive one strip; logical pixels 0–3, 4–7, 8–11, and 12–15 map to local pixels 0–3 on the red, green, blue, and yellow strips respectively:

```text
Wokwi strips rotated 225° clockwise at `top: 60` in the northeast group, ordered red/green/blue/yellow at `left` 647.537/727.537/807.537/887.537 (80 Wokwi units apart), intended just above/right of the servo (visual placement only; no updated full render is available, so review a fresh screenshot before claiming overlap is resolved):
[RED 0-3]   [GREEN 4-7]   [BLUE 8-11]   [YELLOW 12-15]

Direct independent data nets connect each Uno output to its matching DIN (no DOUT-to-DIN chaining and no series resistors in the selected path):
Uno D2 → red DIN
Uno D3 → green DIN
Uno D4 → blue DIN
Uno D5 → yellow DIN

The physical adapter is assumed plugged into the barrel jack and is omitted from Wokwi. The visible breakout terminal wires are:
Breakout VCC (+5V) → bb2:tp.30 → separate rail taps bb2:tp.25/.26/.27/.28/.29 to red/servo/green/blue/yellow VDD/V+
Breakout GND → bb2:bn.30 → separate rail taps bb2:bn.25/.26/.27/.28/.29 to red/servo/green/blue/yellow VSS/GND
bb1:bn.2 → bb2:bn.2 is one common GND reference for Uno data signals; Uno 5V remains isolated
```

Each strip's DOUT is left unconnected; Uno D2–D5 directly connect to matching red/green/blue/yellow DIN pins, and Uno D9 directly connects to servo PWM. The selected data path uses no series resistors. The Wokwi diagram omits the physical adapter, which is assumed plugged into the barrel jack; the breakout's two visible `VCC` (+5V)/`GND` terminals wire directly to bb2. The breakout chip is a visual-only marker, not an electrical source, current limiter, or proof of continuity. Physical strip compatibility, load/current budget, connectors, branch wiring, protection, and supply topology remain unverified; this is not wiring or power-up approval. Keep the hardware unpowered until every applicable gate in [Power and physical limits](#power-and-physical-limits) is closed.

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

The Uno USB supplies the Uno. The user-selected 5 V / 5 A adapter is intended to power both the strips and FS5106B through bb2's separate positive and negative rails, not through Uno 5V or bb1's low-current logic/reference paths. Each strip and servo has its own bb2 rail-hole tap. The user reports bb2 is rated and directs this routing, but the exact physical model/rail rating and combined current capacity are unverified, as are external terminal/wire/connector ratings, protection, and actual load demand. Keep power off until each rating and the adapter polarity/output are verified. If the actual bb2 is unsuitable, use an approved, rated distribution point. Wokwi only depicts topology; it does not model electrical behavior or approve power-up.

```text
Signal direct to the servo input:
Uno D9 ─────────────────────────────────────────> FS5106B signal

Planned shared external 5 V / 5 A adapter (combined capacity unverified):
Adapter barrel plug → barrel-jack-to-screw-terminal breakout
Breakout VCC (+5V) → bb2:tp.30 → separate rail taps bb2:tp.25/.26/.27/.28/.29 to red/servo/green/blue/yellow VDD/V+
Breakout GND → bb2:bn.30 → separate rail taps bb2:bn.25/.26/.27/.28/.29 to red/servo/green/blue/yellow VSS/GND
bb1:bn.2 → bb2:bn.2 is one common GND reference for Uno data signals.
Uno remains laptop-USB powered. External +5 V is isolated from Uno 5V; positive and negative rails stay separate.
Each breakout terminal and each load/component pin has one wire. The user reports bb2 is rated and directs it for combined-load distribution; exact physical model/rail rating and current capacity, terminal/wire/connector ratings, protection, and load demand still require verification before power-up. If the actual board is unsuitable, use an approved, rated distribution point. Keep physical power off; this diagram is not approval.
```

The user reports 5 V / 5 A as the adapter being used; an earlier-mentioned 5 V / 3 A adapter is not the selected supply. The selected plan is to use the 5 A adapter for both the four NeoPixel strips and servo. The user's photo appears to show a female barrel jack with two screw terminals, but does not establish jack size, center/sleeve-to-terminal mapping, polarity, or ratings. The adapter output/polarity, breakout terminal ratings, wire ratings, overcurrent protection, servo current at the real load, strip current at configured brightness, and combined budget remain unverified. No fuse rating or final safe hookup is asserted here.

## Power and physical limits — hard pre-energizing gates

Do **not** energize any circuit until all applicable checks are resolved from the exact parts' markings/datasheets and rated components:

1. Measure/confirm the selected 5 V / 5 A adapter's output connector, polarity, and regulated output; verify its plug fits the photographed female jack, identify which screw terminal connects to the barrel center versus sleeve while everything is unpowered, and confirm breakout terminals, conductors, and overcurrent protection are rated for the combined strip/servo load and fault current. Do not infer safety from the adapter's 5 A label.
2. Verify the FS5106B's voltage, stall/start current at the actual mechanism/load, supply suitability, signal requirements, travel limits, horn/linkage clearance, and safe unloaded angles. The mechanism/load and the conservative physical 0°/90° positions are not verified; hold/retraction timings are tunable values only. The Wokwi 0°/180° sweep is a simulation setting, not an approved physical endpoint range.
3. Verify the MP3-TF-16P board variant, supply/current draw, microSD requirements, serial levels, and speaker output/load ratings. Confirm the aggregate Uno USB budget for the display, module, buttons, and all parts actually powered from the Uno. Never power the physical NeoPixels from Uno USB/5 V.
4. The user reports 5 V, 3-pin addressable WS2812B/NeoPixel-style strips with GND, DIN/DO, and 5 V pads, but exact manufacturer/model, current requirements at configured brightness, pad order/orientation, and signal-interface details are still unverified against each strip's markings/datasheet. The selected data path directly connects Uno D2/D3/D4/D5 to red/green/blue/yellow DIN, respectively, with no series resistors and no DOUT chaining; verify that the actual strip interfaces are compatible with direct Uno signals before any signal test. Verify the selected shared 5 V / 5 A adapter can handle the combined worst-case strip load and servo stall/start current, and verify protection, conductors, connectors, and distribution before considering power-up. No physical strip power-up is currently authorized.
5. Unpowered, continuity-test each four-leg play button to identify its internally joined pairs and ensure GPIO/GND use opposing contacts. Separately verify the physical two-terminal Start button is normally open (open released, connected only when pressed), that its leads fit the intended contacts, and that orientation is correct. Check for shorts before connecting USB.
6. Verify the Grove connector orientation and the Uno's SDA/A4, SCL/A5 mapping. The product is rated for 3.3/5 V by Seeed, but still check the unit's actual label/condition.

Never feed the external adapter's +5 V to Uno +5 V or the barrel jack while USB is attached. External positive/negative feed bb2's separate rails, with an individual rail-hole tap for each strip and servo. bb1 remains the low-current logic/reference board; bb1 GND joins external GND only at the planned common signal-reference point. Keep servo motor current off Uno 5V and logic-only bb1 rails. The user-reported bb2 rating is not independently verified: identify the exact physical board/rail rating and confirm combined current capacity, all other ratings, and protection before power-up. If bb2 is unsuitable, use an approved, rated distribution point.

## Staged physical validation plan
Never feed the external adapter's +5 V to Uno +5 V or the barrel jack while USB is attached. External positive and Uno 5V remain isolated; the positive rail is separate from negative. Load current is distributed through bb2 rail taps, while bb1 GND joins bb2 GND only through the planned single reference wire. The user-reported bb2 rating is not independently verified: identify the exact board and confirm its current budget, all terminal/wire/connector ratings, protection, and combined load before power-up.
1. **Unpowered inspection:** close every applicable gate above; verify the pin map, button released-contact topology, LCD markings, module wiring/card contents, servo ratings, isolation, and absence of shorts. Confirm each reported 5 V addressable strip's model, pad labels/orientation, and current requirements; verify the shared adapter, output distribution, branches, protection, and load budget. Do not connect strip or servo power until those checks pass.
2. **Uno and low-current inputs/display:** only after independently verifying the USB budget for the attached Uno/display/module/buttons and other Uno-powered parts, connect laptop USB. Do not power the physical NeoPixel strip from Uno USB/5 V; strip hardware power-up remains blocked. The four independent four-pixel strips can be checked in Wokwi only; physical signal compatibility remains unverified. Confirm the existing idle and round/score LCD pages and button debounce/release. In Wokwi only, verify the 5.5-second map preview after round 3, the full mapped-color display after each cue sequence, and a 500 ms dark flash for the pressed color; do not power the physical strips. Test Start ignored during a run and a two-button chord.
3. **EEPROM:** record a best score, play a game, power-cycle the Uno, and verify the best score page. The first-color journal continues recording each game's first cue but does not constrain the next sequence. The journal shares no bytes with the best-score record; EEPROM behavior has not been physically power-cycle tested.
4. **MP3:** only after module/USB current and speaker/module ratings are verified, insert the prepared card, connect speaker across SPK1/SPK2, confirm startup/track mapping at volume 3, cue completion, and Game Over audio stop after the minimum display interval and any servo return allowance. Do not connect speaker to GND/GPIO.
5. **Servo electrical check:** only after every external power gate is closed, first test the servo disconnected from its mechanism using its own bb2 rail-hole taps (or an approved, rated distribution point if bb2 is unsuitable) and the planned shared ground reference. Confirm startup retract command, safe configured angles, hold, and retract timing while keeping servo motor current off Uno 5V and logic-only bb1 rails.
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
