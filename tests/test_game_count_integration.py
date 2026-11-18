import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKETCH = (ROOT / "alien-simon-says" / "alien-simon-says.ino").read_text(encoding="utf-8")


def function_body(name):
    match = re.search(rf"(?:static\s+)?[\w:]+\s+{name}\s*\([^;]*?\)\s*\{{", SKETCH)
    if match is None:
        raise AssertionError(f"function {name} not found")
    opening = match.end() - 1
    depth = 0
    for index in range(opening, len(SKETCH)):
        if SKETCH[index] == "{":
            depth += 1
        elif SKETCH[index] == "}":
            depth -= 1
            if depth == 0:
                return SKETCH[opening + 1:index]
    raise AssertionError(f"function {name} has no closing brace")


class GameCountIntegrationTests(unittest.TestCase):
    def test_count_increments_only_after_seed_acquisition_succeeds(self):
        begin_game = function_body("beginGame")
        seed_check = begin_game.index("if (!makeSeed(&freshSeed))")
        failed_seed_return = begin_game.index("return;", seed_check)
        record_start = begin_game.index("recordSuccessfulGameStart();")
        game_start_log = begin_game.index('Serial.println(F("GAME_START"))')
        self.assertLess(failed_seed_return, record_start)
        self.assertLess(record_start, game_start_log)
        self.assertEqual(begin_game.count("recordSuccessfulGameStart();"), 1)

    def test_counter_is_loaded_and_saved_through_the_shared_eeprom_store(self):
        setup = function_body("setup")
        self.assertIn("loadTotalGamesPlayed();", setup)
        loader = function_body("loadTotalGamesPlayed")
        increment = function_body("recordSuccessfulGameStart")
        self.assertIn("gameCountStoreLoad(readEepromByte", loader)
        self.assertIn("gameCountStoreIncrement(readEepromByte, updateEepromByte", increment)
        self.assertIn('GAME_COUNT_EEPROM_ADDRESS + GAME_COUNT_STORE_BYTES == SCORE_STATS_STORE_BASE', SKETCH)
        self.assertIn('SCORE_STATS_STORE_BASE + SCORE_STATS_STORE_BYTES <= FIRST_COLOR_JOURNAL_BASE', SKETCH)

    def test_idle_display_hides_session_count_and_cycles_only_score_pages(self):
        idle_page = function_body("showIdlePage")
        self.assertIn('"YOUR:%010lu"', idle_page)
        self.assertIn('"BEST:%010lu"', idle_page)
        self.assertNotIn('"GAMES:%010lu"', idle_page)
        loop = function_body("loop")
        self.assertIn("idlePage = (uint8_t)((idlePage + 1U) % 2U);", loop)

    def test_simulation_reports_counter_after_each_successful_start(self):
        begin_game = function_body("beginGame")
        self.assertIn('Serial.print(F("SIM_GAMES_PLAYED:"));', begin_game)
        self.assertIn("Serial.println(totalGamesPlayed);", begin_game)

    def test_root_and_firmware_store_headers_match(self):
        root_header = (ROOT / "game_count_store.h").read_text(encoding="utf-8")
        firmware_header = (ROOT / "alien-simon-says" / "game_count_store.h").read_text(encoding="utf-8")
        self.assertEqual(root_header, firmware_header)


if __name__ == "__main__":
    unittest.main()
