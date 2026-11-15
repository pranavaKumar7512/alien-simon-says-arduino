#include <Arduino.h>
#include <EEPROM.h>
#include <Wire.h>
#include <SoftwareSerial.h>
#include <Adafruit_NeoPixel.h>
#include <DFRobotDFPlayerMini.h>
#include <simon.h>
#if !defined(WOKWI_SIM)
#include <Entropy.h>
#include <avr/wdt.h>
#endif
#include "audio_completion_filter.h"
#include "button_mapping.h"
#include "audio_track_config.h"
#include "first_color_journal.h"
#include "game_sequence.h"
#include "player_led_feedback.h"
#include "servo_celebration_config.h"

#if !defined(F_CPU) || F_CPU != SERVO_PWM_CPU_HZ
#error "Timer1 servo PWM requires a 16 MHz Uno-class AVR"
#endif

// Uno R3 pin map (see README.md).
static const uint8_t BUTTON_PINS[5] = {6, 7, 8, A0, A1}; // four play controls left-to-right, then Start
static const char CUE_COLOR_LETTERS[BUTTON_MAPPING_COUNT] = {'R', 'G', 'B', 'Y'};
static const uint8_t SERVO_PIN = 9;
static const uint8_t MP3_RX_PIN = 10; // Uno RX <- DFPlayer TX
static const uint8_t MP3_TX_PIN = 11; // Uno TX -> 1 kOhm -> DFPlayer RX
static const uint16_t DEBOUNCE_MS = 25;
static const uint16_t CUE_GAP_MS = 180;
static const uint16_t BUTTON_FEEDBACK_DARK_MS = 500;
static const uint16_t SEQUENCE_CUE_MS = 2000;
static const uint32_t CUE_TIMEOUT_MS = 2500UL;
static const uint16_t ENTROPY_ACQUIRE_TIMEOUT_MS = 1200U;
static const uint32_t GAME_OVER_MIN_MS = 3000UL;
static const uint32_t SCORE_PAGE_MS = 3000UL;
static const uint32_t BUTTON_MAPPING_DEMO_DURATION_MS = 5500UL;
static const uint32_t MAX_COMPLETED_ROUNDS = UINT32_MAX;
static const uint32_t EEPROM_MAGIC = 0x53494D4FUL;
static const uint32_t EEPROM_CHECK_XOR = 0xA55A39C6UL;

struct ButtonDebouncer {
  uint8_t pin;
  bool rawPressed;
  bool pressed;
  uint32_t changedAt;
};

struct BestScoreRecord {
  uint32_t magic;
  uint32_t score;
  uint32_t check;
};

static_assert(sizeof(BestScoreRecord) <= FIRST_COLOR_JOURNAL_BASE,
              "First-color journal must not overlap the best-score record");
static_assert(PLAYER_LED_SYMBOL_COUNT * PLAYER_LED_PIXELS_PER_SYMBOL == PLAYER_LED_PIXEL_COUNT,
              "There must be four NeoPixels for each Simon symbol");
static_assert(PLAYER_LED_SYMBOL_COUNT == FIRST_COLOR_COUNT,
              "First-color journal and play-button symbols must match");
static_assert(BUTTON_MAPPING_COUNT == PLAYER_LED_SYMBOL_COUNT,
              "Each play-button position must map to one cue color");

ButtonDebouncer buttons[5];
uint32_t bestScore = 0;
uint32_t completedRounds = 0;
uint32_t roundLength = 1;
uint32_t sequenceSeed = 1;
uint32_t buttonMappingState = 1;
uint8_t buttonToCueColor[BUTTON_MAPPING_COUNT] = {0U, 1U, 2U, 3U};
GameSequenceStream sequenceTailState;
GameSequenceStream playbackState;
GameSequenceStream answerState;
SIMON simonGame;
uint8_t answerChunkSymbols[SIMON_MAXSIZE];
uint8_t answerChunkLength = 0;
uint8_t answerChunkIndex = 0;
uint8_t firstGameSymbol = 0;
uint8_t previousFirstColor = FIRST_COLOR_NONE;
bool firstColorRecordedForGame = false;
uint32_t playbackIndex = 0;
uint32_t answerIndex = 0;
uint32_t stateStartedAt = 0;
uint32_t idlePageStartedAt = 0;
uint32_t buttonMappingDemoStartedAt = 0;
uint32_t buttonFeedbackStartedAt = 0;
uint32_t gameOverStartedAt = 0;
uint32_t audioStartedAt = 0;
uint32_t servoExtendedAt = 0;
uint32_t lcdWaitStartedAt = 0;
uint8_t cueSymbol = 0;
uint8_t pendingAnswer = 0xFF;
uint8_t idlePage = 0;
bool buttonMappingDemoPending = false;
bool buttonMappingDemoActive = false;
uint32_t buttonMappingDemoRound = 0UL;
bool startConsumed = false;
bool serialStartPending = false;
bool restartAfterGameOver = false;
bool audioRunning = false;
bool audioNeedsInitialStop = true; // DFPlayer may outlive an MCU reset
bool audioFinished = false;
bool audioIsGameOver = false;
uint8_t activeAudioTrack = 0;
bool servoIsExtended = false;
bool servoRetractionPending = false;
bool lcdInitialized = false;
uint8_t lcdInitStage = 0;
bool celebrationWaitingForAudio = false;

SoftwareSerial mp3Serial(MP3_RX_PIN, MP3_TX_PIN);
Adafruit_NeoPixel playerStripRed(PLAYER_LED_PIXELS_PER_SYMBOL, PLAYER_LED_DATA_PINS[0], NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel playerStripGreen(PLAYER_LED_PIXELS_PER_SYMBOL, PLAYER_LED_DATA_PINS[1], NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel playerStripBlue(PLAYER_LED_PIXELS_PER_SYMBOL, PLAYER_LED_DATA_PINS[2], NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel playerStripYellow(PLAYER_LED_PIXELS_PER_SYMBOL, PLAYER_LED_DATA_PINS[3], NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel *const playerStrips[PLAYER_LED_SYMBOL_COUNT] = {
  &playerStripRed, &playerStripGreen, &playerStripBlue, &playerStripYellow
};
DFRobotDFPlayerMini mp3;
bool mp3Ready = false;

enum GameState : uint8_t {
  IDLE,
  SHOW_INITIAL_MAPPING,
  PLAY_CUE,
  CUE_SOUND,
  CUE_GAP,
  WAIT_RELEASE_BEFORE_INPUT,
  WAIT_INPUT,
  BUTTON_FEEDBACK,
  WAIT_INPUT_RELEASE,
  CELEBRATION,
  GAME_OVER
};

GameState gameState = IDLE;

static bool elapsed(uint32_t now, uint32_t start, uint32_t duration) {
  return (uint32_t)(now - start) >= duration;
}

static uint32_t xorshift32(uint32_t &value) {
  return gameSequenceXorshift32(&value);
}

static bool makeSeed(uint32_t *seedOut) {
  if (seedOut == 0) return false;
#if defined(WOKWI_SIM)
  // Wokwi seeds are host-injected (random per normal build, explicit for tests);
  // the serial seed log preserves replay, and simulation never claims hardware RNG.
#ifndef WOKWI_INITIAL_SEED
#define WOKWI_INITIAL_SEED 1UL
#endif
  static uint32_t nextSimulationSeed = (uint32_t)WOKWI_INITIAL_SEED;
  if (nextSimulationSeed == 0U) nextSimulationSeed = 0x6D2B79F5UL;
  *seedOut = nextSimulationSeed;
  xorshift32(nextSimulationSeed);
  return true;
#else
  // Collect one jitter-derived seed before gameplay, then stop WDT interrupts.
  Entropy.initialize();
  const uint32_t entropyStartedAt = millis();
  while (Entropy.available() == 0U) {
    if (elapsed(millis(), entropyStartedAt, ENTROPY_ACQUIRE_TIMEOUT_MS)) {
      wdt_disable();
      return false;
    }
    delay(1);
  }
  *seedOut = Entropy.random();
  wdt_disable();
  if (*seedOut == 0U) *seedOut = 0x6D2B79F5UL;
  return true;
#endif
}

static uint8_t nextSymbol(GameSequenceStream &stream) {
  return gameSequenceNextSymbol(&stream);
}

static uint8_t nextAudioSymbol(uint32_t &stream) {
  return (uint8_t)(xorshift32(stream) >> 30);
}

static void sendLcdCommand(uint8_t command) {
  Wire.beginTransmission(0x3E);
  Wire.write((uint8_t)0x80); // Seeed Grove library: command control byte
  Wire.write(command);
  Wire.endTransmission();
}

static bool serviceLcdInitialization(uint32_t now) {
  static const uint16_t waitsMs[] = {50, 5, 1, 1, 1, 2, 2};
  if (lcdInitialized) return true;
  if (!elapsed(now, lcdWaitStartedAt, waitsMs[lcdInitStage])) return false;

  switch (lcdInitStage) {
    case 0: case 1: case 2: case 3:
      sendLcdCommand(0x28); // 4-bit, two-line, 5x8 font, per Seeed library
      break;
    case 4:
      sendLcdCommand(0x0C); // display on, cursor/blink off
      break;
    case 5:
      sendLcdCommand(0x01); // clear display
      break;
    case 6:
      sendLcdCommand(0x06); // left-to-right entry mode
      lcdInitialized = true;
      return true;
  }
  ++lcdInitStage;
  lcdWaitStartedAt = now;
  return false;
}

static void updateDisplay(const char *line1, const char *line2) {
  char first[17];
  char second[17];
  memset(first, ' ', 16);
  memset(second, ' ', 16);
  first[16] = '\0';
  second[16] = '\0';
  for (uint8_t i = 0; i < 16 && line1[i]; ++i) first[i] = line1[i];
  for (uint8_t i = 0; i < 16 && line2[i]; ++i) second[i] = line2[i];

  sendLcdCommand(0x80); // DDRAM row 0, column 0
  Wire.beginTransmission(0x3E);
  Wire.write((uint8_t)0x40); // Seeed Grove library: display-data control byte
  Wire.write((const uint8_t *)first, 16);
  Wire.endTransmission();

  sendLcdCommand(0xC0); // DDRAM row 1, column 0
  Wire.beginTransmission(0x3E);
  Wire.write((uint8_t)0x40);
  Wire.write((const uint8_t *)second, 16);
  Wire.endTransmission();
}

static void showIdlePage(uint32_t now) {
  char value[17];
  if (idlePage == 0) {
    snprintf(value, sizeof(value), "YOUR:%010lu", (unsigned long)completedRounds);
  } else {
    snprintf(value, sizeof(value), "BEST:%010lu", (unsigned long)bestScore);
  }
  updateDisplay("PRESS START", value);
  idlePageStartedAt = now;
}

static void renderRoundAndScore(uint32_t roundNumber) {
  char line1[17];
  char line2[17];
  snprintf(line1, sizeof(line1), "ROUND %lu", (unsigned long)roundNumber);
  snprintf(line2, sizeof(line2), "SCORE %lu", (unsigned long)completedRounds);
  updateDisplay(line1, line2);
}

static void refreshRoundDisplay() {
  renderRoundAndScore(roundLength);
}

static void allLedsOff();
static bool showButtonMapping();
static void writePlayerPixel(uint8_t pixel, uint8_t red, uint8_t green, uint8_t blue);
static void showPlayerStrips();

static void beginButtonMappingDemo(uint32_t effectiveRound) {
  // Each four-pixel strip is physically aligned with one left-to-right button
  // position. Update and show all four independent outputs so the complete map
  // is visible simultaneously without relying on the buttons' casing colors.
  if (!showButtonMapping()) {
    buttonMappingDemoActive = false;
    return;
  }
  buttonMappingDemoRound = effectiveRound;
  buttonMappingDemoStartedAt = millis();
  buttonMappingDemoActive = true;
#if defined(WOKWI_SIM)
  Serial.print(F("SIM_BUTTON_DEMO_START:"));
  Serial.print(buttonMappingDemoRound);
  Serial.print(':');
  Serial.println(buttonMappingDemoStartedAt);
  Serial.print(F("SIM_BUTTON_DEMO_MAP:"));
  Serial.print(buttonMappingDemoRound);
  Serial.print(':');
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    Serial.print(buttonToCueColor[position]);
  }
  Serial.println();
#endif
}

static void serviceButtonMappingDemo(uint32_t now) {
  if (!buttonMappingDemoActive ||
      !elapsed(now, buttonMappingDemoStartedAt, BUTTON_MAPPING_DEMO_DURATION_MS)) return;
  allLedsOff();
  buttonMappingDemoActive = false;
#if defined(WOKWI_SIM)
  Serial.print(F("SIM_BUTTON_DEMO_END:"));
  Serial.print(buttonMappingDemoRound);
  Serial.print(':');
  Serial.println(millis());
#endif
}

static void logButtonMapping(uint32_t effectiveRound) {
#if defined(WOKWI_SIM)
  Serial.print(F("SIM_BUTTON_MAP:"));
  Serial.print(effectiveRound);
  Serial.print(':');
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    Serial.print(buttonToCueColor[position]);
  }
  Serial.println();
#else
  (void)effectiveRound;
#endif
}

static void logInputMapping(uint32_t effectiveRound) {
#if defined(WOKWI_SIM)
  Serial.print(F("SIM_INPUT_MAP_ON:"));
  Serial.print(effectiveRound);
  Serial.print(':');
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    Serial.print(buttonToCueColor[position]);
  }
  Serial.print(':');
  Serial.println(millis());
#else
  (void)effectiveRound;
#endif
}

static void writePlayerPixel(uint8_t pixel, uint8_t red, uint8_t green, uint8_t blue) {
  const uint8_t strip = playerLedStripForPixel(pixel);
  if (strip >= PLAYER_LED_SYMBOL_COUNT) return;
  Adafruit_NeoPixel *const output = playerStrips[strip];
  output->setPixelColor(playerLedPixelWithinStrip(pixel), output->Color(red, green, blue));
}

static void showPlayerStrips() {
  for (uint8_t strip = 0U; strip < PLAYER_LED_SYMBOL_COUNT; ++strip) {
    playerStrips[strip]->show();
  }
}

static void writeServoPulseTicks(uint16_t ticks) {
  OCR1A = ticks;
}

static void setServoTarget(uint8_t angle) {
  writeServoPulseTicks(servoAngleToPulseTicks(angle));
}

static void initializeServoPwm(uint8_t initialAngle) {
  // Uno Timer1 runs Fast PWM mode 14: 16 MHz / 8 / (39999 + 1) = 50 Hz.
  // D9/OC1A updates in hardware, so SoftwareSerial interrupt blocking cannot stretch pulses.
  pinMode(SERVO_PIN, OUTPUT);
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  ICR1 = (uint16_t)SERVO_PWM_TOP_TICKS;
  setServoTarget(initialAngle);
  TCCR1A = _BV(COM1A1) | _BV(WGM11); // non-inverting OC1A, WGM13:0 = 14
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11); // prescaler 8
}

static void setLed(uint8_t symbol, bool on) {
  const uint8_t position = buttonMappingPositionForColor(buttonToCueColor, symbol);
  if (position >= BUTTON_MAPPING_COUNT) {
    allLedsOff();
    return;
  }
  if (!playerLedSetMappedCue(buttonToCueColor, symbol, on, writePlayerPixel)) return;
  showPlayerStrips();
#if defined(WOKWI_SIM)
  if (on) {
    Serial.print(F("SIM_MAPPED_LED_ON:"));
    Serial.print(symbol);
    Serial.print(':');
    Serial.print(position);
    Serial.print(':');
    Serial.println(millis());
  }
#endif
}

static bool showButtonMapping() {
  if (!playerLedSetButtonMapping(buttonToCueColor, writePlayerPixel)) {
    allLedsOff();
    return false;
  }
  showPlayerStrips();
  return true;
}

static void allLedsOff() {
  for (uint8_t strip = 0U; strip < PLAYER_LED_SYMBOL_COUNT; ++strip) {
    playerStrips[strip]->clear();
  }
  showPlayerStrips();
}

static void saveBestScore() {
  BestScoreRecord record;
  record.magic = EEPROM_MAGIC;
  record.score = bestScore;
  record.check = EEPROM_MAGIC ^ bestScore ^ EEPROM_CHECK_XOR;
  EEPROM.put(0, record);
}

static void readBestScore() {
  BestScoreRecord record;
  EEPROM.get(0, record);
  if (record.magic == EEPROM_MAGIC &&
      record.check == (EEPROM_MAGIC ^ record.score ^ EEPROM_CHECK_XOR) &&
      record.score <= MAX_COMPLETED_ROUNDS) {
    bestScore = record.score;
  } else {
    bestScore = 0;
  }
}

static uint8_t readEepromByte(uint16_t address, void *context) {
  (void)context;
  return EEPROM.read((int)address);
}

static void updateEepromByte(uint16_t address, uint8_t value, void *context) {
  (void)context;
  EEPROM.update((int)address, value);
}

static void loadPreviousFirstColor() {
#if defined(WOKWI_SIM)
#ifndef WOKWI_PREVIOUS_FIRST_COLOR
#define WOKWI_PREVIOUS_FIRST_COLOR FIRST_COLOR_NONE
#endif
  previousFirstColor = (WOKWI_PREVIOUS_FIRST_COLOR < PLAYER_LED_SYMBOL_COUNT)
      ? (uint8_t)WOKWI_PREVIOUS_FIRST_COLOR
      : FIRST_COLOR_NONE;
#else
  FirstColorJournalEntry entry;
  previousFirstColor = firstColorJournalRead(readEepromByte, NULL, &entry)
      ? entry.color
      : FIRST_COLOR_NONE;
#endif
}

static void rememberFirstColor(uint8_t color) {
  previousFirstColor = color;
#if !defined(WOKWI_SIM)
  firstColorJournalAppend(readEepromByte, updateEepromByte, NULL, color);
#endif
  firstColorRecordedForGame = true;
}

static void prepareGameSequence(uint32_t seed) {
  // Keep the sequence streaming and unbounded; SIMON's fixed-size object is
  // used below only as a rolling answer verifier.
  firstGameSymbol = gameSequenceChooseFirst(&sequenceTailState, seed);
}

static bool prepareAnswerChunk() {
  const uint32_t remaining = roundLength - answerIndex;
  answerChunkLength = remaining < SIMON_MAXSIZE
      ? (uint8_t)remaining
      : (uint8_t)SIMON_MAXSIZE;
  answerChunkIndex = 0U;
  if (answerChunkLength == 0U) return false;

  for (uint8_t i = 0U; i < answerChunkLength; ++i) {
    const uint32_t symbolIndex = answerIndex + i;
    answerChunkSymbols[i] = symbolIndex == 0U
        ? firstGameSymbol
        : nextSymbol(answerState);
  }
  simonGame.clear();
  return simonGame.setSequence(answerChunkSymbols, answerChunkLength);
}

static void drainAudioEvents(bool allowActiveCueCompletion) {
  if (!mp3Ready) return;
  while (mp3.available()) {
    uint8_t type = mp3.readType();
    uint16_t parameter = mp3.read();
    if (type != DFPlayerPlayFinished || parameter == 0) continue;

    bool accepted = allowActiveCueCompletion &&
      audioCompletionMatches(parameter, activeAudioTrack, audioRunning,
                             audioIsGameOver || gameState == GAME_OVER);
    if (accepted) audioFinished = true;
#if defined(WOKWI_SIM)
    if (accepted) {
      Serial.print(F("SIM_AUDIO_DONE:"));
      Serial.println(parameter);
    } else if (gameState == GAME_OVER) {
      Serial.print(F("SIM_GAMEOVER_EVENT_DRAINED:"));
      Serial.println(parameter);
    }
#endif
  }
}

static void stopAudio() {
  drainAudioEvents(false);
  if (mp3Ready && (audioRunning || audioNeedsInitialStop)) {
    mp3.stop();
    audioNeedsInitialStop = false;
  }
  audioRunning = false;
  audioFinished = false;
  audioIsGameOver = false;
  activeAudioTrack = 0;
  drainAudioEvents(false);
}

static void stopSequenceCueAudio(uint8_t symbol) {
  drainAudioEvents(false);
#if defined(WOKWI_SIM)
  Serial.print(F("SIM_CUE_STOP_REQUEST:"));
  Serial.print(symbol);
  Serial.print(':');
  Serial.println(millis());
#endif
  // Stop is deliberately idempotent at the fixed cue deadline. A delayed
  // same-track completion event cannot make an active cue evade its 2 s bound.
  if (mp3Ready) mp3.stop();
  audioNeedsInitialStop = false;
  audioRunning = false;
  audioFinished = false;
  audioIsGameOver = false;
  activeAudioTrack = 0;
  drainAudioEvents(false);
}

static void startTrack(uint8_t track, bool gameOverTrack = false) {
  stopAudio(); // drains old status before the next track can become active
  drainAudioEvents(false);
  activeAudioTrack = track;
  audioIsGameOver = gameOverTrack;
  audioFinished = false;
  audioRunning = true;
  audioStartedAt = millis();
  if (mp3Ready) mp3.playMp3Folder(track); // /mp3/0001.mp3 through /mp3/0005.mp3
#if defined(WOKWI_SIM)
  Serial.print(F("SIM_AUDIO_START:"));
  Serial.println(track);
#endif
}

static bool serviceCueAudio(uint32_t now) {
  if (!audioRunning) return true;
  drainAudioEvents(true);
  if (audioFinished) {
    audioRunning = false;
    audioFinished = false;
    audioIsGameOver = false;
    activeAudioTrack = 0;
    return true;
  }
  if (elapsed(now, audioStartedAt, CUE_TIMEOUT_MS)) {
    stopAudio(); // bounded recovery when the module/card does not report completion
    return true;
  }
  return false;
}

static void beginGameOver(uint32_t now, bool playerLost) {
  allLedsOff();
  stopAudio(); // never overlap an active cue with the Game Over sound
  char line[17];
  snprintf(line, sizeof(line), "SCORE %lu", (unsigned long)completedRounds);
  updateDisplay("GAME OVER", line);
  gameOverStartedAt = millis();
  uint32_t randomTrackState = sequenceSeed ^ now ^ micros();
  if (randomTrackState == 0) randomTrackState = 0x6D2B79F5UL;
  uint8_t randomTrack = (uint8_t)(nextAudioSymbol(randomTrackState) % AUDIO_LAST_CUE_TRACK + 1U);
  uint8_t track = gameOverAudioTrack(playerLost, randomTrack);
  startTrack(track, true);
  gameState = GAME_OVER;
  Serial.println(F("GAME_OVER"));
#if defined(WOKWI_SIM)
  Serial.print(F("SIM_GAME_OVER_START:"));
  Serial.println(gameOverStartedAt);
#endif
  if (servoWriteGameOverTargetIfLost(playerLost, SERVO_GAME_OVER_EXTEND_ANGLE,
                                     writeServoPulseTicks)) {
    servoExtendedAt = millis();
    servoIsExtended = true;
    servoRetractionPending = false;
#if defined(WOKWI_SIM)
    Serial.print(F("SIM_SERVO_EXTEND:"));
    Serial.println(servoExtendedAt);
#endif
  }
}

static void beginRound(uint32_t now) {
  roundLength = completedRounds + 1UL;
  allLedsOff();
  buttonFeedbackStartedAt = 0UL;
  playbackState = sequenceTailState;
  answerState = sequenceTailState;
  playbackIndex = 0;
  answerIndex = 0;
  pendingAnswer = 0xFF;
  if (!prepareAnswerChunk()) {
    beginGameOver(now, false);
    return;
  }
  refreshRoundDisplay();
  gameState = PLAY_CUE;
  stateStartedAt = now;
  Serial.println(F("ROUND_START"));
}

#if defined(WOKWI_SIM)
static void logSimulationScoreState() {
  Serial.print(F("SIM_SCORE_STATE:"));
  Serial.print(completedRounds);
  Serial.print(':');
  Serial.println(bestScore);
}
#endif

static void beginGame() {
  startConsumed = true;
  uint32_t freshSeed = 0U;
  if (!makeSeed(&freshSeed)) {
    allLedsOff();
    updateDisplay("RANDOM NOT READY", "RELEASE & RETRY");
    idlePageStartedAt = millis();
    Serial.println(F("ENTROPY_TIMEOUT"));
    return;
  }
  completedRounds = 0;
#if defined(WOKWI_SIM) && defined(WOKWI_TEST_CHUNK_BOUNDARY)
  completedRounds = 10UL;
  Serial.println(F("SIM_TEST_CHUNK_BOUNDARY"));
#endif
  sequenceSeed = freshSeed;
  prepareGameSequence(sequenceSeed);
  buttonMappingReset(buttonToCueColor);
  buttonMappingState = buttonMappingSeed(sequenceSeed);
  buttonMappingDemoPending = false;
  buttonMappingDemoActive = false;
  buttonMappingDemoRound = 0UL;
  firstColorRecordedForGame = false;
  allLedsOff();
  Serial.println(F("GAME_START"));
#if defined(WOKWI_SIM)
  Serial.println(F("SIM_GAME_START"));
  Serial.print(F("SIM_GAME_SEED:"));
  Serial.println(sequenceSeed);
  logSimulationScoreState();
#endif
  logButtonMapping(1UL);
  beginButtonMappingDemo(1UL);
  gameState = SHOW_INITIAL_MAPPING;
}

static void restartActiveGame() {
  stopAudio();
  allLedsOff();
  gameState = IDLE;
  completedRounds = 0;
  roundLength = 1;
  celebrationWaitingForAudio = false;
  firstColorRecordedForGame = false;
  restartAfterGameOver = false;
  Serial.println(F("GAME_RESET"));
#if defined(WOKWI_SIM)
  Serial.println(F("SIM_GAME_RESET"));
#endif
  beginGame();
}

static void enterIdle(uint32_t now) {
  stopAudio();
  allLedsOff();
  idlePage = 0;
  gameState = IDLE;
  showIdlePage(now);
}

static void completeCorrectAnswer(uint32_t now) {
  allLedsOff();
  ++completedRounds; // called only after a full round is correctly entered
  if (completedRounds > bestScore) {
    bestScore = completedRounds;
    saveBestScore();
  }
#if defined(WOKWI_SIM)
  logSimulationScoreState();
#endif
  Serial.println(F("ROUND_COMPLETE"));
#if defined(WOKWI_SIM)
  Serial.println(F("SIM_ROUND_COMPLETE"));
#endif
#if defined(WOKWI_SIM) && defined(WOKWI_TEST_CHUNK_BOUNDARY)
  if (completedRounds == 11UL) {
    gameState = IDLE; // End the test build after the chunk-boundary answer is accepted.
    return;
  }
#endif

  // Stop safely before the completed-round counter would wrap and corrupt
  // roundLength; this is only a technical overflow safeguard.
  if (completedRounds >= MAX_COMPLETED_ROUNDS) {
    beginGameOver(now, false); // technical exhaustion is not a player loss
    return;
  }
#if defined(WOKWI_SIM) && defined(WOKWI_TEST_BUTTON_REMAP)
  if (completedRounds == 4UL) {
    Serial.println(F("SIM_TEST_BUTTON_REMAP_DONE"));
    gameState = IDLE;
    return;
  }
#endif

  if (completedRounds % 3UL == 0) {
    if (!buttonMappingShuffle(buttonToCueColor, &buttonMappingState)) {
      beginGameOver(now, false);
      return;
    }
    logButtonMapping(completedRounds + 1UL);
    updateDisplay("ROUND COMPLETE", "CELEBRATION");
    buttonMappingDemoRound = completedRounds + 1UL;
    buttonMappingDemoPending = true;
    uint32_t celebrationState = sequenceSeed ^ now ^ completedRounds;
    if (celebrationState == 0) celebrationState = 0x6D2B79F5UL;
    uint8_t track = (uint8_t)(nextAudioSymbol(celebrationState) + 1U);
    startTrack(track);
    celebrationWaitingForAudio = true;
    gameState = CELEBRATION;
    return;
  }

  beginRound(now);
}

static void updateButtons(uint32_t now) {
  for (uint8_t i = 0; i < 5; ++i) {
    bool sampledPressed = digitalRead(buttons[i].pin) == LOW;
    if (sampledPressed != buttons[i].rawPressed) {
      buttons[i].rawPressed = sampledPressed;
      buttons[i].changedAt = now;
    }
    if (buttons[i].pressed != buttons[i].rawPressed &&
        elapsed(now, buttons[i].changedAt, DEBOUNCE_MS)) {
      buttons[i].pressed = buttons[i].rawPressed;
    }
  }
}

static void pollSerialStartCommand() {
  while (Serial.available() > 0) {
    const int received = Serial.read();
    if (received == 'S' || received == 's') {
      serialStartPending = true;
      Serial.println(F("SERIAL_START_REQUESTED"));
    }
  }
}

static uint8_t countPlayButtonsDown(uint8_t *onlyButton) {
  uint8_t count = 0;
  for (uint8_t i = 0; i < 4; ++i) {
    if (buttons[i].pressed) {
      ++count;
      *onlyButton = i;
    }
  }
  return count;
}

static bool playButtonsReleased() {
  for (uint8_t i = 0; i < 4; ++i) {
    if (buttons[i].pressed) return false;
  }
  return true;
}

static void failAnswer(uint32_t now, const __FlashStringHelper *reason) {
  Serial.println(reason);
  beginGameOver(now, true);
}

void setup() {
  Serial.begin(115200); // diagnostics stay on Uno D0/D1
  Wire.begin();
  Wire.setWireTimeout(25000UL, true); // Bound LCD I2C transactions if the bus stalls.
  lcdWaitStartedAt = millis();
  for (uint8_t strip = 0U; strip < PLAYER_LED_SYMBOL_COUNT; ++strip) {
    playerStrips[strip]->begin();
    playerStrips[strip]->setBrightness(PLAYER_LED_BRIGHTNESS);
  }
  playerLedSetAllMappedColors(writePlayerPixel);
  showPlayerStrips();
  delay(500);
  allLedsOff();
  const uint32_t now = millis();
  for (uint8_t i = 0; i < 5; ++i) {
    buttons[i].pin = BUTTON_PINS[i];
    pinMode(buttons[i].pin, INPUT_PULLUP);
    buttons[i].rawPressed = digitalRead(buttons[i].pin) == LOW;
    buttons[i].pressed = buttons[i].rawPressed;
    buttons[i].changedAt = now;
  }
  readBestScore();
  loadPreviousFirstColor();
  initializeServoPwm(SERVO_GAME_OVER_RETRACT_ANGLE);
  mp3Serial.begin(9600);
  // No reset/ACK wait: initialization is bounded; missing player/card is handled as silence.
  mp3Ready = mp3.begin(mp3Serial, false, false);
  if (mp3Ready) mp3.volume(3);
#if defined(WOKWI_SIM)
  Serial.println(F("SIM_MODE: DFPlayer protocol mock; visual speaker has no playback"));
#endif
  gameState = IDLE;

}

void loop() {
  const uint32_t now = millis();
  pollSerialStartCommand();
  updateButtons(now);
  if (!serviceLcdInitialization(now)) return;
  if (idlePageStartedAt == 0) {
    startConsumed = buttons[4].pressed;
    showIdlePage(now);
    Serial.println(F("READY"));
  }
  bool startActionHandled = false;
  const bool serialStartAction = serialStartPending;
  serialStartPending = false;
  if (!buttons[4].pressed) {
    startConsumed = false;
  } else if (!startConsumed) {
    startActionHandled = true;
    startConsumed = true;
  }
  if (!startActionHandled && serialStartAction) {
    startActionHandled = true;
  }
  if (startActionHandled) {
    if (gameState == IDLE) {
      beginGame();
    } else if (gameState == GAME_OVER) {
      // Keep the loss/servo return sequence intact; start a fresh game afterward.
      restartAfterGameOver = true;
      Serial.println(F("GAME_RESET_QUEUED"));
#if defined(WOKWI_SIM)
      Serial.println(F("SIM_GAME_RESET_QUEUED"));
#endif
    } else {
      restartActiveGame();
    }
  }

  switch (gameState) {
    case IDLE:
      if (!startActionHandled && elapsed(now, idlePageStartedAt, SCORE_PAGE_MS)) {
        idlePage ^= 1U;
        showIdlePage(now);
      }
      break;

    case SHOW_INITIAL_MAPPING:
      serviceButtonMappingDemo(millis());
      if (!buttonMappingDemoActive) beginRound(millis());
      break;

    case PLAY_CUE:
      if (playbackIndex >= roundLength) {
        if (!showButtonMapping()) {
          beginGameOver(millis(), false);
          break;
        }
        logInputMapping(roundLength);
        gameState = WAIT_RELEASE_BEFORE_INPUT;
        break;
      }
      cueSymbol = playbackIndex == 0U ? firstGameSymbol : nextSymbol(playbackState);
      if (!firstColorRecordedForGame) {
        rememberFirstColor(firstGameSymbol);
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_FIRST_COLOR:"));
        Serial.println(firstGameSymbol);
#endif
      }
      setLed(cueSymbol, true);
      stateStartedAt = millis(); // the two-second deadline begins when the pixel is lit
#if defined(WOKWI_SIM)
      Serial.print(F("SIM_CUE_ON:"));
      Serial.print(cueSymbol);
      Serial.print(':');
      Serial.println(stateStartedAt);
#endif
      startTrack((uint8_t)(cueSymbol + 1U));
      gameState = CUE_SOUND;
      break;

    case CUE_SOUND:
      serviceCueAudio(now); // natural completion must not shorten the light cue
      if (elapsed(now, stateStartedAt, SEQUENCE_CUE_MS)) {
        setLed(cueSymbol, false);
        const uint32_t cueOffAt = millis();
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_CUE_OFF:"));
        Serial.print(cueSymbol);
        Serial.print(':');
        Serial.println(cueOffAt);
#endif
        stopSequenceCueAudio(cueSymbol);
        ++playbackIndex;
        stateStartedAt = cueOffAt; // preserve the full 180 ms dark gap from pixel-off
        gameState = CUE_GAP;
      }
      break;

    case CUE_GAP:
      if (elapsed(now, stateStartedAt, CUE_GAP_MS)) {
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_CUE_GAP_DONE:"));
        Serial.print(cueSymbol);
        Serial.print(':');
        Serial.println(now);
#endif
        gameState = PLAY_CUE;
      }
      break;

    case WAIT_RELEASE_BEFORE_INPUT: {
      uint8_t heldButton = 0xFF;
      if (countPlayButtonsDown(&heldButton) >= 2) {
        failAnswer(now, F("WRONG_CHORD"));
      } else if (playButtonsReleased()) {
        gameState = WAIT_INPUT;
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_INPUT_READY:"));
        Serial.println(now);
#endif
      }
      break;
    }

    case WAIT_INPUT: {
      uint8_t pressedButton = 0xFF;
      uint8_t pressedCount = countPlayButtonsDown(&pressedButton);
      if (pressedCount >= 2) {
        failAnswer(now, F("WRONG_CHORD"));
      } else if (pressedCount == 1) {
        pendingAnswer = buttonMappingColorForPosition(buttonToCueColor, pressedButton);
        if (pendingAnswer >= BUTTON_MAPPING_COUNT) {
          failAnswer(now, F("WRONG_ANSWER"));
          break;
        }
        const uint32_t inputPressedAt = millis();
        if (!playerLedSetButtonMappingWithColorOff(
                buttonToCueColor, pendingAnswer, writePlayerPixel)) {
          allLedsOff();
          beginGameOver(inputPressedAt, false);
          break;
        }
        showPlayerStrips();
        buttonFeedbackStartedAt = millis();
#if defined(WOKWI_SIM)
        const uint32_t mappedLedOffAt = buttonFeedbackStartedAt;
        Serial.print(F("SIM_MAPPED_LED_OFF:"));
        Serial.print(pendingAnswer);
        Serial.print(':');
        Serial.print(pressedButton);
        Serial.print(':');
        Serial.println(mappedLedOffAt);
        Serial.print(F("SIM_BUTTON_INPUT:"));
        Serial.print(pressedButton);
        Serial.print(':');
        Serial.print(pendingAnswer);
        Serial.print(':');
        Serial.println(inputPressedAt);
        Serial.print(F("SIM_INPUT_PRESS:"));
        Serial.print(pendingAnswer);
        Serial.print(':');
        Serial.println(inputPressedAt);
#endif
        gameState = BUTTON_FEEDBACK;
      }
      break;
    }

    case BUTTON_FEEDBACK: {
      uint8_t heldButton = 0xFF;
      const uint32_t feedbackNow = millis();
      if (countPlayButtonsDown(&heldButton) >= 2) {
        failAnswer(feedbackNow, F("WRONG_CHORD"));
      } else if (elapsed(feedbackNow, buttonFeedbackStartedAt,
                         BUTTON_FEEDBACK_DARK_MS)) {
        if (!showButtonMapping()) {
          beginGameOver(millis(), false);
          break;
        }
        const uint8_t mappedPosition =
            buttonMappingPositionForColor(buttonToCueColor, pendingAnswer);
        const uint32_t restoredAt = millis();
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_MAPPED_LED_RESTORE:"));
        Serial.print(pendingAnswer);
        Serial.print(':');
        Serial.print(mappedPosition);
        Serial.print(':');
        Serial.println(restoredAt);
#endif
        gameState = WAIT_INPUT_RELEASE;
      }
      break;
    }

    case WAIT_INPUT_RELEASE: {
      uint8_t pressedButton = 0xFF;
      uint8_t pressedCount = countPlayButtonsDown(&pressedButton);
      if (pressedCount >= 2) {
        failAnswer(now, F("WRONG_CHORD"));
      } else if (playButtonsReleased()) {
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_INPUT_RELEASE:"));
        Serial.print(pendingAnswer);
        Serial.print(':');
        Serial.println(now);
#endif
        simonGame.add(pendingAnswer);
        ++answerIndex;
        ++answerChunkIndex;
        pendingAnswer = 0xFF;
        if (!simonGame.setSequence(answerChunkSymbols, answerChunkIndex) ||
            !simonGame.verify()) {
          failAnswer(now, F("WRONG_ANSWER"));
        } else if (answerIndex == roundLength) {
          completeCorrectAnswer(now);
        } else if (answerChunkIndex == answerChunkLength) {
          if (!prepareAnswerChunk()) {
            beginGameOver(now, false);
          } else {
            gameState = WAIT_INPUT;
          }
        } else {
          gameState = WAIT_INPUT;
        }
      }
      break;
    }

    case CELEBRATION:
      if (celebrationWaitingForAudio && serviceCueAudio(now)) {
        celebrationWaitingForAudio = false;
      }
      if (!celebrationWaitingForAudio && buttonMappingDemoPending) {
        buttonMappingDemoPending = false;
        beginButtonMappingDemo(buttonMappingDemoRound);
      }
      serviceButtonMappingDemo(millis());
      if (!celebrationWaitingForAudio && !buttonMappingDemoPending &&
          !buttonMappingDemoActive) beginRound(millis());
      break;

    case GAME_OVER:
      drainAudioEvents(false); // discard completion events throughout Game Over
      if (servoIsExtended && elapsed(now, servoExtendedAt, SERVO_GAME_OVER_HOLD_MS)) {
        setServoTarget(SERVO_GAME_OVER_RETRACT_ANGLE);
        servoExtendedAt = millis();
        servoIsExtended = false;
        servoRetractionPending = true;
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_SERVO_RETRACT:"));
        Serial.println(servoExtendedAt);
#endif
      } else if (servoRetractionPending &&
                 elapsed(now, servoExtendedAt, SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS)) {
        // Time-based estimate only; this servo has no position feedback.
        servoRetractionPending = false;
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_SERVO_RETRACT_DONE:"));
        Serial.println(now);
#endif
      }
      if (elapsed(now, gameOverStartedAt, GAME_OVER_MIN_MS) &&
          !servoIsExtended && !servoRetractionPending) {
        stopAudio();
#if defined(WOKWI_SIM)
        Serial.print(F("SIM_GAME_OVER_STOP:"));
        Serial.println(now);
#endif
        const bool restartQueued = restartAfterGameOver;
        restartAfterGameOver = false;
        enterIdle(now);
        if (restartQueued) {
          Serial.println(F("GAME_RESET"));
#if defined(WOKWI_SIM)
          Serial.println(F("SIM_GAME_RESET"));
#endif
          beginGame();
        }
      }
      break;
  }
}
