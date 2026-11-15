#include <Adafruit_NeoPixel.h>
#include "servo_celebration_config.h"

#if !defined(F_CPU) || F_CPU != SERVO_PWM_CPU_HZ
#error "Timer1 servo PWM requires a 16 MHz Uno-class AVR"
#endif

// Temporary connection test for the four independent LED strips and five buttons.
// It intentionally does not initialize the LCD or MP3 player.
// SAFETY: This sketch sends open-loop servo target commands on D9: 0° and 90°,
// changing targets every 1,000 ms. There is no position feedback, so these are
// not measured shaft angles and the interval is not a guaranteed dwell after
// arrival. Run only within verified travel/load/repeat-cycle limits; keep the
// mechanism secured and clear, attend continuously, and stop for binding, stall,
// heat, or unexpected motion. With all power off, connect D9 and the servo's
// external-power branch only through the approved supply path. Never power the
// servo from the Uno or breadboard. Do not upload or reconnect wiring live.

static const uint8_t STRIP_COUNT = 4;
static const uint8_t PIXELS_PER_STRIP = 4;
static const uint8_t BUTTON_COUNT = 5;
static const uint8_t TEST_BRIGHTNESS = 32;  // Conservative diagnostic brightness.
static const uint32_t DEBOUNCE_MS = 25;
static const uint16_t STARTUP_TEST_MS = 500;
static const uint8_t SERVO_PIN = 9;
static const uint32_t SERVO_ENDPOINT_HOLD_MS = 1000UL;

static const uint8_t BUTTON_PINS[BUTTON_COUNT] = {6, 7, 8, A0, A1};

// Independent data outputs: red D2, green D3, blue D4, yellow D5.
Adafruit_NeoPixel strips[STRIP_COUNT] = {
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 2, NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 3, NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 4, NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 5, NEO_GRB + NEO_KHZ800)
};

// RGB values in strip order: red, green, blue, yellow.
static const uint8_t STRIP_COLORS[STRIP_COUNT][3] = {
  {255, 0, 0},
  {0, 255, 0},
  {0, 0, 255},
  {255, 255, 0}
};

struct DebouncedButton {
  bool rawPressed;
  bool stablePressed;
  uint32_t changedAt;
};

DebouncedButton buttons[BUTTON_COUNT];
static uint32_t servoEndpointSince;
static bool servoAtZero = true;

static void writeServoPulseTicks(uint16_t ticks) {
  OCR1A = ticks;
}

static void setServoTarget(uint8_t angle) {
  writeServoPulseTicks(servoAngleToPulseTicks(angle));
}

static void initializeServoPwm(uint8_t initialAngle) {
  // Uno Timer1 Fast PWM mode 14: 16 MHz / 8 / 40000 = 50 Hz (20 ms frame).
  // D9/OC1A generates servo pulses in hardware on the 0.5 us timer tick.
  pinMode(SERVO_PIN, OUTPUT);
  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;
  ICR1 = (uint16_t)SERVO_PWM_TOP_TICKS;
  setServoTarget(initialAngle);
  TCCR1A = _BV(COM1A1) | _BV(WGM11); // non-inverting OC1A, WGM13:0 = 14
  TCCR1B = _BV(WGM13) | _BV(WGM12) | _BV(CS11); // prescaler 8
}

static void updateServoSweep(uint32_t now) {
  if ((uint32_t)(now - servoEndpointSince) < SERVO_ENDPOINT_HOLD_MS) return;

  servoAtZero = !servoAtZero;
  setServoTarget(servoAtZero ? 0U : 90U);
  servoEndpointSince = now;
}

static void showAllStripsForStartupTest() {
  for (uint8_t strip = 0; strip < STRIP_COUNT; ++strip) {
    for (uint8_t pixel = 0; pixel < PIXELS_PER_STRIP; ++pixel) {
      strips[strip].setPixelColor(
          pixel,
          STRIP_COLORS[strip][0],
          STRIP_COLORS[strip][1],
          STRIP_COLORS[strip][2]);
    }
    strips[strip].show();
  }
}

static bool updateButtons(uint32_t now) {
  bool changed = false;

  for (uint8_t i = 0; i < BUTTON_COUNT; ++i) {
    const bool sampledPressed = digitalRead(BUTTON_PINS[i]) == LOW;

    if (sampledPressed != buttons[i].rawPressed) {
      buttons[i].rawPressed = sampledPressed;
      buttons[i].changedAt = now;
    }

    if (buttons[i].stablePressed != buttons[i].rawPressed &&
        (uint32_t)(now - buttons[i].changedAt) >= DEBOUNCE_MS) {
      buttons[i].stablePressed = buttons[i].rawPressed;
      changed = true;
    }
  }

  return changed;
}

static void renderButtonOutputs() {
  const bool startPressed = buttons[4].stablePressed;

  for (uint8_t strip = 0; strip < STRIP_COUNT; ++strip) {
    const bool stripOn = startPressed || buttons[strip].stablePressed;

    for (uint8_t pixel = 0; pixel < PIXELS_PER_STRIP; ++pixel) {
      if (stripOn) {
        strips[strip].setPixelColor(
            pixel,
            STRIP_COLORS[strip][0],
            STRIP_COLORS[strip][1],
            STRIP_COLORS[strip][2]);
      } else {
        strips[strip].setPixelColor(pixel, 0, 0, 0);
      }
    }
    strips[strip].show();
  }
}

void setup() {
  initializeServoPwm(0U);
  servoAtZero = true;
  servoEndpointSince = millis();

  for (uint8_t strip = 0; strip < STRIP_COUNT; ++strip) {
    strips[strip].begin();
    strips[strip].setBrightness(TEST_BRIGHTNESS);
    strips[strip].clear();
  }

  // Briefly prove the four strip data paths, then leave them off until a button is pressed.
  showAllStripsForStartupTest();
  delay(STARTUP_TEST_MS);
  for (uint8_t strip = 0; strip < STRIP_COUNT; ++strip) {
    strips[strip].clear();
    strips[strip].show();
  }

  const uint32_t now = millis();
  for (uint8_t i = 0; i < BUTTON_COUNT; ++i) {
    pinMode(BUTTON_PINS[i], INPUT_PULLUP);
    const bool initiallyPressed = digitalRead(BUTTON_PINS[i]) == LOW;
    buttons[i].rawPressed = initiallyPressed;
    buttons[i].stablePressed = initiallyPressed;
    buttons[i].changedAt = now;
  }

  renderButtonOutputs();
}

void loop() {
  const uint32_t now = millis();
  if (updateButtons(now)) {
    renderButtonOutputs();
  }
  updateServoSweep(now);
}
