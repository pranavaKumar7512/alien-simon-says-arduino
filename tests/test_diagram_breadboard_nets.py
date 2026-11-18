#!/usr/bin/env python3
"""Validate the build-derived breadboard wiring in the main Wokwi diagram.

These checks cover the modeled topology only. They do not verify physical
continuity, board ratings, current capacity, rendered clearance, or safety.
"""

import json
import pathlib
import re
import unittest
from collections import defaultdict, deque


ROOT = pathlib.Path(__file__).resolve().parents[1]
STRIPS = {
    "neopixel-red": ("uno:2", "bb1:bp.14", "bb1:tn.14"),
    "neopixel-green": ("uno:3", "bb1:bp.10", "bb1:tn.10"),
    "neopixel-blue": ("uno:4", "bb1:bp.11", "bb1:tn.11"),
    "neopixel-yellow": ("uno:12", "bb1:bp.16", "bb1:tn.16"),
}
BUTTONS = {
    "button-red": ("6", 6, 4, "black"),
    "button-green": ("7", 12, 10, "black"),
    "button-blue": ("8", 18, 16, "black"),
    "button-yellow": ("A0", 24, 22, "black"),
    "button-start": ("A1", 30, 28, "gray"),
}


def breadboard_graph(connections):
    """Model Wokwi tie groups and its four electrically separate rails."""
    graph = defaultdict(set)
    for item in connections:
        left, right = item[:2]
        graph[left].add(right)
        graph[right].add(left)

    tie_groups = defaultdict(list)
    rails = defaultdict(list)
    for endpoint in graph:
        tie = re.fullmatch(r"bb1:(\d+)([tb])\.([a-j])", endpoint)
        rail = re.fullmatch(r"bb1:([tb])([pn])\.(\d+)", endpoint)
        if tie:
            row, section, hole = tie.groups()
            if (section == "t" and hole in "abcde") or (section == "b" and hole in "fghij"):
                tie_groups[(row, section)].append(endpoint)
        elif rail:
            section, polarity, _position = rail.groups()
            rails[(section, polarity)].append(endpoint)

    for endpoints in (*tie_groups.values(), *rails.values()):
        if endpoints:
            anchor = endpoints[0]
            for endpoint in endpoints[1:]:
                graph[anchor].add(endpoint)
                graph[endpoint].add(anchor)

    # The Uno's two GND pins are physically common on the board.
    graph["uno:GND.1"].add("uno:GND.2")
    graph["uno:GND.2"].add("uno:GND.1")
    return graph


def reachable(graph, start, target):
    queue = deque([start])
    seen = {start}
    while queue:
        node = queue.popleft()
        if node == target:
            return True
        for neighbor in graph[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return False


def find_connection(connections, left, right):
    for item in connections:
        if item[0] == left and item[1] == right:
            return item
        if item[0] == right and item[1] == left:
            return item
    return None


def switch_graph(connections, pressed_button=None):
    graph = breadboard_graph(connections)
    for button_id in BUTTONS:
        graph[f"{button_id}:1.l"].add(f"{button_id}:1.r")
        graph[f"{button_id}:1.r"].add(f"{button_id}:1.l")
        graph[f"{button_id}:2.l"].add(f"{button_id}:2.r")
        graph[f"{button_id}:2.r"].add(f"{button_id}:2.l")
        if button_id == pressed_button:
            graph[f"{button_id}:1.l"].add(f"{button_id}:2.l")
            graph[f"{button_id}:2.l"].add(f"{button_id}:1.l")
    return graph


class DiagramBreadboardNetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "diagram.json").open(encoding="utf-8") as diagram_file:
            cls.diagram = json.load(diagram_file)
        cls.parts = {part["id"]: part for part in cls.diagram["parts"]}
        cls.connections = cls.diagram["connections"]
        cls.graph = breadboard_graph(cls.connections)

    def test_build_derived_diagram_inventory_and_placements(self):
        self.assertEqual(len(self.parts), 19)
        self.assertEqual(len(self.connections), 70)
        self.assertEqual(sum(bool(wire[2]) for wire in self.connections), 50)
        placements = [wire for wire in self.connections if wire[3] == ["$bb"]]
        self.assertEqual(len(placements), 20)
        normalized = {tuple(wire[:3]) + (tuple(wire[3]),) for wire in self.connections}
        self.assertEqual(len(normalized), 70)
        self.assertEqual(self.parts["bb1"]["type"], "wokwi-breadboard-half")
        self.assertEqual((self.parts["bb1"]["left"], self.parts["bb1"]["top"]), (330, 350))
        for strip_id in STRIPS:
            self.assertEqual(self.parts[strip_id]["type"], "wokwi-led-strip")
            self.assertEqual(self.parts[strip_id]["attrs"], {"pixels": "6", "pixelSize": "2020"})
        self.assertNotIn("external-supply", self.parts)

    def test_four_independent_data_routes_and_reported_strip_rail_routes(self):
        self.assertEqual(set(STRIPS), {
            "neopixel-red", "neopixel-green", "neopixel-blue", "neopixel-yellow"
        })
        for strip_id, (gpio, positive_rail, ground_rail) in STRIPS.items():
            with self.subTest(strip=strip_id):
                self.assertIsNotNone(find_connection(self.connections, gpio, f"{strip_id}:DIN"))
                self.assertIsNotNone(find_connection(self.connections, f"{strip_id}:VDD", positive_rail))
                self.assertIsNotNone(find_connection(self.connections, f"{strip_id}:VSS", ground_rail))
                self.assertTrue(reachable(self.graph, "barrel-jack-breakout:5V", f"{strip_id}:VDD"))
                self.assertTrue(reachable(self.graph, "barrel-jack-breakout:GND", f"{strip_id}:VSS"))
        strip_endpoints = {
            endpoint
            for wire in self.connections
            for endpoint in wire[:2]
            if endpoint.startswith("neopixel-")
        }
        for strip_id in STRIPS:
            for unused in ("DOUT", "VDD.2", "VSS.2"):
                self.assertNotIn(f"{strip_id}:{unused}", strip_endpoints)

        expected_colors = {
            ("uno:2", "neopixel-red:DIN"): "#FFFF00",
            ("uno:3", "neopixel-green:DIN"): "#FFFF00",
            ("uno:4", "neopixel-blue:DIN"): "#FFFF00",
            ("uno:12", "neopixel-yellow:DIN"): "#FFFF00",
            ("neopixel-red:VDD", "bb1:bp.14"): "#FF0000",
            ("neopixel-red:VSS", "bb1:tn.14"): "#00FF00",
            ("neopixel-green:VDD", "bb1:bp.10"): "#FFA500",
            ("neopixel-green:VSS", "bb1:tn.10"): "#FFFFFF",
            ("neopixel-blue:VDD", "bb1:bp.11"): "#FFA500",
            ("neopixel-blue:VSS", "bb1:tn.11"): "#A52A2A",
            ("neopixel-yellow:VDD", "bb1:bp.16"): "#FF0000",
            ("neopixel-yellow:VSS", "bb1:tn.16"): "#006400",
        }
        for (left, right), color in expected_colors.items():
            with self.subTest(left=left, right=right):
                wire = find_connection(self.connections, left, right)
                self.assertIsNotNone(wire)
                self.assertEqual(wire[2], color)

    def test_external_load_supply_stays_separate_from_uno_positive(self):
        self.assertTrue(reachable(self.graph, "barrel-jack-breakout:5V", "bb1:bp.3"))
        self.assertTrue(reachable(self.graph, "barrel-jack-breakout:5V", "servo-visual-only:V+"))
        self.assertTrue(reachable(self.graph, "barrel-jack-breakout:GND", "servo-visual-only:GND"))
        self.assertTrue(reachable(self.graph, "barrel-jack-breakout:GND", "uno:GND.1"))
        self.assertTrue(reachable(self.graph, "uno:5V", "lcd:VCC"))
        self.assertTrue(reachable(self.graph, "uno:5V", "dfplayer-mock:VCC"))
        self.assertFalse(reachable(self.graph, "barrel-jack-breakout:5V", "uno:5V"))
        self.assertFalse(reachable(self.graph, "barrel-jack-breakout:5V", "uno:GND.1"))
        self.assertFalse(reachable(self.graph, "barrel-jack-breakout:GND", "barrel-jack-breakout:5V"))

    def test_motor_driver_wiring_and_separate_supply(self):
        driver = "motor-driver-mdd3a"
        # D5 and A2 drive the MDD3A signal inputs; encoder and driver 5VO stay unwired.
        self.assertIsNotNone(find_connection(self.connections, "uno:5", f"{driver}:M1A"))
        self.assertIsNotNone(find_connection(self.connections, "uno:A2", f"{driver}:M1B"))
        self.assertEqual(set(self.parts["motor-fit0458"].get("attrs", {})), set())
        # Logic ground is shared; the motor supply goes straight to the barrel breakout.
        self.assertTrue(reachable(self.graph, f"{driver}:GND", "uno:GND.1"))
        self.assertIsNotNone(find_connection(self.connections, f"{driver}:VB_PLUS", "barrel-jack-breakout:5V"))
        self.assertIsNotNone(find_connection(self.connections, f"{driver}:VB_MINUS", "barrel-jack-breakout:GND"))
        self.assertFalse(reachable(self.graph, f"{driver}:VB_PLUS", "uno:5V"))
        self.assertFalse(reachable(self.graph, f"{driver}:VB_PLUS", f"{driver}:VB_MINUS"))
        self.assertFalse(reachable(self.graph, f"{driver}:M1A", f"{driver}:M1B"))
        self.assertFalse(reachable(self.graph, f"{driver}:M1_OUT_A", "uno:5V"))
        self.assertIsNotNone(find_connection(self.connections, f"{driver}:M1_OUT_A", "motor-fit0458:MOTOR_PLUS"))
        self.assertIsNotNone(find_connection(self.connections, f"{driver}:M1_OUT_B", "motor-fit0458:MOTOR_MINUS"))
        for wire in self.connections:
            self.assertNotIn(f"{driver}:5VO", wire[:2])

    def test_buttons_use_separate_released_gpio_and_ground_contacts(self):
        released = switch_graph(self.connections)
        for button_id, (gpio, signal_row, ground_row, color) in BUTTONS.items():
            with self.subTest(button=button_id):
                self.assertEqual(self.parts[button_id]["type"], "wokwi-pushbutton-6mm")
                self.assertEqual(self.parts[button_id]["attrs"]["color"], color)
                self.assertIsNotNone(find_connection(self.connections, f"uno:{gpio}", f"bb1:{signal_row}t.a"))
                if button_id == "button-start":
                    self.assertIsNotNone(find_connection(self.connections, f"{button_id}:1.l", f"bb1:{signal_row}t.e"))
                    self.assertIsNotNone(find_connection(self.connections, f"{button_id}:2.r", f"bb1:{ground_row}b.f"))
                else:
                    self.assertIsNotNone(find_connection(self.connections, f"{button_id}:1.l", f"bb1:{signal_row}t.e"))
                    self.assertIsNotNone(find_connection(self.connections, f"{button_id}:1.r", f"bb1:{signal_row}b.f"))
                    self.assertIsNotNone(find_connection(self.connections, f"{button_id}:2.l", f"bb1:{ground_row}t.e"))
                    self.assertIsNotNone(find_connection(self.connections, f"{button_id}:2.r", f"bb1:{ground_row}b.f"))
                self.assertFalse(reachable(released, f"uno:{gpio}", "uno:GND.1"))
                pressed = switch_graph(self.connections, button_id)
                self.assertTrue(reachable(pressed, f"uno:{gpio}", "uno:GND.1"))

    def test_lcd_audio_servo_and_speaker_routes(self):
        for left, right in (
            ("uno:A4", "lcd:SDA"),
            ("uno:A5", "lcd:SCL"),
            ("bb1:tp.22", "lcd:VCC"),
            ("bb1:bn.22", "lcd:GND"),
            ("dfplayer-mock:TX", "bb1:5t.a"),
            ("bb1:5t.b", "uno:10"),
            ("uno:11", "bb1:1t.a"),
            ("mp3-tx-resistor:1", "bb1:1t.b"),
            ("mp3-tx-resistor:2", "bb1:1b.f"),
            ("bb1:1b.g", "dfplayer-mock:RX"),
            ("bb1:tp.5", "dfplayer-mock:VCC"),
            ("dfplayer-mock:GND", "bb1:bn.24"),
            ("uno:9", "bb1:7t.a"),
            ("bb1:7t.b", "servo-visual-only:PWM"),
            ("dfplayer-mock:SPK1", "visual-speaker:SPK1"),
            ("dfplayer-mock:SPK2", "visual-speaker:SPK2"),
        ):
            with self.subTest(left=left, right=right):
                self.assertIsNotNone(find_connection(self.connections, left, right))
        self.assertFalse(reachable(self.graph, "dfplayer-mock:SPK1", "uno:GND.1"))
        self.assertFalse(reachable(self.graph, "dfplayer-mock:SPK2", "uno:GND.1"))
        self.assertFalse(reachable(self.graph, "uno:11", "dfplayer-mock:RX"))

    def test_breadboard_endpoints_are_in_supported_ranges(self):
        graph = self.graph
        for endpoint in graph:
            if not endpoint.startswith("bb1:"):
                continue
            tie = re.fullmatch(r"bb1:(\d+)([tb])\.([a-j])", endpoint)
            rail = re.fullmatch(r"bb1:([tb])([pn])\.(\d+)", endpoint)
            self.assertTrue(tie or rail, f"unsupported breadboard endpoint {endpoint}")
            if tie:
                row, section, hole = tie.groups()
                self.assertIn(int(row), range(1, 31))
                self.assertIn(hole, "abcde" if section == "t" else "fghij")
            else:
                section, polarity, position = rail.groups()
                self.assertIn(section, ("t", "b"))
                self.assertIn(polarity, ("p", "n"))
                self.assertIn(int(position), range(1, 31))


if __name__ == "__main__":
    unittest.main()
