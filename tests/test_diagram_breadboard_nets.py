#!/usr/bin/env python3
"""Validate the exact Wokwi breadboard wiring, placements, and safe topology."""

import json
import pathlib
import re
import unittest
from collections import defaultdict, deque


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUTTONS = {
    "button-red": ("6", 6, 4, "bn.28", "black"),
    "button-green": ("7", 12, 10, "bn.28", "black"),
    "button-blue": ("8", 18, 16, "bn.28", "black"),
    "button-yellow": ("A0", 24, 22, "bn.28", "black"),
    "button-start": ("A1", 30, 28, "bn.28", "gray"),
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
    ("external-supply:5V", "barrel-jack-breakout:JACK+"): "#FF0000",
    ("external-supply:GND", "barrel-jack-breakout:JACK-"): "#000000",
    ("barrel-jack-breakout:5V", "servo-visual-only:V+"): "#FF0000",
    ("barrel-jack-breakout:GND", "servo-visual-only:GND"): "#000000",
    ("barrel-jack-breakout:GND", "uno:GND.1"): "#000000",
    ("uno:A4", "bb1:2t.a"): "#00FFFF",
    ("bb1:2t.b", "lcd:SDA"): "#00FFFF",
    ("uno:A5", "bb1:3t.a"): "#FF00FF",
    ("bb1:3t.b", "lcd:SCL"): "#FF00FF",
    ("dfplayer-mock:TX", "bb1:5t.a"): "#800080",
    ("bb1:5t.b", "uno:10"): "#800080",
    ("uno:9", "bb1:7t.a"): "#FFA500",
    ("bb1:7t.b", "servo-visual-only:PWM"): "#FFA500",
    ("dfplayer-mock:SPK1", "bb1:11t.a"): "#A52A2A",
    ("bb1:11t.b", "visual-speaker:SPK1"): "#A52A2A",
    ("dfplayer-mock:SPK2", "bb1:13t.a"): "#D2B48C",
    ("bb1:13t.b", "visual-speaker:SPK2"): "#D2B48C",
    ("uno:11", "bb1:1t.a"): "#808080",
    ("bb1:1b.g", "dfplayer-mock:RX"): "#808080",
    ("uno:2", "neopixel-red:DIN"): "#FFFFFF",
    ("neopixel-red:DOUT", "neopixel-green:DIN"): "#FFFFFF",
    ("neopixel-green:DOUT", "neopixel-blue:DIN"): "#FFFFFF",
    ("neopixel-blue:DOUT", "neopixel-yellow:DIN"): "#FFFFFF",
    ("barrel-jack-breakout:5V", "neopixel-red:VDD"): "#FF0000",
    ("barrel-jack-breakout:GND", "neopixel-red:VSS"): "#000000",
    ("barrel-jack-breakout:5V", "neopixel-green:VDD"): "#FF0000",
    ("barrel-jack-breakout:GND", "neopixel-green:VSS"): "#000000",
    ("barrel-jack-breakout:5V", "neopixel-blue:VDD"): "#FF0000",
    ("barrel-jack-breakout:GND", "neopixel-blue:VSS"): "#000000",
    ("barrel-jack-breakout:5V", "neopixel-yellow:VDD"): "#FF0000",
    ("barrel-jack-breakout:GND", "neopixel-yellow:VSS"): "#000000",
    ("uno:6", "bb1:6t.a"): "#FF0000",
    ("bb1:4b.j", "bb1:10b.j"): "#000000",
    ("uno:7", "bb1:12t.a"): "#00FF00",
    ("uno:8", "bb1:18t.a"): "#0000FF",
    ("bb1:10b.j", "bb1:16b.j"): "#000000",
    ("uno:A0", "bb1:24t.a"): "#FFFF00",
    ("uno:A1", "bb1:30t.a"): "#FFFFFF",
    ("bb1:16b.j", "bb1:22b.j"): "#000000",
    ("bb1:22b.j", "bb1:28b.j"): "#000000",
    ("bb1:28b.j", "bb1:bn.28"): "#000000",
}


def visible_connection(left, right):
    return connection(left, right, WIRE_COLORS[(left, right)])


EXPECTED_CONNECTIONS = {
    visible_connection("uno:5V", "bb1:tp.1"),
    visible_connection("bb1:tp.2", "lcd:VCC"),
    visible_connection("bb1:tp.3", "dfplayer-mock:VCC"),
    visible_connection("uno:GND.1", "bb1:bn.1"),
    visible_connection("bb1:bn.29", "lcd:GND"),
    visible_connection("bb1:bn.30", "dfplayer-mock:GND"),
    visible_connection("external-supply:5V", "barrel-jack-breakout:JACK+"),
    visible_connection("external-supply:GND", "barrel-jack-breakout:JACK-"),
    visible_connection("barrel-jack-breakout:5V", "servo-visual-only:V+"),
    visible_connection("barrel-jack-breakout:GND", "servo-visual-only:GND"),
    visible_connection("barrel-jack-breakout:GND", "uno:GND.1"),
    visible_connection("uno:A4", "bb1:2t.a"),
    visible_connection("bb1:2t.b", "lcd:SDA"),
    visible_connection("uno:A5", "bb1:3t.a"),
    visible_connection("bb1:3t.b", "lcd:SCL"),
    visible_connection("dfplayer-mock:TX", "bb1:5t.a"),
    visible_connection("bb1:5t.b", "uno:10"),
    visible_connection("uno:9", "bb1:7t.a"),
    visible_connection("bb1:7t.b", "servo-visual-only:PWM"),
    visible_connection("dfplayer-mock:SPK1", "bb1:11t.a"),
    visible_connection("bb1:11t.b", "visual-speaker:SPK1"),
    visible_connection("dfplayer-mock:SPK2", "bb1:13t.a"),
    visible_connection("bb1:13t.b", "visual-speaker:SPK2"),
    visible_connection("uno:11", "bb1:1t.a"),
    connection("mp3-tx-resistor:1", "bb1:1t.b", attrs=("$bb",)),
    connection("mp3-tx-resistor:2", "bb1:1b.f", attrs=("$bb",)),
    visible_connection("bb1:1b.g", "dfplayer-mock:RX"),
    visible_connection("uno:2", "neopixel-red:DIN"),
    visible_connection("neopixel-red:DOUT", "neopixel-green:DIN"),
    visible_connection("neopixel-green:DOUT", "neopixel-blue:DIN"),
    visible_connection("neopixel-blue:DOUT", "neopixel-yellow:DIN"),
    visible_connection("barrel-jack-breakout:5V", "neopixel-red:VDD"),
    visible_connection("barrel-jack-breakout:GND", "neopixel-red:VSS"),
    visible_connection("barrel-jack-breakout:5V", "neopixel-green:VDD"),
    visible_connection("barrel-jack-breakout:GND", "neopixel-green:VSS"),
    visible_connection("barrel-jack-breakout:5V", "neopixel-blue:VDD"),
    visible_connection("barrel-jack-breakout:GND", "neopixel-blue:VSS"),
    visible_connection("barrel-jack-breakout:5V", "neopixel-yellow:VDD"),
    visible_connection("barrel-jack-breakout:GND", "neopixel-yellow:VSS"),
}

for left_row, right_row in zip(GROUND_BUS_ROWS, GROUND_BUS_ROWS[1:]):
    EXPECTED_CONNECTIONS.add(
        visible_connection(f"bb1:{left_row}b.j", f"bb1:{right_row}b.j")
    )
EXPECTED_CONNECTIONS.add(visible_connection("bb1:28b.j", "bb1:bn.28"))

for button_id, (gpio, contact1, contact2, _ground_rail, _color) in BUTTONS.items():
    EXPECTED_CONNECTIONS.update(
        {
            visible_connection(f"uno:{gpio}", f"bb1:{contact1}t.a"),
            connection(f"{button_id}:1.l", f"bb1:{contact1}t.e", attrs=("$bb",)),
            connection(f"{button_id}:1.r", f"bb1:{contact1}b.f", attrs=("$bb",)),
            connection(f"{button_id}:2.l", f"bb1:{contact2}t.e", attrs=("$bb",)),
            connection(f"{button_id}:2.r", f"bb1:{contact2}b.f", attrs=("$bb",)),
        }
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
        tiepoint = re.fullmatch(r"bb1:(\d+)([tb])\.([a-j])", endpoint)
        rail = re.fullmatch(r"bb1:([tb])([pn])\.(\d+)", endpoint)
        if tiepoint:
            number, section, hole = tiepoint.groups()
            if (section == "t" and hole in "abcde") or (section == "b" and hole in "fghij"):
                tiepoint_groups[(number, section)].append(endpoint)
        elif rail:
            rail_groups[rail.groups()[:2]].append(endpoint)
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
        self.assertEqual(len(self.connection_tuples), 69)
        self.assertEqual(sum(bool(item[2]) for item in self.connection_tuples), 47)
        self.assertEqual(sum(item[3] == ("$bb",) for item in self.connection_tuples), 22)
        self.assertEqual(len(self.connection_tuples), len(set(self.connection_tuples)))
        self.assertEqual(set(self.connection_tuples), EXPECTED_CONNECTIONS)
        direct_component_wires = {
            visible_connection("external-supply:5V", "barrel-jack-breakout:JACK+"),
            visible_connection("external-supply:GND", "barrel-jack-breakout:JACK-"),
            visible_connection("barrel-jack-breakout:5V", "servo-visual-only:V+"),
            visible_connection("barrel-jack-breakout:GND", "servo-visual-only:GND"),
            visible_connection("barrel-jack-breakout:GND", "uno:GND.1"),
            visible_connection("barrel-jack-breakout:5V", "neopixel-red:VDD"),
            visible_connection("barrel-jack-breakout:GND", "neopixel-red:VSS"),
            visible_connection("barrel-jack-breakout:5V", "neopixel-green:VDD"),
            visible_connection("barrel-jack-breakout:GND", "neopixel-green:VSS"),
            visible_connection("barrel-jack-breakout:5V", "neopixel-blue:VDD"),
            visible_connection("barrel-jack-breakout:GND", "neopixel-blue:VSS"),
            visible_connection("barrel-jack-breakout:5V", "neopixel-yellow:VDD"),
            visible_connection("barrel-jack-breakout:GND", "neopixel-yellow:VSS"),
            visible_connection("uno:2", "neopixel-red:DIN"),
            visible_connection("neopixel-red:DOUT", "neopixel-green:DIN"),
            visible_connection("neopixel-green:DOUT", "neopixel-blue:DIN"),
            visible_connection("neopixel-blue:DOUT", "neopixel-yellow:DIN"),
        }
        for left, right, color, _attrs in self.connection_tuples:
            board_mediated = left.startswith("bb1:") or right.startswith("bb1:")
            self.assertTrue(
                board_mediated or connection(left, right, color) in direct_component_wires,
                f"unexpected component-to-component bypass: {left} -> {right}",
            )
        direct_uno_component_wires = {
            item for item in self.connection_tuples
            if (item[0].startswith("uno:") and not item[1].startswith("bb1:"))
            or (item[1].startswith("uno:") and not item[0].startswith("bb1:"))
        }
        self.assertEqual(
            direct_uno_component_wires,
            {
                visible_connection("barrel-jack-breakout:GND", "uno:GND.1"),
                visible_connection("uno:2", "neopixel-red:DIN"),
            },
        )
        self.assertTrue(all(isinstance(item[3], list) for item in self.connections))
        self.assertFalse(any(item[3] == "$bb" for item in self.connections))

    def test_visible_wire_colors_follow_electrical_function(self):
        self.assertEqual(len(WIRE_COLORS), 47)
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
            ("external-supply:5V", "barrel-jack-breakout:JACK+"),
            ("barrel-jack-breakout:5V", "servo-visual-only:V+"),
            ("barrel-jack-breakout:5V", "neopixel-red:VDD"),
            ("barrel-jack-breakout:5V", "neopixel-green:VDD"),
            ("barrel-jack-breakout:5V", "neopixel-blue:VDD"),
            ("barrel-jack-breakout:5V", "neopixel-yellow:VDD"),
        )
        assert_color(
            "#000000",
            ("uno:GND.1", "bb1:bn.1"),
            ("bb1:bn.29", "lcd:GND"),
            ("bb1:bn.30", "dfplayer-mock:GND"),
            ("external-supply:GND", "barrel-jack-breakout:JACK-"),
            ("barrel-jack-breakout:GND", "servo-visual-only:GND"),
            ("barrel-jack-breakout:GND", "uno:GND.1"),
            ("barrel-jack-breakout:GND", "neopixel-red:VSS"),
            ("barrel-jack-breakout:GND", "neopixel-green:VSS"),
            ("barrel-jack-breakout:GND", "neopixel-blue:VSS"),
            ("barrel-jack-breakout:GND", "neopixel-yellow:VSS"),
            ("bb1:4b.j", "bb1:10b.j"),
            ("bb1:10b.j", "bb1:16b.j"),
            ("bb1:16b.j", "bb1:22b.j"),
            ("bb1:22b.j", "bb1:28b.j"),
            ("bb1:28b.j", "bb1:bn.28"),
        )
        assert_color(
            "#FFFFFF",
            ("uno:2", "neopixel-red:DIN"),
            ("neopixel-red:DOUT", "neopixel-green:DIN"),
            ("neopixel-green:DOUT", "neopixel-blue:DIN"),
            ("neopixel-blue:DOUT", "neopixel-yellow:DIN"),
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
            ("uno:9", "bb1:7t.a"),
            ("bb1:7t.b", "servo-visual-only:PWM"),
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
            for pin, row, section, hole in (
                ("1.l", contact1, "t", "e"),
                ("1.r", contact1, "b", "f"),
                ("2.l", contact2, "t", "e"),
                ("2.r", contact2, "b", "f"),
            ):
                self.assertIn(
                    connection(f"{button_id}:{pin}", f"bb1:{row}{section}.{hole}", attrs=("$bb",)),
                    self.connection_tuples,
                )
        for strip_id in ("neopixel-red", "neopixel-green", "neopixel-blue", "neopixel-yellow"):
            with self.subTest(strip=strip_id):
                strip = self.parts[strip_id]
                self.assertEqual(strip["type"], "wokwi-led-strip")
                self.assertEqual(strip["attrs"]["pixels"], "4")
                self.assertEqual(strip["attrs"]["pixelSize"], "2020")
                self.assertEqual(strip["rotate"], 90)
        self.assertEqual(self.parts["mp3-tx-resistor"]["attrs"]["value"], "1000")
        self.assertEqual(self.parts["lcd"]["type"], "chip-grove-jhd1804")
        self.assertEqual(self.parts["dfplayer-mock"]["type"], "chip-dfplayer-mock")
        self.assertEqual(self.parts["visual-speaker"]["type"], "chip-visual-speaker")
        self.assertEqual(self.parts["external-supply"]["type"], "chip-external-supply")
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

    def test_neopixel_and_servo_power_route_through_barrel_breakout_separate_from_uno_5v(self):
        strip_ids = (
            "neopixel-red",
            "neopixel-green",
            "neopixel-blue",
            "neopixel-yellow",
        )
        expected_data_links = (
            ("uno:2", "neopixel-red:DIN"),
            ("neopixel-red:DOUT", "neopixel-green:DIN"),
            ("neopixel-green:DOUT", "neopixel-blue:DIN"),
            ("neopixel-blue:DOUT", "neopixel-yellow:DIN"),
        )
        self.assertTrue(reachable(self.graph, "uno:2", "neopixel-red:DIN"))
        for left, right in expected_data_links:
            with self.subTest(data_link=(left, right)):
                self.assertIn(visible_connection(left, right), self.connection_tuples)
                self.assertIn(right, self.graph[left])

        power_graph = wire_graph(self.connections)
        # The custom visual-only breakout implies two passive internal terminals;
        # these bridges define the intended physical net without claiming a sim model.
        connect_graph(power_graph, "barrel-jack-breakout:JACK+", "barrel-jack-breakout:5V")
        connect_graph(power_graph, "barrel-jack-breakout:JACK-", "barrel-jack-breakout:GND")
        for strip_id in strip_ids:
            with self.subTest(strip=strip_id):
                self.assertTrue(reachable(power_graph, "external-supply:5V", f"{strip_id}:VDD"))
                self.assertTrue(reachable(power_graph, "external-supply:GND", f"{strip_id}:VSS"))
                self.assertFalse(reachable(power_graph, "uno:5V", f"{strip_id}:VDD"))
                self.assertFalse(reachable(power_graph, f"{strip_id}:VDD", f"{strip_id}:VSS"))
        self.assertTrue(reachable(power_graph, "external-supply:5V", "servo-visual-only:V+"))
        self.assertTrue(reachable(power_graph, "external-supply:GND", "servo-visual-only:GND"))
        self.assertTrue(reachable(power_graph, "external-supply:GND", "uno:GND.1"))
        self.assertFalse(reachable(power_graph, "uno:5V", "servo-visual-only:V+"))
        self.assertFalse(reachable(power_graph, "external-supply:5V", "uno:5V"))

    def test_d11_1k_resistor_separates_uno_tx_from_mock_rx(self):
        self.assertTrue(reachable(self.graph, "uno:11", "mp3-tx-resistor:1"))
        self.assertTrue(reachable(self.graph, "mp3-tx-resistor:2", "dfplayer-mock:RX"))
        self.assertFalse(reachable(self.graph, "uno:11", "mp3-tx-resistor:2"))
        self.assertFalse(reachable(self.graph, "uno:11", "dfplayer-mock:RX"))
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

    def test_breadboard_endpoints_stay_inside_supported_hole_and_rail_ranges(self):
        boards = [part for part in self.diagram["parts"] if part["type"] == "wokwi-breadboard-half"]
        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0]["id"], "bb1")
        self.assertEqual(boards[0]["attrs"], {})
        self.assertNotIn("$bb", json.dumps(boards[0]))
        for endpoint in self.graph:
            if not endpoint.startswith("bb1:"):
                continue
            row = re.fullmatch(r"bb1:(\d+)([tb])\.([a-j])", endpoint)
            rail = re.fullmatch(r"bb1:([tb])([pn])\.(\d+)", endpoint)
            self.assertTrue(row or rail, f"unsupported breadboard endpoint {endpoint}")
            if row:
                number, section, hole = row.groups()
                self.assertIn(int(number), range(1, 31))
                self.assertIn(hole, "abcde" if section == "t" else "fghij")
            else:
                section, polarity, number = rail.groups()
                self.assertIn(section, ("t", "b"))
                self.assertIn(polarity, ("p", "n"))
                self.assertIn(int(number), range(1, 31))

    def test_board_ground_returns_share_row_j_trunk_and_one_bottom_rail_tap(self):
        expected_trunk = {
            (f"bb1:{left_row}b.j", f"bb1:{right_row}b.j")
            for left_row, right_row in zip(GROUND_BUS_ROWS, GROUND_BUS_ROWS[1:])
        }
        expected_trunk.add(("bb1:28b.j", "bb1:bn.28"))
        actual_trunk = {
            (wire[0], wire[1])
            for wire in self.connections
            if wire[0].startswith("bb1:")
            and wire[1].startswith("bb1:")
            and (wire[0].endswith("b.j") or wire[1].endswith("b.j"))
        }
        self.assertEqual(actual_trunk, expected_trunk)
        # Button ground contacts occupy these bottom-strip rows; former LED rows may be unused.
        for row in (4, 10, 16, 22, 28):
            with self.subTest(row=row):
                self.assertTrue(reachable(self.graph, "uno:GND.1", f"bb1:{row}b.f"))


if __name__ == "__main__":
    unittest.main()
