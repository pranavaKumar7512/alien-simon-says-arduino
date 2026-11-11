#ifndef GAME_SEQUENCE_H
#define GAME_SEQUENCE_H

#include <stdint.h>

#define GAME_SEQUENCE_SYMBOL_COUNT 4U

typedef struct {
  uint32_t state;
} GameSequenceStream;

static uint32_t gameSequenceXorshift32(uint32_t *value) {
  // Zero is not part of xorshift32's nonzero period.
  if (*value == 0U) *value = 0x6D2B79F5UL;
  *value ^= *value << 13;
  *value ^= *value >> 17;
  *value ^= *value << 5;
  return *value;
}

// xorshift32 outputs are in 1..UINT32_MAX. Reject the upper remainder values
// so the accepted nonzero output count is divisible by the requested bound.
static uint8_t gameSequenceUniformBelow(uint32_t *state, uint8_t bound) {
  if (bound < 2U) return 0U;
  const uint32_t largestAccepted = UINT32_MAX - (UINT32_MAX % (uint32_t)bound);
  uint32_t value;
  do {
    value = gameSequenceXorshift32(state);
  } while (value > largestAccepted);
  return (uint8_t)(value % (uint32_t)bound);
}

static uint8_t gameSequenceNextSymbol(GameSequenceStream *stream) {
  return gameSequenceUniformBelow(&stream->state, GAME_SEQUENCE_SYMBOL_COUNT);
}

static uint8_t gameSequenceChooseFirst(GameSequenceStream *stream, uint32_t seed) {
  stream->state = seed == 0U ? 0x6D2B79F5UL : seed;
  return gameSequenceNextSymbol(stream);
}

#endif
