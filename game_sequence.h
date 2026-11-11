#ifndef GAME_SEQUENCE_H
#define GAME_SEQUENCE_H

#include <stdint.h>

#define GAME_SEQUENCE_SYMBOL_COUNT 4U
#define GAME_SEQUENCE_NO_PREVIOUS 0xFFU

typedef struct {
  uint32_t state;
  uint8_t bag[GAME_SEQUENCE_SYMBOL_COUNT];
  uint8_t next_index;
} GameSequenceStream;

static uint32_t gameSequenceXorshift32(uint32_t *value) {
  // Zero is not part of xorshift32's nonzero period.
  if (*value == 0U) *value = 0x6D2B79F5UL;
  *value ^= *value << 13;
  *value ^= *value >> 17;
  *value ^= *value << 5;
  return *value;
}

// Rejection sampling avoids modulo bias for bounds such as 3.
static uint8_t gameSequenceUniformBelow(uint32_t *state, uint8_t bound) {
  if (bound < 2U) return 0U;
  const uint32_t threshold = (uint32_t)(0UL - (uint32_t)bound) % (uint32_t)bound;
  uint32_t value;
  do {
    value = gameSequenceXorshift32(state);
  } while (value < threshold);
  return (uint8_t)(value % (uint32_t)bound);
}

static void gameSequenceShuffleRange(GameSequenceStream *stream, uint8_t start,
                                     uint8_t count) {
  for (uint8_t remaining = count; remaining > 1U; --remaining) {
    const uint8_t chosen = gameSequenceUniformBelow(&stream->state, remaining);
    const uint8_t left = (uint8_t)(start + remaining - 1U);
    const uint8_t right = (uint8_t)(start + chosen);
    const uint8_t temporary = stream->bag[left];
    stream->bag[left] = stream->bag[right];
    stream->bag[right] = temporary;
  }
}

static void gameSequenceShuffle(GameSequenceStream *stream) {
  for (uint8_t i = 0U; i < GAME_SEQUENCE_SYMBOL_COUNT; ++i) {
    stream->bag[i] = i;
  }
  gameSequenceShuffleRange(stream, 0U, GAME_SEQUENCE_SYMBOL_COUNT);
}

static uint8_t gameSequenceNextSymbol(GameSequenceStream *stream) {
  if (stream->next_index >= GAME_SEQUENCE_SYMBOL_COUNT) {
    gameSequenceShuffle(stream);
    stream->next_index = 0U;
  }
  return stream->bag[stream->next_index++];
}

static uint8_t gameSequenceChooseFirst(GameSequenceStream *stream, uint32_t seed,
                                       uint8_t previousFirstColor) {
  stream->state = seed == 0U ? 0x6D2B79F5UL : seed;

  // Choose uniformly among allowed first colors, then shuffle the remaining
  // three into the rest of the opening four-cue bag.
  if (previousFirstColor < GAME_SEQUENCE_SYMBOL_COUNT) {
    uint8_t first = gameSequenceUniformBelow(&stream->state,
                                             GAME_SEQUENCE_SYMBOL_COUNT - 1U);
    if (first >= previousFirstColor) ++first;
    stream->bag[0] = first;
    uint8_t destination = 1U;
    for (uint8_t color = 0U; color < GAME_SEQUENCE_SYMBOL_COUNT; ++color) {
      if (color != first) stream->bag[destination++] = color;
    }
    gameSequenceShuffleRange(stream, 1U, GAME_SEQUENCE_SYMBOL_COUNT - 1U);
  } else {
    gameSequenceShuffle(stream);
  }
  stream->next_index = 0U;
  return gameSequenceNextSymbol(stream);
}

#endif
