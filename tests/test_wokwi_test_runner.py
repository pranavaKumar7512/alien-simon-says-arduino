import importlib.util
import re
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
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

        reordered = serial.splitlines()
        ready_index = next(i for i, line in enumerate(reordered)
                           if line.startswith("SIM_INPUT_READY:"))
        ready_line = reordered.pop(ready_index)
        first_release = next(i for i, line in enumerate(reordered)
                             if line.startswith("SIM_INPUT_RELEASE:"))
        reordered.insert(first_release + 1, ready_line)
        with self.assertRaisesRegex(RuntimeError, "input-ready 1 must precede"):
            RUNNER.validate_transcript("button-remap", plans, 2300, "\n".join(reordered))

        demo_start, demo_end = re.findall(
            r"SIM_BUTTON_DEMO_(?:START|END):4:(\d+)", serial
        )
        reversed_demo = serial.replace(
            f"SIM_BUTTON_DEMO_END:4:{demo_end}",
            f"SIM_BUTTON_DEMO_END:4:{int(demo_start) - 1}",
        )
        with self.assertRaisesRegex(RuntimeError, "timestamps are out of order"):
            RUNNER.validate_transcript("button-remap", plans, 2300, reversed_demo)

        first_input_press = re.search(r"SIM_INPUT_PRESS:[0-3]:(\d+)", serial)
        first_input_release = re.search(r"SIM_INPUT_RELEASE:[0-3]:(\d+)", serial)
        self.assertIsNotNone(first_input_press)
        self.assertIsNotNone(first_input_release)
        reversed_release = (
            serial[:first_input_release.start(1)] +
            str(int(first_input_press.group(1)) - 1) +
            serial[first_input_release.end(1):]
        )
        with self.assertRaisesRegex(RuntimeError, "timestamps are out of order"):
            RUNNER.validate_transcript("button-remap", plans, 2300, reversed_release)

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

    def test_button_remap_rejects_later_cue_before_shifted_round_answer(self):
        plan = RUNNER.game_plan(0x12345678, None, 4)
        lines = button_remap_transcript(plan).splitlines()
        shifted = []
        for index, line in enumerate(lines):
            shift_timestamp = (
                line.startswith((
                    "SIM_INPUT_READY:", "SIM_BUTTON_INPUT:", "SIM_INPUT_PRESS:",
                    "SIM_INPUT_RELEASE:", "SIM_BUTTON_DEMO_START:", "SIM_BUTTON_DEMO_END:",
                )) or
                (line.startswith("SIM_MAPPED_LED_ON:") and
                 index + 1 < len(lines) and lines[index + 1].startswith("SIM_BUTTON_INPUT:"))
            )
            if shift_timestamp:
                prefix, timestamp = line.rsplit(":", 1)
                line = f"{prefix}:{(int(timestamp) + 30000) & 0xFFFFFFFF}"
            shifted.append(line)

        self.assertIn("SIM_INPUT_READY:32330", shifted)
        self.assertIn(f"SIM_CUE_ON:{plan.symbols[0]}:2580", shifted)
        with self.assertRaisesRegex(RuntimeError, "timestamps are out of order"):
            RUNNER.validate_transcript("button-remap", [plan], 2300, "\n".join(shifted))

    def test_round_four_cue_timestamp_must_follow_map_demo_end(self):
        plan = RUNNER.game_plan(0x12345678, None, 4)
        serial = button_remap_transcript(plan)
        round_four_cue = re.findall(r"^SIM_CUE_ON:[0-3]:(\d+)$", serial, re.MULTILINE)[6]
        demo_start, demo_end = re.findall(
            r"SIM_BUTTON_DEMO_(?:START|END):4:(\d+)", serial
        )
        late_demo_end = serial.replace(
            f"SIM_BUTTON_DEMO_END:4:{demo_end}",
            f"SIM_BUTTON_DEMO_END:4:{int(round_four_cue) + 1}",
        )
        self.assertGreater(int(round_four_cue) + 1 - int(demo_start), RUNNER.BUTTON_MAPPING_DEMO_MS)
        with self.assertRaisesRegex(RuntimeError, "timestamps are out of order"):
            RUNNER.validate_transcript("button-remap", [plan], 2300, late_demo_end)

    def test_button_remap_transcript_timestamps_wrap_millis(self):
        plan = RUNNER.game_plan(0x12345678, None, 4)
        serial = button_remap_transcript(plan)
        timestamp_patterns = (
            r"^(SIM_CUE_(?:ON|OFF|STOP_REQUEST|GAP_DONE):[0-3]:)(\d+)$",
            r"^(SIM_INPUT_READY:)(\d+)$",
            r"^(SIM_BUTTON_INPUT:[0-3]:[0-3]:)(\d+)$",
            r"^(SIM_INPUT_(?:PRESS|RELEASE):[0-3]:)(\d+)$",
            r"^(SIM_MAPPED_LED_ON:[0-3]:[0-3]:)(\d+)$",
            r"^(SIM_BUTTON_DEMO_(?:START|END):4:)(\d+)$",
        )
        offset = 0xFFFFFF00
        shifted_lines = []
        for line in serial.splitlines():
            for pattern in timestamp_patterns:
                line = re.sub(
                    pattern,
                    lambda match: match.group(1) + str(
                        (int(match.group(2)) + offset) & 0xFFFFFFFF
                    ),
                    line,
                )
            shifted_lines.append(line)
        RUNNER.validate_transcript(
            "button-remap", [plan], 2300, "\n".join(shifted_lines)
        )

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


    def test_transcript_accepts_repeated_first_color_across_games_and_millis_wrap(self):
        plans = RUNNER.make_game_plans("gameover-stale-event", 1, None)
        self.assertEqual([plan.first for plan in plans], [1, 1])
        cue_on = 0xFFFFF000
        cue_off = (cue_on + 2000) & 0xFFFFFFFF
        cue_gap = (cue_off + 180) & 0xFFFFFFFF
        ready = (cue_gap + 20) & 0xFFFFFFFF
        game_over_start = 0xFFFFFF00
        servo_extend = (game_over_start + 1) & 0xFFFFFFFF
        servo_retract = (servo_extend + RUNNER.SERVO_GAME_OVER_HOLD_MS) & 0xFFFFFFFF
        retract_done = (servo_retract + RUNNER.SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS) & 0xFFFFFFFF
        game_over_stop = (game_over_start + 6002) & 0xFFFFFFFF
        next_cue_on = (game_over_stop + 100) & 0xFFFFFFFF
        next_cue_off = (next_cue_on + 2000) & 0xFFFFFFFF
        next_cue_gap = (next_cue_off + 180) & 0xFFFFFFFF
        next_ready = (next_cue_gap + 20) & 0xFFFFFFFF
        lines = [
            "SIM_GAME_START",
            f"SIM_GAME_SEED:{plans[0].seed}",
            f"SIM_FIRST_COLOR:{plans[0].first}",
            f"SIM_CUE_ON:1:{cue_on}",
            "SIM_AUDIO_START:2",
            f"SIM_CUE_OFF:1:{cue_off}",
            f"SIM_CUE_STOP_REQUEST:1:{cue_off}",
            f"SIM_CUE_GAP_DONE:1:{cue_gap}",
            f"SIM_INPUT_READY:{ready}",
            "WRONG_ANSWER",
            "SIM_AUDIO_START:5",
            f"SIM_GAME_OVER_START:{game_over_start}",
            f"SIM_SERVO_EXTEND:{servo_extend}",
            "SIM_GAMEOVER_EVENT_DRAINED:5",
            f"SIM_SERVO_RETRACT:{servo_retract}",
            f"SIM_SERVO_RETRACT_DONE:{retract_done}",
            f"SIM_GAME_OVER_STOP:{game_over_stop}",
            "SIM_GAME_START",
            f"SIM_GAME_SEED:{plans[1].seed}",
            f"SIM_FIRST_COLOR:{plans[1].first}",
            f"SIM_CUE_ON:1:{next_cue_on}",
            "SIM_AUDIO_START:2",
            f"SIM_CUE_OFF:1:{next_cue_off}",
            f"SIM_CUE_STOP_REQUEST:1:{next_cue_off}",
            f"SIM_CUE_GAP_DONE:1:{next_cue_gap}",
            f"SIM_INPUT_READY:{next_ready}",
        ]
        RUNNER.validate_transcript("gameover-stale-event", plans, 2300, "\n".join(lines))

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
                         [reset_plans[0].first, *reset_plans[0].symbols,
                          reset_plans[1].first, reset_plans[2].first])
        self.assertIn("SIM_SCORE_STATE:1:", reset_yaml)
        self.assertEqual(reset_yaml.count("SIM_SCORE_STATE:0:"), 2)

        chunk_plan = RUNNER.make_game_plans("chunk-boundary", 0x12345678, None)[0]
        chunk_yaml = RUNNER.render_scenario("chunk-boundary", [chunk_plan])
        self.assertEqual(len(chunk_plan.symbols), 11)
        self.assertEqual(RUNNER.expected_cues("chunk-boundary", [chunk_plan]),
                         list(chunk_plan.symbols))
        self.assertEqual(chunk_yaml.count("name: pressed"), 24)  # Start plus eleven input pairs.
    def test_scenario_firmware_isolated_from_interactive_default(self):
        seed = 0x12345678
        isolated = RUNNER.scenario_firmware_dir("chunk-boundary", seed, None)
        self.assertEqual(
            isolated,
            RUNNER.ROOT / "build" / "wokwi-tests" / "firmware" / "chunk-boundary-12345678-prev-none",
        )
        self.assertNotEqual(isolated, RUNNER.ROOT / "build" / "wokwi")
        self.assertTrue(isolated.is_absolute())

    def test_scenario_build_uses_absolute_isolated_paths(self):
        original_root = RUNNER.ROOT
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project with spaces"
            root.mkdir()
            (root / "alien-simon-says.ino").write_text("void setup() {}\n", encoding="utf-8")
            (root / "helper.h").write_text("// test header\n", encoding="utf-8")
            RUNNER.ROOT = root
            try:
                with patch.object(RUNNER.subprocess, "run", return_value=SimpleNamespace(
                        returncode=0, stdout="compiled\n")) as compile_run:
                    result, output = RUNNER.build_wokwi_firmware(
                        0x12345678, None, "chunk-boundary", {"ARDUINO_CLI": "arduino-cli"}
                    )
            finally:
                RUNNER.ROOT = original_root

        self.assertEqual((result, output), (0, "compiled\n"))
        command = compile_run.call_args.args[0]
        output_dir = Path(command[command.index("--output-dir") + 1])
        self.assertTrue(output_dir.is_absolute())
        self.assertEqual(
            output_dir,
            root / "build" / "wokwi-tests" / "firmware" /
            "chunk-boundary-12345678-prev-none",
        )
        self.assertNotEqual(output_dir, root / "build" / "wokwi")
        self.assertTrue(Path(command[-1]).is_absolute())
        self.assertEqual(compile_run.call_args.kwargs["cwd"], root)

    def test_timestamp_delta_handles_millis_wraparound(self):
        self.assertEqual(RUNNER.forward_delta(0x00000020, 0xFFFFFFF0, "rollover"), 0x30)
        with self.assertRaisesRegex(RuntimeError, "timestamps are out of order"):
            RUNNER.forward_delta(100, 200, "reversed")

    def test_replay_command_is_project_rooted_and_shell_quoted(self):
        original_root = RUNNER.ROOT
        try:
            RUNNER.ROOT = Path("/tmp/alien simon project")
            command = RUNNER.format_replay_command("first-round", 0x12345678, 2)
        finally:
            RUNNER.ROOT = original_root
        self.assertTrue(command.startswith("python3 '/tmp/alien simon project/scripts/run-wokwi-tests.py' "))
        self.assertIn("--seed 0x12345678 --previous-first-color 2 --no-persist", command)

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

        ready_after_press = early_completion.replace(
            f"SIM_INPUT_READY:2300\nSIM_INPUT_PRESS:{symbol}:7500",
            f"SIM_INPUT_PRESS:{symbol}:7500\nSIM_INPUT_READY:2300",
        )
        with self.assertRaisesRegex(RuntimeError, "follow input-ready"):
            RUNNER.validate_transcript("first-round", [plan], 250, ready_after_press)

        press_timestamp_before_ready = early_completion.replace(
            f"SIM_INPUT_PRESS:{symbol}:7500", f"SIM_INPUT_PRESS:{symbol}:2000"
        )
        with self.assertRaisesRegex(RuntimeError, "timestamps are out of order"):
            RUNNER.validate_transcript("first-round", [plan], 250, press_timestamp_before_ready)

        short_light = early_completion.replace(f"SIM_CUE_OFF:{symbol}:2100", f"SIM_CUE_OFF:{symbol}:2099")
        short_light = short_light.replace(f"SIM_CUE_STOP_REQUEST:{symbol}:2100", f"SIM_CUE_STOP_REQUEST:{symbol}:2099")
        short_light = short_light.replace(f"SIM_CUE_GAP_DONE:{symbol}:2280", f"SIM_CUE_GAP_DONE:{symbol}:2279")
        with self.assertRaisesRegex(RuntimeError, "light duration"):
            RUNNER.validate_transcript("first-round", [plan], 250, short_light)

    def test_start_reset_transcript_proves_score_reset_and_queues_during_return(self):
        plans = RUNNER.make_game_plans("start-reset", 0x12345678, None)
        self.assertEqual(len(plans[0].symbols), 2)
        lines = [
            "SIM_GAME_START",
            f"SIM_GAME_SEED:{plans[0].seed}",
            f"SIM_SCORE_STATE:0:0",
            f"SIM_FIRST_COLOR:{plans[0].first}",
        ]

        def add_cue(symbol, start):
            lines.extend((
                f"SIM_CUE_ON:{symbol}:{start}",
                f"SIM_AUDIO_START:{symbol + 1}",
                f"SIM_CUE_OFF:{symbol}:{start + 2000}",
                f"SIM_CUE_STOP_REQUEST:{symbol}:{start + 2000}",
                f"SIM_CUE_GAP_DONE:{symbol}:{start + 2180}",
            ))

        add_cue(plans[0].first, 100)
        lines.extend((
            "SIM_INPUT_READY:2300",
            f"SIM_BUTTON_INPUT:{plans[0].first}:{plans[0].first}:2350",
            f"SIM_INPUT_PRESS:{plans[0].first}:2350",
            f"SIM_INPUT_RELEASE:{plans[0].first}:2410",
            "SIM_SCORE_STATE:1:1",
            "SIM_ROUND_COMPLETE",
        ))
        add_cue(plans[0].first, 2500)
        add_cue(plans[0].symbols[1], 4680)
        lines.append("SIM_INPUT_READY:6880")

        lines.extend((
            "SIM_GAME_RESET",
            "SIM_GAME_START",
            f"SIM_GAME_SEED:{plans[1].seed}",
            "SIM_SCORE_STATE:0:1",
            f"SIM_FIRST_COLOR:{plans[1].first}",
        ))
        add_cue(plans[1].first, 7100)
        lines.extend((
            "SIM_INPUT_READY:9300",
            "WRONG_ANSWER",
            "SIM_AUDIO_START:5",
            "SIM_GAME_OVER_START:9400",
            "SIM_SERVO_EXTEND:9401",
            "SIM_GAME_RESET_QUEUED",
            "SIM_SERVO_RETRACT:12401",
            "SIM_SERVO_RETRACT_DONE:15401",
            "SIM_GAME_OVER_STOP:15402",
            "SIM_GAME_RESET",
            "SIM_GAME_START",
            f"SIM_GAME_SEED:{plans[2].seed}",
            "SIM_SCORE_STATE:0:1",
            f"SIM_FIRST_COLOR:{plans[2].first}",
        ))
        add_cue(plans[2].first, 15500)
        lines.append("SIM_INPUT_READY:17700")
        serial = "\n".join(lines)
        RUNNER.validate_transcript("start-reset", plans, 2300, serial)

        zero_before_reset = serial.replace("SIM_SCORE_STATE:1:1", "SIM_SCORE_STATE:0:1", 1)
        with self.assertRaisesRegex(RuntimeError, "score telemetry"):
            RUNNER.validate_transcript("start-reset", plans, 2300, zero_before_reset)

        lost_best = serial.replace("SIM_SCORE_STATE:0:1", "SIM_SCORE_STATE:0:0", 1)
        with self.assertRaisesRegex(RuntimeError, "score telemetry"):
            RUNNER.validate_transcript("start-reset", plans, 2300, lost_best)

    def test_chunk_boundary_transcript_requires_all_eleven_released_answers(self):
        plans = RUNNER.make_game_plans("chunk-boundary", 0xA341316C, None)
        plan = plans[0]
        lines = [
            f"SIM_GAME_SEED:{plan.seed}",
            f"SIM_FIRST_COLOR:{plan.first}",
            "SIM_TEST_CHUNK_BOUNDARY",
        ]
        for index, symbol in enumerate(plan.symbols):
            on_at = 100 + index * 2180
            off_at = on_at + 2000
            track = symbol + 1
            lines.extend((
                f"SIM_CUE_ON:{symbol}:{on_at}",
                f"SIM_AUDIO_START:{track}",
                f"SIM_AUDIO_DONE:{track}",
                f"SIM_CUE_OFF:{symbol}:{off_at}",
                f"SIM_CUE_STOP_REQUEST:{symbol}:{off_at}",
                f"SIM_CUE_GAP_DONE:{symbol}:{off_at + 180}",
            ))

        ready_at = 100 + 10 * 2180 + 2180 + 100
        lines.append(f"SIM_INPUT_READY:{ready_at}")
        for index, symbol in enumerate(plan.symbols):
            pressed_at = ready_at + 100 + index * 100
            lines.extend((
                f"SIM_INPUT_PRESS:{symbol}:{pressed_at}",
                f"SIM_INPUT_RELEASE:{symbol}:{pressed_at + 60}",
            ))
        lines.append("SIM_ROUND_COMPLETE")
        RUNNER.validate_transcript("chunk-boundary", plans, 250, "\n".join(lines))

        late_gap = lines.copy()
        first_off = next(i for i, line in enumerate(late_gap) if line.startswith("SIM_CUE_OFF:"))
        first_gap = next(i for i, line in enumerate(late_gap) if line.startswith("SIM_CUE_GAP_DONE:"))
        off_at = int(late_gap[first_off].rsplit(":", 1)[1])
        late_gap[first_gap] = late_gap[first_gap].rsplit(":", 1)[0] + f":{off_at + 250}"
        with self.assertRaisesRegex(RuntimeError, "timestamps are out of order"):
            RUNNER.validate_transcript("chunk-boundary", plans, 250, "\n".join(late_gap))

        broken = lines.copy()
        wrong = (plan.symbols[-1] + 1) % len(RUNNER.COLORS)
        broken[-2] = f"SIM_INPUT_RELEASE:{wrong}:{ready_at + 100 + 10 * 100 + 60}"
        with self.assertRaisesRegex(RuntimeError, "do not match"):
            RUNNER.validate_transcript("chunk-boundary", plans, 250, "\n".join(broken))

    def test_servo_transcript_requires_three_wins_before_loss_motion(self):
        plans = RUNNER.make_game_plans("servo-only-after-loss", 0x12345678, None)
        plan = plans[0]
        lines = [f"SIM_GAME_SEED:{plan.seed}", f"SIM_FIRST_COLOR:{plan.first}"]
        cue_index = 0
        for completed_round in range(1, 5):
            for symbol in plan.symbols[:completed_round]:
                on_at = 100 + cue_index * 2180
                off_at = on_at + 2000
                lines.extend((
                    f"SIM_CUE_ON:{symbol}:{on_at}",
                    f"SIM_AUDIO_START:{symbol + 1}",
                    f"SIM_CUE_OFF:{symbol}:{off_at}",
                    f"SIM_CUE_STOP_REQUEST:{symbol}:{off_at}",
                    f"SIM_CUE_GAP_DONE:{symbol}:{off_at + 180}",
                ))
                cue_index += 1
            lines.append(f"SIM_INPUT_READY:{100 + cue_index * 2180 + 100}")
            if completed_round < 4:
                lines.append("SIM_ROUND_COMPLETE")
        game_over_start = 23000
        servo_extend = game_over_start + 1
        servo_retract = servo_extend + RUNNER.SERVO_GAME_OVER_HOLD_MS
        retract_done = servo_retract + RUNNER.SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS
        lines.extend((
            "WRONG_ANSWER",
            "SIM_AUDIO_START:5",
            f"SIM_GAME_OVER_START:{game_over_start}",
            f"SIM_SERVO_EXTEND:{servo_extend}",
            f"SIM_SERVO_RETRACT:{servo_retract}",
            f"SIM_SERVO_RETRACT_DONE:{retract_done}",
            f"SIM_GAME_OVER_STOP:{retract_done + 1}",
        ))
        RUNNER.validate_transcript("servo-only-after-loss", plans, 2300, "\n".join(lines))

        wrong_loss_reason = lines.copy()
        wrong_loss_reason[wrong_loss_reason.index("WRONG_ANSWER")] = "WRONG_CHORD"
        with self.assertRaisesRegex(RuntimeError, "wrong answer"):
            RUNNER.validate_transcript("servo-only-after-loss", plans, 2300, "\n".join(wrong_loss_reason))
        wrong_chord = lines.copy()
        wrong_chord.insert(wrong_chord.index("WRONG_ANSWER"), "WRONG_CHORD")
        with self.assertRaisesRegex(RuntimeError, "wrong answer"):
            RUNNER.validate_transcript("servo-only-after-loss", plans, 2300, "\n".join(wrong_chord))

        bad_order = lines.copy()
        bad_order.insert(2, "SIM_SERVO_EXTEND:1")
        with self.assertRaisesRegex(RuntimeError, "one timestamped"):
            RUNNER.validate_transcript("servo-only-after-loss", plans, 2300, "\n".join(bad_order))

    def test_gameover_transcript_checks_completion_and_transition_durations(self):
        plans = RUNNER.make_game_plans("gameover-stale-event", 0x12345678, None)
        first, second = plans
        game_over_track = 5  # AUDIO_GAME_OVER_LOSS_TRACK in audio_track_config.h.
        lines = [
            "SIM_GAME_START",
            f"SIM_GAME_SEED:{first.seed}",
            f"SIM_FIRST_COLOR:{first.first}",
            f"SIM_CUE_ON:{first.first}:100",
            f"SIM_AUDIO_START:{first.first + 1}",
            f"SIM_CUE_OFF:{first.first}:2100",
            f"SIM_CUE_STOP_REQUEST:{first.first}:2100",
            f"SIM_CUE_GAP_DONE:{first.first}:2280",
            "SIM_INPUT_READY:2300",
            "WRONG_ANSWER",
            f"SIM_AUDIO_START:{game_over_track}",
            "SIM_GAME_OVER_START:2400",
            "SIM_SERVO_EXTEND:2401",
            f"SIM_GAMEOVER_EVENT_DRAINED:{game_over_track}",
            "SIM_SERVO_RETRACT:5401",
            "SIM_SERVO_RETRACT_DONE:8401",
            "SIM_GAME_OVER_STOP:8402",
            "SIM_GAME_START",
            f"SIM_GAME_SEED:{second.seed}",
            f"SIM_FIRST_COLOR:{second.first}",
            f"SIM_CUE_ON:{second.first}:8500",
            f"SIM_AUDIO_START:{second.first + 1}",
            f"SIM_CUE_OFF:{second.first}:10500",
            f"SIM_CUE_STOP_REQUEST:{second.first}:10500",
            f"SIM_CUE_GAP_DONE:{second.first}:10680",
            "SIM_INPUT_READY:10700",
        ]
        RUNNER.validate_transcript("gameover-stale-event", plans, 2300, "\n".join(lines))

        bad_order = lines.copy()
        start_index = next(i for i, line in enumerate(bad_order)
                           if line.startswith("SIM_GAME_OVER_START:"))
        drain_index = next(i for i, line in enumerate(bad_order)
                           if line.startswith("SIM_GAMEOVER_EVENT_DRAINED:"))
        bad_order[start_index], bad_order[drain_index] = bad_order[drain_index], bad_order[start_index]
        with self.assertRaisesRegex(RuntimeError, "out of order|Game Over completion"):
            RUNNER.validate_transcript("gameover-stale-event", plans, 2300, "\n".join(bad_order))

        accepted = lines.copy()
        start_index = next(i for i, line in enumerate(accepted)
                           if line.startswith("SIM_GAME_OVER_START:"))
        accepted.insert(start_index + 1, f"SIM_AUDIO_DONE:{game_over_track}")
        with self.assertRaisesRegex(RuntimeError, "must be drained"):
            RUNNER.validate_transcript("gameover-stale-event", plans, 2300, "\n".join(accepted))

        too_short_game_over = lines.copy()
        stop_index = next(i for i, line in enumerate(too_short_game_over)
                          if line.startswith("SIM_GAME_OVER_STOP:"))
        too_short_game_over[stop_index] = "SIM_GAME_OVER_STOP:5399"
        with self.assertRaisesRegex(RuntimeError, "Game Over duration"):
            RUNNER.validate_transcript("gameover-stale-event", plans, 2300,
                                       "\n".join(too_short_game_over))

        too_short_hold = lines.copy()
        retract_index = next(i for i, line in enumerate(too_short_hold)
                             if line.startswith("SIM_SERVO_RETRACT:"))
        too_short_hold[retract_index] = "SIM_SERVO_RETRACT:5400"
        with self.assertRaisesRegex(RuntimeError, "servo hold"):
            RUNNER.validate_transcript("gameover-stale-event", plans, 2300,
                                       "\n".join(too_short_hold))

        too_short_return = lines.copy()
        done_index = next(i for i, line in enumerate(too_short_return)
                          if line.startswith("SIM_SERVO_RETRACT_DONE:"))
        too_short_return[done_index] = "SIM_SERVO_RETRACT_DONE:8400"
        with self.assertRaisesRegex(RuntimeError, "servo return allowance"):
            RUNNER.validate_transcript("gameover-stale-event", plans, 2300,
                                       "\n".join(too_short_return))

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

            for invalid_version in (True, 1.0, "1"):
                with self.subTest(invalid_version=invalid_version):
                    state.write_text(
                        json.dumps({"version": invalid_version, "previous_first_color": None}),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(RuntimeError, "invalid Wokwi state file"):
                        RUNNER.read_state(state)

            state.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "invalid Wokwi state file"):
                RUNNER.read_state(state)

            diagram = root / "diagram.json"
            RUNNER.write_diagram_variant(diagram, 2300)
            data = json.loads(diagram.read_text(encoding="utf-8"))
            mock = next(part for part in data["parts"] if part.get("id") == "dfplayer-mock")
            self.assertEqual(mock["attrs"]["completionDelayMs"], "2300")


if __name__ == "__main__":
    unittest.main()
