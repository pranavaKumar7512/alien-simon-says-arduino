#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "../button_mapping.h"

static int is_permutation(const uint8_t *mapping) {
  uint8_t seen = 0U;
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    const uint8_t color = mapping[position];
    if (color >= BUTTON_MAPPING_COUNT || (seen & (uint8_t)(1U << color)) != 0U) return 0;
    seen |= (uint8_t)(1U << color);
  }
  return seen == 0x0FU;
}

static int equal_mapping(const uint8_t *left, const uint8_t *right) {
  for (uint8_t i = 0U; i < BUTTON_MAPPING_COUNT; ++i) {
    if (left[i] != right[i]) return 0;
  }
  return 1;
}

static void test_reset_and_lookup(void) {
  uint8_t mapping[BUTTON_MAPPING_COUNT] = {3U, 2U, 1U, 0U};
  buttonMappingReset(mapping);
  for (uint8_t position = 0U; position < BUTTON_MAPPING_COUNT; ++position) {
    assert(mapping[position] == position);
    assert(buttonMappingColorForPosition(mapping, position) == position);
    assert(buttonMappingPositionForColor(mapping, position) == position);
  }
  assert(buttonMappingColorForPosition(mapping, BUTTON_MAPPING_COUNT) == 0xFFU);
  assert(buttonMappingPositionForColor(mapping, BUTTON_MAPPING_COUNT) == 0xFFU);
  assert(buttonMappingColorForPosition(NULL, 0U) == 0xFFU);
  assert(buttonMappingPositionForColor(NULL, 0U) == 0xFFU);
}

static void test_seeded_shuffles_are_permutations_and_replayable(void) {
  uint8_t first[BUTTON_MAPPING_COUNT];
  uint8_t replay[BUTTON_MAPPING_COUNT];
  buttonMappingReset(first);
  buttonMappingReset(replay);
  uint32_t firstState = buttonMappingSeed(0x12345678UL);
  uint32_t replayState = buttonMappingSeed(0x12345678UL);
  static const uint8_t expectedFirstMaps[3][BUTTON_MAPPING_COUNT] = {
    {1U, 2U, 3U, 0U},
    {1U, 2U, 0U, 3U},
    {3U, 0U, 1U, 2U},
  };
  assert(firstState != 0U);
  assert(firstState == replayState);

  for (uint8_t block = 0U; block < 16U; ++block) {
    const uint8_t previous[BUTTON_MAPPING_COUNT] = {
      first[0], first[1], first[2], first[3]
    };
    assert(buttonMappingShuffle(first, &firstState));
    assert(buttonMappingShuffle(replay, &replayState));
    assert(is_permutation(first));
    assert(equal_mapping(first, replay));
    assert(!equal_mapping(first, previous));
    if (block < 3U) assert(equal_mapping(first, expectedFirstMaps[block]));
  }

  assert(!buttonMappingShuffle(NULL, &firstState));
  assert(!buttonMappingShuffle(first, NULL));
}

static void test_exact_previous_mapping_is_changed(void) {
  uint8_t previous[BUTTON_MAPPING_COUNT];
  uint8_t candidate[BUTTON_MAPPING_COUNT];
  uint32_t firstState = buttonMappingSeed(0xBADA55UL);
  uint32_t replayState = buttonMappingSeed(0xBADA55UL);
  buttonMappingReset(previous);
  buttonMappingReset(candidate);
  assert(buttonMappingShuffle(previous, &firstState));
  for (uint8_t i = 0U; i < BUTTON_MAPPING_COUNT; ++i) candidate[i] = previous[i];
  assert(buttonMappingShuffle(candidate, &replayState));
  assert(is_permutation(candidate));
  assert(!equal_mapping(candidate, previous));
}

static void test_mapping_stream_does_not_advance_cue_stream(void) {
  GameSequenceStream baseline;
  GameSequenceStream withMapping;
  uint8_t baselineCues[20];
  uint8_t mappedCues[20];
  uint8_t mapping[BUTTON_MAPPING_COUNT];
  buttonMappingReset(mapping);
  uint32_t mappingState = buttonMappingSeed(0xA341316CUL);
  gameSequenceChooseFirst(&baseline, 0xA341316CUL);
  gameSequenceChooseFirst(&withMapping, 0xA341316CUL);

  for (uint8_t i = 0U; i < 20U; ++i) {
    if (i == 3U || i == 9U || i == 15U) {
      assert(buttonMappingShuffle(mapping, &mappingState));
    }
    baselineCues[i] = gameSequenceNextSymbol(&baseline);
    mappedCues[i] = gameSequenceNextSymbol(&withMapping);
  }
  for (uint8_t i = 0U; i < 20U; ++i) assert(baselineCues[i] == mappedCues[i]);
}

int main(void) {
  test_reset_and_lookup();
  test_seeded_shuffles_are_permutations_and_replayable();
  test_exact_previous_mapping_is_changed();
  test_mapping_stream_does_not_advance_cue_stream();
  puts("button mapping tests passed");
  return 0;
}
