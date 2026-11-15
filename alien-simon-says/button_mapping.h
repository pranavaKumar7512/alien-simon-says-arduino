#ifndef BUTTON_MAPPING_H
#define BUTTON_MAPPING_H

#include <stdbool.h>
#include <stdint.h>

#include "game_sequence.h"

#define BUTTON_MAPPING_COUNT 4U
#define BUTTON_MAPPING_SEED_SALT 0xB5297A4DUL
#define BUTTON_MAPPING_FALLBACK_SEED 0x68E31DA4UL

// Seed a separate stream so remapping never advances or changes the cue stream.
static uint32_t buttonMappingSeed(uint32_t gameSeed) {
  uint32_t state = gameSeed ^ BUTTON_MAPPING_SEED_SALT;
  return state == 0U ? BUTTON_MAPPING_FALLBACK_SEED : state;
}

static void buttonMappingReset(uint8_t *mapping) {
  if (mapping == 0) return;
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    mapping[position] = position;
  }
}

// Shuffle a position->cue-color permutation. If the full permutation repeats,
// change it deterministically; individual button assignments may repeat.
static bool buttonMappingShuffle(uint8_t *mapping, uint32_t *state) {
  if (mapping == 0 || state == 0) return false;

  uint8_t previous[BUTTON_MAPPING_COUNT];
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    previous[position] = mapping[position];
  }

  buttonMappingReset(mapping);
  for (uint8_t remaining = BUTTON_MAPPING_COUNT - 1U; remaining > 0U; --remaining) {
    const uint8_t selected = gameSequenceUniformBelow(state, (uint8_t)(remaining + 1U));
    const uint8_t temporary = mapping[remaining];
    mapping[remaining] = mapping[selected];
    mapping[selected] = temporary;
  }

  bool same = true;
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    if (mapping[position] != previous[position]) {
      same = false;
      break;
    }
  }
  if (same) {
    const uint8_t temporary = mapping[0];
    mapping[0] = mapping[1];
    mapping[1] = temporary;
  }
  return true;
}

static uint8_t buttonMappingColorForPosition(const uint8_t *mapping, uint8_t position) {
  if (mapping == 0 || position >= BUTTON_MAPPING_COUNT) return 0xFFU;
  return mapping[position];
}

static uint8_t buttonMappingPositionForColor(const uint8_t *mapping, uint8_t color) {
  if (mapping == 0 || color >= BUTTON_MAPPING_COUNT) return 0xFFU;
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    if (mapping[position] == color) return position;
  }
  return 0xFFU;
}

#endif
