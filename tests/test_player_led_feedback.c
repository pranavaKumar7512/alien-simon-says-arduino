#include <assert.h>
#include <stdio.h>

#include "../player_led_feedback.h"

typedef struct {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
} FakePixel;

static unsigned int write_count;
static FakePixel pixels[PLAYER_LED_PIXEL_COUNT];
static const PlayerLedRgb EXPECTED_MAPPED_COLORS[PLAYER_LED_SYMBOL_COUNT] = {
  {255U, 0U, 0U},   // red
  {0U, 255U, 0U},   // green
  {0U, 0U, 255U},   // blue
  {255U, 255U, 0U}  // yellow
};

static void reset_pixels(void) {
  write_count = 0;
  for (uint8_t i = 0; i < PLAYER_LED_PIXEL_COUNT; ++i) {
    pixels[i] = (FakePixel){0U, 0U, 0U};
  }
}

static void fake_pixel_write(uint8_t pixel, uint8_t red, uint8_t green, uint8_t blue) {
  ++write_count;
  assert(pixel < PLAYER_LED_PIXEL_COUNT);
  pixels[pixel].red = red;
  pixels[pixel].green = green;
  pixels[pixel].blue = blue;
}

static bool is_rgb(FakePixel pixel, PlayerLedRgb expected) {
  return pixel.red == expected.red &&
         pixel.green == expected.green &&
         pixel.blue == expected.blue;
}

static void assert_group_pattern(uint8_t active_group, bool active) {
  const PlayerLedRgb black = {0U, 0U, 0U};
  for (uint8_t group = 0; group < PLAYER_LED_SYMBOL_COUNT; ++group) {
    const PlayerLedRgb expected = active && group == active_group
                                      ? EXPECTED_MAPPED_COLORS[group]
                                      : black;
    for (uint8_t offset = 0; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(group * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      assert(is_rgb(pixels[pixel], expected));
    }
  }
}

static void assert_mapping_with_color_off(const uint8_t *mapping, uint8_t color_off) {
  const PlayerLedRgb black = {0U, 0U, 0U};
  for (uint8_t position = 0U; position < PLAYER_LED_SYMBOL_COUNT; ++position) {
    const PlayerLedRgb expected = mapping[position] == color_off
                                      ? black
                                      : EXPECTED_MAPPED_COLORS[mapping[position]];
    for (uint8_t offset = 0U; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(position * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      assert(is_rgb(pixels[pixel], expected));
    }
  }
}

int main(void) {
  assert(PLAYER_LED_SYMBOL_COUNT == 4U);
  assert(PLAYER_LED_PIXELS_PER_SYMBOL == 6U);
  assert(PLAYER_LED_PIXEL_COUNT == 24U);
  assert(PLAYER_LED_PIXEL_COUNT == PLAYER_LED_SYMBOL_COUNT * PLAYER_LED_PIXELS_PER_SYMBOL);
  assert(PLAYER_LED_BRIGHTNESS == 255U);
  const uint8_t expected_data_pins[PLAYER_LED_SYMBOL_COUNT] = {2U, 3U, 4U, 12U};
  for (uint8_t strip = 0U; strip < PLAYER_LED_SYMBOL_COUNT; ++strip) {
    assert(PLAYER_LED_DATA_PINS[strip] == expected_data_pins[strip]);
  }
  for (uint8_t pixel = 0U; pixel < PLAYER_LED_PIXEL_COUNT; ++pixel) {
    assert(playerLedStripForPixel(pixel) ==
           (uint8_t)(pixel / PLAYER_LED_PIXELS_PER_SYMBOL));
    assert(playerLedPixelWithinStrip(pixel) ==
           (uint8_t)(pixel % PLAYER_LED_PIXELS_PER_SYMBOL));
  }
  static const uint8_t groupBoundaries[] = {0U, 5U, 6U, 11U, 12U, 17U, 18U, 23U};
  static const uint8_t expectedBoundaryStrips[] = {0U, 0U, 1U, 1U, 2U, 2U, 3U, 3U};
  static const uint8_t expectedBoundaryOffsets[] = {0U, 5U, 0U, 5U, 0U, 5U, 0U, 5U};
  for (size_t i = 0U; i < sizeof(groupBoundaries) / sizeof(groupBoundaries[0]); ++i) {
    assert(playerLedStripForPixel(groupBoundaries[i]) == expectedBoundaryStrips[i]);
    assert(playerLedPixelWithinStrip(groupBoundaries[i]) == expectedBoundaryOffsets[i]);
  }
  assert(playerLedStripForPixel(PLAYER_LED_PIXEL_COUNT) == PLAYER_LED_SYMBOL_COUNT);
  assert(playerLedPixelWithinStrip(PLAYER_LED_PIXEL_COUNT) == PLAYER_LED_PIXELS_PER_SYMBOL);

  for (uint8_t symbol = 0; symbol < PLAYER_LED_SYMBOL_COUNT; ++symbol) {
    reset_pixels();
    assert(playerLedSet(symbol, true, fake_pixel_write));
    assert(write_count == PLAYER_LED_PIXEL_COUNT);
    assert_group_pattern(symbol, true);

    reset_pixels();
    assert(playerLedSet(symbol, false, fake_pixel_write));
    assert(write_count == PLAYER_LED_PIXEL_COUNT);
    assert_group_pattern(symbol, false);
  }

  reset_pixels();
  assert(playerLedSetAllMappedColors(fake_pixel_write));
  assert(write_count == PLAYER_LED_PIXEL_COUNT);
  for (uint8_t group = 0; group < PLAYER_LED_SYMBOL_COUNT; ++group) {
    for (uint8_t offset = 0; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(group * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      assert(is_rgb(pixels[pixel], EXPECTED_MAPPED_COLORS[group]));
    }
  }

  const uint8_t button_to_color[PLAYER_LED_SYMBOL_COUNT] = {2U, 0U, 3U, 1U};
  reset_pixels();
  assert(playerLedSetButtonMapping(button_to_color, fake_pixel_write));
  assert(write_count == PLAYER_LED_PIXEL_COUNT);
  for (uint8_t position = 0U; position < PLAYER_LED_SYMBOL_COUNT; ++position) {
    for (uint8_t offset = 0U; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
      const uint8_t pixel = (uint8_t)(position * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
      assert(is_rgb(pixels[pixel], EXPECTED_MAPPED_COLORS[button_to_color[position]]));
    }
  }

  for (uint8_t cue_color = 0U; cue_color < PLAYER_LED_SYMBOL_COUNT; ++cue_color) {
    reset_pixels();
    assert(playerLedSetButtonMappingWithColorOff(
        button_to_color, cue_color, fake_pixel_write));
    assert(write_count == PLAYER_LED_PIXEL_COUNT);
    assert_mapping_with_color_off(button_to_color, cue_color);
  }

  for (uint8_t cue_color = 0U; cue_color < PLAYER_LED_SYMBOL_COUNT; ++cue_color) {
    uint8_t mapped_position = 0U;
    while (button_to_color[mapped_position] != cue_color) ++mapped_position;
    reset_pixels();
    assert(playerLedSetMappedCue(button_to_color, cue_color, true, fake_pixel_write));
    assert(write_count == PLAYER_LED_PIXEL_COUNT);
    for (uint8_t position = 0U; position < PLAYER_LED_SYMBOL_COUNT; ++position) {
      const PlayerLedRgb expected = position == mapped_position
                                        ? EXPECTED_MAPPED_COLORS[cue_color]
                                        : (PlayerLedRgb){0U, 0U, 0U};
      for (uint8_t offset = 0U; offset < PLAYER_LED_PIXELS_PER_SYMBOL; ++offset) {
        const uint8_t pixel = (uint8_t)(position * PLAYER_LED_PIXELS_PER_SYMBOL + offset);
        assert(is_rgb(pixels[pixel], expected));
      }
    }
    assert(playerLedSetMappedCue(button_to_color, cue_color, false, fake_pixel_write));
    assert(write_count == 2U * PLAYER_LED_PIXEL_COUNT);
    for (uint8_t pixel = 0U; pixel < PLAYER_LED_PIXEL_COUNT; ++pixel) {
      assert(is_rgb(pixels[pixel], (PlayerLedRgb){0U, 0U, 0U}));
    }
  }

  const uint8_t invalid_mapping[PLAYER_LED_SYMBOL_COUNT] = {0U, 0U, 2U, 3U};
  reset_pixels();
  assert(!playerLedSetButtonMapping(invalid_mapping, fake_pixel_write));
  assert(!playerLedSetButtonMappingWithColorOff(invalid_mapping, 0U, fake_pixel_write));
  assert(!playerLedSetButtonMappingWithColorOff(button_to_color, PLAYER_LED_SYMBOL_COUNT,
                                                fake_pixel_write));
  assert(!playerLedSetButtonMappingWithColorOff(button_to_color, 0U, 0));
  assert(!playerLedSetMappedCue(invalid_mapping, 0U, true, fake_pixel_write));
  assert(!playerLedSetMappedCue(button_to_color, PLAYER_LED_SYMBOL_COUNT, true, fake_pixel_write));
  assert(!playerLedSetMappedCue(button_to_color, 0U, true, 0));
  assert(!playerLedSetButtonMapping(0, fake_pixel_write));
  assert(!playerLedSetButtonMapping(button_to_color, 0));
  assert(write_count == 0U);

  reset_pixels();
  assert(!playerLedSet(PLAYER_LED_SYMBOL_COUNT, true, fake_pixel_write));
  assert(!playerLedSet(0xFFU, false, fake_pixel_write));
  assert(write_count == 0U);
  assert(!playerLedSet(0U, true, 0));
  assert(!playerLedSetAllMappedColors(0));
  assert(write_count == 0U);

  puts("24-pixel four-strip NeoPixel group tests passed");
  return 0;
}

