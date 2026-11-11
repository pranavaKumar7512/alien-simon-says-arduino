import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-wokwi-tests.py"
SPEC = importlib.util.spec_from_file_location("wokwi_test_runner", SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def button_remap_transcript(plan):
    maps = RUNNER.mappings_through_round(plan.seed, 4)
    encode = lambda mapping: "".join(str(color) for color in mapping)
    lines = [
        f"SIM_GAME_START",
        f"SIM_GAME_SEED:{plan.seed}",
        f"SIM_BUTTON_MAP:1:{encode(maps[1])}",
        f"SIM_FIRST_COLOR:{plan.first}",
    ]
    clock = 100
    for round_number in range(1, 5):
        mapping = maps[round_number]
        for color in plan.symbols[:round_number]:
            off = clock + 2000
            position = RUNNER.button_position_for_color(mapping, color)
            lines.extend((
                f"SIM_MAPPED_LED_ON:{color}:{position}:{clock}",
                f"SIM_CUE_ON:{color}:{clock}",
                f"SIM_AUDIO_START:{color + 1}",
                f"SIM_CUE_OFF:{color}:{off}",
                f"SIM_CUE_STOP_REQUEST:{color}:{off}",
                f"SIM_CUE_GAP_DONE:{color}:{off + 180}",
            ))
            clock = off + 180
        ready = clock + 50
        lines.append(f"SIM_INPUT_READY:{ready}")
        for index, color in enumerate(plan.symbols[:round_number]):
            press = ready + 50 + index * 100
            position = RUNNER.button_position_for_color(mapping, color)
            lines.extend((
                f"SIM_MAPPED_LED_ON:{color}:{position}:{press}",
                f"SIM_BUTTON_INPUT:{position}:{color}:{press}",
                f"SIM_INPUT_PRESS:{color}:{press}",
                f"SIM_INPUT_RELEASE:{color}:{press + 60}",
            ))
        lines.append("SIM_ROUND_COMPLETE")
        clock = ready + 50 + round_number * 100 + 100
        if round_number == 3:
            lines.extend((
                f"SIM_BUTTON_MAP:4:{encode(maps[4])}",
                "SIM_AUDIO_START:1",
                "SIM_AUDIO_DONE:1",
                f"SIM_BUTTON_DEMO_START:4:{clock}",
                f"SIM_BUTTON_DEMO_MAP:4:{encode(maps[4])}",
                f"SIM_BUTTON_DEMO_END:4:{clock + 5500}",
            ))
            clock += 5600
    lines.append("SIM_TEST_BUTTON_REMAP_DONE")
    return "\n".join(lines)


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

    def test_button_mappings_shuffle_after_each_three_completed_rounds(self):
        seed = 0x12345678
        cues_before = RUNNER.game_plan(seed, None, 30).symbols
        mapping = RUNNER.mappings_through_round(seed, 10)
        cues_after = RUNNER.game_plan(seed, None, 30).symbols
        identity = (0, 1, 2, 3)
        self.assertEqual([mapping[round_number] for round_number in range(1, 4)],
                         [identity, identity, identity])
        self.assertEqual(mapping[4], (1, 2, 3, 0))
        self.assertEqual(mapping[7], (1, 2, 0, 3))
        self.assertEqual(mapping[10], (3, 0, 1, 2))
        self.assertNotEqual(mapping[7], mapping[4])
        self.assertNotEqual(mapping[10], mapping[7])
        for round_mapping in mapping.values():
            self.assertEqual(sorted(round_mapping), list(range(4)))
        self.assertEqual(mapping, RUNNER.mappings_through_round(seed, 10))
        self.assertEqual(cues_before, cues_after)

        initial = (0, 1, 2, 3)
        stream = RUNNER.button_mapping_seed(seed)
        first, _ = RUNNER.shuffle_button_mapping(initial, stream)
        repeated_candidate, _ = RUNNER.shuffle_button_mapping(first, stream)
        self.assertNotEqual(repeated_candidate, first)
        self.assertEqual(sorted(repeated_candidate), list(range(4)))

    def test_button_remap_scenario_uses_position_to_color_mapping(self):
        plan = RUNNER.game_plan(0x12345678, None, 4)
        scenario = RUNNER.render_scenario("button-remap", [plan])
        maps = RUNNER.mappings_through_round(plan.seed, 4)
        self.assertIn("SIM_BUTTON_MAP:4:" + "".join(map(str, maps[4])), scenario)
        self.assertIn("SIM_BUTTON_DEMO_MAP:4:" + "".join(map(str, maps[4])), scenario)
        self.assertIn("SIM_TEST_BUTTON_REMAP_DONE", scenario)
        self.assertEqual(len(RUNNER.expected_cues("button-remap", [plan])), 10)

        part_ids = re.findall(r"part-id: (button-(?:red|green|blue|yellow|start))", scenario)
        self.assertEqual(part_ids[:2], ["button-start", "button-start"])
        actual_inputs = part_ids[2:]
        expected_inputs = []
        for round_number in range(1, 5):
            mapping = maps[round_number]
            for color in plan.symbols[:round_number]:
                part = RUNNER.BUTTON_PARTS_BY_POSITION[
                    RUNNER.button_position_for_color(mapping, color)
                ]
                expected_inputs.extend((part, part))
        self.assertEqual(actual_inputs, expected_inputs)

    def test_button_remap_transcript_rejects_wrong_position_and_map(self):
        plans = RUNNER.make_game_plans("button-remap", 0x12345678, None)
        serial = button_remap_transcript(plans[0])
        RUNNER.validate_transcript("button-remap", plans, 2300, serial)

        first_led = re.search(r"SIM_MAPPED_LED_ON:([0-3]):([0-3]):(\d+)", serial)
        self.assertIsNotNone(first_led)
        wrong_led_position = (int(first_led.group(2)) + 1) % 4
        malformed_led = (serial[:first_led.start(2)] + str(wrong_led_position) +
                         serial[first_led.end(2):])
        with self.assertRaisesRegex(RuntimeError, "mapped LED cues/feedback"):
            RUNNER.validate_transcript("button-remap", plans, 2300, malformed_led)

        first_input = re.search(r"SIM_BUTTON_INPUT:([0-3]):([0-3]):(\d+)", serial)
        self.assertIsNotNone(first_input)
        wrong_position = (int(first_input.group(1)) + 1) % 4
        malformed_input = serial[:first_input.start(1)] + str(wrong_position) + serial[first_input.end(1):]
        with self.assertRaisesRegex(RuntimeError, "button position/color inputs"):
            RUNNER.validate_transcript("button-remap", plans, 2300, malformed_input)

        maps = RUNNER.mappings_through_round(plans[0].seed, 4)
        wrong_map = list(maps[4])
        wrong_map[0], wrong_map[1] = wrong_map[1], wrong_map[0]
        malformed_map = serial.replace(
            "SIM_BUTTON_MAP:4:" + "".join(map(str, maps[4])),
            "SIM_BUTTON_MAP:4:" + "".join(map(str, wrong_map)),
        )
        with self.assertRaisesRegex(RuntimeError, "button mapping logs"):
            RUNNER.validate_transcript("button-remap", plans, 2300, malformed_map)

        start_demo, end_demo = re.findall(
            r"SIM_BUTTON_DEMO_(?:START|END):4:(\d+)", serial
        )
        too_short = serial.replace(
            f"SIM_BUTTON_DEMO_END:4:{end_demo}",
            f"SIM_BUTTON_DEMO_END:4:{int(start_demo) + 5499}",
        )
        with self.assertRaisesRegex(RuntimeError, "at least 5.5 seconds"):
            RUNNER.validate_transcript("button-remap", plans, 2300, too_short)

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

    def test_randomized_scenarios_use_positioned_buttons(self):
        first_plan = RUNNER.game_plan(0x12345678, None, 4)
        first_yaml = RUNNER.render_scenario("first-round", [first_plan])
        self.assertIn(f"SIM_FIRST_COLOR:{first_plan.first}", first_yaml)
        self.assertIn(f"part-id: {RUNNER.BUTTON_PARTS_BY_POSITION[first_plan.first]}", first_yaml)
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
