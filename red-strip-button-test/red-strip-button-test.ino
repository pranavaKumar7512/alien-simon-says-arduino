#include <Adafruit_NeoPixel.h>
#include <DFRobotDFPlayerMini.h>
#include <SoftwareSerial.h>
#include <Wire.h>

// Standalone Button 1 / red-strip test for an Arduino Uno.
// The LCD and DFPlayer indicate commands/status only; they do not independently
// verify that the physical display or audio module acted on those commands.
static const uint8_t STRIP_COUNT = 4;
static const uint8_t PIXELS_PER_STRIP = 4;
static const uint8_t BUTTON_1_PIN = 6;
static const uint8_t RED_STRIP_INDEX = 0;
static const uint8_t TEST_BRIGHTNESS = 32;
static const uint32_t DEBOUNCE_MS = 25;
static const uint8_t LCD_I2C_ADDRESS = 0x3E;

// Independent strip data outputs: red D2, green D3, blue D4, yellow D5.
Adafruit_NeoPixel strips[STRIP_COUNT] = {
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 2, NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 3, NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 4, NEO_GRB + NEO_KHZ800),
  Adafruit_NeoPixel(PIXELS_PER_STRIP, 5, NEO_GRB + NEO_KHZ800)
};

// SoftwareSerial constructor order is Uno RX, then Uno TX.
SoftwareSerial mp3Serial(10, 11);
DFRobotDFPlayerMini mp3;

static bool buttonRawPressed = false;
static bool buttonStablePressed = false;
static uint32_t buttonChangedAt = 0;

static void sendLcdCommand(uint8_t command) {
  Wire.beginTransmission(LCD_I2C_ADDRESS);
  Wire.write((uint8_t)0x80);  // Grove JHD1804 command-control byte.
  Wire.write(command);
  Wire.endTransmission();
}

static void writeLcdRow(uint8_t ddramAddress, const char *text) {
  sendLcdCommand(ddramAddress);
  Wire.beginTransmission(LCD_I2C_ADDRESS);
  Wire.write((uint8_t)0x40);  // Grove JHD1804 display-data control byte.

  bool padding = false;
  for (uint8_t column = 0; column < 16; ++column) {
    char value = ' ';
    if (!padding) {
      value = text[column];
      if (value == '\0') {
        value = ' ';
        padding = true;
      }
    }
    Wire.write((uint8_t)value);
  }
  Wire.endTransmission();
}

static void initializeLcd() {
  Wire.begin();
  Wire.setWireTimeout(25000UL, true);

  // Staged initialization used by lcd-only-test for the Grove JHD1804.
  delay(50);
  sendLcdCommand(0x28);  // 4-bit, two-line, 5x8 font.
  delay(5);
  sendLcdCommand(0x28);
  delay(1);
  sendLcdCommand(0x28);
  delay(1);
  sendLcdCommand(0x28);
  delay(1);
  sendLcdCommand(0x0C);  // Display on; cursor and blink off.
  delay(2);
  sendLcdCommand(0x01);  // Clear display.
  delay(2);
  sendLcdCommand(0x06);  // Left-to-right entry mode.
  delay(2);

  writeLcdRow(0x80, "RED LIGHT OFF");
  writeLcdRow(0xC0, "");
}

static void setRedStrip(bool on) {
  Adafruit_NeoPixel &redStrip = strips[RED_STRIP_INDEX];
  for (uint8_t pixel = 0; pixel < PIXELS_PER_STRIP; ++pixel) {
    if (on) {
      redStrip.setPixelColor(pixel, 255, 0, 0);
    } else {
      redStrip.setPixelColor(pixel, 0, 0, 0);
    }
  }
  redStrip.show();
}

static void updateOutputsForStableButtonState() {
  setRedStrip(buttonStablePressed);
  writeLcdRow(0x80, buttonStablePressed ? "RED LIGHT ON" : "RED LIGHT OFF");
}

void setup() {
  for (uint8_t strip = 0; strip < STRIP_COUNT; ++strip) {
    strips[strip].begin();
    strips[strip].setBrightness(TEST_BRIGHTNESS);
    strips[strip].clear();
    strips[strip].show();
  }

  initializeLcd();

  // Send one loop-disable and one stop command at startup; never start playback.
  mp3Serial.begin(9600);
  mp3.begin(mp3Serial, false, false);
  mp3.disableLoop();
  mp3.stop();

  pinMode(BUTTON_1_PIN, INPUT_PULLUP);
  buttonRawPressed = digitalRead(BUTTON_1_PIN) == LOW;
  // Begin released so a button held during startup must remain stable for the
  // complete debounce interval before activating the red strip.
  buttonStablePressed = false;
  buttonChangedAt = millis();
}

void loop() {
  const uint32_t now = millis();
  const bool sampledPressed = digitalRead(BUTTON_1_PIN) == LOW;

  if (sampledPressed != buttonRawPressed) {
    buttonRawPressed = sampledPressed;
    buttonChangedAt = now;
  }

  if (buttonRawPressed != buttonStablePressed &&
      (uint32_t)(now - buttonChangedAt) >= DEBOUNCE_MS) {
    buttonStablePressed = buttonRawPressed;
    updateOutputsForStableButtonState();
  }
}
