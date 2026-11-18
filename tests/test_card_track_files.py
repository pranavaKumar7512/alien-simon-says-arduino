import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "sdcard" / "card-mp3"
CONFIG = ROOT / "alien-simon-says" / "audio_track_config.h"

EXPECTED_NAMES = {
    1: "0001-button1.mp3",
    2: "0002-button2.mp3",
    3: "0003-button3.mp3",
    4: "0004-button4.mp3",
    5: "0005-spare.mp3",
    6: "0006-celebration.mp3",
    7: "0007-losing.mp3",
}


def define(name):
    text = CONFIG.read_text(encoding="utf-8")
    match = re.search(r"#define %s (\d+)U" % name, text)
    assert match, name
    return int(match.group(1))


class CardTrackFilesTest(unittest.TestCase):
    def test_card_folder_has_exactly_the_named_files(self):
        self.assertEqual(sorted(p.name for p in CARD.glob("*.mp3")), sorted(EXPECTED_NAMES.values()))

    def test_each_file_starts_with_its_four_digit_track_number(self):
        # The firmware plays with playMp3Folder(n), which finds /mp3/NNNN*.mp3 by its leading digits.
        for number, name in EXPECTED_NAMES.items():
            with self.subTest(track=number):
                self.assertTrue(name.startswith("%04d" % number))
                matches = [p for p in CARD.glob("%04d*.mp3" % number)]
                self.assertEqual(len(matches), 1)

    def test_every_track_the_firmware_plays_has_a_file(self):
        used = list(range(define("AUDIO_FIRST_CUE_TRACK"), define("AUDIO_LAST_CUE_TRACK") + 1))
        used += [define("AUDIO_ROUND_CELEBRATION_TRACK"), define("AUDIO_GAME_OVER_LOSS_TRACK")]
        for number in used:
            with self.subTest(track=number):
                self.assertIn(number, EXPECTED_NAMES)
                self.assertTrue((CARD / EXPECTED_NAMES[number]).is_file())

    def test_track_roles_match_the_names(self):
        self.assertEqual(define("AUDIO_ROUND_CELEBRATION_TRACK"), 6)
        self.assertEqual(define("AUDIO_GAME_OVER_LOSS_TRACK"), 7)
        self.assertIn("celebration", EXPECTED_NAMES[6])
        self.assertIn("losing", EXPECTED_NAMES[7])


if __name__ == "__main__":
    unittest.main()
