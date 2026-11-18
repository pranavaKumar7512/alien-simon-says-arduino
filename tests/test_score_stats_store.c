#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../score_stats_store.h"

#define EEPROM_BYTES 1024U
#define FIRST_COLOR_JOURNAL_BASE 48U

static uint8_t fakeEeprom[EEPROM_BYTES];
static int32_t writesUntilPowerLoss = -1;
static uint32_t changedWrites = 0U;

static uint8_t fakeRead(uint16_t address, void *context) {
  const uint8_t *memory = (const uint8_t *)context;
  assert(address < EEPROM_BYTES);
  return memory[address];
}

static void fakeUpdate(uint16_t address, uint8_t value, void *context) {
  uint8_t *memory = (uint8_t *)context;
  assert(address >= SCORE_STATS_STORE_BASE);
  assert(address < SCORE_STATS_STORE_BASE + SCORE_STATS_STORE_BYTES);
  if (writesUntilPowerLoss == 0) return;
  if (writesUntilPowerLoss > 0) --writesUntilPowerLoss;
  if (memory[address] != value) {
    memory[address] = value;
    ++changedWrites;
  }
}

static void resetFakeEeprom(void) {
  memset(fakeEeprom, 0xFF, sizeof(fakeEeprom));
  writesUntilPowerLoss = -1;
  changedWrites = 0U;
}

static void test_erased_memory_and_average_samples(void) {
  resetFakeEeprom();
  assert(SCORE_STATS_STORE_BASE + SCORE_STATS_STORE_BYTES ==
         FIRST_COLOR_JOURNAL_BASE);
  ScoreStatsRecord record;
  assert(!scoreStatsStoreRead(fakeRead, fakeEeprom, SCORE_STATS_STORE_BASE,
                              &record));

  assert(scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                            SCORE_STATS_STORE_BASE, 0U));
  assert(scoreStatsStoreRead(fakeRead, fakeEeprom, SCORE_STATS_STORE_BASE,
                             &record));
  assert(record.sampleCount == 1U);
  assert(record.scoreSum == 0U);

  assert(scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                            SCORE_STATS_STORE_BASE, 3U));
  assert(scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                            SCORE_STATS_STORE_BASE, 4U));
  assert(scoreStatsStoreRead(fakeRead, fakeEeprom, SCORE_STATS_STORE_BASE,
                             &record));
  assert(record.sampleCount == 3U);
  assert(record.scoreSum == 7U);
  assert(changedWrites > 0U);
}

static void test_torn_update_leaves_previous_copy_readable(void) {
  resetFakeEeprom();
  ScoreStatsRecord record;
  assert(scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                            SCORE_STATS_STORE_BASE, 4U));
  assert(scoreStatsStoreRead(fakeRead, fakeEeprom, SCORE_STATS_STORE_BASE,
                             &record));
  assert(record.sampleCount == 1U && record.scoreSum == 4U);

  // Simulate power loss after the inactive copy has been invalidated and partly written.
  writesUntilPowerLoss = 5;
  assert(scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                            SCORE_STATS_STORE_BASE, 9U));
  writesUntilPowerLoss = -1;
  assert(scoreStatsStoreRead(fakeRead, fakeEeprom, SCORE_STATS_STORE_BASE,
                             &record));
  assert(record.sampleCount == 1U);
  assert(record.scoreSum == 4U);
}

static void test_average_rounds_to_two_decimals_without_overflow(void) {
  uint32_t whole = 0U;
  uint8_t fraction = 0U;
  assert(!scoreStatsAverageHundredths(0U, 0U, &whole, &fraction));
  assert(scoreStatsAverageHundredths(3U, 7U, &whole, &fraction));
  assert(whole == 2U && fraction == 33U);
  assert(scoreStatsAverageHundredths(8U, 1U, &whole, &fraction));
  assert(whole == 0U && fraction == 13U);
  assert(scoreStatsAverageHundredths(200U, 199U, &whole, &fraction));
  assert(whole == 1U && fraction == 0U);

  const uint64_t maximumSum = (uint64_t)UINT32_MAX * UINT32_MAX;
  assert(scoreStatsAverageHundredths(UINT32_MAX, maximumSum, &whole, &fraction));
  assert(whole == UINT32_MAX && fraction == 0U);
}

static void test_crc_fallback_and_saturation(void) {
  resetFakeEeprom();
  ScoreStatsRecord record;
  assert(scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                            SCORE_STATS_STORE_BASE, 2U));
  assert(scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                            SCORE_STATS_STORE_BASE, 8U));
  fakeEeprom[SCORE_STATS_STORE_BASE + SCORE_STATS_STORE_SLOT_SIZE + 12U] ^= 0x01U;
  assert(scoreStatsStoreRead(fakeRead, fakeEeprom, SCORE_STATS_STORE_BASE,
                             &record));
  assert(record.sampleCount == 1U && record.scoreSum == 2U);

  resetFakeEeprom();
  uint8_t encoded[SCORE_STATS_STORE_SLOT_SIZE];
  const uint64_t maximumSum = (uint64_t)UINT32_MAX * UINT32_MAX;
  scoreStatsEncode(UINT32_MAX, maximumSum, encoded);
  memcpy(fakeEeprom + SCORE_STATS_STORE_BASE, encoded, sizeof(encoded));
  changedWrites = 0U;
  assert(!scoreStatsStoreAdd(fakeRead, fakeUpdate, fakeEeprom,
                             SCORE_STATS_STORE_BASE, 1U));
  assert(scoreStatsStoreRead(fakeRead, fakeEeprom, SCORE_STATS_STORE_BASE,
                             &record));
  assert(record.sampleCount == UINT32_MAX);
  assert(record.scoreSum == maximumSum);
  assert(changedWrites == 0U);
}

int main(void) {
  test_erased_memory_and_average_samples();
  test_torn_update_leaves_previous_copy_readable();
  test_average_rounds_to_two_decimals_without_overflow();
  test_crc_fallback_and_saturation();
  puts("score stats EEPROM tests passed");
  return 0;
}
