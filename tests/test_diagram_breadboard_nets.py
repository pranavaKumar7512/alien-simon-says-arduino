#!/usr/bin/env python3
"""Validate the exact Wokwi breadboard wiring, placements, and safe topology."""

import json
import pathlib
import re
import unittest
from collections import defaultdict, deque


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUTTONS = {
    "button-red": ("6", 6, 4, "bn.28", "red"),
    "button-green": ("7", 12, 10, "bn.28", "green"),
    "button-blue": ("8", 18, 16, "bn.28", "blue"),
    "button-yellow": ("A0", 24, 22, "bn.28", "yellow"),
    "button-start": ("A1", 30, 28, "bn.28", "gray"),
}
GROUND_BUS_ROWS = (4, 10, 16, 22, 28)

def connection(left, right, color="", attrs=()):
    return (left, right, color, tuple(attrs))


WIRE_COLORS = {
    ("uno:5V", "bb1:tp.1"): "#1769AA",
    ("bb1:tp.2", "lcd:VCC"): "#E60000",
    ("bb1:tp.3", "dfplayer-mock:VCC"): "#00AD00",
    ("uno:GND.1", "bb1:bn.1"): "#0000E6",
    ("bb1:bn.29", "lcd:GND"): "#E60EA1",
    ("bb1:bn.30", "dfplayer-mock:GND"): "#665012",
    ("uno:5V", "servo-visual-only:V+"): "#009C87",
    ("uno:GND.1", "servo-visual-only:GND"): "#78002C",
    ("uno:A4", "bb1:2t.a"): "#55198A",
    ("bb1:2t.b", "lcd:SDA"): "#D17600",
    ("uno:A5", "bb1:3t.a"): "#8F9C00",
    ("bb1:3t.b", "lcd:SCL"): "#CB00E6",
    ("dfplayer-mock:TX", "bb1:5t.a"): "#066613",
    ("bb1:5t.b", "uno:10"): "#E60054",
    ("uno:9", "bb1:7t.a"): "#0E68E6",
    ("bb1:7t.b", "servo-visual-only:PWM"): "#9C2909",
    ("dfplayer-mock:SPK1", "bb1:11t.a"): "#0B9EBF",
    ("bb1:11t.b", "visual-speaker:SPK1"): "#8A0869",
    ("dfplayer-mock:SPK2", "bb1:13t.a"): "#7849E6",
    ("bb1:13t.b", "visual-speaker:SPK2"): "#B43DBF",
    ("uno:11", "bb1:1t.a"): "#D1437C",
    ("bb1:1b.g", "dfplayer-mock:RX"): "#00378A",
    ("uno:2", "neopixel-red:DIN"): "#9060B0",
    ("neopixel-red:DOUT", "neopixel-green:DIN"): "#F0D0F0",
    ("neopixel-green:DOUT", "neopixel-blue:DIN"): "#F0C0A0",
    ("neopixel-blue:DOUT", "neopixel-yellow:DIN"): "#B07080",
    ("neopixel-red:VDD", "bb1:tp.4"): "#808060",
    ("neopixel-red:VSS", "bb1:bn.28"): "#303020",
    ("neopixel-green:VDD", "bb1:tp.4"): "#D0F0B0",
    ("neopixel-green:VSS", "bb1:bn.28"): "#F0F030",
    ("neopixel-blue:VDD", "bb1:tp.4"): "#30F090",
    ("neopixel-blue:VSS", "bb1:bn.28"): "#C0F0F0",
    ("neopixel-yellow:VDD", "bb1:tp.4"): "#A0F030",
    ("neopixel-yellow:VSS", "bb1:bn.28"): "#F090D0",
    ("uno:6", "bb1:6t.a"): "#662912",
    ("bb1:4b.j", "bb1:10b.j"): "#AD8E37",
    ("uno:7", "bb1:12t.a"): "#AD6537",
    ("uno:8", "bb1:18t.a"): "#657826",
    ("bb1:10b.j", "bb1:16b.j"): "#099C5C",
    ("uno:A0", "bb1:24t.a"): "#E65149",
    ("uno:A1", "bb1:30t.a"): "#66214B",
    ("bb1:16b.j", "bb1:22b.j"): "#589C1C",
    ("bb1:22b.j", "bb1:28b.j"): "#4985E6",
    ("bb1:28b.j", "bb1:bn.28"): "#00FFFF",
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
    visible_connection("uno:5V", "servo-visual-only:V+"),
    visible_connection("uno:GND.1", "servo-visual-only:GND"),
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
    visible_connection("neopixel-red:VDD", "bb1:tp.4"),
    visible_connection("neopixel-red:VSS", "bb1:bn.28"),
    visible_connection("neopixel-green:VDD", "bb1:tp.4"),
    visible_connection("neopixel-green:VSS", "bb1:bn.28"),
    visible_connection("neopixel-blue:VDD", "bb1:tp.4"),
    visible_connection("neopixel-blue:VSS", "bb1:bn.28"),
    visible_connection("neopixel-yellow:VDD", "bb1:tp.4"),
    visible_connection("neopixel-yellow:VSS", "bb1:bn.28"),
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
        self.assertEqual(len(self.connection_tuples), 66)
        self.assertEqual(sum(bool(item[2]) for item in self.connection_tuples), 44)
        self.assertEqual(sum(item[3] == ("$bb",) for item in self.connection_tuples), 22)
        self.assertEqual(len(self.connection_tuples), len(set(self.connection_tuples)))
        self.assertEqual(set(self.connection_tuples), EXPECTED_CONNECTIONS)
        direct_component_wires = {
            visible_connection("uno:5V", "servo-visual-only:V+"),
            visible_connection("uno:GND.1", "servo-visual-only:GND"),
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
                visible_connection("uno:5V", "servo-visual-only:V+"),
                visible_connection("uno:GND.1", "servo-visual-only:GND"),
                visible_connection("uno:2", "neopixel-red:DIN"),
            },
        )
        self.assertTrue(all(isinstance(item[3], list) for item in self.connections))
        self.assertFalse(any(item[3] == "$bb" for item in self.connections))

    def test_visible_wire_colors_are_unique_and_well_separated_per_wire(self):
        visible_colors = [item[2] for item in self.connection_tuples if item[2]]
        self.assertEqual(len(visible_colors), 44)
        self.assertEqual(len(set(visible_colors)), 44)
        self.assertEqual(len(WIRE_COLORS), 44)
        self.assertEqual(set(visible_colors), set(WIRE_COLORS.values()))

        def lab_coordinates(hex_color):
            rgb = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]

            def linearize(value):
                return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

            red, green, blue = map(linearize, rgb)
            x = (0.4124564 * red + 0.3575761 * green + 0.1804375 * blue) / 0.95047
            y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
            z = (0.0193339 * red + 0.1191920 * green + 0.9503041 * blue) / 1.08883

            def pivot(value):
                return value ** (1 / 3) if value > 0.008856451679 else 7.787037037 * value + 16 / 116

            fx, fy, fz = map(pivot, (x, y, z))
            return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))

        labs = [lab_coordinates(color) for color in visible_colors]
        min_delta_e = min(
            sum((left - right) ** 2 for left, right in zip(labs[i], labs[j])) ** 0.5
            for i in range(len(labs))
            for j in range(i)
        )
        self.assertGreaterEqual(min_delta_e, 20.0)

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

    def test_neopixel_chain_and_simulated_rails_follow_strip_order(self):
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

        for strip_id in strip_ids:
            with self.subTest(strip=strip_id):
                self.assertTrue(reachable(self.graph, "uno:5V", f"{strip_id}:VDD"))
                self.assertTrue(reachable(self.graph, "uno:GND.1", f"{strip_id}:VSS"))
                self.assertFalse(reachable(self.graph, f"{strip_id}:VDD", f"{strip_id}:VSS"))

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
