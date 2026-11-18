#ifndef GAME_COUNT_STORE_H
#define GAME_COUNT_STORE_H

#include <stdint.h>

// Four EEPROM bytes are reserved between the 12-byte best-score record and
// FIRST_COLOR_JOURNAL_BASE. Store the bitwise complement so erased 0xFFFFFFFF
// bytes decode to a logical count of zero while preserving the full uint32 range.
#define GAME_COUNT_STORE_BYTES 4U

typedef uint8_t (*GameCountReadByte)(uint16_t address, void *context);
typedef void (*GameCountUpdateByte)(uint16_t address, uint8_t value, void *context);

static uint32_t gameCountStoreLoad(GameCountReadByte readByte, void *context,
                                   uint16_t address) {
  if (readByte == 0) return 0U;

  uint32_t encoded = 0U;
  for (uint8_t i = 0U; i < GAME_COUNT_STORE_BYTES; ++i) {
    encoded |= (uint32_t)readByte((uint16_t)(address + i), context) << (8U * i);
  }
  return ~encoded;
}

static uint32_t gameCountStoreIncrement(GameCountReadByte readByte,
                                        GameCountUpdateByte updateByte,
                                        void *context, uint16_t address) {
  uint32_t value = gameCountStoreLoad(readByte, context, address);
  if (readByte == 0 || updateByte == 0 || value == UINT32_MAX) return value;

  ++value;
  const uint32_t encoded = ~value;
  for (uint8_t i = 0U; i < GAME_COUNT_STORE_BYTES; ++i) {
    updateByte((uint16_t)(address + i), (uint8_t)(encoded >> (8U * i)), context);
  }
  return value;
}

#endif
