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


class ScoreStatsIntegrationTests(unittest.TestCase):
    def test_stats_are_loaded_and_use_the_authorized_eeprom_layout(self):
        setup = function_body("setup")
        self.assertIn("loadScoreStats();", setup)
        loader = function_body("loadScoreStats")
        self.assertIn("scoreStatsStoreRead(readEepromByte", loader)

        store = (ROOT / "score_stats_store.h").read_text(encoding="utf-8")
        journal = (ROOT / "alien-simon-says" / "first_color_journal.h").read_text(encoding="utf-8")
        self.assertIn("#define SCORE_STATS_STORE_BASE 16U", store)
        self.assertIn("#define SCORE_STATS_STORE_BYTES (SCORE_STATS_STORE_SLOT_SIZE * SCORE_STATS_STORE_SLOT_COUNT)", store)
        self.assertIn("#define FIRST_COLOR_JOURNAL_BASE 48U", journal)
        self.assertEqual(16 + 32, 48)

    def test_successful_starts_count_sessions_but_only_endings_enter_average(self):
        begin_game = function_body("beginGame")
        seed_failure = begin_game.index("if (!makeSeed(&freshSeed))")
        seed_failure_return = begin_game.index("return;", seed_failure)
        session_count = begin_game.index("recordSuccessfulGameStart();")
        active = begin_game.index("gameSessionActive = true;")
        self.assertLess(seed_failure_return, session_count)
        self.assertLess(session_count, active)

        finalize = function_body("recordCurrentSessionScore")
        self.assertIn("if (!gameSessionActive) return;", finalize)
        self.assertIn("SCORE_STATS_STORE_BASE, completedRounds", finalize)
        self.assertIn("gameSessionActive = false;", finalize)

    def test_game_over_and_active_restart_record_a_session_before_state_is_reset(self):
        game_over = function_body("beginGameOver")
        restart = function_body("restartActiveGame")
        self.assertLess(
            game_over.index("recordCurrentSessionScore();"),
            game_over.index("gameState = GAME_OVER;"),
        )
        self.assertLess(
            restart.index("recordCurrentSessionScore();"),
            restart.index("completedRounds = 0;"),
        )

    def test_stats_command_is_line_based_and_exports_a_machine_readable_summary(self):
        process = function_body("processSerialCommand")
        self.assertIn('serialCommandEquals("STATS")', process)
        self.assertIn("printGameStats();", process)
        self.assertIn('serialCommandEquals("START")', process)

        report = function_body("printGameStats")
        for column in ("best_rounds", "average_rounds"):
            self.assertIn(column, report)
        self.assertNotIn("sessions", report)
        self.assertNotIn("score_samples", report)
        self.assertNotIn("totalGamesPlayed", report)
        self.assertNotIn("scoreSampleCount", report)
        self.assertIn("bestScore", report)
        self.assertIn("printAverageScore();", report)

        average = function_body("printAverageScore")
        self.assertIn('"N/A"', average)
        self.assertIn("scoreStatsAverageHundredths(scoreSampleCount, scoreSum", average)

        store = (ROOT / "score_stats_store.h").read_text(encoding="utf-8")
        self.assertIn("static bool scoreStatsAverageHundredths", store)
        self.assertIn("remainder * 100ULL", store)

    def test_host_and_firmware_headers_match(self):
        for name in ("score_stats_store.h", "first_color_journal.h", "game_count_store.h"):
            root_copy = (ROOT / name).read_text(encoding="utf-8")
            firmware_copy = (ROOT / "alien-simon-says" / name).read_text(encoding="utf-8")
            self.assertEqual(root_copy, firmware_copy, name)


if __name__ == "__main__":
    unittest.main()
