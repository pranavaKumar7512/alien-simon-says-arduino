#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../chips/grove-jhd1804.chip.c"

static i2c_config_t registered_i2c;
static uint8_t rendered_pixels[DISPLAY_WIDTH * DISPLAY_HEIGHT * 4];

void timer_start_ns_d(timer_t timer, double nanos, bool repeat) {
  (void)timer;
  (void)nanos;
  (void)repeat;
}

double get_sim_nanos_d(void) {
  return 0.0;
}

pin_t pin_init(const char *name, uint32_t mode) {
  (void)name;
  (void)mode;
  return 1;
}

buffer_t framebuffer_init(uint32_t *width, uint32_t *height) {
  *width = DISPLAY_WIDTH;
  *height = DISPLAY_HEIGHT;
  return 7;
}

void buffer_write(buffer_t buffer, uint32_t offset, void *data, uint32_t data_len) {
  assert(buffer == 7);
  assert(offset == 0);
  assert(data_len == sizeof(rendered_pixels));
  memcpy(rendered_pixels, data, data_len);
}

i2c_dev_t i2c_init(const i2c_config_t *config) {
  registered_i2c = *config;
  return 1;
}

static void beginWrite(void) {
  assert(registered_i2c.connect(registered_i2c.user_data, LCD_ADDRESS, false));
}

static void writeByte(uint8_t value) {
  assert(registered_i2c.write(registered_i2c.user_data, value));
}

int main(void) {
  chip_init();
  assert(registered_i2c.address == 0x3E);
  assert(!registered_i2c.connect(registered_i2c.user_data, 0x3F, false));

  // Seeed Grove library setCursor(0, 0): control 0x80 followed by command 0x80.
  // The payload equals the prefix, so it must still be parsed as a command.
  beginWrite();
  writeByte(0x80);
  writeByte(0x80);
  assert(cursor_address == 0x00);

  beginWrite();
  writeByte(0x80);
  writeByte(0x0C); // display on, cursor/blink off
  assert(display_enabled);

  const char row0[] = "PRESS START     ";
  beginWrite();
  writeByte(0x40);
  for (uint8_t i = 0; i < sizeof(row0) - 1; ++i) writeByte((uint8_t)row0[i]);
  assert(memcmp(ddram[0], row0, sizeof(row0) - 1) == 0);

  // Seeed Grove library setCursor(0, 1): control 0x80, command 0xC0.
  beginWrite();
  writeByte(0x80);
  writeByte(0xC0);
  assert(cursor_address == 0x40);

  const char row1[] = "YOUR:0000000000 ";
  beginWrite();
  writeByte(0x40);
  for (uint8_t i = 0; i < sizeof(row1) - 1; ++i) writeByte((uint8_t)row1[i]);
  assert(memcmp(ddram[1], row1, sizeof(row1) - 1) == 0);

  bool has_dark_pixel = false;
  for (size_t i = 0; i < sizeof(rendered_pixels); i += 4) {
    if (rendered_pixels[i] < 0x80 && rendered_pixels[i + 1] < 0x80) {
      has_dark_pixel = true;
      break;
    }
  }
  assert(has_dark_pixel);

  beginWrite();
  writeByte(0x80);
  writeByte(0xC3); // move the cursor away from home without changing DDRAM
  assert(cursor_address == 0x43);

  beginWrite();
  writeByte(0x80);
  writeByte(0x02); // Return Home resets address mode, but preserves displayed text
  assert(cursor_address == 0x00);
  assert(!cgram_selected);
  assert(memcmp(ddram[0], row0, sizeof(row0) - 1) == 0);
  assert(memcmp(ddram[1], row1, sizeof(row1) - 1) == 0);

  beginWrite();
  writeByte(0x80);
  writeByte(0x01); // clear display
  assert(cursor_address == 0x00);
  for (uint8_t row = 0; row < 2; ++row) {
    for (uint8_t col = 0; col < 16; ++col) assert(ddram[row][col] == ' ');
  }

  puts("Grove JHD1804 I2C command/data model tests passed");
  return 0;
}
