#!/usr/bin/env python3
"""Validate the exact Wokwi breadboard wiring, placements, and safe topology."""

import json
import pathlib
import re
import unittest
from collections import defaultdict, deque


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUTTONS = {
    "button-red": ("6", 6, 4, "bn.3", "black"),
    "button-green": ("7", 12, 10, "bn.4", "black"),
    "button-blue": ("8", 18, 16, "bn.5", "black"),
    "button-yellow": ("A0", 24, 22, "bn.6", "black"),
    "button-start": ("A1", 30, 28, "bn.7", "gray"),
}
GROUND_BUS_ROWS = (4, 10, 16, 22, 28)

def connection(left, right, color="", attrs=()):
    return (left, right, color, tuple(attrs))


WIRE_COLORS = {
    ("uno:5V", "bb1:tp.1"): "#FF0000",
    ("bb1:tp.2", "lcd:VCC"): "#FF0000",
    ("bb1:tp.3", "dfplayer-mock:VCC"): "#FF0000",
    ("uno:GND.1", "bb1:bn.1"): "#000000",
    ("bb1:bn.29", "lcd:GND"): "#000000",
    ("bb1:bn.30", "dfplayer-mock:GND"): "#000000",
    ("bb2:tp.30", "barrel-jack-breakout:VCC"): "#008B8B",
    ("bb2:bn.30", "barrel-jack-breakout:GND"): "#000000",
    ("bb1:bn.2", "bb2:bn.2"): "#000000",
    ("uno:A4", "bb1:2t.a"): "#00FFFF",
    ("bb1:2t.b", "lcd:SDA"): "#00FFFF",
    ("uno:A5", "bb1:3t.a"): "#FF00FF",
    ("bb1:3t.b", "lcd:SCL"): "#FF00FF",
    ("dfplayer-mock:TX", "bb1:5t.a"): "#800080",
    ("bb1:5t.b", "uno:10"): "#800080",
    ("uno:9", "servo-visual-only:PWM"): "#FFA500",
    ("dfplayer-mock:SPK1", "bb1:11t.a"): "#A52A2A",
    ("bb1:11t.b", "visual-speaker:SPK1"): "#A52A2A",
    ("dfplayer-mock:SPK2", "bb1:13t.a"): "#D2B48C",
    ("bb1:13t.b", "visual-speaker:SPK2"): "#D2B48C",
    ("uno:11", "bb1:1t.a"): "#808080",
    ("bb1:1b.g", "dfplayer-mock:RX"): "#808080",
    ("uno:2", "neopixel-red:DIN"): "#FFFFFF",
    ("uno:3", "neopixel-green:DIN"): "#FFFFFF",
    ("uno:4", "neopixel-blue:DIN"): "#FFFFFF",
    ("uno:5", "neopixel-yellow:DIN"): "#FFFFFF",
    ("bb2:tp.25", "neopixel-red:VDD"): "#FF0000",
    ("bb2:bn.25", "neopixel-red:VSS"): "#000000",
    ("bb2:tp.27", "neopixel-green:VDD"): "#FF0000",
    ("bb2:bn.27", "neopixel-green:VSS"): "#000000",
    ("bb2:tp.28", "neopixel-blue:VDD"): "#FF0000",
    ("bb2:bn.28", "neopixel-blue:VSS"): "#000000",
    ("bb2:tp.29", "neopixel-yellow:VDD"): "#FF0000",
    ("bb2:bn.29", "neopixel-yellow:VSS"): "#000000",
    ("bb2:tp.26", "servo-visual-only:V+"): "#FF0000",
    ("bb2:bn.26", "servo-visual-only:GND"): "#000000",
    ("uno:6", "bb1:6t.a"): "#FF0000",
    ("bb1:4b.j", "bb1:bn.3"): "#000000",
    ("uno:7", "bb1:12t.a"): "#00FF00",
    ("uno:8", "bb1:18t.a"): "#0000FF",
    ("bb1:10b.j", "bb1:bn.4"): "#000000",
    ("uno:A0", "bb1:24t.a"): "#FFFF00",
    ("uno:A1", "bb1:30t.a"): "#FFFFFF",
    ("bb1:16b.j", "bb1:bn.5"): "#000000",
    ("bb1:22b.j", "bb1:bn.6"): "#000000",
    ("bb1:28b.j", "bb1:bn.7"): "#000000",
}


def visible_connection(left, right):
    return connection(left, right, WIRE_COLORS[(left, right)])


STRIP_DATA_LINKS = (
    ("uno:2", "neopixel-red:DIN"),
    ("uno:3", "neopixel-green:DIN"),
    ("uno:4", "neopixel-blue:DIN"),
    ("uno:5", "neopixel-yellow:DIN"),
)
SERVO_PWM_ROUTE = ("uno:9", "servo-visual-only:PWM")

STRIP_POWER_LINKS = (
    ("bb2:tp.25", "neopixel-red:VDD"),
    ("bb2:bn.25", "neopixel-red:VSS"),
    ("bb2:tp.26", "servo-visual-only:V+"),
    ("bb2:bn.26", "servo-visual-only:GND"),
    ("bb2:tp.27", "neopixel-green:VDD"),
    ("bb2:bn.27", "neopixel-green:VSS"),
    ("bb2:tp.28", "neopixel-blue:VDD"),
    ("bb2:bn.28", "neopixel-blue:VSS"),
    ("bb2:tp.29", "neopixel-yellow:VDD"),
    ("bb2:bn.29", "neopixel-yellow:VSS"),
)
EXPECTED_STRIP_CONNECTIONS = {
    visible_connection(source, destination)
    for source, destination in STRIP_DATA_LINKS
}
EXPECTED_STRIP_CONNECTIONS.update(
    visible_connection(left, right)
    for left, right in STRIP_POWER_LINKS
    if right.startswith("neopixel-")
)


EXPECTED_CONNECTIONS = {
    visible_connection("uno:5V", "bb1:tp.1"),
    visible_connection("bb1:tp.2", "lcd:VCC"),
    visible_connection("bb1:tp.3", "dfplayer-mock:VCC"),
    visible_connection("uno:GND.1", "bb1:bn.1"),
    visible_connection("bb1:bn.29", "lcd:GND"),
    visible_connection("bb1:bn.30", "dfplayer-mock:GND"),
    visible_connection("bb2:tp.30", "barrel-jack-breakout:VCC"),
    visible_connection("bb2:bn.30", "barrel-jack-breakout:GND"),
    visible_connection("bb1:bn.2", "bb2:bn.2"),
    visible_connection("uno:A4", "bb1:2t.a"),
    visible_connection("bb1:2t.b", "lcd:SDA"),
    visible_connection("uno:A5", "bb1:3t.a"),
    visible_connection("bb1:3t.b", "lcd:SCL"),
    visible_connection("dfplayer-mock:TX", "bb1:5t.a"),
    visible_connection("bb1:5t.b", "uno:10"),
    visible_connection("uno:9", "servo-visual-only:PWM"),
    visible_connection("dfplayer-mock:SPK1", "bb1:11t.a"),
    visible_connection("bb1:11t.b", "visual-speaker:SPK1"),
    visible_connection("dfplayer-mock:SPK2", "bb1:13t.a"),
    visible_connection("bb1:13t.b", "visual-speaker:SPK2"),
    visible_connection("uno:11", "bb1:1t.a"),
    connection("mp3-tx-resistor:1", "bb1:1t.b", attrs=("$bb",)),
    connection("mp3-tx-resistor:2", "bb1:1b.f", attrs=("$bb",)),
    visible_connection("bb1:1b.g", "dfplayer-mock:RX"),
    visible_connection("uno:2", "neopixel-red:DIN"),
    visible_connection("uno:3", "neopixel-green:DIN"),
    visible_connection("uno:4", "neopixel-blue:DIN"),
    visible_connection("uno:5", "neopixel-yellow:DIN"),
}
EXPECTED_CONNECTIONS.update(
    visible_connection(left, right) for left, right in STRIP_POWER_LINKS
)

for row, rail_index in zip(GROUND_BUS_ROWS, range(3, 8)):
    EXPECTED_CONNECTIONS.add(
        visible_connection(f"bb1:{row}b.j", f"bb1:bn.{rail_index}")
    )

for button_id, (gpio, contact1, contact2, _ground_rail, _color) in BUTTONS.items():
    EXPECTED_CONNECTIONS.add(
        visible_connection(f"uno:{gpio}", f"bb1:{contact1}t.a")
    )
    if button_id == "button-start":
        mounted_pins = (("1.l", contact1, "t", "e"), ("2.r", contact2, "b", "f"))
    else:
        mounted_pins = (
            ("1.l", contact1, "t", "e"),
            ("1.r", contact1, "b", "f"),
            ("2.l", contact2, "t", "e"),
            ("2.r", contact2, "b", "f"),
        )
    EXPECTED_CONNECTIONS.update(
        connection(f"{button_id}:{pin}", f"bb1:{row}{section}.{hole}", attrs=("$bb",))
        for pin, row, section, hole in mounted_pins
    )

def wire_graph(connections):
    """Return wires plus breadboard tie-strip/rail continuity, not component internals."""
    graph = defaultdict(set)
    for left, right, *_ in connections:
        graph[left].add(right)
        graph[right].add(left)

    tiepoint_groups = defaultdict(list)
    rail_groups = defaultdict(list)
    for endpoint in graph:
        tiepoint = re.fullmatch(r"bb(\d+):(\d+)([tb])\.([a-j])", endpoint)
        rail = re.fullmatch(r"bb(\d+):([tb])([pn])\.(\d+)", endpoint)
        if tiepoint:
            board, number, section, hole = tiepoint.groups()
            if (section == "t" and hole in "abcde") or (section == "b" and hole in "fghij"):
                tiepoint_groups[(board, number, section)].append(endpoint)
        elif rail:
            board, section, polarity, _number = rail.groups()
            rail_groups[(board, section, polarity)].append(endpoint)
    for endpoints in (*tiepoint_groups.values(), *rail_groups.values()):
        for endpoint in endpoints[1:]:
            graph[endpoints[0]].add(endpoint)
            graph[endpoint].add(endpoints[0])
    return graph


def connect_graph(graph, left, right):
    graph[left].add(right)
    graph[right].add(left)


def button_state_graph(connections, button_ids, pressed_button=None):
    """Add permanent switch contact pairs and optionally press one button."""
    graph = wire_graph(connections)
    for button_id in button_ids:
        connect_graph(graph, f"{button_id}:1.l", f"{button_id}:1.r")
        connect_graph(graph, f"{button_id}:2.l", f"{button_id}:2.r")
        if button_id == pressed_button:
            connect_graph(graph, f"{button_id}:1.l", f"{button_id}:2.l")
    return graph


def reachable(graph, start, target):
    queue = deque([start])
    visited = {start}
    while queue:
        node = queue.popleft()
        if node == target:
            return True
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return False


class DiagramBreadboardNetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "diagram.json").open(encoding="utf-8") as diagram_file:
            cls.diagram = json.load(diagram_file)
        cls.parts = {part["id"]: part for part in cls.diagram["parts"]}
        cls.connections = cls.diagram["connections"]
        cls.connection_tuples = [
            tuple(item[:3]) + (tuple(item[3]),) for item in cls.connections
        ]
        cls.graph = wire_graph(cls.connections)

    def test_exact_netlist_and_only_expected_component_bypasses(self):
        self.assertEqual(len(self.connection_tuples), 66)
        self.assertEqual(sum(bool(item[2]) for item in self.connection_tuples), 46)
        self.assertEqual(sum(item[3] == ("$bb",) for item in self.connection_tuples), 20)
        self.assertEqual(len(self.connection_tuples), len(set(self.connection_tuples)))
        self.assertEqual(set(self.connection_tuples), EXPECTED_CONNECTIONS)
        self.assertEqual(
            {
                item for item in self.connection_tuples
                if any(endpoint.startswith("neopixel-") for endpoint in item[:2])
            },
            EXPECTED_STRIP_CONNECTIONS,
        )
        self.assertEqual(len(EXPECTED_STRIP_CONNECTIONS), 12)
        for source, destination in (*STRIP_DATA_LINKS, SERVO_PWM_ROUTE):
            with self.subTest(data_link=(source, destination)):
                self.assertIn(visible_connection(source, destination), self.connection_tuples)
        for left, right in STRIP_POWER_LINKS:
            with self.subTest(power_link=(left, right)):
                self.assertIn(visible_connection(left, right), self.connection_tuples)
        direct_component_wires = {
            *(visible_connection(source, destination) for source, destination in STRIP_DATA_LINKS),
            visible_connection(*SERVO_PWM_ROUTE),
            visible_connection("bb2:tp.30", "barrel-jack-breakout:VCC"),
            visible_connection("bb2:bn.30", "barrel-jack-breakout:GND"),
            visible_connection("bb1:bn.2", "bb2:bn.2"),
        }
        for left, right, color, _attrs in self.connection_tuples:
            board_mediated = left.startswith(("bb1:", "bb2:")) or right.startswith(("bb1:", "bb2:"))
            self.assertTrue(
                board_mediated or connection(left, right, color) in direct_component_wires,
                f"unexpected component-to-component bypass: {left} -> {right}",
            )
        self.assertTrue(all(isinstance(item[3], list) for item in self.connections))
        self.assertFalse(any(item[3] == "$bb" for item in self.connections))
        endpoint_counts = defaultdict(int)
        for left, right, _color, _attrs in self.connection_tuples:
            endpoint_counts[left] += 1
            endpoint_counts[right] += 1
        for endpoint, count in endpoint_counts.items():
            if endpoint.startswith(("bb1:", "bb2:")):
                self.assertLessEqual(count, 1, f"breadboard hole/rail {endpoint} has multiple wires")
            elif endpoint.split(":", 1)[0] in self.parts:
                self.assertLessEqual(count, 1, f"component pin {endpoint} has multiple wires")

    def test_visible_wire_colors_follow_electrical_function(self):
        self.assertEqual(len(WIRE_COLORS), 46)
        visible = {
            (left, right): color
            for left, right, color, _attrs in self.connection_tuples
            if color
        }

        def assert_color(expected, *endpoints):
            for endpoint in endpoints:
                with self.subTest(endpoint=endpoint):
                    self.assertEqual(visible[endpoint], expected)

        assert_color(
            "#FF0000",
            ("uno:5V", "bb1:tp.1"),
            ("bb1:tp.2", "lcd:VCC"),
            ("bb1:tp.3", "dfplayer-mock:VCC"),
            ("bb2:tp.25", "neopixel-red:VDD"),
            ("bb2:tp.27", "neopixel-green:VDD"),
            ("bb2:tp.28", "neopixel-blue:VDD"),
            ("bb2:tp.29", "neopixel-yellow:VDD"),
            ("bb2:tp.26", "servo-visual-only:V+"),
        )
        assert_color("#008B8B", ("bb2:tp.30", "barrel-jack-breakout:VCC"))
        assert_color(
            "#000000",
            ("uno:GND.1", "bb1:bn.1"),
            ("bb1:bn.29", "lcd:GND"),
            ("bb1:bn.30", "dfplayer-mock:GND"),
            ("bb2:bn.30", "barrel-jack-breakout:GND"),
            ("bb2:bn.25", "neopixel-red:VSS"),
            ("bb2:bn.27", "neopixel-green:VSS"),
            ("bb2:bn.28", "neopixel-blue:VSS"),
            ("bb2:bn.29", "neopixel-yellow:VSS"),
            ("bb2:bn.26", "servo-visual-only:GND"),
            ("bb1:bn.2", "bb2:bn.2"),
            ("bb1:4b.j", "bb1:bn.3"),
            ("bb1:10b.j", "bb1:bn.4"),
            ("bb1:16b.j", "bb1:bn.5"),
            ("bb1:22b.j", "bb1:bn.6"),
            ("bb1:28b.j", "bb1:bn.7"),
        )
        assert_color(
            "#FFFFFF",
            ("uno:2", "neopixel-red:DIN"),
            ("uno:3", "neopixel-green:DIN"),
            ("uno:4", "neopixel-blue:DIN"),
            ("uno:5", "neopixel-yellow:DIN"),
            ("uno:A1", "bb1:30t.a"),
        )
        assert_color(
            "#00FFFF",
            ("uno:A4", "bb1:2t.a"),
            ("bb1:2t.b", "lcd:SDA"),
        )
        assert_color(
            "#FF00FF",
            ("uno:A5", "bb1:3t.a"),
            ("bb1:3t.b", "lcd:SCL"),
        )
        assert_color(
            "#800080",
            ("dfplayer-mock:TX", "bb1:5t.a"),
            ("bb1:5t.b", "uno:10"),
        )
        assert_color(
            "#808080",
            ("uno:11", "bb1:1t.a"),
            ("bb1:1b.g", "dfplayer-mock:RX"),
        )
        assert_color(
            "#FFA500",
            ("uno:9", "servo-visual-only:PWM"),
        )
        assert_color(
            "#A52A2A",
            ("dfplayer-mock:SPK1", "bb1:11t.a"),
            ("bb1:11t.b", "visual-speaker:SPK1"),
        )
        assert_color(
            "#D2B48C",
            ("dfplayer-mock:SPK2", "bb1:13t.a"),
            ("bb1:13t.b", "visual-speaker:SPK2"),
        )
        assert_color("#FF0000", ("uno:6", "bb1:6t.a"))
        assert_color("#00FF00", ("uno:7", "bb1:12t.a"))
        assert_color("#0000FF", ("uno:8", "bb1:18t.a"))
        assert_color("#FFFF00", ("uno:A0", "bb1:24t.a"))


    def test_all_board_mounted_components_use_exact_editor_pin_holes(self):
        for button_id, (_gpio, contact1, contact2, _rail, color) in BUTTONS.items():
            self.assertEqual(self.parts[button_id]["type"], "wokwi-pushbutton-6mm")
            self.assertEqual(self.parts[button_id]["attrs"]["color"], color)
            if button_id == "button-start":
                mounted_pins = (("1.l", contact1, "t", "e"), ("2.r", contact2, "b", "f"))
                unused_pins = ("1.r", "2.l")
            else:
                mounted_pins = (
                    ("1.l", contact1, "t", "e"),
                    ("1.r", contact1, "b", "f"),
                    ("2.l", contact2, "t", "e"),
                    ("2.r", contact2, "b", "f"),
                )
                unused_pins = ()
            for pin, row, section, hole in mounted_pins:
                self.assertIn(
                    connection(f"{button_id}:{pin}", f"bb1:{row}{section}.{hole}", attrs=("$bb",)),
                    self.connection_tuples,
                )
            for pin in unused_pins:
                self.assertFalse(
                    any(item[0] == f"{button_id}:{pin}" or item[1] == f"{button_id}:{pin}"
                        for item in self.connection_tuples),
                    f"unused Start symbol pin {pin} must not be routed",
                )
        for strip_id in ("neopixel-red", "neopixel-green", "neopixel-blue", "neopixel-yellow"):
            with self.subTest(strip=strip_id):
                strip = self.parts[strip_id]
                self.assertEqual(strip["type"], "wokwi-led-strip")
                self.assertEqual(strip["attrs"]["pixels"], "4")
                self.assertEqual(strip["attrs"]["pixelSize"], "2020")
                self.assertEqual(strip["rotate"], 225)
        self.assertEqual(self.parts["mp3-tx-resistor"]["attrs"]["value"], "1000")
        self.assertEqual(self.parts["lcd"]["type"], "chip-grove-jhd1804")
        self.assertEqual(self.parts["dfplayer-mock"]["type"], "chip-dfplayer-mock")
        self.assertEqual(self.parts["visual-speaker"]["type"], "chip-visual-speaker")
        self.assertNotIn("external-supply", self.parts)
        self.assertEqual(self.parts["barrel-jack-breakout"]["type"], "chip-barrel-jack-breakout")
        self.assertEqual(self.parts["servo-visual-only"]["type"], "wokwi-servo")

    def test_buttons_keep_released_gpio_and_ground_contacts_separate(self):
        gpio_pins = [details[0] for details in BUTTONS.values()]
        self.assertEqual(len(gpio_pins), len(set(gpio_pins)))
        released_graph = button_state_graph(self.connections, BUTTONS)
        for button_id, (gpio, _contact1, _contact2, ground_rail, _color) in BUTTONS.items():
            with self.subTest(button=button_id):
                pressed_graph = button_state_graph(
                    self.connections, BUTTONS, pressed_button=button_id
                )
                contact1_left = f"{button_id}:1.l"
                contact1_right = f"{button_id}:1.r"
                contact2_left = f"{button_id}:2.l"
                contact2_right = f"{button_id}:2.r"
                gpio_node = f"uno:{gpio}"
                ground_node = f"bb1:{ground_rail}"

                # Each permanent contact pair is joined in both switch states.
                self.assertTrue(reachable(released_graph, contact1_left, contact1_right))
                self.assertTrue(reachable(released_graph, contact2_left, contact2_right))
                self.assertTrue(reachable(released_graph, gpio_node, contact1_left))
                self.assertTrue(reachable(released_graph, contact2_right, ground_node))
                self.assertFalse(
                    reachable(released_graph, gpio_node, ground_node),
                    "released pushbuttons must keep GPIO isolated from GND",
                )
                self.assertFalse(reachable(released_graph, contact1_left, contact2_left))

                # Pressing bridges the two contacts, completing GPIO-to-GND.
                self.assertTrue(reachable(pressed_graph, gpio_node, ground_node))
                for other_gpio, *_ in BUTTONS.values():
                    if other_gpio != gpio:
                        self.assertFalse(reachable(released_graph, gpio_node, f"uno:{other_gpio}"))


    def test_barrel_breakout_supply_pins_connect_directly_to_bb2(self):
        breakout = json.loads((ROOT / "chips" / "barrel-jack-breakout.chip.json").read_text(encoding="utf-8"))
        self.assertEqual(breakout["pins"], ["VCC", "GND"])
        expected_supply_links = (
            ("bb2:tp.30", "barrel-jack-breakout:VCC"),
            ("bb2:bn.30", "barrel-jack-breakout:GND"),
        )
        for left, right in expected_supply_links:
            with self.subTest(terminal=left):
                self.assertIn(visible_connection(left, right), self.connection_tuples)
                for endpoint in (left, right):
                    self.assertEqual(
                        sum(endpoint in item[:2] for item in self.connection_tuples),
                        1,
                    )

    def test_neopixel_and_servo_signals_stay_direct_and_power_reaches_loads(self):
        strip_ids = tuple(f"neopixel-{color}" for color in ("red", "green", "blue", "yellow"))
        for source, destination in (*STRIP_DATA_LINKS, SERVO_PWM_ROUTE):
            with self.subTest(signal=(source, destination)):
                self.assertIn(visible_connection(source, destination), self.connection_tuples)
                self.assertTrue(reachable(self.graph, source, destination))
                if destination.endswith(":DIN"):
                    self.assertFalse(any(
                        reachable(self.graph, source, f"{other_id}:DIN")
                        for other_id in strip_ids if f"{other_id}:DIN" != destination
                    ))
        self.assertFalse(
            any(endpoint.endswith(":DOUT") for item in self.connection_tuples for endpoint in item[:2]),
            "independent strip outputs must not have any DOUT-to-DIN chaining wires",
        )

        power_graph = wire_graph(self.connections)
        positive_endpoints = (
            "barrel-jack-breakout:VCC",
            "bb2:tp.30",
            *(f"bb2:tp.{index}" for index in range(25, 30)),
            "neopixel-red:VDD",
            "servo-visual-only:V+",
            "neopixel-green:VDD",
            "neopixel-blue:VDD",
            "neopixel-yellow:VDD",
        )
        negative_endpoints = (
            "barrel-jack-breakout:GND",
            "bb2:bn.30",
            *(f"bb2:bn.{index}" for index in range(25, 30)),
            "neopixel-red:VSS",
            "servo-visual-only:GND",
            "neopixel-green:VSS",
            "neopixel-blue:VSS",
            "neopixel-yellow:VSS",
            "bb2:bn.2",
            "bb1:bn.2",
            "uno:GND.1",
        )
        for endpoint in positive_endpoints:
            with self.subTest(positive_endpoint=endpoint):
                self.assertTrue(reachable(power_graph, "barrel-jack-breakout:VCC", endpoint))
                self.assertFalse(reachable(power_graph, endpoint, "uno:5V"))
                self.assertFalse(reachable(power_graph, "barrel-jack-breakout:GND", endpoint))
        for endpoint in negative_endpoints:
            with self.subTest(negative_endpoint=endpoint):
                self.assertTrue(reachable(power_graph, "barrel-jack-breakout:GND", endpoint))
                self.assertFalse(reachable(power_graph, "barrel-jack-breakout:VCC", endpoint))
        self.assertEqual(
            sum(item[:2] == ("bb1:bn.2", "bb2:bn.2") for item in self.connection_tuples),
            1,
        )
 

    def test_d11_1k_resistor_separates_uno_tx_from_mock_rx(self):
        self.assertTrue(reachable(self.graph, "uno:11", "mp3-tx-resistor:1"))
        self.assertTrue(reachable(self.graph, "mp3-tx-resistor:2", "dfplayer-mock:RX"))
        self.assertFalse(reachable(self.graph, "uno:11", "mp3-tx-resistor:2"))
        self.assertIn(
            connection("mp3-tx-resistor:1", "bb1:1t.b", attrs=("$bb",)),
            EXPECTED_CONNECTIONS,
        )
        self.assertIn(
            connection("mp3-tx-resistor:2", "bb1:1b.f", attrs=("$bb",)),
            EXPECTED_CONNECTIONS,
        )

    def test_shared_power_rails_returns_and_isolated_speaker_rows(self):
        for device in ("lcd", "dfplayer-mock"):
            self.assertTrue(reachable(self.graph, "uno:5V", f"{device}:VCC"))
            self.assertTrue(reachable(self.graph, "uno:GND.1", f"{device}:GND"))
        for _, (_gpio, _c1, _c2, ground_rail, _color) in BUTTONS.items():
            self.assertTrue(reachable(self.graph, "uno:GND.1", f"bb1:{ground_rail}"))
        self.assertFalse(reachable(self.graph, "uno:5V", "uno:GND.1"))
        self.assertTrue(reachable(self.graph, "dfplayer-mock:SPK1", "visual-speaker:SPK1"))
        self.assertTrue(reachable(self.graph, "dfplayer-mock:SPK2", "visual-speaker:SPK2"))
        self.assertFalse(reachable(self.graph, "dfplayer-mock:SPK1", "dfplayer-mock:SPK2"))
        self.assertFalse(reachable(self.graph, "dfplayer-mock:SPK1", "uno:GND.1"))
        self.assertFalse(reachable(self.graph, "dfplayer-mock:SPK2", "uno:GND.1"))

    def test_bb2_is_only_external_load_distribution_and_common_ground(self):
        expected_connections = {
            visible_connection("bb2:tp.30", "barrel-jack-breakout:VCC"),
            visible_connection("bb2:bn.30", "barrel-jack-breakout:GND"),
            visible_connection("bb1:bn.2", "bb2:bn.2"),
            *(visible_connection(left, right) for left, right in STRIP_POWER_LINKS),
        }
        actual_connections = {
            item for item in self.connection_tuples
            if any(endpoint.startswith("bb2:") for endpoint in item[:2])
        }
        self.assertEqual(actual_connections, expected_connections)
        for load in ("neopixel-red", "neopixel-green", "neopixel-blue", "neopixel-yellow"):
            self.assertTrue(reachable(self.graph, "barrel-jack-breakout:VCC", f"{load}:VDD"))
            self.assertTrue(reachable(self.graph, "barrel-jack-breakout:GND", f"{load}:VSS"))
        self.assertTrue(reachable(self.graph, "barrel-jack-breakout:VCC", "servo-visual-only:V+"))
        self.assertTrue(reachable(self.graph, "barrel-jack-breakout:GND", "servo-visual-only:GND"))
        self.assertTrue(reachable(self.graph, "uno:GND.1", "barrel-jack-breakout:GND"))
        self.assertFalse(reachable(self.graph, "uno:5V", "barrel-jack-breakout:VCC"))
        self.assertFalse(reachable(self.graph, "barrel-jack-breakout:VCC", "barrel-jack-breakout:GND"))

    def test_breadboard_endpoints_stay_inside_supported_hole_and_rail_ranges(self):
        boards = [part for part in self.diagram["parts"] if part["type"] == "wokwi-breadboard-half"]
        self.assertEqual(len(boards), 2)
        self.assertEqual([board["id"] for board in boards], ["bb1", "bb2"])
        for board in boards:
            self.assertEqual(board["attrs"], {})
            self.assertNotIn("$bb", json.dumps(board))
        for endpoint in self.graph:
            if not endpoint.startswith(("bb1:", "bb2:")):
                continue
            row = re.fullmatch(r"(bb\d+):(\d+)([tb])\.([a-j])", endpoint)
            rail = re.fullmatch(r"(bb\d+):([tb])([pn])\.(\d+)", endpoint)
            self.assertTrue(row or rail, f"unsupported breadboard endpoint {endpoint}")
            if row:
                board, number, section, hole = row.groups()
                self.assertIn(board, ("bb1", "bb2"))
                self.assertIn(int(number), range(1, 31))
                self.assertIn(hole, "abcde" if section == "t" else "fghij")
            else:
                board, section, polarity, number = rail.groups()
                self.assertIn(board, ("bb1", "bb2"))
                self.assertIn(section, ("t", "b"))
                self.assertIn(polarity, ("p", "n"))
                self.assertIn(int(number), range(1, 31))

    def test_board_ground_returns_use_individual_rail_taps(self):
        expected_taps = {
            (f"bb1:{row}b.j", f"bb1:bn.{rail_index}")
            for row, rail_index in zip(GROUND_BUS_ROWS, range(3, 8))
        }
        actual_taps = {
            (wire[0], wire[1])
            for wire in self.connections
            if wire[0].startswith("bb1:")
            and wire[1].startswith("bb1:")
            and (wire[0].endswith("b.j") or wire[1].endswith("b.j"))
        }
        self.assertEqual(actual_taps, expected_taps)
        # Button ground contacts occupy these bottom-strip rows; former LED rows may be unused.
        for row in (4, 10, 16, 22, 28):
            with self.subTest(row=row):
                self.assertTrue(reachable(self.graph, "uno:GND.1", f"bb1:{row}b.f"))


if __name__ == "__main__":
    unittest.main()
