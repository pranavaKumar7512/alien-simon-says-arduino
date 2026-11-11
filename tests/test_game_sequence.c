#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "../game_sequence.h"

static uint8_t take_four_symbol_mask(GameSequenceStream *stream, uint8_t first) {
  uint8_t seen = (uint8_t)(1U << first);
  for (uint8_t i = 1U; i < GAME_SEQUENCE_SYMBOL_COUNT; ++i) {
    const uint8_t symbol = gameSequenceNextSymbol(stream);
    assert(symbol < GAME_SEQUENCE_SYMBOL_COUNT);
    assert((seen & (uint8_t)(1U << symbol)) == 0U);
    seen |= (uint8_t)(1U << symbol);
  }
  return seen;
}

static void test_each_four_cues_use_every_color_once(void) {
  for (uint32_t seed = 1U; seed <= 2048U; ++seed) {
    GameSequenceStream stream;
    const uint8_t first = gameSequenceChooseFirst(
        &stream, seed, GAME_SEQUENCE_NO_PREVIOUS);
    assert(first < GAME_SEQUENCE_SYMBOL_COUNT);
    assert(take_four_symbol_mask(&stream, first) == 0x0FU);

    for (uint8_t block = 1U; block < 8U; ++block) {
      const uint8_t next = gameSequenceNextSymbol(&stream);
      assert(take_four_symbol_mask(&stream, next) == 0x0FU);
    }
  }
}

static void test_first_color_excludes_previous_but_all_others_are_eligible(void) {
  for (uint8_t previous = 0U; previous < GAME_SEQUENCE_SYMBOL_COUNT; ++previous) {
    uint16_t counts[GAME_SEQUENCE_SYMBOL_COUNT] = {0U, 0U, 0U, 0U};
    for (uint32_t seed = 1U; seed <= 4096U; ++seed) {
      GameSequenceStream stream;
      const uint8_t first = gameSequenceChooseFirst(&stream, seed, previous);
      assert(first < GAME_SEQUENCE_SYMBOL_COUNT);
      assert(first != previous);
      ++counts[first];
    }

    assert(counts[previous] == 0U);
    for (uint8_t color = 0U; color < GAME_SEQUENCE_SYMBOL_COUNT; ++color) {
      if (color != previous) assert(counts[color] > 100U);
    }
  }
}

static void test_first_color_is_unconstrained_on_first_game(void) {
  uint16_t counts[GAME_SEQUENCE_SYMBOL_COUNT] = {0U, 0U, 0U, 0U};
  for (uint32_t seed = 1U; seed <= 4096U; ++seed) {
    GameSequenceStream stream;
    const uint8_t first = gameSequenceChooseFirst(
        &stream, seed, GAME_SEQUENCE_NO_PREVIOUS);
    assert(first < GAME_SEQUENCE_SYMBOL_COUNT);
    ++counts[first];
  }
  for (uint8_t color = 0U; color < GAME_SEQUENCE_SYMBOL_COUNT; ++color) {
    assert(counts[color] > 500U);
  }
}

static void test_seed_replay(void) {
  static const uint8_t expected[16] = {
    3U, 0U, 1U, 2U, 0U, 2U, 1U, 3U,
    0U, 2U, 1U, 3U, 1U, 2U, 0U, 3U
  };
  GameSequenceStream first;
  GameSequenceStream replay;
  const uint8_t firstSymbol = gameSequenceChooseFirst(&first, 0xA341316CUL, 2U);
  const uint8_t replayFirst = gameSequenceChooseFirst(&replay, 0xA341316CUL, 2U);
  assert(firstSymbol == replayFirst);
  assert(firstSymbol == expected[0]);

  for (uint8_t i = 1U; i < 16U; ++i) {
    assert(gameSequenceNextSymbol(&first) == expected[i]);
    assert(gameSequenceNextSymbol(&replay) == expected[i]);
  }
  for (uint16_t i = 0U; i < 112U; ++i) {
    assert(gameSequenceNextSymbol(&first) == gameSequenceNextSymbol(&replay));
  }
  assert(first.state == replay.state);
  assert(first.next_index == replay.next_index);
}

static void test_zero_seed_recovers_to_nonzero_stream(void) {
  GameSequenceStream stream;
  const uint8_t symbol = gameSequenceChooseFirst(
      &stream, 0U, GAME_SEQUENCE_NO_PREVIOUS);
  assert(symbol < GAME_SEQUENCE_SYMBOL_COUNT);
  assert(stream.state != 0U);
}

int main(void) {
  test_each_four_cues_use_every_color_once();
  test_first_color_excludes_previous_but_all_others_are_eligible();
  test_first_color_is_unconstrained_on_first_game();
  test_seed_replay();
  test_zero_seed_recovers_to_nonzero_stream();
  puts("balanced shuffled-bag game sequence tests passed");
  return 0;
}
