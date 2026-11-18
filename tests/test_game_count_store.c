#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../game_count_store.h"

#define EEPROM_BYTES 1024U
#define GAME_COUNT_ADDRESS 12U
#define FIRST_COLOR_JOURNAL_ADDRESS 16U

static uint8_t fakeEeprom[EEPROM_BYTES];
static uint32_t updateCount;

static uint8_t fakeRead(uint16_t address, void *context) {
  const uint8_t *memory = (const uint8_t *)context;
  assert(address < EEPROM_BYTES);
  return memory[address];
}

static void fakeUpdate(uint16_t address, uint8_t value, void *context) {
  uint8_t *memory = (uint8_t *)context;
  assert(address >= GAME_COUNT_ADDRESS);
  assert(address < GAME_COUNT_ADDRESS + GAME_COUNT_STORE_BYTES);
  if (memory[address] != value) {
    memory[address] = value;
    ++updateCount;
  }
}

static void resetFakeEeprom(void) {
  memset(fakeEeprom, 0xFF, sizeof(fakeEeprom));
  updateCount = 0U;
}

static void test_erased_memory_starts_at_zero_and_persists(void) {
  resetFakeEeprom();
  assert(gameCountStoreLoad(fakeRead, fakeEeprom, GAME_COUNT_ADDRESS) == 0U);
  assert(gameCountStoreIncrement(fakeRead, fakeUpdate, fakeEeprom,
                                 GAME_COUNT_ADDRESS) == 1U);
  assert(gameCountStoreLoad(fakeRead, fakeEeprom, GAME_COUNT_ADDRESS) == 1U);

  // Simulate a reboot by reloading from the same EEPROM bytes.
  assert(gameCountStoreIncrement(fakeRead, fakeUpdate, fakeEeprom,
                                 GAME_COUNT_ADDRESS) == 2U);
  assert(gameCountStoreLoad(fakeRead, fakeEeprom, GAME_COUNT_ADDRESS) == 2U);
}

static void test_counter_isolated_from_score_and_first_color_journal(void) {
  resetFakeEeprom();
  fakeEeprom[0] = 0x51U; // best-score region sentinel
  fakeEeprom[FIRST_COLOR_JOURNAL_ADDRESS] = 0xA5U;
  const uint8_t scoreSentinel = fakeEeprom[0];
  const uint8_t journalSentinel = fakeEeprom[FIRST_COLOR_JOURNAL_ADDRESS];

  assert(gameCountStoreIncrement(fakeRead, fakeUpdate, fakeEeprom,
                                 GAME_COUNT_ADDRESS) == 1U);
  assert(fakeEeprom[0] == scoreSentinel);
  assert(fakeEeprom[FIRST_COLOR_JOURNAL_ADDRESS] == journalSentinel);
  assert(updateCount > 0U);
}

static void test_increment_carries_and_saturates_without_wrapping(void) {
  resetFakeEeprom();
  const uint32_t beforeCarry = 0x000000FFUL;
  const uint32_t encoded = ~beforeCarry;
  for (uint8_t i = 0U; i < GAME_COUNT_STORE_BYTES; ++i) {
    fakeEeprom[GAME_COUNT_ADDRESS + i] = (uint8_t)(encoded >> (8U * i));
  }
  assert(gameCountStoreIncrement(fakeRead, fakeUpdate, fakeEeprom,
                                 GAME_COUNT_ADDRESS) == 0x00000100UL);

  const uint32_t maximum = UINT32_MAX;
  const uint32_t encodedMaximum = ~maximum;
  for (uint8_t i = 0U; i < GAME_COUNT_STORE_BYTES; ++i) {
    fakeEeprom[GAME_COUNT_ADDRESS + i] = (uint8_t)(encodedMaximum >> (8U * i));
  }
  updateCount = 0U;
  assert(gameCountStoreIncrement(fakeRead, fakeUpdate, fakeEeprom,
                                 GAME_COUNT_ADDRESS) == UINT32_MAX);
  assert(updateCount == 0U);
}

int main(void) {
  test_erased_memory_starts_at_zero_and_persists();
  test_counter_isolated_from_score_and_first_color_journal();
  test_increment_carries_and_saturates_without_wrapping();
  puts("game count EEPROM tests passed");
  return 0;
}
