#ifndef SCORE_STATS_STORE_H
#define SCORE_STATS_STORE_H

#include <stdbool.h>
#include <stdint.h>

#define SCORE_STATS_STORE_BASE 16U
#define SCORE_STATS_STORE_SLOT_SIZE 16U
#define SCORE_STATS_STORE_SLOT_COUNT 2U
#define SCORE_STATS_STORE_BYTES (SCORE_STATS_STORE_SLOT_SIZE * SCORE_STATS_STORE_SLOT_COUNT)
#define SCORE_STATS_STORE_MAGIC 0x53U
#define SCORE_STATS_STORE_COMMIT 0xA5U

typedef uint8_t (*ScoreStatsReadByte)(uint16_t address, void *context);
typedef void (*ScoreStatsUpdateByte)(uint16_t address, uint8_t value, void *context);

typedef struct {
  uint32_t sampleCount;
  uint64_t scoreSum;
  uint8_t slot;
} ScoreStatsRecord;

static uint16_t scoreStatsCrc16(const uint8_t *bytes, uint8_t length) {
  uint16_t crc = 0xFFFFU;
  for (uint8_t i = 0U; i < length; ++i) {
    crc ^= (uint16_t)bytes[i] << 8;
    for (uint8_t bit = 0U; bit < 8U; ++bit) {
      crc = (crc & 0x8000U)
          ? (uint16_t)((crc << 1) ^ 0x1021U)
          : (uint16_t)(crc << 1);
    }
  }
  return crc;
}

static void scoreStatsEncode(uint32_t sampleCount, uint64_t scoreSum,
                             uint8_t bytes[SCORE_STATS_STORE_SLOT_SIZE]) {
  for (uint8_t i = 0U; i < 4U; ++i) {
    bytes[i] = (uint8_t)(sampleCount >> (8U * i));
  }
  for (uint8_t i = 0U; i < 8U; ++i) {
    bytes[4U + i] = (uint8_t)(scoreSum >> (8U * i));
  }
  const uint16_t crc = scoreStatsCrc16(bytes, 12U);
  bytes[12] = (uint8_t)crc;
  bytes[13] = (uint8_t)(crc >> 8);
  bytes[14] = SCORE_STATS_STORE_COMMIT;
  bytes[15] = SCORE_STATS_STORE_MAGIC;
}

static bool scoreStatsDecode(const uint8_t bytes[SCORE_STATS_STORE_SLOT_SIZE],
                             ScoreStatsRecord *record) {
  if (record == 0 || bytes[14] != SCORE_STATS_STORE_COMMIT ||
      bytes[15] != SCORE_STATS_STORE_MAGIC) return false;

  const uint16_t storedCrc = (uint16_t)bytes[12] | ((uint16_t)bytes[13] << 8);
  if (storedCrc != scoreStatsCrc16(bytes, 12U)) return false;

  uint32_t sampleCount = 0U;
  uint64_t scoreSum = 0U;
  for (uint8_t i = 0U; i < 4U; ++i) {
    sampleCount |= (uint32_t)bytes[i] << (8U * i);
  }
  for (uint8_t i = 0U; i < 8U; ++i) {
    scoreSum |= (uint64_t)bytes[4U + i] << (8U * i);
  }

  // A sample is a uint32 score, so this bound also guarantees future sum additions
  // cannot overflow uint64_t before the uint32 sample count saturates.
  if (scoreSum > (uint64_t)sampleCount * UINT32_MAX) return false;
  record->sampleCount = sampleCount;
  record->scoreSum = scoreSum;
  return true;
}

static bool scoreStatsAverageHundredths(uint32_t sampleCount, uint64_t scoreSum,
                                         uint32_t *whole, uint8_t *fraction) {
  if (sampleCount == 0U || whole == 0 || fraction == 0) return false;

  uint64_t roundedWhole = scoreSum / sampleCount;
  const uint64_t remainder = scoreSum % sampleCount;
  uint16_t hundredths = (uint16_t)((remainder * 100ULL + sampleCount / 2U) /
                                   sampleCount);
  if (hundredths >= 100U) {
    ++roundedWhole;
    hundredths = (uint16_t)(hundredths - 100U);
  }
  *whole = (uint32_t)roundedWhole;
  *fraction = (uint8_t)hundredths;
  return true;
}

static bool scoreStatsStoreRead(ScoreStatsReadByte readByte, void *context,
                                uint16_t baseAddress, ScoreStatsRecord *latest) {
  if (readByte == 0 || latest == 0) return false;

  bool found = false;
  uint8_t bytes[SCORE_STATS_STORE_SLOT_SIZE];
  for (uint8_t slot = 0U; slot < SCORE_STATS_STORE_SLOT_COUNT; ++slot) {
    const uint16_t base = (uint16_t)(baseAddress + slot * SCORE_STATS_STORE_SLOT_SIZE);
    for (uint8_t i = 0U; i < SCORE_STATS_STORE_SLOT_SIZE; ++i) {
      bytes[i] = readByte((uint16_t)(base + i), context);
    }

    ScoreStatsRecord candidate;
    if (!scoreStatsDecode(bytes, &candidate)) continue;
    candidate.slot = slot;
    // Each committed update increases sampleCount; equal-count records represent
    // the same aggregate because the count stops changing when saturated.
    if (!found || candidate.sampleCount > latest->sampleCount) {
      *latest = candidate;
      found = true;
    }
  }
  return found;
}

static bool scoreStatsStoreAdd(ScoreStatsReadByte readByte,
                               ScoreStatsUpdateByte updateByte,
                               void *context, uint16_t baseAddress,
                               uint32_t score) {
  if (readByte == 0 || updateByte == 0) return false;

  ScoreStatsRecord latest;
  const bool found = scoreStatsStoreRead(readByte, context, baseAddress, &latest);
  const uint32_t currentCount = found ? latest.sampleCount : 0U;
  const uint64_t currentSum = found ? latest.scoreSum : 0U;
  if (currentCount == UINT32_MAX) return false;

  const uint8_t targetSlot = found ? (uint8_t)(latest.slot ^ 1U) : 0U;
  const uint16_t targetBase =
      (uint16_t)(baseAddress + targetSlot * SCORE_STATS_STORE_SLOT_SIZE);
  uint8_t bytes[SCORE_STATS_STORE_SLOT_SIZE];
  scoreStatsEncode(currentCount + 1U, currentSum + score, bytes);

  // Invalidate only the inactive copy, write payload/CRC and magic, then commit last.
  updateByte((uint16_t)(targetBase + 14U), 0x00U, context);
  for (uint8_t i = 0U; i < 14U; ++i) {
    updateByte((uint16_t)(targetBase + i), bytes[i], context);
  }
  updateByte((uint16_t)(targetBase + 15U), bytes[15], context);
  updateByte((uint16_t)(targetBase + 14U), bytes[14], context);
  return true;
}

#endif
