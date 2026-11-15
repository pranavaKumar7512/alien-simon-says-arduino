#!/usr/bin/env python3
"""Check the editor-derived physical footprints on the Wokwi breadboard."""

import json
import pathlib
import unittest
from itertools import combinations


ROOT = pathlib.Path(__file__).resolve().parents[1]
BOARD_TOP = 350
BOARD_LEFT = 330
DIAGRAM_ROW_PITCH = 9.6
CSS_ROW_PITCH = 7.65
CSS_SCALE = CSS_ROW_PITCH / DIAGRAM_ROW_PITCH
BOARD_CSS_WIDTH = 261.9484
BOARD_CSS_HEIGHT = 165.5952
STRIP_LEFTS = {
    "neopixel-red": 647.537,
    "neopixel-green": 727.537,
    "neopixel-blue": 807.537,
    "neopixel-yellow": 887.537,
}
EXPECTED_PART_COUNT = 17
EXPECTED_CONNECTION_COUNT = 63
EXPECTED_COLORED_CONNECTION_COUNT = 43
BUTTON_BODY = (20.7212, 22.3145, 0.78274, -0.82034)
RESISTOR_BODY = (9.02873, 47.10189, 19.02441, -19.06064)
BUTTON_ROWS = {
    "button-red": (6, 4),
    "button-green": (12, 10),
    "button-blue": (18, 16),
    "button-yellow": (24, 22),
    "button-start": (30, 28),
}
BUTTON_COLORS = {
    "button-red": "black",
    "button-green": "black",
    "button-blue": "black",
    "button-yellow": "black",
    "button-start": "gray",
}


def css_body_box(part, body_measurement):
    width, height, offset_x, offset_y = body_measurement
    left = BOARD_LEFT + (part["left"] - BOARD_LEFT) * CSS_SCALE + offset_x
    top = BOARD_TOP + (part["top"] - BOARD_TOP) * CSS_SCALE + offset_y
    return (left, top, left + width, top + height)


def css_edge_clearance(first, second):
    horizontal_gap = max(first[0] - second[2], second[0] - first[2], 0)
    vertical_gap = max(first[1] - second[3], second[1] - first[3], 0)
    return (horizontal_gap**2 + vertical_gap**2) ** 0.5


def boxes_overlap(first, second):
    return (
        max(first[0], second[0]) < min(first[2], second[2])
        and max(first[1], second[1]) < min(first[3], second[3])
    )


class DiagramLedButtonLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "diagram.json").open(encoding="utf-8") as diagram_file:
            cls.diagram = json.load(diagram_file)
        cls.parts = {part["id"]: part for part in cls.diagram["parts"]}

    def test_one_half_breadboard_uses_the_requested_origin(self):
        boards = [part for part in self.diagram["parts"] if part["type"] == "wokwi-breadboard-half"]
        self.assertEqual(len(boards), 1)
        self.assertEqual(
            {key: boards[0][key] for key in ("id", "top", "left", "attrs")},
            {"id": "bb1", "top": BOARD_TOP, "left": BOARD_LEFT, "attrs": {}},
        )
        self.assertEqual(boards[0].get("rotate", 0), 0)
        self.assertIn("bb1", self.parts)

    def test_buttons_and_independent_strips_follow_reference_coordinates(self):
        self.assertEqual(len(self.diagram["parts"]), EXPECTED_PART_COUNT)
        self.assertEqual(len(BUTTON_ROWS), 5)
        for button_id, (contact1, contact2) in BUTTON_ROWS.items():
            with self.subTest(button=button_id):
                button = self.parts[button_id]
                self.assertEqual(button["type"], "wokwi-pushbutton-6mm")
                self.assertEqual(button["attrs"]["color"], BUTTON_COLORS[button_id])
                self.assertEqual(button["rotate"], 90)
                self.assertAlmostEqual(button["top"], BOARD_TOP + 90.4)
                self.assertAlmostEqual(
                    button["left"],
                    BOARD_LEFT + 212.4 + DIAGRAM_ROW_PITCH * (contact1 - 23),
                )
                self.assertIn(contact1, range(1, 31))
                self.assertIn(contact2, range(1, 31))
                self.assertEqual(contact1 - contact2, 2)

        self.assertEqual(
            [part["id"] for part in self.diagram["parts"] if part["id"].startswith("neopixel-")],
            ["neopixel-red", "neopixel-green", "neopixel-blue", "neopixel-yellow"],
        )
        for strip_id, expected_left in STRIP_LEFTS.items():
            with self.subTest(strip=strip_id):
                strip = self.parts[strip_id]
                self.assertEqual(strip["type"], "wokwi-led-strip")
                self.assertEqual(strip["attrs"], {"pixels": "6", "pixelSize": "2020"})
                self.assertEqual(strip["rotate"], 225)
                self.assertAlmostEqual(strip["top"], 60)
                self.assertAlmostEqual(strip["left"], expected_left)
                self.assertLess(strip["top"], self.parts["button-red"]["top"])

        tx_resistor = self.parts["mp3-tx-resistor"]
        self.assertEqual(tx_resistor["type"], "wokwi-resistor")
        self.assertEqual(tx_resistor["attrs"]["value"], "1000")
        self.assertEqual(tx_resistor["rotate"], 90)
        self.assertAlmostEqual(tx_resistor["top"], BOARD_TOP + 84.6)
        self.assertAlmostEqual(
            tx_resistor["left"],
            BOARD_LEFT + 102.25 + DIAGRAM_ROW_PITCH * (1 - 12),
        )

        occupied_rows = [row for pair in BUTTON_ROWS.values() for row in pair]
        occupied_rows += [1]
        self.assertTrue(all(row in range(1, 31) for row in occupied_rows))

    def test_measured_button_and_resistor_bodies_fit_and_keep_minimum_clearances(self):
        self.assertAlmostEqual(CSS_SCALE, 0.796875)
        board_box = (
            BOARD_LEFT,
            BOARD_TOP,
            BOARD_LEFT + BOARD_CSS_WIDTH,
            BOARD_TOP + BOARD_CSS_HEIGHT,
        )
        button_boxes = {
            button_id: css_body_box(self.parts[button_id], BUTTON_BODY)
            for button_id in BUTTON_ROWS
        }
        # The measured body fixture is checked in its original board-local orientation.
        resistor_ids = [
            "mp3-tx-resistor",
        ]
        resistor_boxes = {
            resistor_id: css_body_box(self.parts[resistor_id], RESISTOR_BODY)
            for resistor_id in resistor_ids
        }
        all_boxes = {
            **button_boxes,
            **resistor_boxes,
        }

        for part_id, body_box in all_boxes.items():
            with self.subTest(part=part_id):
                self.assertGreaterEqual(body_box[0], board_box[0])
                self.assertGreaterEqual(body_box[1], board_box[1])
                self.assertLessEqual(body_box[2], board_box[2])
                self.assertLessEqual(body_box[3], board_box[3])

        for button_id, button_box in button_boxes.items():
            for resistor_id, resistor_box in resistor_boxes.items():
                with self.subTest(button=button_id, resistor=resistor_id):
                    self.assertFalse(boxes_overlap(button_box, resistor_box))

        button_button_clearance = min(
            css_edge_clearance(first, second)
            for first, second in combinations(button_boxes.values(), 2)
        )
        button_resistor_clearance = min(
            css_edge_clearance(button_box, resistor_box)
            for button_box in button_boxes.values()
            for resistor_box in resistor_boxes.values()
        )
        all_body_clearance = min(
            css_edge_clearance(first, second)
            for first, second in combinations(all_boxes.values(), 2)
        )
        self.assertGreater(button_button_clearance, 0)
        self.assertGreater(button_resistor_clearance, 0)
        self.assertGreater(
            all_body_clearance,
            1.3,
            "every measured component body must keep at least the measured 1.3px guard",
        )

    def test_every_editor_generated_component_placement_uses_an_array_attribute(self):
        placements = [wire for wire in self.diagram["connections"] if wire[3] == ["$bb"]]
        self.assertEqual(len(self.diagram["parts"]), EXPECTED_PART_COUNT)
        self.assertEqual(len(self.diagram["connections"]), EXPECTED_CONNECTION_COUNT)
        self.assertEqual(
            sum(bool(wire[2]) for wire in self.diagram["connections"]),
            EXPECTED_COLORED_CONNECTION_COUNT,
        )
        self.assertEqual(len(placements), 20)
        self.assertTrue(all(isinstance(wire[3], list) for wire in placements))
        self.assertFalse(any(wire[3] == "$bb" for wire in self.diagram["connections"]))

        strip_connections = {
            (wire[0], wire[1], wire[2])
            for wire in self.diagram["connections"]
            if wire[0].startswith("neopixel-") or wire[1].startswith("neopixel-")
        }
        self.assertEqual(
            strip_connections,
            {
                ("uno:2", "neopixel-red:DIN", "#FFFF00"),
                ("uno:3", "neopixel-green:DIN", "#FFFF00"),
                ("uno:4", "neopixel-blue:DIN", "#FFFF00"),
                ("uno:12", "neopixel-yellow:DIN", "#FFFF00"),
                ("neopixel-red:VSS", "bb1:tn.14", "#00FF00"),
                ("neopixel-red:VDD", "bb1:bp.14", "#FF0000"),
                ("neopixel-green:VSS", "bb1:tn.10", "#FFFFFF"),
                ("neopixel-green:VDD", "bb1:bp.10", "#FFA500"),
                ("neopixel-blue:VSS", "bb1:tn.11", "#A52A2A"),
                ("neopixel-blue:VDD", "bb1:bp.11", "#FFA500"),
                ("neopixel-yellow:VSS", "bb1:tn.16", "#006400"),
                ("neopixel-yellow:VDD", "bb1:bp.16", "#FF0000"),
            },
        )
        strip_endpoints = {
            endpoint
            for wire in self.diagram["connections"]
            for endpoint in wire[:2]
            if endpoint.startswith("neopixel-")
        }
        self.assertEqual(
            {endpoint for endpoint in strip_endpoints if endpoint.endswith(("VDD", "VSS"))},
            {
                f"neopixel-{color}:{pin}"
                for color in ("red", "green", "blue", "yellow")
                for pin in ("VDD", "VSS")
            },
        )
        self.assertTrue(
            all(
                f"neopixel-{color}:{pin}" not in strip_endpoints
                for color in ("red", "green", "blue", "yellow")
                for pin in ("DOUT", "VDD.2", "VSS.2")
            )
        )

    def test_dfplayer_mock_keeps_its_anchor_and_clockwise_rotation(self):
        dfplayer = self.parts["dfplayer-mock"]
        self.assertEqual((dfplayer["left"], dfplayer["top"]), (680, 405))
        self.assertEqual(dfplayer["rotate"], 45)

    def test_reviewed_external_component_anchors_match_the_compact_layout(self):
        # Static anchor regression only; body clearances still need a rendered review.
        expected_anchors = {
            "uno": (260, 0),
            "lcd": (150, 300),
            "servo-visual-only": (680, 125),
            "dfplayer-mock": (680, 405),
            "visual-speaker": (820, 405),
            "barrel-jack-breakout": (820, 320),
        }
        expected_rotations = {
            "uno": 45,
            "lcd": 45,
            "servo-visual-only": None,
            "dfplayer-mock": 45,
            "visual-speaker": 45,
            "barrel-jack-breakout": 45,
        }
        for part_id, (left, top) in expected_anchors.items():
            with self.subTest(part=part_id):
                self.assertAlmostEqual(self.parts[part_id]["left"], left)
                self.assertAlmostEqual(self.parts[part_id]["top"], top)
                if expected_rotations[part_id] is None:
                    self.assertNotIn("rotate", self.parts[part_id])
                else:
                    self.assertEqual(self.parts[part_id]["rotate"], expected_rotations[part_id])


if __name__ == "__main__":
    unittest.main()
