#ifndef PLAYER_LED_FEEDBACK_H
#define PLAYER_LED_FEEDBACK_H

#include <stdbool.h>
#include <stdint.h>

#define PLAYER_LED_SYMBOL_COUNT 4U
#define PLAYER_LED_PIXELS_PER_SYMBOL 6U
#define PLAYER_LED_PIXEL_COUNT (PLAYER_LED_SYMBOL_COUNT * PLAYER_LED_PIXELS_PER_SYMBOL)
#ifndef PLAYER_LED_BRIGHTNESS
#define PLAYER_LED_BRIGHTNESS 64U
#endif

// Each color group is one independent six-pixel strip, in red/green/blue/yellow order.
static const uint8_t PLAYER_LED_DATA_PINS[PLAYER_LED_SYMBOL_COUNT] = {2U, 3U, 4U, 12U};

static inline uint8_t playerLedStripForPixel(uint8_t pixel) {
  return pixel < PLAYER_LED_PIXEL_COUNT
             ? (uint8_t)(pixel / PLAYER_LED_PIXELS_PER_SYMBOL)
             : PLAYER_LED_SYMBOL_COUNT;
}

static inline uint8_t playerLedPixelWithinStrip(uint8_t pixel) {
  return pixel < PLAYER_LED_PIXEL_COUNT
             ? (uint8_t)(pixel % PLAYER_LED_PIXELS_PER_SYMBOL)
             : PLAYER_LED_PIXELS_PER_SYMBOL;
}

typedef struct {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
} PlayerLedRgb;

// Color groups: pixels 0-5 red, 6-11 green, 12-17 blue, and 18-23 yellow.
static const PlayerLedRgb PLAYER_LED_COLORS[PLAYER_LED_SYMBOL_COUNT] = {
  {255U, 0U, 0U},   // red, pixels 0-5
  {0U, 255U, 0U},   // green, pixels 6-11
  {0U, 0U, 255U},   // blue, pixels 12-17
  {255U, 255U, 0U}  // yellow, pixels 18-23
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

static inline bool playerLedMappingIsValid(const uint8_t *buttonToColor) {
  if (buttonToColor == 0) return false;

  uint8_t seen = 0U;
  for (uint8_t position = 0U; position < PLAYER_LED_SYMBOL_COUNT; ++position) {
    const uint8_t color = buttonToColor[position];
    if (color >= PLAYER_LED_SYMBOL_COUNT || (seen & (uint8_t)(1U << color)) != 0U) {
      return false;
    }
    seen |= (uint8_t)(1U << color);
  }
  return true;
}

// Illuminate every physical button-position group at once using that
// position's currently assigned cue color (not the strip's default color).
static inline bool playerLedSetButtonMapping(const uint8_t *buttonToColor,
                                             PlayerLedWritePixel writePixel) {
  if (!playerLedMappingIsValid(buttonToColor) || writePixel == 0) return false;

  for (uint8_t position = 0U; position < PLAYER_LED_SYMBOL_COUNT; ++position) {
    const PlayerLedRgb color = PLAYER_LED_COLORS[buttonToColor[position]];
    for (uint8_t offset = 0U; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(position * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      writePixel(pixel, color.red, color.green, color.blue);
    }
  }
  return true;
}

// Keep the current button/color map visible, but blank only the group assigned
// to the color the player just pressed.
static inline bool playerLedSetButtonMappingWithColorOff(
    const uint8_t *buttonToColor, uint8_t colorToTurnOff,
    PlayerLedWritePixel writePixel) {
  if (!playerLedMappingIsValid(buttonToColor) ||
      colorToTurnOff >= PLAYER_LED_SYMBOL_COUNT || writePixel == 0) return false;

  const PlayerLedRgb black = {0U, 0U, 0U};
  for (uint8_t position = 0U; position < PLAYER_LED_SYMBOL_COUNT; ++position) {
    const uint8_t mappedColor = buttonToColor[position];
    const PlayerLedRgb color = mappedColor == colorToTurnOff
                                   ? black
                                   : PLAYER_LED_COLORS[mappedColor];
    for (uint8_t offset = 0U; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(position * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      writePixel(pixel, color.red, color.green, color.blue);
    }
  }
  return true;
}

// During sequence playback, light only the physical button-position group
// assigned to a cue color, rendering that group's pixels in the assigned color.
static inline bool playerLedSetMappedCue(const uint8_t *buttonToColor,
                                         uint8_t cueColor, bool on,
                                         PlayerLedWritePixel writePixel) {
  if (!playerLedMappingIsValid(buttonToColor) ||
      cueColor >= PLAYER_LED_SYMBOL_COUNT || writePixel == 0) return false;

  uint8_t cuePosition = 0U;
  while (buttonToColor[cuePosition] != cueColor) ++cuePosition;
  for (uint8_t position = 0U; position < PLAYER_LED_SYMBOL_COUNT; ++position) {
    PlayerLedRgb color = {0U, 0U, 0U};
    if (on && position == cuePosition) color = PLAYER_LED_COLORS[cueColor];
    for (uint8_t offset = 0U; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(position * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
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
