# Alien Simon Says — Arduino Uno R3

A complete Simon Says sketch for the confirmed **Arduino Uno R3**, with four colored play buttons and four separate chained four-pixel NeoPixel strips—one strip per red, green, blue, and yellow button color—a separate Start button, the exact Seeed Grove 16x2 LCD Black-on-Yellow V2.0 / JHD1804M1 display, an MP3-TF-16P physical audio backend, an FS5106B positional servo, and a Wokwi DFPlayer protocol mock. The exact physical NeoPixel strip parts, pinouts, ratings, and electrical requirements are unverified.

> **Physical power is not approved by this README.** Several part-specific ratings and connectors remain unverified. Keep everything unpowered until every hard gate in [Power and physical limits](#power-and-physical-limits) is closed. The Wokwi circuit is a simulation, not a safe physical wiring reference for servo power.

## Project contents

- `alien-simon-says.ino` — nonblocking gameplay/state machine; both builds send DFRobotDFPlayerMini frames over SoftwareSerial D10/D11, drive sixteen NeoPixels across four chained four-pixel strips from D2 with one Adafruit_NeoPixel object, and drive the servo from Timer1 hardware PWM on D9/OC1A.
- `scripts/build-arduino.sh` — stages the sketch under Arduino CLI's required matching basename and builds physical and Wokwi firmware into the configured output folders.
- `scripts/run-wokwi-tests.py` — generates randomized, seed-replayable Wokwi scenarios and manages the local previous-first-color state file.
- `first_color_journal.h` — CRC/commit-checked, wear-levelled Uno EEPROM ring for the previous game's first color, separate from the best-score record.
- `game_sequence.h` — the deterministic, seed-replayable shuffled-bag generator used by Wokwi tests; physical sequence generation uses the third-party SIMON library instead.
- Physical and Wokwi builds use Rob Tillaart's SIMON library for sequence storage and answer verification. Physical generation uses the library's `micros()`-seeded Arduino PRNG; Wokwi retains host-seeded replayable sequences.
- `servo_celebration_config.h` — shared Game Over servo angle/timing settings and Timer1 pulse conversion for physical and Wokwi builds.
- `sdcard/mp3/0001.mp3`–`0004.mp3` — card-ready button cues.
- `assets/source-sound-alien1-hq.mp3` — attributed source sample.
- `SHA256SUMS` — verified SHA-256 hashes for all five copied audio assets.
- `chips/grove-jhd1804.chip.c` / `.chip.json` — local I2C/framebuffer model for the specified Grove/JHD1804 LCD, not a substitute display.
- `chips/dfplayer-mock.chip.c` / `.chip.json` — UART protocol mock for volume, track, stop, and simulated track-finished events; it does not decode or play the copied MP3 files.
- `chips/visual-speaker.chip.c` / `.chip.json` — separate two-terminal component named `8 Ω / 0.5 W — no playback`; it is a visual pinout only.
- `diagram.json`, `wokwi.toml` — Uno simulation with one 30-row half breadboard, four vertically rotated `wokwi-led-strip` parts (four pixels each) centered by diagram coordinates above their matching buttons, direct D2 to red-strip DIN and DOUT-to-DIN chaining in R/G/B/Y order, and Wokwi-only simulated supply-rail endpoints. The `pixelSize: "2020"` setting is a diagram rendering choice, not a verified physical package. The diagram also has five `wokwi-pushbutton-6mm` buttons, the LCD model, DFPlayer mock, no-playback speaker model, and a visual-only servo; there is no buzzer. Button pins and the MP3 TX resistor use `$bb` placements/tie points. Simulated rails and unknown strip ratings are not physical wiring or safety evidence.

## Build and run

Host-tool prerequisites: install [Arduino CLI](https://docs.arduino.cc/arduino-cli/installation/) for firmware builds; [Wokwi CLI](https://docs.wokwi.com/wokwi-ci/cli-installation) is needed for diagram lint, custom-chip builds, and runtime scenarios. The validation commands below also assume Bash, GCC (`gcc`), Python 3.8 or newer, and `sha256sum` are on `PATH` (for example, Git Bash plus a GCC toolchain). Runtime scenarios additionally require a valid `WOKWI_CLI_TOKEN`.

This project was built with Arduino CLI, Arduino AVR Boards 1.8.8, `DFRobotDFPlayerMini` 1.0.6, and `Adafruit NeoPixel` 1.15.5. Install any missing AVR core/libraries once after installing Arduino CLI:

```sh
arduino-cli core update-index
arduino-cli core install arduino:avr@1.8.8
arduino-cli lib install "DFRobotDFPlayerMini@1.0.6"
arduino-cli lib install "Adafruit NeoPixel@1.15.5"
arduino-cli lib install "SIMON@0.1.5"
```

The sketch has no Servo-library build dependency: D9/OC1A uses Timer1 Fast PWM mode 14 with a 16 MHz clock, prescaler 8, `ICR1=39999` (20 ms frame), and `OCR1A` pulse widths in 0.5 µs ticks. This hardware PWM continues without interrupt servicing, avoiding SoftwareSerial's interrupt blocking stretching servo pulses. The sketch retains the Servo library's default 544–2400 µs angle mapping and approximately 2 µs trim. Timer1 is reserved for this servo output; do not use `analogWrite()` on D9/D10 or another library/configuration that takes over Timer1. Both firmware builds use the existing DFRobot library and SoftwareSerial; the Wokwi diagram connects those same serial pins to the custom UART mock. The sketch does not require installing the Grove library: it sends the documented Grove LCD command/data protocol over `Wire` directly.

From this folder (Git Bash on the development machine):

```sh
sha256sum -c SHA256SUMS
bash scripts/build-arduino.sh
wokwi-cli chip compile --output chips/dfplayer-mock.chip.wasm chips/dfplayer-mock.chip.c
wokwi-cli chip compile --output chips/visual-speaker.chip.wasm chips/visual-speaker.chip.c
wokwi-cli lint --warnings-as-errors .
gcc -std=c99 -Wno-attributes tests/test_grove_jhd1804.c -o build/test_grove_jhd1804 && build/test_grove_jhd1804
gcc -std=c99 -Wno-attributes tests/test_dfplayer_mock.c -o build/test_dfplayer_mock && build/test_dfplayer_mock
gcc -std=c99 tests/test_audio_completion_filter.c -o build/test_audio_completion_filter && build/test_audio_completion_filter
gcc -std=c99 tests/test_player_led_feedback.c -o build/test_player_led_feedback && build/test_player_led_feedback
gcc -std=c99 tests/test_first_color_journal.c -o build/test_first_color_journal && build/test_first_color_journal
gcc -std=c99 tests/test_game_sequence.c -o build/test_game_sequence && build/test_game_sequence
gcc -std=c99 tests/test_servo_celebration_config.c -o build/test_servo_celebration_config_physical && build/test_servo_celebration_config_physical
gcc -std=c99 -DWOKWI_SIM tests/test_servo_celebration_config.c -o build/test_servo_celebration_config_wokwi && build/test_servo_celebration_config_wokwi
python3 tests/test_diagram_led_button_layout.py
python3 tests/test_diagram_breadboard_nets.py
python3 tests/test_wokwi_test_runner.py
python3 scripts/run-wokwi-tests.py --scenario all
```

The first build is the physical Uno firmware. The second is the default Wokwi build; unless overridden, it injects a new nonzero host-generated seed at each build and prints it. Re-running the same firmware image intentionally repeats its sequence; use `WOKWI_INITIAL_SEED=<seed> bash scripts/build-arduino.sh` to rebuild a replayable image. Randomized automation recompiles a Wokwi image with a per-run logged seed and prior-first-color macro. The mock checks the 10-byte DFRobot frame/header/checksum, handles volume/play/stop, and schedules configurable completion events, but never reads the copied MP3 files or plays sound. The separate speaker has no playback behavior; no buzzer or `tone()` backend is used. Host tests cover protocol parsing, checksums, completion cancellation, the LCD model, four chained strips with grouped 16-pixel NeoPixel feedback, first-color journal integrity/wear-leveling, sequence selection, loss-gated servo targets, and exact breadboard diagram nets. `python3 scripts/run-wokwi-tests.py --scenario all` generates randomized matching button scenarios, prints replay commands, stores the Wokwi previous-first-color state in `.wokwi-sequence-state.json`, and saves transcripts/manifests under `build/wokwi-tests/`. Use `--scenario first-round` for one test. To reproduce a run, use the printed seed and previous-color arguments with `--no-persist`. Runtime scenarios require a valid `WOKWI_CLI_TOKEN`; Wokwi's monthly CI-minute quota can also block them. Wokwi simulation does **not** validate physical NeoPixel current/power, actual DFPlayer playback, speaker output/current, external servo power/travel/load, or the real LCD hardware. Official interface references: [Wokwi Custom Chip UART API](https://docs.wokwi.com/chips-api/uart), [custom chip JSON](https://docs.wokwi.com/chips-api/chip-definition), [automation scenarios](https://docs.wokwi.com/wokwi-ci/automation-scenarios), [Wokwi CLI usage/token requirement](https://docs.wokwi.com/wokwi-ci/cli-usage), and [Wokwi LED strip part](https://docs.wokwi.com/parts/wokwi-led-strip).

### Wokwi audio model

The Uno's D11 SoftwareSerial TX reaches the custom DFPlayer mock RX (through the diagram's 1 kΩ signal resistor), and mock TX returns to Uno D10 SoftwareSerial RX. The mock parses the real DFRobot 9600-baud command frames, accepts volume/play/stop, and sends a checksummed `0x3D` finish event after the configured simulation delay. Stop cancels pending completion. It has no SD-card audio decoder and emits no sound. The separate two-terminal part is named exactly `8 Ω / 0.5 W — no playback`; it is wired only across mock `SPK1`/`SPK2`, never to Uno GPIO or GND.

The mock's VCC/GND links through the breadboard's top +5 V rail and bottom GND rail to the Uno are **Wokwi-only**. All four strips' input-side VDD/VSS pins use the simulated rails; D2 connects directly to red-strip DIN, then each strip's DOUT connects directly to the next strip's DIN in R/G/B/Y order. Wokwi has no series resistor in this data path. Runtime behavior has not been confirmed, and the earlier resistor path has not been proven to cause the reported failure. The existing physical guidance remains conditional: a 440 Ω series path (two 220 Ω resistors) is described before the first verified physical strip's DIN, but the physical strips, pinouts, power, current, and suitability are unverified and this is not wiring approval. Firmware addresses pixels 0–3 as red, 4–7 green, 8–11 blue, and 12–15 yellow. The simulated rails are fixtures only: do not transfer them to hardware or power physical strips from Uno USB/5 V. The five 6 mm buttons and the MP3 TX signal resistor use breadboard placements. Mock speaker outputs reach the visual speaker through separate, ungrounded breadboard rows. Wokwi lint and netlist tests validate structure/connectivity, not visual clarity or runtime behavior. Every visible Wokwi wire segment has its own high-contrast hex color, but the current palette has not been checked in a fresh rendered screenshot: the local screenshot attempt was blocked by the Free-plan monthly CI-minute quota. This does not validate runtime behavior or physical wiring. The diagram and mock are not a physical audio/servo power reference, and Wokwi visuals do not approve any physical power path. Physical wiring remains the separate staged plan below; when physical speaker testing is permitted, the speaker stays directly across the physical module's SPK1/SPK2 outputs.

### Randomized Wokwi automation

Run the generated scenarios with a valid `WOKWI_CLI_TOKEN`:

```sh
python3 scripts/run-wokwi-tests.py --scenario all
# Or run one scenario:
python3 scripts/run-wokwi-tests.py --scenario first-round
```

By default, each randomized test launch gets a nonzero seed from the host OS random source; the runner logs the seed plus prior-color state. The runner generates the scenario buttons from the same xorshift32 sequence, so randomized first colors do not break correct-answer tests. `first-round` checks that early audio completion does not shorten the 2 s light and that the player can wait 5.2 s before pressing and hold the debounced answer for 5.2 s before release; the other scenarios use a longer mock completion delay to verify the cue-boundary Stop, Game Over event draining, successful rounds without servo extension, and loss-triggered servo motion. The runner checks cue-on/off/Stop/gap timestamps, parses the serial transcript, and stores per-run YAML, diagram, transcript, and JSON manifest under `build/wokwi-tests/`. Cross-launch Wokwi previous-color state lives in the local `.wokwi-sequence-state.json`; running `wokwi-cli` directly bypasses this persistence wrapper. Use the printed `--seed` and `--previous-first-color` values with `--no-persist` to replay a failure. A Wokwi CI-minute quota error prevents runtime verification; only a successful scenario completion counts as runtime evidence.

### SIMON library experiment

Both builds now use Rob Tillaart's [SIMON library 0.1.5](https://github.com/RobTillaart/SIMON) for storing a sequence and checking player answers. Physical games call `generateSequence(10, 0, 3)`: the library seeds Arduino's built-in pseudorandom generator with `micros()` and fills a ten-symbol sequence with values 0–3. The sketch keeps the prior-game first-color rule by adjusting the first symbol if necessary. Each round sets the library's expected sequence to the current prefix; each released button is added with `add()`, then `verify()` checks that prefix immediately. No extra RNG module or Entropy library is used.

This is a direct trial of the library, with its trade-offs: the default `SIMON_MAXSIZE` is 10, so a physical game ends after ten completed rounds, and the generated sequence can repeat colors freely—four consecutive cues are **not** guaranteed to contain each color. `micros()` seeds a pseudorandom generator; it is not a hardware entropy source, certification, or a cryptographic guarantee, and repeated physical starts can produce the same sequence. The physical seed behavior has not been measured on the Uno. The library also does not implement LED, button, audio, scoring, LCD, or servo behavior; those remain in this sketch.

Wokwi deliberately does not call `generateSequence()`, because that method reseeds from simulation `micros()` and would break the runner's logged seed/replay contract. It uses the host-injected seed and shuffled-bag generator; cues stay deterministic for a given seed and every four-cue group remains color-balanced. Ordinary builds get a fresh host seed at build time, while tests inject their own explicit seeds. Re-running one built image gives the same sequence by design. Thus physical and Wokwi sequence-generation policies differ in this experiment. The previous-first-color journal and its Wokwi state file remain in use.

### Simulation/physical behavior

- Start is accepted only while idle. Start is ignored during a run and must be released before it can start another.
- Physical games use a SIMON-library sequence of up to ten symbols with replacement, while Wokwi uses the host-seeded shuffled-bag stream and keeps every four-cue group color-balanced. The library checks answer prefixes through `add()`/`verify()`. The first physical cue is adjusted to differ from the prior game's first cue when one is recorded; that color is stored in the wear-levelled, CRC/commit-checked EEPROM journal. Wokwi's previous-first-color state is stored by the CLI wrapper in `.wokwi-sequence-state.json`; each test run logs its host seed and previous color for replay. Direct Wokwi CLI launches do not update that file.
- Four chained NeoPixel strips contain sixteen addressable LEDs total: indices 0–3 are red, 4–7 green, 8–11 blue, and 12–15 yellow. A cue or answer lights all four pixels in its matching group and clears the other groups. Sequence cues stay lit for 2,000 ms from cue-on; an early natural audio-finished event does not shorten the light. At that deadline the firmware issues an idempotent DFPlayer Stop request to bound playback (harmless if the track already completed), then all strips remain off for the existing 180 ms gap. The physical module's exact Stop latency is not validated. In Wokwi, matching track numbers go to the DFPlayer mock; the mock has no MP3 decoder and plays no sound. During answer entry, exactly one debounced play-button press lights its matching four-pixel group while held; that group turns off on release before the answer is evaluated. The 25 ms debounce, chord detection, and release-to-submit behavior remain. Players may wait indefinitely before answering and may hold a debounced answer indefinitely before releasing it. Held buttons during cue playback or the wait-for-release-before-input phase do not light a group. Two or more simultaneously debounced play buttons fail the run.
- The display shows the attempted round during play; `SCORE` counts only fully completed rounds. A wrong answer, chord, or reaching the SIMON library's ten-round sequence capacity ends the run.
- The final score is stored in Uno EEPROM when it improves the best score. Idle keeps `PRESS START` on the first row and alternates `YOUR` / `BEST` score values on the second row every three seconds. EEPROM behavior still needs a physical power-cycle check.
- Game Over begins a random one of the four physical tracks (or the matching mock track command). The screen remains visible for at least three seconds and, after a player loss, until the servo's configured return allowance has elapsed; the firmware then sends Stop before returning to score pages. This is three seconds on the physical configuration and six seconds in Wokwi. Reaching the ten-round SIMON capacity ends the game without servo motion because it is not a player loss. Completion events are drained throughout Game Over.
- Successful rounds 3, 6, 9, … still play a random celebration audio cue, but do not move the servo. The servo extends only after a player loses through a wrong answer or chord, then returns to 0°. In Wokwi, its target changes to 180° for a 3-second hold, then to 0° for a separate 3-second return allowance. Physical builds retain the conservative, unverified settings of 90° extend, 0° retract, a 1-second hold, and a 1-second return allowance until the real FS5106B linkage endpoints and supply are verified. These are command-based intervals that include travel time; neither simulation nor elapsed time provides position feedback. The [Wokwi servo reference](https://docs.wokwi.com/parts/wokwi-servo) documents its range as 0°–180° with hard stops. Do not widen physical settings until the actual mechanism/load and supply are checked.
- This library experiment has a physical cap of ten completed rounds, matching its default `SIMON_MAXSIZE=10`. Reaching the cap ends the game without loss-triggered servo movement. Wokwi scenarios retain their existing replayable sequence generator and do not exercise the physical library cap.

## Pin map — physical Uno R3

| Uno pin | Connection | Notes |
|---|---|---|
| D2 | NeoPixel data input (direct in Wokwi, with a conditional physical series-resistor note) | Wokwi connects D2 directly to `neopixel-red:DIN`; the four strips then chain R/G/B/Y by `DOUT`→`DIN`. The existing physical guidance describes two 220 Ω resistors in series (440 Ω total) before the first physical strip's DIN, subject to verifying the exact strip, pinout, interface, and manufacturer requirements. Physical parts, voltage compatibility, data path, and current remain unverified; this is not wiring approval. |
| D3–D5 | Unused | Former individual LED outputs are no longer used |
| D6, D7, D8, A0 | Four play buttons, one per color above | `INPUT_PULLUP`; button connects its input to GND when pressed |
| A1 | Start button | `INPUT_PULLUP`; button connects its input to GND when pressed |
| A4 / A5 | Grove LCD SDA / SCL | I²C address `0x3E`; do not swap data and clock |
| D9 | FS5106B signal | Servo motor power must come directly from a verified external supply path, not Uno/breadboard power |
| D10 | Uno SoftwareSerial RX ← MP3-TF-16P TX | No connection to Uno D0/D1 |
| D11 | Uno SoftwareSerial TX → 1 kΩ series resistor → MP3-TF-16P RX | Start at module volume 3 |
| D12 | Unused | No tone/buzzer backend is used in Wokwi or on the physical build |
| 5V / GND | Wokwi-only simulated VDD/VSS rails for four strips | The diagram connects each strip's VDD/VSS to simulated rails. Never power physical strips from Uno USB or Uno 5 V. Their current and a suitable separate supply remain unverified; physical power-up is blocked. |
| D0 / D1 | USB serial diagnostics | Reserved; keep free of MP3 wiring |
| A2 / A3 | Unused | No random-number hardware is connected |

Timer1 is dedicated to the D9/OC1A servo signal. It generates 50 Hz Fast PWM using a 0.5 µs timer tick and a 39999 TOP; servo targets use the standard angle-to-pulse range with the Servo library's ~2 µs trim retained. The timer continues producing active pulses while the servo is parked—there is no detach operation. Timer1 also owns D10/OC1B's PWM timing, so do not use D9/D10 `analogWrite()` or code that reconfigures Timer1. This does not change the D10 SoftwareSerial RX / D11 TX audio map.

The firmware runs a 500 ms power-on self-test in `setup()` that lights all sixteen pixels simultaneously in four mapped-color groups (0–3 red, 4–7 green, 8–11 blue, 12–15 yellow), then clears them and enters IDLE. Normal cues and button responses light all four pixels in one matching group and clear the other groups. This is the commanded pattern only; no runtime or physical strip behavior is confirmed. The simulated strip rails are Wokwi fixtures only, not approval of physical parts or topology. Existing physical guidance describes two 220 Ω resistors in series (440 Ω total) before the first physical strip's DIN, but the exact strip models, voltage/current at configured brightness, pin labels, and appropriate separate supply remain unknown. Do not power physical strips from Uno USB or Uno 5 V; physical power-up remains blocked until all applicable electrical requirements and a suitable rated supply/wiring are verified. Adafruit's [NeoPixel best practices](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices) do not substitute for checking the actual strips' ratings. Play-button inputs use the Uno's internal pull-ups, so no button is wired to +5 V.

The MP3 files belong in `/mp3/` at the root of a FAT32 microSD/TF card:

```text
/mp3/0001.mp3
/mp3/0002.mp3
/mp3/0003.mp3
/mp3/0004.mp3
```

`0001`–`0004` map respectively to red, green, blue, and yellow. The physical speaker connects across the module's **SPK1 and SPK2 speaker outputs** (one lead per output). Never connect a speaker terminal to an Uno GPIO or GND.

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
| 19, 25 | Spare rows (used for series resistors in physical wiring) | Keep free for the physical 440 Ω series resistors on D2; not wired in Wokwi simulation |
| 22 | Yellow button contact 2 | Row 22 bottom group returns to GND |
| 24 | Yellow button contact 1 | GPIO A0 uses row 24 |
| 28 | Start button contact 2 | Row 28 bottom group returns to GND |
| 30 | Start button contact 1 | GPIO A1 uses row 30 |
| Top + rail | Shared +5 V in Wokwi simulation only | Simulated Uno 5V, LCD VCC, mock VCC, and all four strip VDD inputs at `tp.4`; this is not a physical strip power path. |
| Bottom GND rail | Wokwi simulation return | Simulated Uno GND, LCD/mock GND, button grounds, and all four strip VSS inputs at `bn.28`; physical strip/servo power wiring is not approved by this diagram. |

For the Wokwi layout, the five button GND tie groups (rows 4, 10, 16, 22, 28) are chained across their bottom-section J holes: `4b.j → 10b.j → 16b.j → 22b.j → 28b.j → bn.28`. Each J hole is in the same lower F–J tie group as that row’s button return. This keeps a direct, clean trunk along the lower edge, away from the F-hole return endpoints, and uses a single `bn.28` tap. Uno GND uses `bn.1`; the off-board LCD and DFPlayer mock returns use `bn.29` and `bn.30`. This daisy-chain is a Wokwi layout choice, not physical wiring approval: a broken jumper would disconnect later groups, and the real board’s tie groups/rail continuity and current limits must be verified before wiring.

Wokwi wire colors now follow electrical function rather than assigning a unique color to every segment: red is positive supply, black is GND, each play-button input matches its button color, Start is white, SDA/SCL are cyan/magenta, NeoPixel data is white, DFPlayer TX/RX links are purple/gray, servo PWM is orange, and the two speaker leads are brown/tan. Same-function paths retain the same color across breadboard segments; use endpoints to trace each connection. These colors are for diagram readability, not physical wiring approval; verify actual connections and keep power-up blocked until the physical ratings and supply paths are confirmed.

The Wokwi data path connects Uno D2 directly to `neopixel-red:DIN`, then chains red→green→blue→yellow with direct DOUT-to-DIN links. No series resistor is present in the simulated data path. Runtime behavior remains unverified, so this layout does not establish the root cause of the reported failure. The existing physical note describes two 220 Ω resistors in series (440 Ω total) before the first physical strip's DIN, only after the exact physical strip, pinout, interface, and manufacturer requirements are verified; it is not wiring approval. Each strip's simulated `VDD` uses `bb1:tp.4`, and `VSS` uses `bb1:bn.28`. The four strips represent sixteen sequential pixels, grouped in firmware as red, green, blue, and yellow. These simulated endpoints do not establish physical rail/hole occupancy or ratings. Never power physical strips from Uno USB/5 V. For each button, contact 1 uses rows 6, 12, 18, 24, 30; contact 2 uses rows 4, 10, 16, 22, 28. Its Wokwi pins are `1.l=c1t.e`, `1.r=c1b.f`, `2.l=c2t.e`, `2.r=c2b.f`; the GPIO tie group is contact 1's `t` section and `c2b.g` returns to GND. This keeps the two contacts separate while released. The separate 1 kΩ resistor spans `1t.b`/`1b.f`. These hole assignments describe the Wokwi logical/layout plan, not unverified physical switch pin orientation.

The Wokwi half breadboard is a logical/visual wiring aid only: it does not verify the physical board's tie-point continuity, component ratings, current capacity, servo supply isolation, or speaker compatibility. The layout uses the 30-row half-board model and checks assigned hole ranges, button/resistor footprints and clearances, strip rotations, and nominal horizontal center alignment derived from diagram coordinates and the documented 9px `pixelSize: "2020"` setting. The strip's actual rendered bounds/offset and exact strip/button clearance were not measured or verified; no fresh render is available. The breadboard is first in `diagram.json`'s `parts` array so it renders behind mounted components; the layout test guards that order. The selected local Wokwi layout places the board at `(left, top)=(330, 350)`, Uno at `(300, 35)`, LCD at `(150, 300)`, servo at `(680, 125)`, DFPlayer mock at `(680, 405)`, and visual speaker at `(820, 405)`. Six components use `$bb` placements (the five buttons and the MP3 TX resistor); the four strips remain direct diagram components. Keep every hard gate in [Power and physical limits](#power-and-physical-limits) closed until verified.

### Step 1 — five tactile buttons

First use a continuity meter, with the button unpowered and removed from any circuit, to identify which two pins are the same contact while released and which separate contact is bridged only when pressed. The common four-leg tactile-switch layout has two internally connected pairs, but the physical part's orientation is **not verified here**. Do not assume the package orientation from this generic drawing.

Place each button across the breadboard's center trench. Connect one released contact pair to the specified GPIO and the other released contact pair to the GND rail. Pressing should bridge the two sides; released must remain open between sides. Repeat the continuity check after placement.

```text
Wokwi/editor pin placement example — red button contact 1 on row 6, contact 2 on row 4
Verify the actual physical switch contact pairs and board tie strips with a meter.

columns     A   B   C   D   E       trench       F   G   H   I   J
row 6t      D6 ───────●──────────────● 1.l  ||  1.r ●──────────────●
row 6b                                     ||
row 4t      ──────────● 2.l───────────────||────────────────────────
row 4b                                     ||  2.r ● at 4b.f (same F–J group as 4b.j)
                         pins straddle trench at each contact row

The editor placement links are 1.l=6t.e, 1.r=6b.f, 2.l=4t.e, and 2.r=4b.f;
D6 is tied to contact 1's row-6 top group; the row-4 bottom group joins the
row-j Wokwi GND trunk, which taps the bottom rail at `bn.28`.
Repeat with contact rows (12,10), (18,16), (24,22), and (30,28) for D7, D8,
A0, and A1. Released GPIO and GND contacts stay separate; pressing bridges them.
The sketch uses INPUT_PULLUP, not an external +5 V.
```

| Button | Uno input | Other contact |
|---|---:|---|
| Red | D6 | GND |
| Green | D7 | GND |
| Blue | D8 | GND |
| Yellow | A0 | GND |
| Start | A1 | GND |

### Step 2 — four chained four-pixel NeoPixel strips (Wokwi preview only)

This describes the simulation, not physical build instructions. Each `wokwi-led-strip` has `pixels: "4"`, `rotate: 90`, and the `pixelSize: "2020"` rendering option. The firmware treats all four chained strips as one 16-pixel Adafruit_NeoPixel object:

```text
Vertical Wokwi strips, aligned by nominal horizontal center above each button:
[RED 0-3]   [GREEN 4-7]   [BLUE 8-11]   [YELLOW 12-15]

Wokwi-only data chain (no series resistor in simulation):
Uno D2 → red DIN → red DOUT → green DIN → green DOUT
       → blue DIN → blue DOUT → yellow DIN

Wokwi-only simulated supplies:
Each strip VDD → simulated +5 V rail; each strip VSS → simulated GND rail
```

The Wokwi model documentation defines `DOUT` for chaining to the next strip and `pixels` as the strip LED count. The direct D2 data path and each DOUT→DIN link are simulation wiring only. Runtime behavior remains unverified, so this change does not establish the reported failure's root cause. Existing physical guidance describes two 220 Ω resistors in series (440 Ω total) before the first verified physical strip's DIN, but the exact physical strips, pinout/orientation, voltage/current, data requirements, and suitable separate supply remain unknown. This description is not physical wiring approval; do not energize hardware until every applicable gate in [Power and physical limits](#power-and-physical-limits) is closed. The simulated rails are not physical supply assignments.

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

Format/copy the card as required by the module, then place the four files at `/mp3/0001.mp3`–`0004.mp3` on the card. Begin at volume 3. The actual MP3-TF-16P clone/card compatibility and current budget are not confirmed by simulation.

### Step 5 — servo signal and isolated motor supply

The Uno USB supplies the Uno. The FS5106B motor current must have its own external direct supply path. The drawing is only the intended topology: **do not connect an adapter until the adapter plug, breakout, polarity, wire/terminal ratings, protection, and actual servo demand are all verified**. Do not route servo motor current through Uno USB/5 V, breadboard rails, or a 700 mA breadboard supply.

```text
Signal only through breadboard row 7:
Uno D9 ───────────── row 7 ─────────────────────────> FS5106B signal

Motor power and return bypass both breadboard and Uno 5V:
verified external +5 V supply + ──────────────────> servo V+ (direct)
verified external supply GND ──────────────────────> servo GND (direct return)
           │
           └── one common-ground reference point ── Uno GND / signal reference

Uno remains laptop-USB powered. NO external +5 V connection to Uno 5V/barrel.
Do not route servo V+ or motor-current return through the breadboard or Uno.
Join Uno/supply grounds only at the verified common-reference point; do not
add a second servo-ground path through the breadboard rail.
```

The adapter label provided by the user is 5 V / 5 A / 25 W, center-positive, with a male barrel connector. A separate female barrel breakout is still to be obtained/borrowed. The physical plug dimensions, breakout/terminal/wire current ratings, overcurrent protection, servo current at the real load, and the remaining module current budget are not verified. No fuse rating or final safe hookup is asserted here.

## Power and physical limits — hard pre-energizing gates

Do **not** energize any circuit until all applicable checks are resolved from the exact parts' markings/datasheets and rated components:

1. Measure/confirm the adapter's barrel dimensions, center polarity, and output; confirm the exact breakout jack, terminal block, conductors, connectors, and overcurrent protection are rated for the actual servo supply and fault current. Do not infer ratings from a 5 A adapter label.
2. Verify the FS5106B's voltage, stall/start current at the actual mechanism/load, supply suitability, signal requirements, travel limits, horn/linkage clearance, and safe unloaded angles. The mechanism/load and the conservative physical 0°/90° positions are not verified; hold/retraction timings are tunable values only. The Wokwi 0°/180° sweep is a simulation setting, not an approved physical endpoint range.
3. Verify the MP3-TF-16P board variant, supply/current draw, microSD requirements, serial levels, and speaker output/load ratings. Confirm the aggregate Uno USB budget for the display, module, buttons, and all parts actually powered from the Uno. Never power the physical NeoPixels from Uno USB/5 V.
4. The exact physical four-strip NeoPixel assembly, strip models, voltage/current requirements at configured brightness, pin labels/orientation, and required signal interface are unverified. Identify every actual strip and verify its electrical requirements, suitable separate supply, protection, conductors, connectors, and data path before considering power-up. Existing physical guidance describes two 220 Ω resistors in series (440 Ω total) on D2 before the first physical strip's DIN; the direct Wokwi route and simulated rails do not establish physical component ratings or wiring. Check the exact strips' manufacturer guidance before connecting physical data. No physical strip power-up is currently authorized.
5. Continuity-test each tactile button unpowered: released contacts must be separate across the switch; identify its permanently joined pin pairs and ensure GPIO/GND are on opposing contacts. Check for shorts before connecting USB.
6. Verify the Grove connector orientation and the Uno's SDA/A4, SCL/A5 mapping. The product is rated for 3.3/5 V by Seeed, but still check the unit's actual label/condition.

Never feed external adapter +5 V to Uno +5 V or the barrel jack while USB is attached. Servo motor current uses the external direct path only, with common ground solely for signal reference. The Uno USB ground and external supply ground are joined at the reference point. Do not connect the external positive rail to the Uno supply. A verified external supply is not permission to exceed a breakout, wiring, connector, or protection rating.

## Staged physical validation plan

1. **Unpowered inspection:** close every applicable gate above; verify the pin map, button released-contact topology, LCD markings, module wiring/card contents, servo ratings, isolation, and absence of shorts. The exact physical NeoPixel parts, pinout, and electrical requirements are unknown; do not connect or power their supply pins. Leave servo power disconnected.
2. **Uno and low-current inputs/display:** only after independently verifying the USB budget for the attached Uno/display/module/buttons and other Uno-powered parts, connect laptop USB. Do not power the physical NeoPixel strip from Uno USB/5 V; strip hardware power-up remains blocked. The short four-pixel D2 strip can be checked in Wokwi only. Confirm idle pages, button debounce/release, attempted-round display, and one-pixel-per-color mapping. Test Start ignored during a run and a two-button chord.
3. **EEPROM:** record a best score, play a game and note its first color, power-cycle the Uno, and verify the best score page plus that the next game's first color differs from the stored one. The journal shares no bytes with the best-score record; neither behavior has been physically power-cycle tested.
4. **MP3:** only after module/USB current and speaker/module ratings are verified, insert the prepared card, connect speaker across SPK1/SPK2, confirm startup/track mapping at volume 3, cue completion, and Game Over audio stop after the minimum display interval and any servo return allowance. Do not connect speaker to GND/GPIO.
5. **Servo electrical check:** only after every external power gate is closed, first test the servo disconnected from its mechanism with the rated direct supply and shared ground. Confirm startup retract command, safe configured angles, hold, and retract timing while keeping servo motor current off the Uno/breadboard rails.
6. **Mechanism/load check:** install/tune linkage only with a safe clear zone and verified load/current/travel. Confirm the servo stays still after successful rounds 3/6/9, then extends and retracts only after a player loss; verify the configured return allowance before Game Over exits.
7. **Full game:** validate a response delayed beyond five seconds, a debounced press held beyond five seconds before release, wrong answer/chord handling, score accounting, best-score persistence, audio overlap protection, and repeated power cycles. There is no player-response timeout. Record any changes to provisional servo constants and hardware details here.

## Audio attribution

“sound-alien1” by **zippi1**, https://freesound.org/people/zippi1/sounds/18027/, licensed **CC BY-NC 4.0**: https://creativecommons.org/licenses/by-nc/4.0/ . The project includes the source file `assets/source-sound-alien1-hq.mp3` and four pitch-shifted modifications for the game cues:

| File | Button/LED | Pitch modification |
|---|---|---:|
| `0001.mp3` | Red pixel/button | −3 semitones |
| `0002.mp3` | Green pixel/button | −1 semitone |
| `0003.mp3` | Blue pixel/button | +1 semitone |
| `0004.mp3` | Yellow pixel/button | +3 semitones |

Attribution is retained in this README beside the audio assets.
