#!/usr/bin/env python3
"""Run randomized, replayable Wokwi automation scenarios for Alien Simon Says."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DEFAULT = ROOT / ".wokwi-sequence-state.json"
COLORS = ("red", "green", "blue", "yellow")
BUTTON_PARTS_BY_POSITION = tuple(f"button-{color}" for color in COLORS)
BUTTON_MAPPING_SEED_SALT = 0xB5297A4D
BUTTON_MAPPING_FALLBACK_SEED = 0x68E31DA4
BUTTON_MAPPING_DEMO_MS = 5500
SCENARIOS = ("first-round", "gameover-stale-event", "servo-only-after-loss", "start-reset", "button-remap")
UNSET = object()
TIMEOUT_MS = {
    "first-round": 20000,
    "gameover-stale-event": 24000,
    "servo-only-after-loss": 45000,
    "start-reset": 45000,
    "button-remap": 60000,
}
MOCK_DELAY_MS = {
    "first-round": 250,  # natural audio completion must not shorten the 2 s light cue
    "gameover-stale-event": 2300,  # sequence audio is still active at the 2 s stop boundary
    "servo-only-after-loss": 2300,
    "start-reset": 2300,
    "button-remap": 2300,
}


@dataclass(frozen=True)
class GamePlan:
    seed: int
    previous_first: int | None
    symbols: tuple[int, ...]

    @property
    def first(self) -> int:
        return self.symbols[0]


def xorshift32(state: int) -> int:
    state &= 0xFFFFFFFF
    if state == 0:
        state = 0x6D2B79F5
    state ^= (state << 13) & 0xFFFFFFFF
    state ^= state >> 17
    state ^= (state << 5) & 0xFFFFFFFF
    return state & 0xFFFFFFFF


def uniform_below(state: int, bound: int) -> tuple[int, int]:
    """Mirror firmware rejection over xorshift32's nonzero output domain."""
    if bound < 2:
        return 0, state
    largest_accepted = 0xFFFFFFFF - (0xFFFFFFFF % bound)
    while True:
        state = xorshift32(state)
        if state <= largest_accepted:
            return state % bound, state


def game_plan(seed: int, previous_first: int | None, length: int) -> GamePlan:
    """Plan with-replacement pseudo-random cues; previous_first is metadata only."""
    if not 1 <= seed <= 0xFFFFFFFF:
        raise ValueError("Wokwi seed must be a nonzero 32-bit value")
    state = seed
    symbols: list[int] = []
    for _ in range(length):
        symbol, state = uniform_below(state, len(COLORS))
        symbols.append(symbol)
    return GamePlan(seed, previous_first, tuple(symbols))


def next_game_seed(seed: int) -> int:
    result = xorshift32(seed)
    return result if result != 0 else 0x6D2B79F5


def button_mapping_seed(game_seed: int) -> int:
    state = (game_seed ^ BUTTON_MAPPING_SEED_SALT) & 0xFFFFFFFF
    return state if state != 0 else BUTTON_MAPPING_FALLBACK_SEED


def shuffle_button_mapping(previous: tuple[int, ...], state: int) -> tuple[tuple[int, ...], int]:
    mapping = list(range(len(COLORS)))
    for remaining in range(len(COLORS) - 1, 0, -1):
        selected, state = uniform_below(state, remaining + 1)
        mapping[remaining], mapping[selected] = mapping[selected], mapping[remaining]
    result = tuple(mapping)
    if result == previous:
        mapping[0], mapping[1] = mapping[1], mapping[0]
        result = tuple(mapping)
    return result, state


def mappings_through_round(game_seed: int, final_round: int) -> dict[int, tuple[int, ...]]:
    mapping = tuple(range(len(COLORS)))
    state = button_mapping_seed(game_seed)
    result: dict[int, tuple[int, ...]] = {}
    for round_number in range(1, final_round + 1):
        if round_number > 1 and (round_number - 1) % 3 == 0:
            mapping, state = shuffle_button_mapping(mapping, state)
        result[round_number] = mapping
    return result


def button_position_for_color(mapping: tuple[int, ...], color: int) -> int:
    return mapping.index(color)


def yaml_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def wait_step(text: str) -> str:
    return f"  - wait-serial: {yaml_quote(text)}"


def delay_step(milliseconds: int = 60) -> str:
    return f"  - delay: {milliseconds}ms"


def control_step(part_id: str, pressed: bool) -> str:
    value = 1 if pressed else 0
    return "\n".join((
        "  - set-control:",
        f"      part-id: {part_id}",
        "      name: pressed",
        f"      value: {value}",
    ))


def press_and_release(steps: list[str], button: str) -> None:
    steps.extend((control_step(button, True), delay_step(), control_step(button, False), delay_step()))


def start_game(steps: list[str], plan: GamePlan) -> None:
    press_and_release(steps, "button-start")
    steps.extend((
        wait_step("SIM_GAME_START"),
        wait_step(f"SIM_GAME_SEED:{plan.seed}"),
        wait_step(f"SIM_FIRST_COLOR:{plan.first}"),
    ))


def render_scenario(name: str, plans: list[GamePlan]) -> str:
    steps = [wait_step("READY")]
    start_game(steps, plans[0])

    if name == "first-round":
        first = plans[0].first
        steps.extend((
            wait_step(f"SIM_CUE_OFF:{first}:"),
            wait_step(f"SIM_CUE_STOP_REQUEST:{first}:"),
            wait_step(f"SIM_CUE_GAP_DONE:{first}:"),
            wait_step("SIM_INPUT_READY"),
        ))
        # Prove the game accepts input after the old 5 s limit, then waits for
        # a pressed answer to be released even after another 5 s has elapsed.
        steps.append(delay_step(5200))
        steps.extend((
            control_step(BUTTON_PARTS_BY_POSITION[first], True),
            delay_step(5200),
            control_step(BUTTON_PARTS_BY_POSITION[first], False),
            delay_step(100),
            wait_step("SIM_ROUND_COMPLETE"),
        ))

    elif name == "gameover-stale-event":
        first = plans[0].first
        wrong = (first + 1) % len(COLORS)
        steps.append(wait_step("SIM_INPUT_READY"))
        press_and_release(steps, BUTTON_PARTS_BY_POSITION[wrong])
        steps.extend((
            wait_step("SIM_GAME_OVER_START"),
            wait_step("SIM_GAMEOVER_EVENT_DRAINED:"),
            wait_step("SIM_GAME_OVER_STOP"),
        ))
        start_game(steps, plans[1])
        steps.append(wait_step("SIM_INPUT_READY"))

    elif name == "start-reset":
        steps.append(wait_step("SIM_INPUT_READY"))
        press_and_release(steps, "button-start")
        steps.extend((
            wait_step("SIM_GAME_RESET"),
            wait_step("SIM_GAME_START"),
            wait_step(f"SIM_GAME_SEED:{plans[1].seed}"),
            wait_step(f"SIM_FIRST_COLOR:{plans[1].first}"),
            wait_step("SIM_INPUT_READY"),
        ))
        wrong = (plans[1].first + 1) % len(COLORS)
        press_and_release(steps, BUTTON_PARTS_BY_POSITION[wrong])
        steps.extend((
            wait_step("SIM_GAME_OVER_START"),
            wait_step("SIM_SERVO_EXTEND"),
        ))
        press_and_release(steps, "button-start")
        steps.extend((
            wait_step("SIM_GAME_RESET_QUEUED"),
            wait_step("SIM_SERVO_RETRACT"),
            wait_step("SIM_SERVO_RETRACT_DONE"),
            wait_step("SIM_GAME_OVER_STOP"),
            wait_step("SIM_GAME_RESET"),
            wait_step("SIM_GAME_START"),
            wait_step(f"SIM_GAME_SEED:{plans[2].seed}"),
            wait_step(f"SIM_FIRST_COLOR:{plans[2].first}"),
            wait_step("SIM_INPUT_READY"),
        ))

    elif name == "servo-only-after-loss":
        symbols = plans[0].symbols
        for completed_round in range(1, 4):
            steps.append(wait_step("SIM_INPUT_READY"))
            for symbol in symbols[:completed_round]:
                press_and_release(steps, BUTTON_PARTS_BY_POSITION[symbol])
            steps.append(wait_step("SIM_ROUND_COMPLETE"))
        steps.append(wait_step("SIM_INPUT_READY"))
        round_four_mapping = mappings_through_round(plans[0].seed, 4)[4]
        wrong = (symbols[0] + 1) % len(COLORS)
        wrong_position = button_position_for_color(round_four_mapping, wrong)
        press_and_release(steps, BUTTON_PARTS_BY_POSITION[wrong_position])
        steps.extend((
            wait_step("SIM_GAME_OVER_START"),
            wait_step("SIM_SERVO_EXTEND"),
            wait_step("SIM_SERVO_RETRACT"),
            wait_step("SIM_GAME_OVER_STOP"),
        ))

    elif name == "button-remap":
        symbols = plans[0].symbols
        mapping = tuple(range(len(COLORS)))
        mapping_state = button_mapping_seed(plans[0].seed)
        for completed_round in range(1, 5):
            steps.append(wait_step("SIM_INPUT_READY"))
            for symbol in symbols[:completed_round]:
                position = button_position_for_color(mapping, symbol)
                press_and_release(steps, BUTTON_PARTS_BY_POSITION[position])
            steps.append(wait_step("SIM_ROUND_COMPLETE"))
            if completed_round % 3 == 0:
                mapping, mapping_state = shuffle_button_mapping(mapping, mapping_state)
                encoded = "".join(str(color) for color in mapping)
                steps.extend((
                    wait_step(f"SIM_BUTTON_MAP:{completed_round + 1}:{encoded}"),
                    wait_step("SIM_AUDIO_DONE:"),
                    wait_step(f"SIM_BUTTON_DEMO_START:{completed_round + 1}:"),
                    wait_step(f"SIM_BUTTON_DEMO_MAP:{completed_round + 1}:{encoded}"),
                    wait_step(f"SIM_BUTTON_DEMO_END:{completed_round + 1}:"),
                ))
        steps.append(wait_step("SIM_TEST_BUTTON_REMAP_DONE"))
    else:
        raise ValueError(f"unknown scenario: {name}")

    return "\n".join((
        f"name: {yaml_quote('Randomized ' + name)}",
        "version: 1",
        "author: Project-local randomized test runner",
        "steps:",
        *steps,
        "",
    ))


def expected_cues(name: str, plans: list[GamePlan]) -> list[int]:
    if name == "first-round":
        return [plans[0].first]
    if name == "gameover-stale-event":
        return [plans[0].first, plans[1].first]
    if name == "start-reset":
        return [plan.first for plan in plans]
    if name in ("servo-only-after-loss", "button-remap"):
        sequence = plans[0].symbols
        return [symbol for round_length in range(1, 5) for symbol in sequence[:round_length]]
    raise ValueError(f"unknown scenario: {name}")


def parse_color(value: str | None) -> int | None:
    if value is None or value.lower() == "none":
        return None
    lowered = value.lower()
    if lowered in COLORS:
        return COLORS.index(lowered)
    try:
        parsed = int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("use none, a color name, or an index 0..3") from error
    if not 0 <= parsed < len(COLORS):
        raise argparse.ArgumentTypeError("previous color must be in 0..3")
    return parsed


def parse_seed(value: str | None) -> int:
    if value is None:
        seed = secrets.randbits(32)
        return seed or 1
    try:
        seed = int(value, 0)
    except ValueError as error:
        raise argparse.ArgumentTypeError("seed must be decimal or 0x-prefixed hexadecimal") from error
    if not 1 <= seed <= 0xFFFFFFFF:
        raise argparse.ArgumentTypeError("seed must be a nonzero 32-bit value")
    return seed


def read_state(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        color = data["previous_first_color"]
        if data.get("version") != 1 or (color is not None and (type(color) is not int or color not in range(4))):
            raise ValueError("unsupported or invalid state values")
        return color
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"invalid Wokwi state file {path}: {error}; back it up or remove it") from error


def write_state(path: Path, color: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"version": 1, "previous_first_color": color}, indent=2) + "\n"
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


class StateLock:
    def __init__(self, state_path: Path, timeout_seconds: float = 60.0):
        self.path = state_path.with_name(state_path.name + ".lock")
        self.timeout_seconds = timeout_seconds
        self.held = False

    def __enter__(self) -> "StateLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self.path.mkdir()
                (self.path / "owner.txt").write_text(f"pid={os.getpid()}\n", encoding="ascii")
                self.held = True
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        f"timed out waiting for {self.path}; if no runner is active, remove this stale lock directory"
                    )
                time.sleep(0.25)

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.held:
            try:
                (self.path / "owner.txt").unlink(missing_ok=True)
                self.path.rmdir()
            except OSError:
                pass


def make_game_plans(name: str, seed: int, previous: int | None) -> list[GamePlan]:
    scenario_lengths = {
        "first-round": (1,),
        "gameover-stale-event": (1, 1),
        "servo-only-after-loss": (4,),
        "start-reset": (1, 1, 1),
        "button-remap": (4,),
    }
    try:
        lengths = scenario_lengths[name]
    except KeyError as error:
        raise ValueError(f"unknown scenario: {name}") from error
    plans: list[GamePlan] = []
    current_seed = seed
    current_previous = previous
    for length in lengths:
        plan = game_plan(current_seed, current_previous, length)
        plans.append(plan)
        current_previous = plan.first
        current_seed = next_game_seed(current_seed)
    return plans


def build_wokwi_firmware(seed: int, previous: int | None, scenario: str,
                         environment: dict[str, str]) -> tuple[int, str]:
    arduino_cli = environment.get("ARDUINO_CLI") or shutil.which("arduino-cli")
    if not arduino_cli:
        raise RuntimeError("arduino-cli is not on PATH")

    staging_root = Path(tempfile.mkdtemp(prefix="alien-simon-says-wokwi-build-"))
    try:
        sketch_dir = staging_root / "alien-simon-says"
        sketch_dir.mkdir()
        for source in (ROOT / "alien-simon-says.ino", *ROOT.glob("*.h")):
            shutil.copy2(source, sketch_dir / source.name)

        output_dir = ROOT / "build" / "wokwi"
        output_dir.mkdir(parents=True, exist_ok=True)
        previous_macro = 255 if previous is None else previous
        flags = (
            f"-DWOKWI_SIM -DWOKWI_INITIAL_SEED={seed}UL "
            f"-DWOKWI_PREVIOUS_FIRST_COLOR={previous_macro}"
        )
        if scenario == "button-remap":
            flags += " -DWOKWI_TEST_BUTTON_REMAP"
        command = [
            arduino_cli, "compile",
            "--fqbn", "arduino:avr:uno",
            "--build-property", f"compiler.cpp.extra_flags={flags}",
            "--output-dir", str(output_dir),
            str(sketch_dir),
        ]
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        return result.returncode, result.stdout
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def write_diagram_variant(destination: Path, completion_delay_ms: int) -> None:
    diagram = json.loads((ROOT / "diagram.json").read_text(encoding="utf-8"))
    mock = next((part for part in diagram["parts"] if part.get("id") == "dfplayer-mock"), None)
    if mock is None:
        raise RuntimeError("diagram.json has no dfplayer-mock part")
    mock.setdefault("attrs", {})["completionDelayMs"] = str(completion_delay_ms)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(diagram, indent=2) + "\n", encoding="utf-8")


def marker_values(serial: str, name: str) -> list[tuple[int, int]]:
    pattern = re.compile(rf"^{re.escape(name)}:(\d+):(\d+)\s*$", re.MULTILINE)
    return [(int(symbol), int(timestamp) & 0xFFFFFFFF) for symbol, timestamp in pattern.findall(serial)]


def button_input_values(serial: str) -> list[tuple[int, int, int]]:
    pattern = re.compile(r"^SIM_BUTTON_INPUT:([0-3]):([0-3]):(\d+)\s*$", re.MULTILINE)
    return [(int(position), int(color), int(timestamp) & 0xFFFFFFFF)
            for position, color, timestamp in pattern.findall(serial)]


def validate_transcript(name: str, plans: list[GamePlan], completion_delay_ms: int,
                        serial: str) -> None:
    seeds = [int(value) for value in re.findall(r"^SIM_GAME_SEED:(\d+)\s*$", serial, re.MULTILINE)]
    expected_seeds = [plan.seed for plan in plans]
    if seeds != expected_seeds:
        raise RuntimeError(f"firmware seed log {seeds} does not match expected {expected_seeds}")

    first_colors = [int(value) for value in re.findall(r"^SIM_FIRST_COLOR:(\d+)\s*$", serial, re.MULTILINE)]
    expected_first_colors = [plan.first for plan in plans]
    if first_colors != expected_first_colors:
        raise RuntimeError(f"firmware first-color log {first_colors} does not match expected {expected_first_colors}")
    cues = expected_cues(name, plans)
    on = marker_values(serial, "SIM_CUE_ON")
    off = marker_values(serial, "SIM_CUE_OFF")
    stop = marker_values(serial, "SIM_CUE_STOP_REQUEST")
    gap = marker_values(serial, "SIM_CUE_GAP_DONE")
    if not all(len(markers) == len(cues) for markers in (on, off, stop, gap)):
        raise RuntimeError(
            "incomplete cue markers: "
            f"expected {len(cues)}, on/off/stop/gap={len(on)}/{len(off)}/{len(stop)}/{len(gap)}"
        )

    for index, expected_symbol in enumerate(cues):
        on_symbol, on_at = on[index]
        off_symbol, off_at = off[index]
        stop_symbol, stop_at = stop[index]
        gap_symbol, gap_at = gap[index]
        if {on_symbol, off_symbol, stop_symbol, gap_symbol} != {expected_symbol}:
            raise RuntimeError(f"cue {index} color markers do not match expected symbol {expected_symbol}")
        light_duration = (off_at - on_at) & 0xFFFFFFFF
        stop_offset = (stop_at - off_at) & 0xFFFFFFFF
        dark_gap = (gap_at - off_at) & 0xFFFFFFFF
        if not 2000 <= light_duration <= 2200:
            raise RuntimeError(f"cue {index} light duration was {light_duration} ms, expected about 2000 ms")
        if stop_offset > 150:
            raise RuntimeError(f"cue {index} stop request was {stop_offset} ms after pixel-off")
        if not 180 <= dark_gap <= 300:
            raise RuntimeError(f"cue {index} dark gap was {dark_gap} ms, expected at least 180 ms")
        if index + 1 < len(on):
            next_on = on[index + 1][1]
            if ((next_on - off_at) & 0xFFFFFFFF) < 180:
                raise RuntimeError(f"cue {index + 1} began less than 180 ms after cue {index} turned off")

    lines = serial.splitlines()
    cue_on_line_indices = [i for i, line in enumerate(lines) if re.match(r"SIM_CUE_ON:\d+:\d+", line)]
    cue_off_line_indices = [i for i, line in enumerate(lines) if re.match(r"SIM_CUE_OFF:\d+:\d+", line)]
    if len(cue_on_line_indices) != len(cues) or len(cue_off_line_indices) != len(cues):
        raise RuntimeError("could not pair cue markers with serial transcript lines")
    for index, symbol in enumerate(cues):
        region = lines[cue_on_line_indices[index] + 1:cue_off_line_indices[index]]
        track = symbol + 1
        completed_early = any(line.strip() == f"SIM_AUDIO_DONE:{track}" for line in region)
        if completion_delay_ms < 2000 and not completed_early:
            raise RuntimeError(f"cue {index} did not register its expected early audio completion")
        if completion_delay_ms > 2000 and completed_early:
            raise RuntimeError(f"cue {index} completed before the 2 s Stop boundary despite a long mock delay")

    if name == "first-round":
        ready = [int(value) & 0xFFFFFFFF for value in
                 re.findall(r"^SIM_INPUT_READY:(\d+)\s*$", serial, re.MULTILINE)]
        presses = marker_values(serial, "SIM_INPUT_PRESS")
        releases = marker_values(serial, "SIM_INPUT_RELEASE")
        if len(ready) != 1 or len(presses) != 1 or len(releases) != 1:
            raise RuntimeError("first-round transcript must contain one ready/press/release marker")
        if ((presses[0][1] - ready[0]) & 0xFFFFFFFF) < 5000:
            raise RuntimeError("player answer was not accepted after waiting beyond the former 5 s limit")
        if presses[0][0] != plans[0].first or releases[0][0] != plans[0].first:
            raise RuntimeError("first-round input markers do not match the randomized expected color")
        if ((releases[0][1] - presses[0][1]) & 0xFFFFFFFF) < 5000:
            raise RuntimeError("pressed answer was not held beyond the former 5 s limit")
        if "INPUT_TIMEOUT" in serial:
            raise RuntimeError("transcript contains the removed player input timeout")
        if "SIM_GAME_OVER_START" in serial:
            raise RuntimeError("first-round answer entered Game Over before successful completion")
        press_line = next(i for i, line in enumerate(lines)
                          if re.match(r"SIM_INPUT_PRESS:\d+:\d+", line))
        release_line = next(i for i, line in enumerate(lines)
                            if re.match(r"SIM_INPUT_RELEASE:\d+:\d+", line))
        if press_line >= release_line:
            raise RuntimeError("answer release must follow its press")
        complete_line = next((i for i, line in enumerate(lines)
                              if line.strip() == "SIM_ROUND_COMPLETE"), None)
        if complete_line is None or complete_line <= release_line:
            raise RuntimeError("answer must be committed only after its debounced release")

    if name == "start-reset":
        reset_lines = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_RESET"]
        game_starts = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_START"]
        queued = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_RESET_QUEUED"]
        game_over = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_OVER_START"]
        retract_done = [i for i, line in enumerate(lines) if line.strip() == "SIM_SERVO_RETRACT_DONE"]
        game_over_stop = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_OVER_STOP"]
        if not (len(reset_lines) == 2 and len(game_starts) == 3 and len(queued) == 1 and
                len(game_over) == 1 and len(retract_done) == 1 and len(game_over_stop) == 1 and
                game_starts[0] < reset_lines[0] < game_starts[1] < game_over[0] < queued[0] <
                retract_done[0] < game_over_stop[0] < reset_lines[1] < game_starts[2]):
            raise RuntimeError("Start must reset active play and defer a queued reset until servo return finishes")

    if name == "servo-only-after-loss":
        game_over = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_OVER_START"]
        extensions = [i for i, line in enumerate(lines) if line.strip() == "SIM_SERVO_EXTEND"]
        if len(game_over) != 1 or len(extensions) != 1 or extensions[0] <= game_over[0]:
            raise RuntimeError("servo extension must occur only after the player-loss Game Over marker")

    if name == "button-remap":
        plan = plans[0]
        mapping_by_round = mappings_through_round(plan.seed, 4)
        expected_maps = [
            (1, "".join(str(color) for color in mapping_by_round[1])),
            (4, "".join(str(color) for color in mapping_by_round[4])),
        ]
        actual_maps = [(int(round_number), encoded)
                       for round_number, encoded in re.findall(
                           r"^SIM_BUTTON_MAP:(\d+):([0-3]{4})\s*$", serial, re.MULTILINE)]
        if actual_maps != expected_maps:
            raise RuntimeError(f"button mapping logs {actual_maps} do not match {expected_maps}")

        expected_inputs = []
        for round_number in range(1, 5):
            mapping = mapping_by_round[round_number]
            expected_inputs.extend(
                (button_position_for_color(mapping, color), color)
                for color in plan.symbols[:round_number]
            )
        button_inputs = button_input_values(serial)
        actual_inputs = [(position, color) for position, color, _ in button_inputs]
        if actual_inputs != expected_inputs:
            raise RuntimeError(f"button position/color inputs {actual_inputs} do not match {expected_inputs}")

        expected_led_assignments = []
        for round_number in range(1, 5):
            mapping = mapping_by_round[round_number]
            round_colors = plan.symbols[:round_number]
            expected_led_assignments.extend(
                (color, button_position_for_color(mapping, color)) for color in round_colors
            )
            expected_led_assignments.extend(
                (color, button_position_for_color(mapping, color)) for color in round_colors
            )
        actual_led_assignments = [
            (int(color), int(position))
            for color, position in re.findall(
                r"^SIM_MAPPED_LED_ON:([0-3]):([0-3]):\d+\s*$", serial, re.MULTILINE
            )
        ]
        if actual_led_assignments != expected_led_assignments:
            raise RuntimeError(
                "mapped LED cues/feedback must use each cue color's assigned button position: "
                f"{actual_led_assignments} != {expected_led_assignments}"
            )

        presses = marker_values(serial, "SIM_INPUT_PRESS")
        releases = marker_values(serial, "SIM_INPUT_RELEASE")
        ready = [int(value) & 0xFFFFFFFF for value in
                 re.findall(r"^SIM_INPUT_READY:(\d+)\s*$", serial, re.MULTILINE)]
        completed = [i for i, line in enumerate(lines) if line.strip() == "SIM_ROUND_COMPLETE"]
        if not (len(ready) == len(completed) == 4 and
                len(presses) == len(releases) == len(expected_inputs) and
                [color for color, _ in presses] == [color for _, color in expected_inputs] and
                [color for color, _ in releases] == [color for _, color in expected_inputs] and
                serial.count("SIM_TEST_BUTTON_REMAP_DONE") == 1):
            raise RuntimeError("button-remap transcript is missing mapped input/round completion events")
        for button_input, press, release in zip(button_inputs, presses, releases):
            position, color, button_at = button_input
            if press != (color, button_at) or release[0] != color:
                raise RuntimeError("button position, mapped color, and input markers disagree")
            if ((release[1] - press[1]) & 0xFFFFFFFF) < 25:
                raise RuntimeError(f"button {position + 1} input was released before the debounce interval")
        map_lines = [i for i, line in enumerate(lines) if line.startswith("SIM_BUTTON_MAP:")]
        round_completions = [i for i, line in enumerate(lines) if line.strip() == "SIM_ROUND_COMPLETE"]
        ready_lines = [i for i, line in enumerate(lines)
                       if re.match(r"SIM_INPUT_READY:\d+", line)]
        demo_starts = [(int(round_number), int(timestamp) & 0xFFFFFFFF)
                       for round_number, timestamp in re.findall(
                           r"^SIM_BUTTON_DEMO_START:(\d+):(\d+)\s*$", serial, re.MULTILINE)]
        demo_ends = [(int(round_number), int(timestamp) & 0xFFFFFFFF)
                     for round_number, timestamp in re.findall(
                         r"^SIM_BUTTON_DEMO_END:(\d+):(\d+)\s*$", serial, re.MULTILINE)]
        demo_maps = [(int(round_number), encoded)
                     for round_number, encoded in re.findall(
                         r"^SIM_BUTTON_DEMO_MAP:(\d+):([0-3]{4})\s*$", serial, re.MULTILINE)]
        expected_demo_map = "".join(str(color) for color in mapping_by_round[4])
        demo_duration = ((demo_ends[0][1] - demo_starts[0][1]) & 0xFFFFFFFF
                         if demo_ends and demo_starts else 0)
        if not (len(demo_starts) == len(demo_ends) == 1 and
                demo_starts[0][0] == demo_ends[0][0] == 4 and
                demo_maps == [(4, expected_demo_map)] and
                demo_duration >= BUTTON_MAPPING_DEMO_MS):
            raise RuntimeError("simultaneous LED map must match the new assignment and stay on for at least 5.5 seconds")
        demo_start_lines = [i for i, line in enumerate(lines)
                            if line.startswith("SIM_BUTTON_DEMO_START:")]
        demo_map_lines = [i for i, line in enumerate(lines)
                          if line.startswith("SIM_BUTTON_DEMO_MAP:")]
        demo_end_lines = [i for i, line in enumerate(lines)
                          if line.startswith("SIM_BUTTON_DEMO_END:")]
        audio_done_lines = [i for i, line in enumerate(lines)
                            if re.match(r"SIM_AUDIO_DONE:\d+", line)]
        demo_order_checks = (
            len(demo_map_lines) == 1,
            map_lines[0] < ready_lines[0] < round_completions[0] <
            round_completions[1] < round_completions[2] < map_lines[1],
            any(round_completions[2] < done < demo_start_lines[0]
                for done in audio_done_lines),
            demo_start_lines[0] < demo_map_lines[0] < demo_end_lines[0] <
            ready_lines[3] < round_completions[3],
        )
        if not all(demo_order_checks):
            raise RuntimeError(
                "simultaneous LED map must follow round 3 celebration and finish before round 4 input: "
                f"{demo_order_checks}"
            )


def display_color(color: int | None) -> str:
    return "none" if color is None else f"{COLORS[color]}({color})"


def run_one(name: str, seed: int, previous: int | None, state_path: Path,
            persist: bool, output_root: Path) -> tuple[bool, int | None]:
    plans = make_game_plans(name, seed, previous)
    print(
        f"WOKWI_TEST scenario={name} seed=0x{seed:08X} previous_first={display_color(previous)} "
        f"expected_first={[display_color(plan.first) for plan in plans]}",
        flush=True,
    )
    replay_previous = "none" if previous is None else str(previous)
    print(
        f"REPLAY: python3 scripts/run-wokwi-tests.py --scenario {name} --seed 0x{seed:08X} "
        f"--previous-first-color {replay_previous} --no-persist",
        flush=True,
    )

    artifact_dir = output_root / f"{name}-{seed:08x}-{int(time.time() * 1000)}-{secrets.token_hex(2)}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    scenario_path = artifact_dir / "scenario.yaml"
    diagram_path = artifact_dir / "diagram.json"
    serial_path = artifact_dir / "serial.log"
    manifest_path = artifact_dir / "run.json"
    scenario_path.write_text(render_scenario(name, plans), encoding="utf-8")
    write_diagram_variant(diagram_path, MOCK_DELAY_MS[name])

    manifest = {
        "scenario": name,
        "seed": seed,
        "previous_first_color": previous,
        "expected_first_colors": [plan.first for plan in plans],
        "mock_completion_delay_ms": MOCK_DELAY_MS[name],
        "replay_command": (
            f"python3 scripts/run-wokwi-tests.py --scenario {name} --seed 0x{seed:08X} "
            f"--previous-first-color {replay_previous} --no-persist"
        ),
    }
    if name == "button-remap":
        manifest["expected_button_mappings"] = {
            str(round_number): list(mapping)
            for round_number, mapping in mappings_through_round(plans[0].seed, 4).items()
        }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    environment = os.environ.copy()
    build_code, build_output = build_wokwi_firmware(seed, previous, name, environment)
    print(build_output, end="")
    if build_code != 0:
        manifest.update({"result": "build-failed", "build_exit_code": build_code})
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return False, previous

    cli = os.environ.get("WOKWI_CLI", "wokwi-cli")
    command = [
        cli, ".",
        "--diagram-file", str(diagram_path),
        "--scenario", str(scenario_path),
        "--timeout", str(TIMEOUT_MS[name]),
        "--serial-log-file", str(serial_path),
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(result.stdout, end="")
    serial = serial_path.read_text(encoding="utf-8", errors="replace") if serial_path.exists() else result.stdout
    actual_first_colors = [
        int(value) for value in re.findall(r"^SIM_FIRST_COLOR:(\d+)\s*$", serial, re.MULTILINE)
    ]
    latest_color = actual_first_colors[-1] if actual_first_colors else previous
    try:
        if result.returncode != 0:
            raise RuntimeError(f"wokwi-cli exited with status {result.returncode}")
        validate_transcript(name, plans, MOCK_DELAY_MS[name], serial)
        manifest.update({"result": "passed", "actual_first_colors": actual_first_colors})
        print(f"PASS {name}: {serial_path}")
        passed = True
    except RuntimeError as error:
        manifest.update({"result": "failed", "error": str(error), "actual_first_colors": actual_first_colors})
        print(f"FAIL {name}: {error}", file=sys.stderr)
        passed = False
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if persist and latest_color is not None:
        write_state(state_path, latest_color)
    return passed, latest_color


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="all")
    parser.add_argument("--seed", type=parse_seed,
                        help="replay seed (decimal or 0x-prefixed hex); omitted seeds use OS randomness")
    parser.add_argument("--previous-first-color", type=parse_color, default=UNSET,
                        help="replay metadata only: none, red/green/blue/yellow, or index 0..3")
    parser.add_argument("--state-file", type=Path, default=STATE_DEFAULT)
    parser.add_argument("--no-persist", action="store_true", help="do not update the local state file")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "build" / "wokwi-tests")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state_path = args.state_file.expanduser().resolve()
    output_root = args.artifacts.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    with StateLock(state_path):
        previous = read_state(state_path) if args.previous_first_color is UNSET else args.previous_first_color
        names = SCENARIOS if args.scenario == "all" else (args.scenario,)
        provided_seed = args.seed
        all_passed = True
        for index, name in enumerate(names):
            seed = provided_seed if provided_seed is not None and index == 0 else parse_seed(None)
            passed, latest = run_one(name, seed, previous, state_path, not args.no_persist, output_root)
            all_passed = all_passed and passed
            if latest is not None:
                previous = latest
            if not passed:
                break
            if args.no_persist and latest is not None:
                # Still model the state transition between scenarios in a single --scenario all run.
                previous = latest
        return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
