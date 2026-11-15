#include <Wire.h>

// LCD-only diagnostic for the Seeed Grove 16x2 JHD1804M1 at I2C address 0x3E.
// It writes "PI AGENT" on row 1 and blanks row 2. It does not command the
// NeoPixel strips, buttons, servo, or MP3 player. This sketch cannot remove
// power from modules that remain physically connected to Uno 5V.

static const uint8_t LCD_I2C_ADDRESS = 0x3E;

static void sendLcdCommand(uint8_t command) {
  Wire.beginTransmission(LCD_I2C_ADDRESS);
  Wire.write((uint8_t)0x80);  // Seeed Grove library command-control byte.
  Wire.write(command);
  Wire.endTransmission();
}

static void writeLcdRow(uint8_t ddramAddress, const char *text) {
  sendLcdCommand(ddramAddress);
  Wire.beginTransmission(LCD_I2C_ADDRESS);
  Wire.write((uint8_t)0x40);  // Seeed Grove library display-data control byte.
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

void setup() {
  Wire.begin();
  Wire.setWireTimeout(25000UL, true);

  // Match the staged initialization used by the project firmware.
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

  writeLcdRow(0x80, "PI AGENT");
  writeLcdRow(0xC0, "");
}

void loop() {
  // Hold the test message; no other components are actively driven.
}
