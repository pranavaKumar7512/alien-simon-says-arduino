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
    def test_previous_first_color_does_not_influence_generated_symbols(self):
        baseline = RUNNER.game_plan(0xA341316C, None, 32)
        for previous in range(4):
            plan = RUNNER.game_plan(0xA341316C, previous, 32)
            self.assertEqual(plan.symbols, baseline.symbols)
            self.assertEqual(plan.previous_first, previous)

    def test_seed_replay_and_next_game_seed_match_firmware_prng(self):
        first = RUNNER.game_plan(0xA341316C, 2, 12)
        replay = RUNNER.game_plan(0xA341316C, 2, 12)
        self.assertEqual(first, replay)
        self.assertEqual(
            first.symbols,
            (2, 2, 3, 3, 1, 1, 3, 1, 3, 3, 3, 0),
        )
        self.assertEqual(RUNNER.next_game_seed(1), 270369)
        self.assertEqual(first.symbols[:8], (2, 2, 3, 3, 1, 1, 3, 1))

    def test_sampling_with_replacement_allows_repeats(self):
        plan = RUNNER.game_plan(1, None, 8)
        self.assertEqual(plan.symbols, (1, 1, 1, 3, 1, 0, 2, 2))
        self.assertEqual(plan.symbols[0], plan.symbols[1])

    def test_uniform_below_rejects_upper_nonzero_states(self):
        vectors = (
            (0xBB07F6B5, 0xFFFFFFFD, 1, 0x000BA05D),
            (0xACD979CE, 0xFFFFFFFE, 2, 0x0007C03E),
            (0x5E6CFCE7, 0xFFFFFFFF, 3, 0x0003E01F),
        )
        for seed, rejected, expected_symbol, accepted in vectors:
            with self.subTest(rejected_state=rejected):
                self.assertEqual(RUNNER.xorshift32(seed), rejected)
                self.assertEqual(
                    RUNNER.uniform_below(seed, 4),
                    (expected_symbol, accepted),
                )

        # UINT32_MAX is the top of the nonzero domain; its count is divisible by 3.
        seed = 0x5E6CFCE7
        self.assertEqual(RUNNER.uniform_below(seed, 3), (0, 0xFFFFFFFF))
        self.assertEqual(RUNNER.uniform_below(seed, 1), (0, seed))


    def test_transcript_accepts_repeated_first_color_across_games(self):
        plans = RUNNER.make_game_plans("gameover-stale-event", 1, None)
        self.assertEqual([plan.first for plan in plans], [1, 1])
        serial = "\n".join((
            f"SIM_GAME_SEED:{plans[0].seed}",
            f"SIM_FIRST_COLOR:{plans[0].first}",
            "SIM_CUE_ON:1:100",
            "SIM_CUE_OFF:1:2100",
            "SIM_CUE_STOP_REQUEST:1:2100",
            "SIM_CUE_GAP_DONE:1:2280",
            f"SIM_GAME_SEED:{plans[1].seed}",
            f"SIM_FIRST_COLOR:{plans[1].first}",
            "SIM_CUE_ON:1:2400",
            "SIM_CUE_OFF:1:4400",
            "SIM_CUE_STOP_REQUEST:1:4400",
            "SIM_CUE_GAP_DONE:1:4580",
        ))
        RUNNER.validate_transcript("gameover-stale-event", plans, 2300, serial)

    def test_randomized_scenarios_use_generated_button_colors(self):
        first_plan = RUNNER.game_plan(0x12345678, None, 4)
        first_yaml = RUNNER.render_scenario("first-round", [first_plan])
        self.assertIn(f"SIM_FIRST_COLOR:{first_plan.first}", first_yaml)
        self.assertIn(f"part-id: {RUNNER.BUTTONS[first_plan.first]}", first_yaml)
        self.assertIn("SIM_CUE_OFF:", first_yaml)
        self.assertIn("SIM_CUE_GAP_DONE:", first_yaml)
        self.assertEqual(first_yaml.count("delay: 5200ms"), 2)

        stale_plans = RUNNER.make_game_plans("gameover-stale-event", 0x12345678, None)
        self.assertEqual(stale_plans[1].previous_first, stale_plans[0].first)
        self.assertEqual(
            stale_plans[1].symbols,
            RUNNER.game_plan(stale_plans[1].seed, None, len(stale_plans[1].symbols)).symbols,
        )
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

        reordered_input = early_completion.replace(
            f"SIM_INPUT_PRESS:{symbol}:7500\nSIM_INPUT_RELEASE:{symbol}:12700",
            f"SIM_INPUT_RELEASE:{symbol}:12700\nSIM_INPUT_PRESS:{symbol}:7500",
        )
        with self.assertRaisesRegex(RuntimeError, "release must follow its press"):
            RUNNER.validate_transcript("first-round", [plan], 250, reordered_input)

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
        import json
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state.json"
            self.assertIsNone(RUNNER.read_state(state))
            RUNNER.write_state(state, None)
            self.assertIsNone(RUNNER.read_state(state))
            RUNNER.write_state(state, 3)
            self.assertEqual(RUNNER.read_state(state), 3)
            for invalid_color in (True, 1.0, "1"):
                with self.subTest(invalid_color=invalid_color):
                    state.write_text(
                        json.dumps({"version": 1, "previous_first_color": invalid_color}),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(RuntimeError, "invalid Wokwi state file"):
                        RUNNER.read_state(state)

            diagram = root / "diagram.json"
            RUNNER.write_diagram_variant(diagram, 2300)
            data = json.loads(diagram.read_text(encoding="utf-8"))
            mock = next(part for part in data["parts"] if part.get("id") == "dfplayer-mock")
            self.assertEqual(mock["attrs"]["completionDelayMs"], "2300")


if __name__ == "__main__":
    unittest.main()
