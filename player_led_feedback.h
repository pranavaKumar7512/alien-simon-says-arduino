#ifndef PLAYER_LED_FEEDBACK_H
#define PLAYER_LED_FEEDBACK_H

#include <stdbool.h>
#include <stdint.h>

#define PLAYER_LED_SYMBOL_COUNT 4U
#define PLAYER_LED_PIXELS_PER_SYMBOL 4U
#define PLAYER_LED_PIXEL_COUNT (PLAYER_LED_SYMBOL_COUNT * PLAYER_LED_PIXELS_PER_SYMBOL)
#define PLAYER_LED_DATA_PIN 2U
#define PLAYER_LED_BRIGHTNESS 255U

typedef struct {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
} PlayerLedRgb;

// Color groups: pixels 0-3 red, 4-7 green, 8-11 blue, and 12-15 yellow.
static const PlayerLedRgb PLAYER_LED_COLORS[PLAYER_LED_SYMBOL_COUNT] = {
  {255U, 0U, 0U},   // red, pixels 0-3
  {0U, 255U, 0U},   // green, pixels 4-7
  {0U, 0U, 255U},   // blue, pixels 8-11
  {255U, 255U, 0U}  // yellow, pixels 12-15
};

typedef void (*PlayerLedWritePixel)(uint8_t pixel, uint8_t red,
                                    uint8_t green, uint8_t blue);

static inline bool playerLedSet(uint8_t symbol, bool on,
                                PlayerLedWritePixel writePixel) {
  if (symbol >= PLAYER_LED_SYMBOL_COUNT || writePixel == 0) return false;

  for (uint8_t group = 0; group < PLAYER_LED_SYMBOL_COUNT; ++group) {
    PlayerLedRgb color = {0U, 0U, 0U};
    if (on && group == symbol) color = PLAYER_LED_COLORS[group];

    for (uint8_t offset = 0; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(group * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      writePixel(pixel, color.red, color.green, color.blue);
    }
  }
  return true;
}

static inline bool playerLedSetAllMappedColors(PlayerLedWritePixel writePixel) {
  if (writePixel == 0) return false;

  for (uint8_t group = 0; group < PLAYER_LED_SYMBOL_COUNT; ++group) {
    const PlayerLedRgb color = PLAYER_LED_COLORS[group];
    for (uint8_t offset = 0; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(group * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      writePixel(pixel, color.red, color.green, color.blue);
    }
  }
  return true;
}

#endif
