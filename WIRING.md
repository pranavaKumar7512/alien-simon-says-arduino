# Alien Simon Says - Wiring Guide (Uno R3)

> **WARNING - topology aid, NOT verified.** This guide is derived only from `diagram.json` connections plus README hardware notes. It is not a physical wiring record. Keep ALL power disconnected while wiring: USB unplugged, barrel jack unplugged, external supply OFF.
>
> **Single-supply design: never connect USB or the Uno barrel jack / VIN while the external supply feeds the Uno 5V pin.** The external regulated 5 V enters at the breakout 5V and feeds the Uno 5V pin through `tp`. Back-feeding through USB or barrel can damage the board.
>
> **Before any power:** verify the supply rating, polarity and combined current (Uno + LCD + DFPlayer + servo + motor + 4 strips) against the README physical-power gates. See section 5. This guide grants NO power-up approval.

Counts from `diagram.json`: **19 parts**, **71 connection entries** = 51 colored wires + 20 `$bb` component-lead placements. The README's '17 parts / 63 entries / 43 wires' is stale.

## 0. Reading hole names and rails

- A hole is `<column><half>.<row>`. `6t.a` = column 6, **top** half, row **a**. `4b.j` = column 4, **bottom** half, row **j**.
- Top half rows a-e are joined within each column. Bottom half rows f-j are joined within each column. The centre trench separates top and bottom, so a part straddling the trench (button, resistor) bridges two columns.
- Rail holes are `tp.N`, `bn.N`, `bp.N`, `tn.N`. Each rail is one strip; `N` is the hole position along it. As modelled, all holes of one rail are one net. Confirm on the physical board whether a rail is split.
- Rail meanings used here:
  - `tp` = Uno logic **+5 V** (Uno 5V pin #38, and breakout 5V via #52). Feeds LCD VCC and DFPlayer VCC.
  - `bn` = Uno logic **GND** (Uno GND.1 #32). Feeds LCD GND, DFPlayer GND, MDD3A logic GND and the button GND chain.
  - `bp` = **external +5 V load** rail (breakout 5V via #51). Feeds servo V+, strip VDD and MDD3A VB+. Never join to `tp`.
  - `tn` = **external GND** return rail. Feeds breakout GND, servo GND, strip VSS and MDD3A VB-. Tied to Uno GND through `GND.2` (#47).
- Logic and external returns meet only at the Uno GND pins: #32 (to `bn`) and #47 (to `tn`).

## 1. Connection table (all entries)

`$bb` rows are component leads placed in breadboard holes: place the component legs there. Other rows are wires. Wire colors are the diagram's colors (visual aids; the strip wires keep the user-reported jumper colors per project rules).

| # | From (part:pin) | To (part:pin) | Wire color | Purpose |
|---:|---|---|---|---|
| 1 | `button-red:1.l` | `bb1:6t.e` | n/a (component lead) | Place component legs here: red button, contact 1, left lead (column 6 top; joins D6 wire #21) |
| 2 | `button-red:1.r` | `bb1:6b.f` | n/a (component lead) | Place component legs here: red button, contact 1, right lead (column 6 bottom, across trench) |
| 3 | `button-red:2.l` | `bb1:4t.e` | n/a (component lead) | Place component legs here: red button, contact 2, left lead (column 4 top) |
| 4 | `button-red:2.r` | `bb1:4b.f` | n/a (component lead) | Place component legs here: red button, contact 2, right lead (column 4 bottom; GND chain #27) |
| 5 | `button-green:1.l` | `bb1:12t.e` | n/a (component lead) | Place component legs here: green button, contact 1, left lead (column 12 top; joins D7 wire #22) |
| 6 | `button-green:1.r` | `bb1:12b.f` | n/a (component lead) | Place component legs here: green button, contact 1, right lead (column 12 bottom) |
| 7 | `button-green:2.l` | `bb1:10t.e` | n/a (component lead) | Place component legs here: green button, contact 2, left lead (column 10 top) |
| 8 | `button-green:2.r` | `bb1:10b.f` | n/a (component lead) | Place component legs here: green button, contact 2, right lead (column 10 bottom; GND chain #28) |
| 9 | `button-blue:1.l` | `bb1:18t.e` | n/a (component lead) | Place component legs here: blue button, contact 1, left lead (column 18 top; joins D8 wire #23) |
| 10 | `button-blue:1.r` | `bb1:18b.f` | n/a (component lead) | Place component legs here: blue button, contact 1, right lead (column 18 bottom) |
| 11 | `button-blue:2.l` | `bb1:16t.e` | n/a (component lead) | Place component legs here: blue button, contact 2, left lead (column 16 top) |
| 12 | `button-blue:2.r` | `bb1:16b.f` | n/a (component lead) | Place component legs here: blue button, contact 2, right lead (column 16 bottom; GND chain #29) |
| 13 | `button-yellow:1.l` | `bb1:24t.e` | n/a (component lead) | Place component legs here: yellow button, contact 1, left lead (column 24 top; joins A0 wire #25) |
| 14 | `button-yellow:1.r` | `bb1:24b.f` | n/a (component lead) | Place component legs here: yellow button, contact 1, right lead (column 24 bottom) |
| 15 | `button-yellow:2.l` | `bb1:22t.e` | n/a (component lead) | Place component legs here: yellow button, contact 2, left lead (column 22 top) |
| 16 | `button-yellow:2.r` | `bb1:22b.f` | n/a (component lead) | Place component legs here: yellow button, contact 2, right lead (column 22 bottom; GND chain #30) |
| 17 | `button-start:1.l` | `bb1:30t.e` | n/a (component lead) | Place component legs here: Start button lead 1 (column 30 top; joins A1 wire #26) |
| 18 | `button-start:2.r` | `bb1:28b.f` | n/a (component lead) | Place component legs here: Start button lead 2 (column 28 bottom; GND return #31) |
| 19 | `mp3-tx-resistor:1` | `bb1:1t.b` | n/a (component lead) | Place component legs here: 1 kOhm resistor pin 1 (column 1 top) |
| 20 | `mp3-tx-resistor:2` | `bb1:1b.f` | n/a (component lead) | Place component legs here: 1 kOhm resistor pin 2 (column 1 bottom; to DFPlayer RX #34) |
| 21 | `uno:6` | `bb1:6t.a` | White (#FFFFFF) | Button signal: Uno D6 to red play button (Button 1, leftmost) |
| 22 | `uno:7` | `bb1:12t.a` | White (#FFFFFF) | Button signal: Uno D7 to green play button (Button 2) |
| 23 | `uno:8` | `bb1:18t.a` | White (#FFFFFF) | Button signal: Uno D8 to blue play button (Button 3) |
| 24 | `uno:9` | `bb1:7t.a` | White (#FFFFFF) | Servo signal: Uno D9 (Timer1 OC1A) to row 7; then servo PWM via #46 |
| 25 | `uno:A0` | `bb1:24t.a` | White (#FFFFFF) | Button signal: Uno A0 to yellow play button (Button 4) |
| 26 | `uno:A1` | `bb1:30t.a` | White (#FFFFFF) | Button signal: Uno A1 to Start button (lead 1) |
| 27 | `bb1:4b.j` | `bb1:10b.j` | Black (#000000) | Button GND return chain: row 4 bottom to row 10 bottom |
| 28 | `bb1:10b.i` | `bb1:16b.i` | Black (#000000) | Button GND return chain: row 10 bottom to row 16 bottom |
| 29 | `bb1:16b.j` | `bb1:22b.j` | Black (#000000) | Button GND return chain: row 16 bottom to row 22 bottom |
| 30 | `bb1:22b.i` | `bb1:28b.i` | Black (#000000) | Button GND return chain: row 22 bottom to row 28 bottom |
| 31 | `bb1:28b.j` | `bb1:bn.25` | Black (#000000) | Button GND return chain: row 28 bottom to logic GND rail bn.25 |
| 32 | `uno:GND.1` | `bb1:bn.1` | Black (#000000) | Logic GND: Uno GND.1 to logic GND rail bn.1 |
| 33 | `uno:11` | `bb1:1t.a` | Orange (#FFA500) | UART TX (SoftwareSerial): Uno D11 to column 1 top, through 1 kOhm resistor (#19) |
| 34 | `bb1:1b.g` | `dfplayer-mock:RX` | Orange (#FFA500) | UART TX (SoftwareSerial): resistor pin 2 (column 1 bottom) to DFPlayer RX |
| 35 | `dfplayer-mock:TX` | `bb1:5t.a` | Orange (#FFA500) | UART RX (SoftwareSerial): DFPlayer TX to column 5 top |
| 36 | `bb1:5t.b` | `uno:10` | Orange (#FFA500) | UART RX (SoftwareSerial): column 5 bottom group to Uno D10 |
| 37 | `dfplayer-mock:GND` | `bb1:bn.24` | Black (#000000) | Logic GND: DFPlayer GND to logic GND rail bn.24 |
| 38 | `uno:5V` | `bb1:tp.1` | Red (#FF0000) | Logic +5 V: Uno 5V pin to logic +5 V rail tp.1 |
| 39 | `bb1:tp.5` | `dfplayer-mock:VCC` | Red (#FF0000) | Logic +5 V: logic +5 V rail tp.5 to DFPlayer VCC |
| 40 | `dfplayer-mock:SPK1` | `visual-speaker:SPK1` | Gray (#808080) | Speaker: DFPlayer SPK1 to speaker lead 1 (direct wire, not via breadboard) |
| 41 | `dfplayer-mock:SPK2` | `visual-speaker:SPK2` | Black (#000000) | Speaker: DFPlayer SPK2 to speaker lead 2 (direct wire, not via breadboard) |
| 42 | `uno:A4` | `lcd:SDA` | Blue (#0000FF) | LCD SDA (I2C): Uno A4 to Grove LCD SDA |
| 43 | `uno:A5` | `lcd:SCL` | Yellow (#FFFF00) | LCD SCL (I2C): Uno A5 to Grove LCD SCL |
| 44 | `bb1:bn.22` | `lcd:GND` | Black (#000000) | Logic GND: logic GND rail bn.22 to LCD GND |
| 45 | `bb1:tp.22` | `lcd:VCC` | Red (#FF0000) | Logic +5 V: logic +5 V rail tp.22 to LCD VCC |
| 46 | `bb1:7t.b` | `servo-visual-only:PWM` | Orange (#FFA500) | Servo signal: column 7 bottom (fed from D9 via #24) to servo PWM |
| 47 | `uno:GND.2` | `bb1:tn.1` | Black (#000000) | Common ground: Uno GND.2 to external GND rail tn.1 |
| 48 | `servo-visual-only:GND` | `bb1:tn.2` | Black (#000000) | Servo GND: servo GND to external GND rail tn.2 |
| 49 | `barrel-jack-breakout:GND` | `bb1:tn.3` | Black (#000000) | External GND: barrel breakout GND to external GND rail tn.3 |
| 50 | `servo-visual-only:V+` | `bb1:bp.2` | Red (#FF0000) | Servo power: servo V+ to external +5 V rail bp.2 |
| 51 | `barrel-jack-breakout:5V` | `bb1:bp.3` | Red (#FF0000) | External +5 V: barrel breakout 5V to external +5 V rail bp.3 |
| 52 | `barrel-jack-breakout:5V` | `bb1:tp.2` | Red (#FF0000) | Logic +5 V feed: barrel breakout 5V to logic +5 V rail tp.2 (single-supply design) |
| 53 | `uno:2` | `neopixel-red:DIN` | Yellow (#FFFF00) | LED data: Uno D2 to red strip DIN |
| 54 | `uno:3` | `neopixel-green:DIN` | Yellow (#FFFF00) | LED data: Uno D3 to green strip DIN |
| 55 | `uno:4` | `neopixel-blue:DIN` | Yellow (#FFFF00) | LED data: Uno D4 to blue strip DIN |
| 56 | `uno:12` | `neopixel-yellow:DIN` | Yellow (#FFFF00) | LED data: Uno D12 to yellow strip DIN |
| 57 | `neopixel-red:VSS` | `bb1:tn.14` | Bright green (#00FF00) | Strip GND (VSS): red strip VSS to external GND rail tn.14 |
| 58 | `neopixel-green:VSS` | `bb1:tn.10` | White (#FFFFFF) | Strip GND (VSS): green strip VSS to external GND rail tn.10 |
| 59 | `neopixel-blue:VSS` | `bb1:tn.11` | Brown (#A52A2A) | Strip GND (VSS): blue strip VSS to external GND rail tn.11 |
| 60 | `neopixel-yellow:VSS` | `bb1:tn.16` | Dark green (#006400) | Strip GND (VSS): yellow strip VSS to external GND rail tn.16 |
| 61 | `neopixel-red:VDD` | `bb1:bp.14` | Red (#FF0000) | Strip power (VDD): red strip VDD to external +5 V rail bp.14 |
| 62 | `neopixel-green:VDD` | `bb1:bp.10` | Orange (#FFA500) | Strip power (VDD): green strip VDD to external +5 V rail bp.10 |
| 63 | `neopixel-blue:VDD` | `bb1:bp.11` | Orange (#FFA500) | Strip power (VDD): blue strip VDD to external +5 V rail bp.11 |
| 64 | `neopixel-yellow:VDD` | `bb1:bp.16` | Red (#FF0000) | Strip power (VDD): yellow strip VDD to external +5 V rail bp.16 |
| 65 | `motor-driver-mdd3a:GND` | `bb1:bn.5` | Black (#000000) | Motor driver logic GND: MDD3A GND to logic GND rail bn.5 |
| 66 | `uno:5` | `motor-driver-mdd3a:M1A` | Purple (#800080) | Motor control: Uno D5 to MDD3A M1A (PWM forward) |
| 67 | `uno:A2` | `motor-driver-mdd3a:M1B` | Purple (#800080) | Motor control: Uno A2 to MDD3A M1B (held LOW) |
| 68 | `motor-driver-mdd3a:VB_MINUS` | `bb1:tn.7` | Black (#000000) | Motor driver power return: MDD3A VB- to external GND rail tn.7 |
| 69 | `motor-driver-mdd3a:VB_PLUS` | `bb1:bp.4` | Red (#FF0000) | Motor driver power +: MDD3A VB+ to external +5 V rail bp.4 |
| 70 | `motor-driver-mdd3a:M1_OUT_A` | `motor-fit0458:MOTOR_PLUS` | Red (named) | Motor output: MDD3A M1_OUT_A to FIT0458 MOTOR_PLUS |
| 71 | `motor-driver-mdd3a:M1_OUT_B` | `motor-fit0458:MOTOR_MINUS` | Black (named) | Motor output: MDD3A M1_OUT_B to FIT0458 MOTOR_MINUS |

## 2. Build order (grouped)

Each group lists its connections by #. Every connection appears in exactly one group.

### A) Power and ground rails

Wire the rails first, with USB, barrel and supply all unplugged. Rails: `tp` = Uno logic +5 V, `bn` = Uno logic GND, `bp` = external +5 V load, `tn` = external GND. The Uno 5V pin (#38) and the breakout 5V into `tp` (#52) form the single-supply feed; the breakout 5V also goes to `bp` (#51).

- **#38** `uno:5V` -> `bb1:tp.1`: Logic +5 V: Uno 5V pin to logic +5 V rail tp.1
- **#52** `barrel-jack-breakout:5V` -> `bb1:tp.2`: Logic +5 V feed: barrel breakout 5V to logic +5 V rail tp.2 (single-supply design)
- **#51** `barrel-jack-breakout:5V` -> `bb1:bp.3`: External +5 V: barrel breakout 5V to external +5 V rail bp.3
- **#49** `barrel-jack-breakout:GND` -> `bb1:tn.3`: External GND: barrel breakout GND to external GND rail tn.3
- **#32** `uno:GND.1` -> `bb1:bn.1`: Logic GND: Uno GND.1 to logic GND rail bn.1
- **#47** `uno:GND.2` -> `bb1:tn.1`: Common ground: Uno GND.2 to external GND rail tn.1

### B) Uno signals (buttons, GND chain, servo signal, UART, LCD I2C, strip data, motor control)

Place the button component legs (#1-#18). Wire the Uno pins: buttons (#21-#23, #25, #26), servo signal (#24), GND chain (#27-#31), UART TX/RX (#33, #36), LCD SDA/SCL (#42, #43), strip data (#53-#56) and motor control (#66, #67). The resistor legs (#19, #20) are in C.

- **#1** `button-red:1.l` -> `bb1:6t.e` (place leg): Place component legs here: red button, contact 1, left lead (column 6 top; joins D6 wire #21)
- **#2** `button-red:1.r` -> `bb1:6b.f` (place leg): Place component legs here: red button, contact 1, right lead (column 6 bottom, across trench)
- **#3** `button-red:2.l` -> `bb1:4t.e` (place leg): Place component legs here: red button, contact 2, left lead (column 4 top)
- **#4** `button-red:2.r` -> `bb1:4b.f` (place leg): Place component legs here: red button, contact 2, right lead (column 4 bottom; GND chain #27)
- **#5** `button-green:1.l` -> `bb1:12t.e` (place leg): Place component legs here: green button, contact 1, left lead (column 12 top; joins D7 wire #22)
- **#6** `button-green:1.r` -> `bb1:12b.f` (place leg): Place component legs here: green button, contact 1, right lead (column 12 bottom)
- **#7** `button-green:2.l` -> `bb1:10t.e` (place leg): Place component legs here: green button, contact 2, left lead (column 10 top)
- **#8** `button-green:2.r` -> `bb1:10b.f` (place leg): Place component legs here: green button, contact 2, right lead (column 10 bottom; GND chain #28)
- **#9** `button-blue:1.l` -> `bb1:18t.e` (place leg): Place component legs here: blue button, contact 1, left lead (column 18 top; joins D8 wire #23)
- **#10** `button-blue:1.r` -> `bb1:18b.f` (place leg): Place component legs here: blue button, contact 1, right lead (column 18 bottom)
- **#11** `button-blue:2.l` -> `bb1:16t.e` (place leg): Place component legs here: blue button, contact 2, left lead (column 16 top)
- **#12** `button-blue:2.r` -> `bb1:16b.f` (place leg): Place component legs here: blue button, contact 2, right lead (column 16 bottom; GND chain #29)
- **#13** `button-yellow:1.l` -> `bb1:24t.e` (place leg): Place component legs here: yellow button, contact 1, left lead (column 24 top; joins A0 wire #25)
- **#14** `button-yellow:1.r` -> `bb1:24b.f` (place leg): Place component legs here: yellow button, contact 1, right lead (column 24 bottom)
- **#15** `button-yellow:2.l` -> `bb1:22t.e` (place leg): Place component legs here: yellow button, contact 2, left lead (column 22 top)
- **#16** `button-yellow:2.r` -> `bb1:22b.f` (place leg): Place component legs here: yellow button, contact 2, right lead (column 22 bottom; GND chain #30)
- **#17** `button-start:1.l` -> `bb1:30t.e` (place leg): Place component legs here: Start button lead 1 (column 30 top; joins A1 wire #26)
- **#18** `button-start:2.r` -> `bb1:28b.f` (place leg): Place component legs here: Start button lead 2 (column 28 bottom; GND return #31)
- **#21** `uno:6` -> `bb1:6t.a`: Button signal: Uno D6 to red play button (Button 1, leftmost)
- **#22** `uno:7` -> `bb1:12t.a`: Button signal: Uno D7 to green play button (Button 2)
- **#23** `uno:8` -> `bb1:18t.a`: Button signal: Uno D8 to blue play button (Button 3)
- **#24** `uno:9` -> `bb1:7t.a`: Servo signal: Uno D9 (Timer1 OC1A) to row 7; then servo PWM via #46
- **#25** `uno:A0` -> `bb1:24t.a`: Button signal: Uno A0 to yellow play button (Button 4)
- **#26** `uno:A1` -> `bb1:30t.a`: Button signal: Uno A1 to Start button (lead 1)
- **#27** `bb1:4b.j` -> `bb1:10b.j`: Button GND return chain: row 4 bottom to row 10 bottom
- **#28** `bb1:10b.i` -> `bb1:16b.i`: Button GND return chain: row 10 bottom to row 16 bottom
- **#29** `bb1:16b.j` -> `bb1:22b.j`: Button GND return chain: row 16 bottom to row 22 bottom
- **#30** `bb1:22b.i` -> `bb1:28b.i`: Button GND return chain: row 22 bottom to row 28 bottom
- **#31** `bb1:28b.j` -> `bb1:bn.25`: Button GND return chain: row 28 bottom to logic GND rail bn.25
- **#33** `uno:11` -> `bb1:1t.a`: UART TX (SoftwareSerial): Uno D11 to column 1 top, through 1 kOhm resistor (#19)
- **#36** `bb1:5t.b` -> `uno:10`: UART RX (SoftwareSerial): column 5 bottom group to Uno D10
- **#42** `uno:A4` -> `lcd:SDA`: LCD SDA (I2C): Uno A4 to Grove LCD SDA
- **#43** `uno:A5` -> `lcd:SCL`: LCD SCL (I2C): Uno A5 to Grove LCD SCL
- **#53** `uno:2` -> `neopixel-red:DIN`: LED data: Uno D2 to red strip DIN
- **#54** `uno:3` -> `neopixel-green:DIN`: LED data: Uno D3 to green strip DIN
- **#55** `uno:4` -> `neopixel-blue:DIN`: LED data: Uno D4 to blue strip DIN
- **#56** `uno:12` -> `neopixel-yellow:DIN`: LED data: Uno D12 to yellow strip DIN
- **#66** `uno:5` -> `motor-driver-mdd3a:M1A`: Motor control: Uno D5 to MDD3A M1A (PWM forward)
- **#67** `uno:A2` -> `motor-driver-mdd3a:M1B`: Motor control: Uno A2 to MDD3A M1B (held LOW)

### C) DFPlayer and speaker

Place the resistor legs (#19, #20). Wire DFPlayer RX/TX (#34, #35), GND (#37) and VCC (#39), then the speaker leads (#40, #41) directly to the module's SPK1/SPK2 only.

- **#19** `mp3-tx-resistor:1` -> `bb1:1t.b` (place leg): Place component legs here: 1 kOhm resistor pin 1 (column 1 top)
- **#20** `mp3-tx-resistor:2` -> `bb1:1b.f` (place leg): Place component legs here: 1 kOhm resistor pin 2 (column 1 bottom; to DFPlayer RX #34)
- **#34** `bb1:1b.g` -> `dfplayer-mock:RX`: UART TX (SoftwareSerial): resistor pin 2 (column 1 bottom) to DFPlayer RX
- **#35** `dfplayer-mock:TX` -> `bb1:5t.a`: UART RX (SoftwareSerial): DFPlayer TX to column 5 top
- **#37** `dfplayer-mock:GND` -> `bb1:bn.24`: Logic GND: DFPlayer GND to logic GND rail bn.24
- **#39** `bb1:tp.5` -> `dfplayer-mock:VCC`: Logic +5 V: logic +5 V rail tp.5 to DFPlayer VCC
- **#40** `dfplayer-mock:SPK1` -> `visual-speaker:SPK1`: Speaker: DFPlayer SPK1 to speaker lead 1 (direct wire, not via breadboard)
- **#41** `dfplayer-mock:SPK2` -> `visual-speaker:SPK2`: Speaker: DFPlayer SPK2 to speaker lead 2 (direct wire, not via breadboard)

### D) LCD power

LCD SDA/SCL are in B (#42, #43). Power: GND from `bn.22` (#44), VCC from `tp.22` (#45).

- **#44** `bb1:bn.22` -> `lcd:GND`: Logic GND: logic GND rail bn.22 to LCD GND
- **#45** `bb1:tp.22` -> `lcd:VCC`: Logic +5 V: logic +5 V rail tp.22 to LCD VCC

### E) LED strips (power and return; data is in B)

Each strip: VSS to `tn` (#57-#60), VDD to `bp` (#61-#64). Data pins (D2/D3/D4/D12) are wires #53-#56 in B. DOUT and VDD.2/VSS.2 are not used.

- **#57** `neopixel-red:VSS` -> `bb1:tn.14`: Strip GND (VSS): red strip VSS to external GND rail tn.14
- **#58** `neopixel-green:VSS` -> `bb1:tn.10`: Strip GND (VSS): green strip VSS to external GND rail tn.10
- **#59** `neopixel-blue:VSS` -> `bb1:tn.11`: Strip GND (VSS): blue strip VSS to external GND rail tn.11
- **#60** `neopixel-yellow:VSS` -> `bb1:tn.16`: Strip GND (VSS): yellow strip VSS to external GND rail tn.16
- **#61** `neopixel-red:VDD` -> `bb1:bp.14`: Strip power (VDD): red strip VDD to external +5 V rail bp.14
- **#62** `neopixel-green:VDD` -> `bb1:bp.10`: Strip power (VDD): green strip VDD to external +5 V rail bp.10
- **#63** `neopixel-blue:VDD` -> `bb1:bp.11`: Strip power (VDD): blue strip VDD to external +5 V rail bp.11
- **#64** `neopixel-yellow:VDD` -> `bb1:bp.16`: Strip power (VDD): yellow strip VDD to external +5 V rail bp.16

### F) Servo

Signal: D9 (wire #24 in B) lands on column 7; #46 carries it from column 7 bottom to servo PWM. Power: servo V+ to `bp.2` (#50); servo GND to `tn.2` (#48).

- **#46** `bb1:7t.b` -> `servo-visual-only:PWM`: Servo signal: column 7 bottom (fed from D9 via #24) to servo PWM
- **#48** `servo-visual-only:GND` -> `bb1:tn.2`: Servo GND: servo GND to external GND rail tn.2
- **#50** `servo-visual-only:V+` -> `bb1:bp.2`: Servo power: servo V+ to external +5 V rail bp.2

### G) Motor driver and motor

Driver logic GND to `bn.5` (#65). Driver control inputs D5/A2 are wires #66/#67 in B. Power: VB- to `tn.7` (#68), VB+ to `bp.4` (#69). Motor leads: #70 (red) and #71 (black).

- **#65** `motor-driver-mdd3a:GND` -> `bb1:bn.5`: Motor driver logic GND: MDD3A GND to logic GND rail bn.5
- **#68** `motor-driver-mdd3a:VB_MINUS` -> `bb1:tn.7`: Motor driver power return: MDD3A VB- to external GND rail tn.7
- **#69** `motor-driver-mdd3a:VB_PLUS` -> `bb1:bp.4`: Motor driver power +: MDD3A VB+ to external +5 V rail bp.4
- **#70** `motor-driver-mdd3a:M1_OUT_A` -> `motor-fit0458:MOTOR_PLUS`: Motor output: MDD3A M1_OUT_A to FIT0458 MOTOR_PLUS
- **#71** `motor-driver-mdd3a:M1_OUT_B` -> `motor-fit0458:MOTOR_MINUS`: Motor output: MDD3A M1_OUT_B to FIT0458 MOTOR_MINUS

## 3. Per-part pin checklist

Tick each pin when wired. Every pin used by the diagram is listed, with the wire # that lands there.

### servo-visual-only (`wokwi-servo`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `PWM` | 46 | `bb1:7t.b` |
| [ ] | `GND` | 48 | `bb1:tn.2` |
| [ ] | `V+` | 50 | `bb1:bp.2` |

### uno (`wokwi-arduino-uno`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `6` | 21 | `bb1:6t.a` |
| [ ] | `7` | 22 | `bb1:12t.a` |
| [ ] | `8` | 23 | `bb1:18t.a` |
| [ ] | `9` | 24 | `bb1:7t.a` |
| [ ] | `A0` | 25 | `bb1:24t.a` |
| [ ] | `A1` | 26 | `bb1:30t.a` |
| [ ] | `GND.1` | 32 | `bb1:bn.1` |
| [ ] | `11` | 33 | `bb1:1t.a` |
| [ ] | `10` | 36 | `bb1:5t.b` |
| [ ] | `5V` | 38 | `bb1:tp.1` |
| [ ] | `A4` | 42 | `lcd:SDA` |
| [ ] | `A5` | 43 | `lcd:SCL` |
| [ ] | `GND.2` | 47 | `bb1:tn.1` |
| [ ] | `2` | 53 | `neopixel-red:DIN` |
| [ ] | `3` | 54 | `neopixel-green:DIN` |
| [ ] | `4` | 55 | `neopixel-blue:DIN` |
| [ ] | `12` | 56 | `neopixel-yellow:DIN` |
| [ ] | `5` | 66 | `motor-driver-mdd3a:M1A` |
| [ ] | `A2` | 67 | `motor-driver-mdd3a:M1B` |

### button-red (`wokwi-pushbutton-6mm`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `1.l` | 1 | `bb1:6t.e` (place leg here) |
| [ ] | `1.r` | 2 | `bb1:6b.f` (place leg here) |
| [ ] | `2.l` | 3 | `bb1:4t.e` (place leg here) |
| [ ] | `2.r` | 4 | `bb1:4b.f` (place leg here) |

### button-green (`wokwi-pushbutton-6mm`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `1.l` | 5 | `bb1:12t.e` (place leg here) |
| [ ] | `1.r` | 6 | `bb1:12b.f` (place leg here) |
| [ ] | `2.l` | 7 | `bb1:10t.e` (place leg here) |
| [ ] | `2.r` | 8 | `bb1:10b.f` (place leg here) |

### button-blue (`wokwi-pushbutton-6mm`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `1.l` | 9 | `bb1:18t.e` (place leg here) |
| [ ] | `1.r` | 10 | `bb1:18b.f` (place leg here) |
| [ ] | `2.l` | 11 | `bb1:16t.e` (place leg here) |
| [ ] | `2.r` | 12 | `bb1:16b.f` (place leg here) |

### button-yellow (`wokwi-pushbutton-6mm`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `1.l` | 13 | `bb1:24t.e` (place leg here) |
| [ ] | `1.r` | 14 | `bb1:24b.f` (place leg here) |
| [ ] | `2.l` | 15 | `bb1:22t.e` (place leg here) |
| [ ] | `2.r` | 16 | `bb1:22b.f` (place leg here) |

### button-start (`wokwi-pushbutton-6mm`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `1.l` | 17 | `bb1:30t.e` (place leg here) |
| [ ] | `2.r` | 18 | `bb1:28b.f` (place leg here) |

### mp3-tx-resistor (`wokwi-resistor`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `1` | 19 | `bb1:1t.b` (place leg here) |
| [ ] | `2` | 20 | `bb1:1b.f` (place leg here) |

### dfplayer-mock (`chip-dfplayer-mock`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `RX` | 34 | `bb1:1b.g` |
| [ ] | `TX` | 35 | `bb1:5t.a` |
| [ ] | `GND` | 37 | `bb1:bn.24` |
| [ ] | `VCC` | 39 | `bb1:tp.5` |
| [ ] | `SPK1` | 40 | `visual-speaker:SPK1` |
| [ ] | `SPK2` | 41 | `visual-speaker:SPK2` |

### visual-speaker (`chip-visual-speaker`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `SPK1` | 40 | `dfplayer-mock:SPK1` |
| [ ] | `SPK2` | 41 | `dfplayer-mock:SPK2` |

### lcd (`chip-grove-jhd1804`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `SDA` | 42 | `uno:A4` |
| [ ] | `SCL` | 43 | `uno:A5` |
| [ ] | `GND` | 44 | `bb1:bn.22` |
| [ ] | `VCC` | 45 | `bb1:tp.22` |

### barrel-jack-breakout (`chip-barrel-jack-breakout`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `GND` | 49 | `bb1:tn.3` |
| [ ] | `5V` | 51 | `bb1:bp.3` |
| [ ] | `5V` | 52 | `bb1:tp.2` |

### neopixel-red (`wokwi-led-strip`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `DIN` | 53 | `uno:2` |
| [ ] | `VSS` | 57 | `bb1:tn.14` |
| [ ] | `VDD` | 61 | `bb1:bp.14` |
| [ ] | `DOUT`, `VDD.2`, `VSS.2` | - | not connected (leave open) |

### neopixel-green (`wokwi-led-strip`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `DIN` | 54 | `uno:3` |
| [ ] | `VSS` | 58 | `bb1:tn.10` |
| [ ] | `VDD` | 62 | `bb1:bp.10` |
| [ ] | `DOUT`, `VDD.2`, `VSS.2` | - | not connected (leave open) |

### neopixel-blue (`wokwi-led-strip`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `DIN` | 55 | `uno:4` |
| [ ] | `VSS` | 59 | `bb1:tn.11` |
| [ ] | `VDD` | 63 | `bb1:bp.11` |
| [ ] | `DOUT`, `VDD.2`, `VSS.2` | - | not connected (leave open) |

### neopixel-yellow (`wokwi-led-strip`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `DIN` | 56 | `uno:12` |
| [ ] | `VSS` | 60 | `bb1:tn.16` |
| [ ] | `VDD` | 64 | `bb1:bp.16` |
| [ ] | `DOUT`, `VDD.2`, `VSS.2` | - | not connected (leave open) |

### motor-driver-mdd3a (`chip-mdd3a-board-visual`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `GND` | 65 | `bb1:bn.5` |
| [ ] | `M1A` | 66 | `uno:5` |
| [ ] | `M1B` | 67 | `uno:A2` |
| [ ] | `VB_MINUS` | 68 | `bb1:tn.7` |
| [ ] | `VB_PLUS` | 69 | `bb1:bp.4` |
| [ ] | `M1_OUT_A` | 70 | `motor-fit0458:MOTOR_PLUS` |
| [ ] | `M1_OUT_B` | 71 | `motor-fit0458:MOTOR_MINUS` |

### motor-fit0458 (`chip-fit0458-motor-visual`)

| Done | Pin | Wire # | Arrives at |
|:---:|---|---:|---|
| [ ] | `MOTOR_PLUS` | 70 | `motor-driver-mdd3a:M1_OUT_A` |
| [ ] | `MOTOR_MINUS` | 71 | `motor-driver-mdd3a:M1_OUT_B` |

## 4. Notes on hole-based nets

- Button GND chain: `4b.j -> 10b.j -> 16b.j -> 22b.j -> 28b.j -> bn.25` (#27-#31). Each button's return lead joins this chain through its row's bottom group.
- Column 7: `uno:9` (D9, #24) lands on `7t.a`; the servo PWM wire (#46) lands on `7t.b`. They share the column.
- DFPlayer UART: TX (#35) into column 5 top; Uno D10 (#36) from column 5 bottom. RX from D11 (#33) through the 1 kOhm resistor (#19, #20) into `1b.g` (#34). Keep the TX and RX nets separate.
- Start button: lead 1 at `30t.e` (A1, #26); lead 2 at `28b.f` (GND return, #18). Its other two Wokwi pins are unused.
- The Uno 5V pin has exactly one wire (#38). Its supply comes from the breakout through `tp` (#52).

## 5. Check before power (from README gates)

Nothing here is energization approval. Work through every item with the supply OFF and disconnected.

1. [ ] USB unplugged. Barrel jack unplugged from the Uno. External supply OFF and disconnected.
2. [ ] Single supply: confirm the supply is a regulated 5 V source, fused or current-limited, and sized for Uno + LCD + DFPlayer + servo + motor + 4 strips. Confirm polarity at the breakout (+ to 5V, - to GND) with a meter before connecting.
3. [ ] Confirm the breadboard rails and jumper wires are rated for the combined load. The user's breadboard rating is a user report only and is NOT independently verified.
4. [ ] Motor stall current can reach about 2.8 A. Fit a fuse (about 3-5 A) and a 470-1000 uF capacitor at MDD3A VB+/VB-. Never connect motor VB+ to Uno 5V, USB or VIN. Never use the 9 V battery (FIT0458 is rated 3-7.5 V).
5. [ ] Measure the shared 5 V supply under strips + servo + motor before trusting it. Do not run full-white strips and the motor together until the current is measured.
6. [ ] Motor driver: check the real MDD3A silkscreen and truth table (High/Low forward, Low/Low stop). D5 and A2 float during Uno reset/upload and there are no external pull-downs. With the motor disconnected, power the driver, hold the Uno in reset and meter M1A/M1B to GND. If they are not near 0 V, add 10 kOhm pull-downs from each input to GND.
7. [ ] Motor test order: motor disconnected while watching M1A/M1B, then unloaded, then loaded.
8. [ ] LED strips: verify each strip's model, pad labels (VDD/VSS/DIN) and orientation. Verify data-level compatibility with the Uno 5 V signal; add a series resistor or level shifter if the strip datasheet requires it. Leave DOUT and the second VDD/VSS pads unconnected.
9. [ ] Common ground only at the intended points (Uno GND.1 to `bn`, GND.2 to `tn`). Confirm no positive-rail crossover: `bp` must never touch `tp`, and external +5 V must never reach Uno 5V or the barrel jack.
10. [ ] Backfeed and sequencing: confirm no signal line (strip DIN, servo PWM, D5/A2) can back-feed an unpowered load or the Uno. Confirm a safe power-off signal state and the power-up/power-down order.
11. [ ] Servo (FS5106B): identify the real model and rated supply/current. Check horn/linkage clearance and safe travel. Physical settings are 90 deg extend, 0 deg retract, 1 s timing. Do not widen them without a separate mechanism assessment.
12. [ ] Buttons: check each four-leg button's contact pairs with a meter (pairs connect only when pressed). Check that Start is a normally-open two-terminal switch.
13. [ ] Yellow D12-to-yellow-DIN jumper: continuity is user-reported but not tested. Meter it.
14. [ ] LCD: use the Seeed Grove 16x2 LCD (JHD1804M1). Follow the Grove connector orientation. Do not swap SDA (A4) and SCL (A5). I2C address 0x3E.
15. [ ] DFPlayer (MP3-TF-16P): verify the module's supply and output ratings before powering. Speaker goes ONLY across SPK1 and SPK2, never to an Uno pin or GND. Start at volume 3. Verify microSD/card compatibility.
16. [ ] No approved power-up sequence exists yet. Complete README 'Physical validation plan' step 1 (unpowered inspection) before any energization.
