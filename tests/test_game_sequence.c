#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "../game_sequence.h"

static void test_every_cue_is_a_valid_symbol(void) {
  for (uint32_t seed = 1U; seed <= 2048U; ++seed) {
    GameSequenceStream stream;
    uint8_t symbol = gameSequenceChooseFirst(&stream, seed);
    assert(symbol < GAME_SEQUENCE_SYMBOL_COUNT);
    for (uint8_t cue = 1U; cue < 32U; ++cue) {
      symbol = gameSequenceNextSymbol(&stream);
      assert(symbol < GAME_SEQUENCE_SYMBOL_COUNT);
    }
  }
}

static void test_first_draws_cover_all_four_colors(void) {
  uint16_t counts[GAME_SEQUENCE_SYMBOL_COUNT] = {0U, 0U, 0U, 0U};
  for (uint32_t seed = 1U; seed <= 4096U; ++seed) {
    GameSequenceStream stream;
    const uint8_t first = gameSequenceChooseFirst(&stream, seed);
    ++counts[first];
  }
  for (uint8_t color = 0U; color < GAME_SEQUENCE_SYMBOL_COUNT; ++color) {
    assert(counts[color] == 1024U);
  }
}

static void test_repeated_cues_are_allowed(void) {
  static const uint8_t expected[8] = {1U, 1U, 1U, 3U, 1U, 0U, 2U, 2U};
  GameSequenceStream stream;
  assert(gameSequenceChooseFirst(&stream, 1U) == expected[0]);
  for (uint8_t i = 1U; i < 8U; ++i) {
    assert(gameSequenceNextSymbol(&stream) == expected[i]);
  }
}

static void test_uniform_below_rejects_upper_nonzero_states(void) {
  static const uint32_t seeds[3] = {
    0xBB07F6B5UL, 0xACD979CEUL, 0x5E6CFCE7UL
  };
  static const uint32_t rejected[3] = {
    0xFFFFFFFDUL, 0xFFFFFFFEUL, 0xFFFFFFFFUL
  };
  static const uint32_t accepted[3] = {
    0x000BA05DUL, 0x0007C03EUL, 0x0003E01FUL
  };
  static const uint8_t expected[3] = {1U, 2U, 3U};

  for (uint8_t i = 0U; i < 3U; ++i) {
    uint32_t probe = seeds[i];
    assert(gameSequenceXorshift32(&probe) == rejected[i]);

    uint32_t state = seeds[i];
    assert(gameSequenceUniformBelow(&state, 4U) == expected[i]);
    assert(state == accepted[i]);
  }
}


static void test_seed_replay(void) {
  static const uint8_t expected[16] = {
    2U, 2U, 3U, 3U, 1U, 1U, 3U, 1U,
    3U, 3U, 3U, 0U, 2U, 1U, 0U, 2U
  };
  GameSequenceStream first;
  GameSequenceStream replay;
  const uint8_t firstSymbol = gameSequenceChooseFirst(&first, 0xA341316CUL);
  const uint8_t replayFirst = gameSequenceChooseFirst(&replay, 0xA341316CUL);
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
}

static void test_zero_seed_recovers_to_nonzero_stream(void) {
  GameSequenceStream stream;
  const uint8_t symbol = gameSequenceChooseFirst(&stream, 0U);
  assert(symbol < GAME_SEQUENCE_SYMBOL_COUNT);
  assert(stream.state != 0U);
}

int main(void) {
  test_every_cue_is_a_valid_symbol();
  test_first_draws_cover_all_four_colors();
  test_repeated_cues_are_allowed();
  test_uniform_below_rejects_upper_nonzero_states();
  test_seed_replay();
  test_zero_seed_recovers_to_nonzero_stream();
  puts("with-replacement pseudo-random game sequence tests passed");
  return 0;
}
