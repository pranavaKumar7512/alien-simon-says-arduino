#ifndef FIRST_COLOR_JOURNAL_H
#define FIRST_COLOR_JOURNAL_H

#include <stdbool.h>
#include <stdint.h>

#define FIRST_COLOR_NONE 0xFFU
#define FIRST_COLOR_COUNT 4U
#define FIRST_COLOR_JOURNAL_BASE 48U
#define FIRST_COLOR_JOURNAL_SLOT_SIZE 8U
#define FIRST_COLOR_JOURNAL_EEPROM_SIZE 1024U
#define FIRST_COLOR_JOURNAL_SLOT_COUNT \
  ((FIRST_COLOR_JOURNAL_EEPROM_SIZE - FIRST_COLOR_JOURNAL_BASE) / FIRST_COLOR_JOURNAL_SLOT_SIZE)

#if FIRST_COLOR_JOURNAL_BASE + \
    FIRST_COLOR_JOURNAL_SLOT_COUNT * FIRST_COLOR_JOURNAL_SLOT_SIZE > \
    FIRST_COLOR_JOURNAL_EEPROM_SIZE
#error "First-color journal exceeds Uno EEPROM"
#endif

typedef uint8_t (*FirstColorReadByte)(uint16_t address, void *context);
typedef void (*FirstColorUpdateByte)(uint16_t address, uint8_t value, void *context);

typedef struct {
  uint32_t generation;
  uint16_t slot;
  uint8_t color;
} FirstColorJournalEntry;

static uint16_t firstColorJournalCrc16(const uint8_t *bytes, uint8_t length) {
  uint16_t crc = 0xFFFFU;
  for (uint8_t i = 0; i < length; ++i) {
    crc ^= (uint16_t)bytes[i] << 8;
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x8000U) ? (uint16_t)((crc << 1) ^ 0x1021U) : (uint16_t)(crc << 1);
    }
  }
  return crc;
}

static bool firstColorJournalGenerationIsNewer(uint32_t candidate, uint32_t current) {
  const uint32_t distance = candidate - current;
  return distance != 0U && distance < 0x80000000UL;
}

static bool firstColorJournalDecode(const uint8_t bytes[FIRST_COLOR_JOURNAL_SLOT_SIZE],
                                   FirstColorJournalEntry *entry) {
  if (bytes[7] != 0xA5U || bytes[4] >= FIRST_COLOR_COUNT) return false;
  const uint16_t storedCrc = (uint16_t)bytes[5] | ((uint16_t)bytes[6] << 8);
  if (storedCrc != firstColorJournalCrc16(bytes, 5U)) return false;

  entry->generation = (uint32_t)bytes[0] |
      ((uint32_t)bytes[1] << 8) |
      ((uint32_t)bytes[2] << 16) |
      ((uint32_t)bytes[3] << 24);
  entry->color = bytes[4];
  return true;
}

static void firstColorJournalEncode(uint32_t generation, uint8_t color,
                                    uint8_t bytes[FIRST_COLOR_JOURNAL_SLOT_SIZE]) {
  bytes[0] = (uint8_t)generation;
  bytes[1] = (uint8_t)(generation >> 8);
  bytes[2] = (uint8_t)(generation >> 16);
  bytes[3] = (uint8_t)(generation >> 24);
  bytes[4] = color;
  const uint16_t crc = firstColorJournalCrc16(bytes, 5U);
  bytes[5] = (uint8_t)crc;
  bytes[6] = (uint8_t)(crc >> 8);
  bytes[7] = 0xA5U; // commit marker; always written last by the journal append routine
}

static bool firstColorJournalRead(FirstColorReadByte readByte, void *context,
                                  FirstColorJournalEntry *latest) {
  if (readByte == 0 || latest == 0) return false;

  bool found = false;
  uint8_t bytes[FIRST_COLOR_JOURNAL_SLOT_SIZE];
  for (uint16_t slot = 0; slot < FIRST_COLOR_JOURNAL_SLOT_COUNT; ++slot) {
    const uint16_t base = (uint16_t)(FIRST_COLOR_JOURNAL_BASE + slot * FIRST_COLOR_JOURNAL_SLOT_SIZE);
    for (uint8_t i = 0; i < FIRST_COLOR_JOURNAL_SLOT_SIZE; ++i) {
      bytes[i] = readByte((uint16_t)(base + i), context);
    }

    FirstColorJournalEntry candidate;
    if (!firstColorJournalDecode(bytes, &candidate)) continue;
    candidate.slot = slot;
    if (!found || firstColorJournalGenerationIsNewer(candidate.generation, latest->generation)) {
      *latest = candidate;
      found = true;
    }
  }
  return found;
}

static bool firstColorJournalAppend(FirstColorReadByte readByte,
                                    FirstColorUpdateByte updateByte,
                                    void *context, uint8_t color) {
  if (readByte == 0 || updateByte == 0 || color >= FIRST_COLOR_COUNT) return false;

  FirstColorJournalEntry latest;
  const bool found = firstColorJournalRead(readByte, context, &latest);
  const uint16_t slot = found
      ? (uint16_t)((latest.slot + 1U) % FIRST_COLOR_JOURNAL_SLOT_COUNT)
      : 0U;
  const uint32_t generation = found ? latest.generation + 1U : 0U;
  const uint16_t base = (uint16_t)(FIRST_COLOR_JOURNAL_BASE + slot * FIRST_COLOR_JOURNAL_SLOT_SIZE);
  uint8_t bytes[FIRST_COLOR_JOURNAL_SLOT_SIZE];
  firstColorJournalEncode(generation, color, bytes);

  // Keep the previous committed slot intact. A torn write to this destination
  // remains invalid until the final marker is stored.
  updateByte((uint16_t)(base + 7U), 0x00U, context);
  for (uint8_t i = 0; i < 7U; ++i) updateByte((uint16_t)(base + i), bytes[i], context);
  updateByte((uint16_t)(base + 7U), bytes[7], context);
  return true;
}

#endif
