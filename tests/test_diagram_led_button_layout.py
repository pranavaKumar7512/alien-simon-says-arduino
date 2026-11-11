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

# Wokwi's pixelSize="2020" is documented as a 9px LED rendering.
LED_STRIP_PIXEL_CSS_SIZE = 9.0
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
    "button-red": "red",
    "button-green": "green",
    "button-blue": "blue",
    "button-yellow": "yellow",
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
        self.assertEqual(
            self.diagram["parts"][0]["id"],
            "bb1",
            "the breadboard must render behind its inserted components",
        )

    def test_buttons_and_four_strips_follow_reference_coordinates(self):
        self.assertEqual(len(self.diagram["parts"]), 16)
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

        strip_ids = {
            "button-red": "neopixel-red",
            "button-green": "neopixel-green",
            "button-blue": "neopixel-blue",
            "button-yellow": "neopixel-yellow",
        }
        self.assertEqual(
            {part_id for part_id in self.parts if part_id.startswith("neopixel-")},
            set(strip_ids.values()),
        )
        for button_id, strip_id in strip_ids.items():
            with self.subTest(strip=strip_id):
                strip = self.parts[strip_id]
                button = self.parts[button_id]
                self.assertEqual(strip["type"], "wokwi-led-strip")
                self.assertEqual(strip["attrs"]["pixels"], "4")
                self.assertEqual(strip["attrs"]["pixelSize"], "2020")
                self.assertEqual(strip["rotate"], 90)
                self.assertAlmostEqual(strip["top"], 359)
                self.assertLess(strip["top"], button["top"])

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

    def test_strip_nominal_centers_align_with_matching_button_centers(self):
        # Static anchor calculation only: pixelSize is documented as a nominal 9px
        # package for "2020". The strip's rendered bounds/offset are not measured.
        strip_ids = {
            "button-red": "neopixel-red",
            "button-green": "neopixel-green",
            "button-blue": "neopixel-blue",
            "button-yellow": "neopixel-yellow",
        }
        for button_id, strip_id in strip_ids.items():
            button = self.parts[button_id]
            strip = self.parts[strip_id]
            button_box = css_body_box(button, BUTTON_BODY)
            button_center = (button_box[0] + button_box[2]) / 2
            strip_anchor_left = BOARD_LEFT + (strip["left"] - BOARD_LEFT) * CSS_SCALE
            strip_nominal_center = strip_anchor_left + LED_STRIP_PIXEL_CSS_SIZE / 2
            with self.subTest(strip=strip_id):
                self.assertAlmostEqual(strip_nominal_center, button_center, places=2)

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
        # Both 90-degree resistors use the same measured Wokwi body fixture.
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
        self.assertEqual(len(self.diagram["connections"]), 66)
        self.assertEqual(sum(bool(wire[2]) for wire in self.diagram["connections"]), 44)
        self.assertEqual(len(placements), 22)
        self.assertTrue(all(isinstance(wire[3], list) for wire in placements))
        self.assertFalse(any(wire[3] == "$bb" for wire in self.diagram["connections"]))

    def test_reviewed_external_component_anchors_match_the_compact_layout(self):
        # Static anchor regression only; body clearances still need a rendered review.
        expected_anchors = {
            "uno": (300, 35),
            "lcd": (150, 300),
            "servo-visual-only": (680, 125),
            "dfplayer-mock": (680, 405),
            "visual-speaker": (820, 405),
        }
        for part_id, (left, top) in expected_anchors.items():
            with self.subTest(part=part_id):
                self.assertAlmostEqual(self.parts[part_id]["left"], left)
                self.assertAlmostEqual(self.parts[part_id]["top"], top)


if __name__ == "__main__":
    unittest.main()
