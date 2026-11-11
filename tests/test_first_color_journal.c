#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../first_color_journal.h"

#define EEPROM_BYTES FIRST_COLOR_JOURNAL_EEPROM_SIZE

static uint8_t fakeEeprom[EEPROM_BYTES];
static uint32_t writes;
static uint32_t writeLimit;
static uint16_t lowestWrite;
static uint16_t highestWrite;

static uint8_t fakeRead(uint16_t address, void *context) {
  uint8_t *memory = (uint8_t *)context;
  assert(address < EEPROM_BYTES);
  return memory[address];
}

static void fakeUpdate(uint16_t address, uint8_t value, void *context) {
  uint8_t *memory = (uint8_t *)context;
  assert(address >= FIRST_COLOR_JOURNAL_BASE);
  assert(address < EEPROM_BYTES);
  if (writes == 0U || address < lowestWrite) lowestWrite = address;
  if (writes == 0U || address > highestWrite) highestWrite = address;
  if (writes >= writeLimit) return; // simulate power loss before the next byte write
  memory[address] = value;
  ++writes;
}

static void resetFakeEeprom(void) {
  memset(fakeEeprom, 0xFF, sizeof(fakeEeprom));
  writes = 0;
  writeLimit = UINT32_MAX;
  lowestWrite = UINT16_MAX;
  highestWrite = 0;
}

static FirstColorJournalEntry readLatest(void) {
  FirstColorJournalEntry entry;
  memset(&entry, 0, sizeof(entry));
  assert(firstColorJournalRead(fakeRead, fakeEeprom, &entry));
  return entry;
}

static void test_blank_and_round_trip(void) {
  resetFakeEeprom();
  FirstColorJournalEntry entry;
  assert(!firstColorJournalRead(fakeRead, fakeEeprom, &entry));

  assert(firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, 2U));
  entry = readLatest();
  assert(entry.generation == 0U);
  assert(entry.slot == 0U);
  assert(entry.color == 2U);

  assert(firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, 0U));
  entry = readLatest();
  assert(entry.generation == 1U);
  assert(entry.slot == 1U);
  assert(entry.color == 0U);
  assert(lowestWrite >= FIRST_COLOR_JOURNAL_BASE);
  assert(highestWrite < EEPROM_BYTES);
  assert(fakeEeprom[0] == 0xFFU); // the independent best-score region is untouched
}

static void test_invalid_entries_and_colors_are_rejected(void) {
  resetFakeEeprom();
  assert(!firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, FIRST_COLOR_COUNT));
  assert(!firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, FIRST_COLOR_NONE));

  uint8_t bytes[FIRST_COLOR_JOURNAL_SLOT_SIZE];
  firstColorJournalEncode(10U, 1U, bytes);
  memcpy(fakeEeprom + FIRST_COLOR_JOURNAL_BASE, bytes, sizeof(bytes));
  fakeEeprom[FIRST_COLOR_JOURNAL_BASE + 2U] ^= 0x01U; // CRC mismatch
  FirstColorJournalEntry entry;
  assert(!firstColorJournalRead(fakeRead, fakeEeprom, &entry));

  firstColorJournalEncode(11U, 1U, bytes);
  bytes[4] = FIRST_COLOR_COUNT; // impossible color with an otherwise plausible marker
  memcpy(fakeEeprom + FIRST_COLOR_JOURNAL_BASE, bytes, sizeof(bytes));
  assert(!firstColorJournalRead(fakeRead, fakeEeprom, &entry));

  firstColorJournalEncode(12U, 1U, bytes);
  bytes[7] = 0x00U; // uncommitted destination
  memcpy(fakeEeprom + FIRST_COLOR_JOURNAL_BASE, bytes, sizeof(bytes));
  assert(!firstColorJournalRead(fakeRead, fakeEeprom, &entry));
}

static void test_newest_record_and_generation_wrap(void) {
  resetFakeEeprom();
  uint8_t bytes[FIRST_COLOR_JOURNAL_SLOT_SIZE];
  firstColorJournalEncode(UINT32_MAX, 3U, bytes);
  memcpy(fakeEeprom + FIRST_COLOR_JOURNAL_BASE, bytes, sizeof(bytes));
  FirstColorJournalEntry entry = readLatest();
  assert(entry.generation == UINT32_MAX);
  assert(entry.color == 3U);

  assert(firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, 1U));
  entry = readLatest();
  assert(entry.generation == 0U);
  assert(entry.slot == 1U);
  assert(entry.color == 1U);

  assert(firstColorJournalGenerationIsNewer(0U, UINT32_MAX));
  assert(!firstColorJournalGenerationIsNewer(UINT32_MAX, 0U));
}

static void test_ring_rollover(void) {
  resetFakeEeprom();
  for (uint16_t i = 0; i < FIRST_COLOR_JOURNAL_SLOT_COUNT + 5U; ++i) {
    assert(firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, (uint8_t)(i % FIRST_COLOR_COUNT)));
  }
  FirstColorJournalEntry entry = readLatest();
  assert(entry.generation == FIRST_COLOR_JOURNAL_SLOT_COUNT + 4U);
  assert(entry.color == (FIRST_COLOR_JOURNAL_SLOT_COUNT + 4U) % FIRST_COLOR_COUNT);
  assert(entry.slot == 4U);
}

static void test_torn_write_preserves_previous_record(void) {
  for (uint32_t cutoff = 0; cutoff <= 9U; ++cutoff) {
    resetFakeEeprom();
    assert(firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, 2U));
    writes = 0;
    writeLimit = cutoff;
    assert(firstColorJournalAppend(fakeRead, fakeUpdate, fakeEeprom, 1U));

    FirstColorJournalEntry entry = readLatest();
    if (cutoff < 9U) {
      assert(entry.generation == 0U);
      assert(entry.slot == 0U);
      assert(entry.color == 2U);
    } else {
      assert(entry.generation == 1U);
      assert(entry.slot == 1U);
      assert(entry.color == 1U);
    }
  }
}

int main(void) {
  test_blank_and_round_trip();
  test_invalid_entries_and_colors_are_rejected();
  test_newest_record_and_generation_wrap();
  test_ring_rollover();
  test_torn_write_preserves_previous_record();
  puts("first-color EEPROM journal tests passed");
  return 0;
}
