#!/usr/bin/env python3
"""Run randomized, replayable Wokwi automation scenarios for Alien Simon Says."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shlex
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
BUTTONS = BUTTON_PARTS_BY_POSITION
BUTTON_MAPPING_SEED_SALT = 0xB5297A4D
BUTTON_MAPPING_FALLBACK_SEED = 0x68E31DA4
BUTTON_MAPPING_DEMO_MS = 5500
GAME_OVER_MIN_MS = 3000
SERVO_GAME_OVER_HOLD_MS = 3000
SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS = 3000
SCENARIOS = (
    "first-round", "gameover-stale-event", "servo-only-after-loss", "start-reset",
    "button-remap", "chunk-boundary",
)
UNSET = object()
TIMEOUT_MS = {
    "first-round": 20000,
    "gameover-stale-event": 24000,
    "servo-only-after-loss": 45000,
    "start-reset": 45000,
    "button-remap": 60000,
    "chunk-boundary": 45000,
}
MOCK_DELAY_MS = {
    "first-round": 250,  # natural audio completion must not shorten the 2 s light cue
    "gameover-stale-event": 2300,  # completion event must be drained during Game Over
    "servo-only-after-loss": 2300,
    "start-reset": 2300,
    "button-remap": 2300,
    "chunk-boundary": 250,
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

    elif name == "chunk-boundary":
        steps.append(wait_step("SIM_INPUT_READY"))
        for symbol in plans[0].symbols:
            press_and_release(steps, BUTTONS[symbol])
        steps.append(wait_step("SIM_ROUND_COMPLETE"))

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
        first = plans[0].first
        steps.append(wait_step("SIM_INPUT_READY"))
        press_and_release(steps, BUTTON_PARTS_BY_POSITION[first])
        steps.extend((
            wait_step("SIM_SCORE_STATE:1:"),
            wait_step("SIM_ROUND_COMPLETE"),
            wait_step("SIM_INPUT_READY"),
        ))
        press_and_release(steps, "button-start")
        steps.extend((
            wait_step("SIM_GAME_RESET"),
            wait_step("SIM_GAME_START"),
            wait_step(f"SIM_GAME_SEED:{plans[1].seed}"),
            wait_step("SIM_SCORE_STATE:0:"),
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
            wait_step("SIM_SCORE_STATE:0:"),
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
        return [plans[0].first, *plans[0].symbols, plans[1].first, plans[2].first]
    if name == "chunk-boundary":
        return list(plans[0].symbols)
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
        if type(data) is not dict:
            raise ValueError("state must be a JSON object")
        version = data.get("version")
        color = data["previous_first_color"]
        if (type(version) is not int or version != 1 or
                (color is not None and (type(color) is not int or color not in range(4)))):
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
        "start-reset": (2, 1, 1),
        "button-remap": (4,),
        "chunk-boundary": (11,),
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


def scenario_firmware_dir(scenario: str, seed: int, previous: int | None = None) -> Path:
    previous_tag = "none" if previous is None else str(previous)
    return ROOT / "build" / "wokwi-tests" / "firmware" / f"{scenario}-{seed:08x}-prev-{previous_tag}"


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

        output_dir = scenario_firmware_dir(scenario, seed, previous)
        output_dir.mkdir(parents=True, exist_ok=True)
        previous_macro = 255 if previous is None else previous
        flags = (
            f"-DWOKWI_SIM -DWOKWI_INITIAL_SEED={seed}UL "
            f"-DWOKWI_PREVIOUS_FIRST_COLOR={previous_macro}"
        )
        if scenario == "button-remap":
            flags += " -DWOKWI_TEST_BUTTON_REMAP"
        if scenario == "chunk-boundary":
            flags += " -DWOKWI_TEST_CHUNK_BOUNDARY"
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


def forward_delta(later: int, earlier: int, label: str) -> int:
    delta = (later - earlier) & 0xFFFFFFFF
    if delta >= 0x80000000:
        raise RuntimeError(f"{label} timestamps are out of order")
    return delta


def timed_event_values(lines: list[str], marker: str) -> list[tuple[int, int]]:
    pattern = re.compile(rf"^{re.escape(marker)}:(\d+)\s*$")
    return [(index, int(match.group(1)) & 0xFFFFFFFF)
            for index, line in enumerate(lines)
            if (match := pattern.match(line)) is not None]


def validate_game_over_timing(lines: list[str]) -> None:
    started = timed_event_values(lines, "SIM_GAME_OVER_START")
    stopped = timed_event_values(lines, "SIM_GAME_OVER_STOP")
    extended = timed_event_values(lines, "SIM_SERVO_EXTEND")
    retracted = timed_event_values(lines, "SIM_SERVO_RETRACT")
    retract_done = timed_event_values(lines, "SIM_SERVO_RETRACT_DONE")
    if not any((started, stopped, extended, retracted, retract_done)):
        return
    if len(started) != 1 or len(stopped) != 1:
        raise RuntimeError("Game Over must have one timestamped start and stop")

    duration = forward_delta(stopped[0][1], started[0][1], "Game Over duration")
    if duration < GAME_OVER_MIN_MS:
        raise RuntimeError(
            f"Game Over duration was {duration} ms, expected at least {GAME_OVER_MIN_MS} ms"
        )

    servo_events = (extended, retracted, retract_done)
    if not any(servo_events):
        return
    if any(len(events) != 1 for events in servo_events):
        raise RuntimeError("servo loss path must have one timestamped extend/retract/return-done event")
    if not (started[0][0] < extended[0][0] < retracted[0][0] <
            retract_done[0][0] < stopped[0][0]):
        raise RuntimeError("Game Over and servo transition markers are out of order")

    hold = forward_delta(retracted[0][1], extended[0][1], "servo hold")
    if hold < SERVO_GAME_OVER_HOLD_MS:
        raise RuntimeError(
            f"servo hold was {hold} ms, expected at least {SERVO_GAME_OVER_HOLD_MS} ms"
        )
    return_allowance = forward_delta(
        retract_done[0][1], retracted[0][1], "servo return allowance"
    )
    if return_allowance < SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS:
        raise RuntimeError(
            "servo return allowance was "
            f"{return_allowance} ms, expected at least {SERVO_GAME_OVER_RETRACT_ALLOWANCE_MS} ms"
        )
    forward_delta(stopped[0][1], retract_done[0][1], "Game Over stop after servo return")


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
        light_duration = forward_delta(off_at, on_at, f"cue {index} light")
        stop_offset = forward_delta(stop_at, off_at, f"cue {index} stop")
        dark_gap = forward_delta(gap_at, off_at, f"cue {index} dark gap")
        if not 2000 <= light_duration <= 2200:
            raise RuntimeError(f"cue {index} light duration was {light_duration} ms, expected about 2000 ms")
        if stop_offset > 150:
            raise RuntimeError(f"cue {index} stop request was {stop_offset} ms after pixel-off")
        if not 180 <= dark_gap <= 300:
            raise RuntimeError(f"cue {index} dark gap was {dark_gap} ms, expected at least 180 ms")
        if index + 1 < len(on):
            next_on = on[index + 1][1]
            if forward_delta(next_on, off_at, f"cue {index + 1} onset") < 180:
                raise RuntimeError(f"cue {index + 1} began less than 180 ms after cue {index} turned off")
            forward_delta(next_on, gap_at, f"cue {index + 1} onset after cue {index} dark gap")

    lines = serial.splitlines()
    validate_game_over_timing(lines)
    cue_on_line_indices = [i for i, line in enumerate(lines) if re.match(r"SIM_CUE_ON:\d+:\d+", line)]
    cue_off_line_indices = [i for i, line in enumerate(lines) if re.match(r"SIM_CUE_OFF:\d+:\d+", line)]
    cue_stop_line_indices = [i for i, line in enumerate(lines)
                             if re.match(r"SIM_CUE_STOP_REQUEST:\d+:\d+", line)]
    cue_gap_line_indices = [i for i, line in enumerate(lines)
                            if re.match(r"SIM_CUE_GAP_DONE:\d+:\d+", line)]
    if not all(len(indices) == len(cues) for indices in (
            cue_on_line_indices, cue_off_line_indices,
            cue_stop_line_indices, cue_gap_line_indices)):
        raise RuntimeError("could not pair cue markers with serial transcript lines")
    for index in range(len(cues)):
        if not (cue_on_line_indices[index] < cue_off_line_indices[index] <
                cue_stop_line_indices[index] < cue_gap_line_indices[index]):
            raise RuntimeError(f"cue {index} serial markers are out of order")
        if index + 1 < len(cues) and cue_gap_line_indices[index] >= cue_on_line_indices[index + 1]:
            raise RuntimeError(f"cue {index + 1} began before cue {index}'s dark gap completed")

    cue_groups_before_input = {
        "first-round": (1,),
        "gameover-stale-event": (1, 1),
        "servo-only-after-loss": (1, 2, 3, 4),
        "start-reset": (1, 2, 1, 1),
        "button-remap": (1, 2, 3, 4),
        "chunk-boundary": (11,),
    }[name]
    ready_values = [int(value) & 0xFFFFFFFF for value in
                    re.findall(r"^SIM_INPUT_READY:(\d+)\s*$", serial, re.MULTILINE)]
    ready_line_indices = [i for i, line in enumerate(lines)
                          if re.match(r"SIM_INPUT_READY:\d+", line)]
    if len(ready_values) != len(cue_groups_before_input):
        raise RuntimeError(
            f"expected {len(cue_groups_before_input)} input-ready events, found {len(ready_values)}"
        )
    cue_offset = 0
    for round_index, group_length in enumerate(cue_groups_before_input):
        final_cue = cue_offset + group_length - 1
        if cue_gap_line_indices[final_cue] >= ready_line_indices[round_index]:
            raise RuntimeError(f"input-ready {round_index + 1} preceded completion of its cue group")
        forward_delta(
            ready_values[round_index], gap[final_cue][1],
            f"input-ready {round_index + 1} after final cue gap",
        )
        cue_offset += group_length

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
        wait_before_press = forward_delta(presses[0][1], ready[0], "input-ready/press")
        if wait_before_press < 5000:
            raise RuntimeError("player answer was not accepted after waiting beyond the former 5 s limit")
        if presses[0][0] != plans[0].first or releases[0][0] != plans[0].first:
            raise RuntimeError("first-round input markers do not match the randomized expected color")
        hold_duration = forward_delta(releases[0][1], presses[0][1], "input press/release")
        if hold_duration < 5000:
            raise RuntimeError("pressed answer was not held beyond the former 5 s limit")
        if "INPUT_TIMEOUT" in serial:
            raise RuntimeError("transcript contains the removed player input timeout")
        if "SIM_GAME_OVER_START" in serial:
            raise RuntimeError("first-round answer entered Game Over before successful completion")
        ready_line = next(i for i, line in enumerate(lines)
                          if re.match(r"SIM_INPUT_READY:\d+", line))
        press_line = next(i for i, line in enumerate(lines)
                          if re.match(r"SIM_INPUT_PRESS:\d+:\d+", line))
        release_line = next(i for i, line in enumerate(lines)
                            if re.match(r"SIM_INPUT_RELEASE:\d+:\d+", line))
        if ready_line >= press_line:
            raise RuntimeError("answer press must follow input-ready")
        if press_line >= release_line:
            raise RuntimeError("answer release must follow its press")
        complete_lines = [i for i, line in enumerate(lines)
                          if line.strip() == "SIM_ROUND_COMPLETE"]
        if len(complete_lines) != 1 or complete_lines[0] <= release_line:
            raise RuntimeError("answer must be committed once, only after its debounced release")

    if name == "gameover-stale-event":
        game_over_start = [index for index, _ in timed_event_values(lines, "SIM_GAME_OVER_START")]
        drained_lines = [i for i, line in enumerate(lines)
                         if re.match(r"SIM_GAMEOVER_EVENT_DRAINED:\d+", line)]
        game_over_stop = [index for index, _ in timed_event_values(lines, "SIM_GAME_OVER_STOP")]
        game_starts = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_START"]
        wrong_answers = [i for i, line in enumerate(lines) if line.strip() == "WRONG_ANSWER"]
        wrong_chords = [i for i, line in enumerate(lines) if line.strip() == "WRONG_CHORD"]
        ready_lines = [i for i, line in enumerate(lines)
                       if re.match(r"SIM_INPUT_READY:\d+", line)]
        if not (not wrong_chords and
                len(game_over_start) == len(drained_lines) == len(game_over_stop) == 1 and
                len(game_starts) == 2 and len(wrong_answers) == 1 and len(ready_lines) == 2 and
                game_starts[0] < ready_lines[0] < wrong_answers[0] < game_over_start[0] <
                drained_lines[0] < game_over_stop[0] < game_starts[1] and
                game_starts[1] < ready_lines[1]):
            raise RuntimeError("Game Over completion must follow the wrong answer, drain before stop, and reach input in the next game")
        prior_audio_starts = [i for i, line in enumerate(lines[:game_over_start[0]])
                              if re.match(r"SIM_AUDIO_START:(\d+)", line)]
        if len(prior_audio_starts) < 2:
            raise RuntimeError("Game Over audio start must be present before its state marker")
        game_over_track = int(re.match(r"SIM_AUDIO_START:(\d+)", lines[prior_audio_starts[-1]]).group(1))
        drained_track = int(re.match(r"SIM_GAMEOVER_EVENT_DRAINED:(\d+)", lines[drained_lines[0]]).group(1))
        if drained_track != game_over_track:
            raise RuntimeError("Game Over must drain its own completion event")
        game_over_region = lines[game_over_start[0] + 1:game_over_stop[0]]
        if any(line.startswith("SIM_AUDIO_DONE:") for line in game_over_region):
            raise RuntimeError("Game Over completion must be drained, not accepted as active audio completion")
        extensions = [index for index, _ in timed_event_values(lines, "SIM_SERVO_EXTEND")]
        retract = [index for index, _ in timed_event_values(lines, "SIM_SERVO_RETRACT")]
        retract_done = [index for index, _ in timed_event_values(lines, "SIM_SERVO_RETRACT_DONE")]
        if not (len(extensions) == len(retract) == len(retract_done) == 1 and
                game_over_start[0] < extensions[0] < drained_lines[0] < retract[0] <
                retract_done[0] < game_over_stop[0]):
            raise RuntimeError("Game Over must extend and finish servo return before stopping")

    if name == "chunk-boundary":
        expected = list(plans[0].symbols)
        if len(expected) != 11 or serial.count("SIM_TEST_CHUNK_BOUNDARY") != 1:
            raise RuntimeError("chunk-boundary run must start directly at round 11")
        ready = [int(value) & 0xFFFFFFFF for value in
                 re.findall(r"^SIM_INPUT_READY:(\d+)\s*$", serial, re.MULTILINE)]
        presses = marker_values(serial, "SIM_INPUT_PRESS")
        releases = marker_values(serial, "SIM_INPUT_RELEASE")
        if len(ready) != 1 or len(presses) != 11 or len(releases) != 11:
            raise RuntimeError("round 11 must contain one ready marker and eleven press/release pairs")
        if [symbol for symbol, _ in presses] != expected or [symbol for symbol, _ in releases] != expected:
            raise RuntimeError("round-11 answers do not match the planned eleven-symbol sequence")
        ready_line = next(i for i, line in enumerate(lines) if re.match(r"SIM_INPUT_READY:\d+", line))
        press_lines = [i for i, line in enumerate(lines) if re.match(r"SIM_INPUT_PRESS:\d+:\d+", line)]
        release_lines = [i for i, line in enumerate(lines) if re.match(r"SIM_INPUT_RELEASE:\d+:\d+", line)]
        complete_lines = [i for i, line in enumerate(lines) if line.strip() == "SIM_ROUND_COMPLETE"]
        if not (len(press_lines) == len(release_lines) == 11 and len(complete_lines) == 1 and
                ready_line < press_lines[0]):
            raise RuntimeError("round-11 input must contain eleven ordered pairs after input-ready")
        previous_release_at = ready[0]
        for index, (pressed, released) in enumerate(zip(presses, releases)):
            if not press_lines[index] < release_lines[index]:
                raise RuntimeError(f"round-11 answer {index + 1} release must follow its press")
            if index and release_lines[index - 1] >= press_lines[index]:
                raise RuntimeError(f"round-11 answer {index + 1} began before the previous release")
            forward_delta(pressed[1], previous_release_at, f"round-11 answer {index + 1} press")
            if not 25 <= forward_delta(released[1], pressed[1], f"round-11 answer {index + 1}") < 1000:
                raise RuntimeError(f"round-11 answer {index + 1} was not debounced and released")
            previous_release_at = released[1]
        if complete_lines[0] <= release_lines[-1]:
            raise RuntimeError("round 11 must complete only after the eleventh released answer")
        if "WRONG_ANSWER" in serial or "WRONG_CHORD" in serial or "SIM_GAME_OVER_START" in serial:
            raise RuntimeError("valid round-11 answers unexpectedly entered Game Over")

    if name == "start-reset":
        reset_lines = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_RESET"]
        game_starts = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_START"]
        queued = [i for i, line in enumerate(lines) if line.strip() == "SIM_GAME_RESET_QUEUED"]
        game_over = [index for index, _ in timed_event_values(lines, "SIM_GAME_OVER_START")]
        extensions = [index for index, _ in timed_event_values(lines, "SIM_SERVO_EXTEND")]
        retract = [index for index, _ in timed_event_values(lines, "SIM_SERVO_RETRACT")]
        retract_done = [index for index, _ in timed_event_values(lines, "SIM_SERVO_RETRACT_DONE")]
        game_over_stop = [index for index, _ in timed_event_values(lines, "SIM_GAME_OVER_STOP")]
        wrong_answers = [i for i, line in enumerate(lines) if line.strip() == "WRONG_ANSWER"]
        wrong_chords = [i for i, line in enumerate(lines) if line.strip() == "WRONG_CHORD"]
        ready_lines = [i for i, line in enumerate(lines)
                       if re.match(r"SIM_INPUT_READY:\d+", line)]
        round_completions = [i for i, line in enumerate(lines) if line.strip() == "SIM_ROUND_COMPLETE"]
        if not (not wrong_chords and
                len(reset_lines) == 2 and len(game_starts) == 3 and len(queued) == 1 and
                len(wrong_answers) == 1 and len(ready_lines) == 4 and len(round_completions) == 1 and
                len(game_over) == len(extensions) == len(retract) == len(retract_done) ==
                len(game_over_stop) == 1 and
                game_starts[0] < ready_lines[0] < round_completions[0] < ready_lines[1] <
                reset_lines[0] < game_starts[1] < ready_lines[2] < wrong_answers[0] <
                game_over[0] < extensions[0] < queued[0] < retract[0] < retract_done[0] <
                game_over_stop[0] < reset_lines[1] < game_starts[2] < ready_lines[3]):
            raise RuntimeError("Start must reset after a completed round and defer a queued reset until the wrong-answer loss and servo return finish")

        score_states = []
        for index, line in enumerate(lines):
            match = re.match(r"SIM_SCORE_STATE:(\d+):(\d+)$", line)
            if match is not None:
                score_states.append((index, int(match.group(1)), int(match.group(2))))
        if len(score_states) != 4:
            raise RuntimeError(f"start-reset must report four score states, found {len(score_states)}")
        initial_score, completed_score, reset_score, queued_reset_score = score_states
        if not (initial_score[1] == 0 and completed_score[1] == 1 and
                reset_score[1] == queued_reset_score[1] == 0 and
                completed_score[2] >= 1 and completed_score[2] >= initial_score[2] and
                reset_score[2] == completed_score[2] and
                queued_reset_score[2] == reset_score[2] and
                game_starts[0] < initial_score[0] < ready_lines[0] <
                completed_score[0] < round_completions[0] <
                reset_lines[0] < game_starts[1] < reset_score[0] < ready_lines[2] and
                reset_lines[1] < game_starts[2] < queued_reset_score[0] < ready_lines[3]):
            raise RuntimeError(
                "start-reset score telemetry must show a completed round, reset current score to zero, "
                "and preserve best score across both restarts"
            )

    if name == "servo-only-after-loss":
        rounds = [i for i, line in enumerate(lines) if line.strip() == "SIM_ROUND_COMPLETE"]
        game_over = [index for index, _ in timed_event_values(lines, "SIM_GAME_OVER_START")]
        extensions = [index for index, _ in timed_event_values(lines, "SIM_SERVO_EXTEND")]
        retract = [index for index, _ in timed_event_values(lines, "SIM_SERVO_RETRACT")]
        retract_done = [index for index, _ in timed_event_values(lines, "SIM_SERVO_RETRACT_DONE")]
        game_over_stop = [index for index, _ in timed_event_values(lines, "SIM_GAME_OVER_STOP")]
        wrong_answers = [i for i, line in enumerate(lines) if line.strip() == "WRONG_ANSWER"]
        wrong_chords = [i for i, line in enumerate(lines) if line.strip() == "WRONG_CHORD"]
        ready_lines = [i for i, line in enumerate(lines)
                       if re.match(r"SIM_INPUT_READY:\d+", line)]
        if not (not wrong_chords and
                len(rounds) == 3 and len(ready_lines) == 4 and len(wrong_answers) == 1 and
                len(game_over) == len(extensions) == len(retract) ==
                len(retract_done) == len(game_over_stop) == 1 and
                rounds[-1] < ready_lines[3] < wrong_answers[0] < game_over[0] <
                extensions[0] < retract[0] < retract_done[0] < game_over_stop[0]):
            raise RuntimeError("servo must stay still for three successful rounds and return only after a wrong answer")

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
        previous_release_at = None
        input_offset = 0
        for round_index, round_length in enumerate(range(1, 5)):
            ready_at = ready[round_index]
            for _ in range(round_length):
                button_input = button_inputs[input_offset]
                press = presses[input_offset]
                release = releases[input_offset]
                position, color, button_at = button_input
                if press != (color, button_at) or release[0] != color:
                    raise RuntimeError("button position, mapped color, and input markers disagree")
                forward_delta(button_at, ready_at, f"button {position + 1} input after readiness")
                if previous_release_at is not None:
                    forward_delta(button_at, previous_release_at, f"button {position + 1} input chronology")
                if forward_delta(release[1], press[1], f"button {position + 1} press/release") < 25:
                    raise RuntimeError(f"button {position + 1} input was released before the debounce interval")
                previous_release_at = release[1]
                input_offset += 1
        map_lines = [i for i, line in enumerate(lines) if line.startswith("SIM_BUTTON_MAP:")]
        round_completions = [i for i, line in enumerate(lines) if line.strip() == "SIM_ROUND_COMPLETE"]
        ready_lines = [i for i, line in enumerate(lines)
                       if re.match(r"SIM_INPUT_READY:\d+", line)]
        button_input_lines = [i for i, line in enumerate(lines)
                              if re.match(r"SIM_BUTTON_INPUT:[0-3]:[0-3]:\d+", line)]
        press_lines = [i for i, line in enumerate(lines)
                       if re.match(r"SIM_INPUT_PRESS:[0-3]:\d+", line)]
        release_lines = [i for i, line in enumerate(lines)
                         if re.match(r"SIM_INPUT_RELEASE:[0-3]:\d+", line)]
        input_offset = 0
        cue_group_offset = 0
        for round_index, round_length in enumerate(range(1, 5)):
            final_release_line = None
            if ready_lines[round_index] >= button_input_lines[input_offset]:
                raise RuntimeError(f"input-ready {round_index + 1} must precede its mapped button inputs")
            for answer_index in range(round_length):
                event_index = input_offset + answer_index
                if not (button_input_lines[event_index] < press_lines[event_index] <
                        release_lines[event_index]):
                    raise RuntimeError(f"mapped button input {event_index + 1} markers are out of order")
                if answer_index and release_lines[event_index - 1] >= button_input_lines[event_index]:
                    raise RuntimeError(f"mapped button input {event_index + 1} began before the prior release")
                final_release_line = release_lines[event_index]
            if final_release_line is None or final_release_line >= round_completions[round_index]:
                raise RuntimeError(f"round {round_index + 1} completed before its mapped answers were released")
            if round_index < 3:
                next_round_cue = cue_group_offset + round_length
                if not (round_completions[round_index] < cue_on_line_indices[next_round_cue]):
                    raise RuntimeError(
                        f"round {round_index + 2} cue began before round {round_index + 1} completed"
                    )
                forward_delta(
                    on[next_round_cue][1], releases[input_offset + round_length - 1][1],
                    f"round {round_index + 2} cue after round {round_index + 1} final answer",
                )
            input_offset += round_length
            cue_group_offset += round_length
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
        demo_duration = 0
        if len(demo_starts) == len(demo_ends) == 1:
            demo_duration = forward_delta(
                demo_ends[0][1], demo_starts[0][1], "button-map demo"
            )
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
        round_four_first_cue = sum(cue_groups_before_input[:3])
        if demo_end_lines[0] >= cue_on_line_indices[round_four_first_cue]:
            raise RuntimeError("round 4 cue began before the round-3 map demo ended")
        forward_delta(
            on[round_four_first_cue][1], demo_ends[0][1],
            "round 4 cue after round-3 map demo",
        )


def display_color(color: int | None) -> str:
    return "none" if color is None else f"{COLORS[color]}({color})"


def format_replay_command(name: str, seed: int, previous: int | None) -> str:
    previous_argument = "none" if previous is None else str(previous)
    script_path = shlex.quote((ROOT / "scripts" / "run-wokwi-tests.py").as_posix())
    return (
        f"python3 {script_path} --scenario {name} --seed 0x{seed:08X} "
        f"--previous-first-color {previous_argument} --no-persist"
    )


def run_one(name: str, seed: int, previous: int | None, state_path: Path,
            persist: bool, output_root: Path) -> tuple[bool, int | None]:
    plans = make_game_plans(name, seed, previous)
    cues = expected_cues(name, plans)
    print(
        f"WOKWI_TEST scenario={name} seed=0x{seed:08X} previous_first={display_color(previous)} "
        f"expected_first={[display_color(plan.first) for plan in plans]} expected_cues={cues}",
        flush=True,
    )
    replay_command = format_replay_command(name, seed, previous)
    print(f"REPLAY: {replay_command}", flush=True)

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
        "expected_cues": cues,
        "mock_completion_delay_ms": MOCK_DELAY_MS[name],
        "replay_command": replay_command,
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
    firmware_elf = scenario_firmware_dir(name, seed, previous) / "alien-simon-says.ino.elf"
    command = [
        cli, ".",
        "--elf", str(firmware_elf),
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
