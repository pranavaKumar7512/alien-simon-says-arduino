#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "wokwi-api.h"

#define LCD_ADDRESS 0x3E
#define DISPLAY_WIDTH 128
#define DISPLAY_HEIGHT 32
#define CELL_WIDTH 8
#define CELL_HEIGHT 16

static buffer_t display_buffer;
static uint8_t pixels[DISPLAY_WIDTH * DISPLAY_HEIGHT * 4];
static char ddram[2][16];
static uint8_t cursor_address;
static uint8_t control_prefix;
static bool has_control_prefix;
static bool display_enabled;
static bool entry_increment;
static bool cgram_selected;

static void glyph(char character, uint8_t columns[5]) {
  memset(columns, 0, 5);
  if (character >= 'a' && character <= 'z') character = (char)(character - 'a' + 'A');
  switch (character) {
    case 'A': { const uint8_t g[5] = {0x7E,0x11,0x11,0x11,0x7E}; memcpy(columns,g,5); break; }
    case 'B': { const uint8_t g[5] = {0x7F,0x49,0x49,0x49,0x36}; memcpy(columns,g,5); break; }
    case 'C': { const uint8_t g[5] = {0x3E,0x41,0x41,0x41,0x22}; memcpy(columns,g,5); break; }
    case 'D': { const uint8_t g[5] = {0x7F,0x41,0x41,0x22,0x1C}; memcpy(columns,g,5); break; }
    case 'E': { const uint8_t g[5] = {0x7F,0x49,0x49,0x49,0x41}; memcpy(columns,g,5); break; }
    case 'F': { const uint8_t g[5] = {0x7F,0x09,0x09,0x09,0x01}; memcpy(columns,g,5); break; }
    case 'G': { const uint8_t g[5] = {0x3E,0x41,0x49,0x49,0x7A}; memcpy(columns,g,5); break; }
    case 'H': { const uint8_t g[5] = {0x7F,0x08,0x08,0x08,0x7F}; memcpy(columns,g,5); break; }
    case 'I': { const uint8_t g[5] = {0x00,0x41,0x7F,0x41,0x00}; memcpy(columns,g,5); break; }
    case 'J': { const uint8_t g[5] = {0x20,0x40,0x41,0x3F,0x01}; memcpy(columns,g,5); break; }
    case 'K': { const uint8_t g[5] = {0x7F,0x08,0x14,0x22,0x41}; memcpy(columns,g,5); break; }
    case 'L': { const uint8_t g[5] = {0x7F,0x40,0x40,0x40,0x40}; memcpy(columns,g,5); break; }
    case 'M': { const uint8_t g[5] = {0x7F,0x02,0x04,0x02,0x7F}; memcpy(columns,g,5); break; }
    case 'N': { const uint8_t g[5] = {0x7F,0x04,0x08,0x10,0x7F}; memcpy(columns,g,5); break; }
    case 'O': { const uint8_t g[5] = {0x3E,0x41,0x41,0x41,0x3E}; memcpy(columns,g,5); break; }
    case 'P': { const uint8_t g[5] = {0x7F,0x09,0x09,0x09,0x06}; memcpy(columns,g,5); break; }
    case 'Q': { const uint8_t g[5] = {0x3E,0x41,0x51,0x21,0x5E}; memcpy(columns,g,5); break; }
    case 'R': { const uint8_t g[5] = {0x7F,0x09,0x19,0x29,0x46}; memcpy(columns,g,5); break; }
    case 'S': { const uint8_t g[5] = {0x46,0x49,0x49,0x49,0x31}; memcpy(columns,g,5); break; }
    case 'T': { const uint8_t g[5] = {0x01,0x01,0x7F,0x01,0x01}; memcpy(columns,g,5); break; }
    case 'U': { const uint8_t g[5] = {0x3F,0x40,0x40,0x40,0x3F}; memcpy(columns,g,5); break; }
    case 'V': { const uint8_t g[5] = {0x1F,0x20,0x40,0x20,0x1F}; memcpy(columns,g,5); break; }
    case 'W': { const uint8_t g[5] = {0x3F,0x40,0x38,0x40,0x3F}; memcpy(columns,g,5); break; }
    case 'X': { const uint8_t g[5] = {0x63,0x14,0x08,0x14,0x63}; memcpy(columns,g,5); break; }
    case 'Y': { const uint8_t g[5] = {0x07,0x08,0x70,0x08,0x07}; memcpy(columns,g,5); break; }
    case 'Z': { const uint8_t g[5] = {0x61,0x51,0x49,0x45,0x43}; memcpy(columns,g,5); break; }
    case '0': { const uint8_t g[5] = {0x3E,0x45,0x49,0x51,0x3E}; memcpy(columns,g,5); break; }
    case '1': { const uint8_t g[5] = {0x00,0x42,0x7F,0x40,0x00}; memcpy(columns,g,5); break; }
    case '2': { const uint8_t g[5] = {0x62,0x51,0x49,0x49,0x46}; memcpy(columns,g,5); break; }
    case '3': { const uint8_t g[5] = {0x22,0x41,0x49,0x49,0x36}; memcpy(columns,g,5); break; }
    case '4': { const uint8_t g[5] = {0x18,0x14,0x12,0x7F,0x10}; memcpy(columns,g,5); break; }
    case '5': { const uint8_t g[5] = {0x2F,0x49,0x49,0x49,0x31}; memcpy(columns,g,5); break; }
    case '6': { const uint8_t g[5] = {0x3E,0x49,0x49,0x49,0x32}; memcpy(columns,g,5); break; }
    case '7': { const uint8_t g[5] = {0x01,0x71,0x09,0x05,0x03}; memcpy(columns,g,5); break; }
    case '8': { const uint8_t g[5] = {0x36,0x49,0x49,0x49,0x36}; memcpy(columns,g,5); break; }
    case '9': { const uint8_t g[5] = {0x26,0x49,0x49,0x49,0x3E}; memcpy(columns,g,5); break; }
    case ':': { const uint8_t g[5] = {0x00,0x36,0x36,0x00,0x00}; memcpy(columns,g,5); break; }
    case '-': { const uint8_t g[5] = {0x08,0x08,0x08,0x08,0x08}; memcpy(columns,g,5); break; }
    case '.': { const uint8_t g[5] = {0x00,0x60,0x60,0x00,0x00}; memcpy(columns,g,5); break; }
    case '!': { const uint8_t g[5] = {0x00,0x00,0x5F,0x00,0x00}; memcpy(columns,g,5); break; }
    default: break;
  }
}

static void setPixel(uint32_t x, uint32_t y, uint8_t red, uint8_t green, uint8_t blue) {
  uint32_t offset = (y * DISPLAY_WIDTH + x) * 4;
  pixels[offset] = red;
  pixels[offset + 1] = green;
  pixels[offset + 2] = blue;
  pixels[offset + 3] = 0xFF;
}

static void render(void) {
  const uint8_t bgR = 0xE8, bgG = 0xD5, bgB = 0x8E;
  for (uint32_t y = 0; y < DISPLAY_HEIGHT; ++y) {
    for (uint32_t x = 0; x < DISPLAY_WIDTH; ++x) setPixel(x, y, bgR, bgG, bgB);
  }

  if (display_enabled) {
    for (uint8_t row = 0; row < 2; ++row) {
      for (uint8_t col = 0; col < 16; ++col) {
        uint8_t columns[5];
        glyph(ddram[row][col], columns);
        for (uint8_t gx = 0; gx < 5; ++gx) {
          for (uint8_t gy = 0; gy < 7; ++gy) {
            if (columns[gx] & (1U << gy)) {
              for (uint8_t sy = 0; sy < 2; ++sy) {
                setPixel(col * CELL_WIDTH + gx,
                         row * CELL_HEIGHT + 1 + gy * 2 + sy,
                         0x12, 0x12, 0x12);
              }
            }
          }
        }
      }
    }
  }
  buffer_write(display_buffer, 0, pixels, sizeof(pixels));
}

static void clearDisplay(void) {
  memset(ddram, ' ', sizeof(ddram));
  cursor_address = 0;
  cgram_selected = false;
  render();
}

static void returnHome(void) {
  cursor_address = 0;
  cgram_selected = false;
}

static void setDdramAddress(uint8_t address) {
  cursor_address = address & 0x7F;
  cgram_selected = false;
}

static void executeCommand(uint8_t command) {
  if (command == 0x01) {
    clearDisplay();
    return;
  }
  if (command == 0x02) {
    returnHome();
    return;
  }
  if ((command & 0x80) != 0) {
    setDdramAddress(command & 0x7F);
    return;
  }
  if ((command & 0x40) != 0) {
    cgram_selected = true; // The game uses only the standard character set.
    return;
  }
  if ((command & 0xF8) == 0x08) {
    display_enabled = (command & 0x04) != 0;
    render();
    return;
  }
  if ((command & 0xFC) == 0x04) {
    entry_increment = (command & 0x02) != 0;
  }
}

static void writeDisplayData(uint8_t value) {
  if (cgram_selected) return;
  uint8_t address = cursor_address & 0x7F;
  uint8_t row = 0xFF;
  uint8_t col = 0;
  if (address < 16) {
    row = 0;
    col = address;
  } else if (address >= 0x40 && address < 0x50) {
    row = 1;
    col = address - 0x40;
  }
  if (row != 0xFF) {
    ddram[row][col] = (char)value;
    render();
  }
  if (entry_increment) {
    ++cursor_address;
  } else if ((cursor_address & 0x7F) != 0) {
    --cursor_address;
  }
}

static bool onI2cConnect(void *user_data, uint32_t address, bool read) {
  (void)user_data;
  (void)read;
  if (address != LCD_ADDRESS) return false;
  has_control_prefix = false; // each Seeed library I2C transaction begins with 0x80 or 0x40
  return true;
}

static bool onI2cWrite(void *user_data, uint8_t value) {
  (void)user_data;
  if (!has_control_prefix) {
    if (value != 0x80 && value != 0x40) return false;
    control_prefix = value;
    has_control_prefix = true;
    return true;
  }
  if (control_prefix == 0x80) executeCommand(value);
  else if (control_prefix == 0x40) writeDisplayData(value);
  return true;
}

void chip_init(void) {
  uint32_t width = DISPLAY_WIDTH;
  uint32_t height = DISPLAY_HEIGHT;
  display_buffer = framebuffer_init(&width, &height);
  memset(ddram, ' ', sizeof(ddram));
  control_prefix = 0;
  has_control_prefix = false;
  cursor_address = 0;
  display_enabled = false;
  entry_increment = true;
  cgram_selected = false;

  i2c_config_t config = {
    .user_data = NULL,
    .address = LCD_ADDRESS,
    .scl = pin_init("SCL", INPUT_PULLUP),
    .sda = pin_init("SDA", INPUT_PULLUP),
    .connect = onI2cConnect,
    .read = NULL,
    .write = onI2cWrite,
    .disconnect = NULL,
  };
  i2c_init(&config);
  render();
}
