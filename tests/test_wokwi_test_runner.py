import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-wokwi-tests.py"
SPEC = importlib.util.spec_from_file_location("wokwi_test_runner", SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


class WokwiTestRunnerTests(unittest.TestCase):
    def test_first_symbol_differs_and_only_first_symbol_is_constrained(self):
        first_game = RUNNER.game_plan(0x12345678, None, 32)
        next_game = RUNNER.game_plan(0x12345678, first_game.first, 32)
        self.assertNotEqual(first_game.first, next_game.first)
        self.assertEqual(set(next_game.symbols[1:]), set(range(4)))
        for plan in (first_game, next_game):
            for start in range(0, len(plan.symbols), 4):
                self.assertEqual(set(plan.symbols[start:start + 4]), set(range(4)))

    def test_seed_replay_and_next_game_seed_match_firmware_prng(self):
        first = RUNNER.game_plan(0xA341316C, 2, 12)
        replay = RUNNER.game_plan(0xA341316C, 2, 12)
        self.assertEqual(first, replay)
        self.assertEqual(
            first.symbols,
            (3, 0, 1, 2, 0, 2, 1, 3, 0, 2, 1, 3),
        )
        self.assertEqual(RUNNER.next_game_seed(1), 270369)
        self.assertEqual(set(first.symbols[:4]), set(range(4)))
        self.assertEqual(set(first.symbols[4:8]), set(range(4)))

    def test_randomized_scenarios_use_generated_button_colors(self):
        first_plan = RUNNER.game_plan(0x12345678, None, 4)
        first_yaml = RUNNER.render_scenario("first-round", [first_plan])
        self.assertIn(f"SIM_FIRST_COLOR:{first_plan.first}", first_yaml)
        self.assertIn(f"part-id: {RUNNER.BUTTONS[first_plan.first]}", first_yaml)
        self.assertIn("SIM_CUE_OFF:", first_yaml)
        self.assertIn("SIM_CUE_GAP_DONE:", first_yaml)
        self.assertEqual(first_yaml.count("delay: 5200ms"), 2)

        stale_plans = RUNNER.make_game_plans("gameover-stale-event", 0x12345678, None)
        self.assertNotEqual(stale_plans[0].first, stale_plans[1].first)
        stale_yaml = RUNNER.render_scenario("gameover-stale-event", stale_plans)
        self.assertIn(f"SIM_GAME_SEED:{stale_plans[1].seed}", stale_yaml)
        self.assertIn(f"SIM_FIRST_COLOR:{stale_plans[1].first}", stale_yaml)

        reset_plans = RUNNER.make_game_plans("start-reset", 0x12345678, None)
        reset_yaml = RUNNER.render_scenario("start-reset", reset_plans)
        self.assertIn("SIM_GAME_RESET", reset_yaml)
        self.assertIn(f"SIM_GAME_SEED:{reset_plans[1].seed}", reset_yaml)
        self.assertEqual(reset_yaml.count("part-id: button-start"), 6)
        self.assertEqual(RUNNER.expected_cues("start-reset", reset_plans),
                         [plan.first for plan in reset_plans])

    def test_servo_scenario_answers_generated_sequence_then_loses(self):
        plan = RUNNER.game_plan(0x12345678, 0, 4)
        scenario = RUNNER.render_scenario("servo-only-after-loss", [plan])
        self.assertIn("SIM_SERVO_EXTEND", scenario)
        self.assertIn("SIM_GAME_OVER_START", scenario)
        self.assertEqual(len(RUNNER.expected_cues("servo-only-after-loss", [plan])), 10)

    def test_transcript_validator_checks_early_audio_and_fixed_cue_timing(self):
        plan = RUNNER.game_plan(0x12345678, None, 1)
        symbol = plan.first
        track = symbol + 1
        early_completion = "\n".join((
            f"SIM_GAME_SEED:{plan.seed}",
            f"SIM_FIRST_COLOR:{symbol}",
            f"SIM_CUE_ON:{symbol}:100",
            f"SIM_AUDIO_START:{track}",
            f"SIM_AUDIO_DONE:{track}",
            f"SIM_CUE_OFF:{symbol}:2100",
            f"SIM_CUE_STOP_REQUEST:{symbol}:2100",
            f"SIM_CUE_GAP_DONE:{symbol}:2280",
            "SIM_INPUT_READY:2300",
            f"SIM_INPUT_PRESS:{symbol}:7500",
            f"SIM_INPUT_RELEASE:{symbol}:12700",
            "SIM_ROUND_COMPLETE",
        ))
        RUNNER.validate_transcript("first-round", [plan], 250, early_completion)

        short_wait = early_completion.replace(
            f"SIM_INPUT_PRESS:{symbol}:7500", f"SIM_INPUT_PRESS:{symbol}:7299"
        )
        with self.assertRaisesRegex(RuntimeError, "after waiting"):
            RUNNER.validate_transcript("first-round", [plan], 250, short_wait)

        short_hold = early_completion.replace(
            f"SIM_INPUT_RELEASE:{symbol}:12700", f"SIM_INPUT_RELEASE:{symbol}:12499"
        )
        with self.assertRaisesRegex(RuntimeError, "held beyond"):
            RUNNER.validate_transcript("first-round", [plan], 250, short_hold)

        premature_loss = early_completion.replace(
            "SIM_INPUT_READY:2300", "SIM_INPUT_READY:2300\nSIM_GAME_OVER_START"
        )
        with self.assertRaisesRegex(RuntimeError, "Game Over"):
            RUNNER.validate_transcript("first-round", [plan], 250, premature_loss)

        short_light = early_completion.replace(f"SIM_CUE_OFF:{symbol}:2100", f"SIM_CUE_OFF:{symbol}:2099")
        short_light = short_light.replace(f"SIM_CUE_STOP_REQUEST:{symbol}:2100", f"SIM_CUE_STOP_REQUEST:{symbol}:2099")
        short_light = short_light.replace(f"SIM_CUE_GAP_DONE:{symbol}:2280", f"SIM_CUE_GAP_DONE:{symbol}:2279")
        with self.assertRaisesRegex(RuntimeError, "light duration"):
            RUNNER.validate_transcript("first-round", [plan], 250, short_light)

    def test_start_reset_transcript_restarts_and_queues_during_servo_return(self):
        plans = RUNNER.make_game_plans("start-reset", 0x12345678, None)
        lines = []
        cue_times = (100, 2400, 4700)
        for index, plan in enumerate(plans):
            symbol = plan.first
            start = cue_times[index]
            if index == 0:
                lines.extend(("SIM_GAME_START", f"SIM_GAME_SEED:{plan.seed}",
                              f"SIM_FIRST_COLOR:{symbol}"))
            elif index == 1:
                lines.extend(("SIM_GAME_RESET", "SIM_GAME_START",
                              f"SIM_GAME_SEED:{plan.seed}", f"SIM_FIRST_COLOR:{symbol}"))
            else:
                lines.extend(("SIM_SERVO_RETRACT_DONE", "SIM_GAME_OVER_STOP",
                              "SIM_GAME_RESET", "SIM_GAME_START",
                              f"SIM_GAME_SEED:{plan.seed}", f"SIM_FIRST_COLOR:{symbol}"))
            lines.extend((
                f"SIM_CUE_ON:{symbol}:{start}",
                f"SIM_AUDIO_START:{symbol + 1}",
                f"SIM_CUE_OFF:{symbol}:{start + 2000}",
                f"SIM_CUE_STOP_REQUEST:{symbol}:{start + 2000}",
                f"SIM_CUE_GAP_DONE:{symbol}:{start + 2180}",
            ))
            if index == 0:
                lines.append("SIM_INPUT_READY:2300")
            elif index == 1:
                lines.extend(("SIM_GAME_OVER_START", "SIM_SERVO_EXTEND",
                              "SIM_GAME_RESET_QUEUED", "SIM_SERVO_RETRACT"))
            else:
                lines.append("SIM_INPUT_READY:6900")
        RUNNER.validate_transcript("start-reset", plans, 2300, "\n".join(lines))

    def test_state_file_round_trip_and_diagram_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state.json"
            self.assertIsNone(RUNNER.read_state(state))
            RUNNER.write_state(state, 3)
            self.assertEqual(RUNNER.read_state(state), 3)

            diagram = root / "diagram.json"
            RUNNER.write_diagram_variant(diagram, 2300)
            import json
            data = json.loads(diagram.read_text(encoding="utf-8"))
            mock = next(part for part in data["parts"] if part.get("id") == "dfplayer-mock")
            self.assertEqual(mock["attrs"]["completionDelayMs"], "2300")


if __name__ == "__main__":
    unittest.main()
