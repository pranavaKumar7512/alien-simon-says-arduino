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


class ActiveScoreLcdIntegrationTests(unittest.TestCase):
    def test_active_lcd_formats_completed_rounds_and_best_score(self):
        render = function_body("refreshActiveScoreDisplay")
        self.assertIn('"SCORE:%010lu"', render)
        self.assertIn('"BEST:%010lu"', render)
        self.assertIn("(unsigned long)completedRounds", render)
        self.assertIn("(unsigned long)bestScore", render)
        self.assertIn("updateDisplay(line1, line2);", render)
        self.assertNotIn("roundLength", render)

        self.assertEqual(len(f"SCORE:{0:010d}"), 16)
        self.assertEqual(len(f"SCORE:{0xFFFFFFFF:010d}"), 16)
        self.assertEqual(len(f"BEST:{0xFFFFFFFF:010d}"), 15)

    def test_successful_game_start_shows_scores_before_initial_mapping(self):
        begin_game = function_body("beginGame")
        score_reset = begin_game.index("completedRounds = 0;")
        display_refresh = begin_game.index("refreshActiveScoreDisplay();")
        mapping_preview = begin_game.index("beginButtonMappingDemo(1UL);")
        active_state = begin_game.index("gameState = SHOW_INITIAL_MAPPING;")
        self.assertLess(score_reset, display_refresh)
        self.assertLess(display_refresh, mapping_preview)
        self.assertLess(mapping_preview, active_state)

    def test_active_score_is_preserved_through_cue_and_answer_wait_states(self):
        begin_round = function_body("beginRound")
        self.assertLess(
            begin_round.index("refreshActiveScoreDisplay();"),
            begin_round.index("gameState = PLAY_CUE;"),
        )

        loop = function_body("loop")
        self.assertNotIn("updateDisplay(", loop)
        for state in (
            "SHOW_INITIAL_MAPPING",
            "PLAY_CUE",
            "CUE_SOUND",
            "CUE_GAP",
            "WAIT_RELEASE_BEFORE_INPUT",
            "WAIT_INPUT",
            "BUTTON_FEEDBACK",
            "WAIT_INPUT_RELEASE",
            "CELEBRATION",
        ):
            self.assertIn(f"case {state}:", loop)

    def test_correct_round_refreshes_both_scores_before_celebration_or_next_round(self):
        complete = function_body("completeCorrectAnswer")
        increment = complete.index("++completedRounds;")
        update_best = complete.index("bestScore = completedRounds;")
        refresh = complete.index("refreshActiveScoreDisplay();")
        self.assertLess(increment, update_best)
        self.assertLess(update_best, refresh)

        self.assertNotIn('updateDisplay("ROUND COMPLETE", "CELEBRATION")', complete)
        celebration = complete.index("if (completedRounds % 3UL == 0)")
        self.assertLess(refresh, celebration)
        self.assertIn("gameState = CELEBRATION;", complete)

    def test_idle_pages_remain_unchanged_and_round_number_is_not_rendered(self):
        idle_page = function_body("showIdlePage")
        self.assertIn('"YOUR:%010lu"', idle_page)
        self.assertIn('"BEST:%010lu"', idle_page)
        self.assertNotIn('"GAMES:%010lu"', idle_page)
        self.assertIn('updateDisplay("PRESS START", value);', idle_page)
        self.assertNotIn("ROUND %lu", SKETCH)


if __name__ == "__main__":
    unittest.main()
