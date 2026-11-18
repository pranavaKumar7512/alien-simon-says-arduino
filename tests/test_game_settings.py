import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "game_settings_probe.c"
SETTINGS = ROOT / "alien-simon-says" / "game_settings.h"
GCC = shutil.which("gcc")


def compile_probe(extra_args, run=True):
    """Compile the probe; return (returncode, stdout, stderr) of the compile or run."""
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "probe.exe"
        build = subprocess.run(
            [GCC, "-std=c99", "-Wall", "-Wextra", "-Werror", *extra_args, str(PROBE), "-o", str(exe)],
            capture_output=True,
            text=True,
        )
        if build.returncode != 0 or not run:
            return build.returncode, build.stdout, build.stderr
        ran = subprocess.run([str(exe)], capture_output=True, text=True)
        return ran.returncode, ran.stdout, ran.stderr


def parse(stdout):
    return dict(line.split("=", 1) for line in stdout.strip().splitlines())


@unittest.skipUnless(GCC, "gcc is required for the settings tests")
class GameSettingsTest(unittest.TestCase):
    def test_settings_defaults_match_the_header_defaults(self):
        code, with_settings, err = compile_probe([])
        self.assertEqual(code, 0, err)
        code, without_settings, err = compile_probe(["-DNO_SETTINGS"])
        self.assertEqual(code, 0, err)
        self.assertEqual(parse(with_settings), parse(without_settings))

    def test_documented_default_values(self):
        _, out, _ = compile_probe([])
        values = parse(out)
        self.assertEqual(values["MOTOR_DUTY_MAX"], "128")
        self.assertEqual(values["MOTOR_MAX_RUN_MS"], "2500")
        self.assertEqual(values["PLAYER_LED_BRIGHTNESS"], "64")
        self.assertEqual(values["SERVO_GAME_OVER_EXTEND_ANGLE"], "90")

    def test_command_line_override_wins_over_the_header_defaults(self):
        code, out, err = compile_probe(
            ["-DNO_SETTINGS", "-DMOTOR_DUTY_MAX=64U", "-DPLAYER_LED_BRIGHTNESS=32U"]
        )
        self.assertEqual(code, 0, err)
        values = parse(out)
        self.assertEqual(values["MOTOR_DUTY_MAX"], "64")
        self.assertEqual(values["PLAYER_LED_BRIGHTNESS"], "32")

    def test_edited_settings_file_changes_the_values(self):
        text = SETTINGS.read_text(encoding="utf-8")
        edited = text.replace("#define MOTOR_DUTY_MAX 128U", "#define MOTOR_DUTY_MAX 100U").replace(
            "#define SETTING_AUDIO_VOLUME 3U", "#define SETTING_AUDIO_VOLUME 9U"
        )
        self.assertNotEqual(text, edited)
        with tempfile.TemporaryDirectory() as tmp:
            sketch = Path(tmp) / "alien-simon-says"
            sketch.mkdir()
            for header in (ROOT / "alien-simon-says").glob("*.h"):
                shutil.copy(header, sketch / header.name)
            (sketch / "game_settings.h").write_text(edited, encoding="utf-8")
            tests = Path(tmp) / "tests"
            tests.mkdir()
            shutil.copy(PROBE, tests / PROBE.name)
            exe = Path(tmp) / "probe.exe"
            build = subprocess.run(
                [GCC, "-std=c99", "-Wall", "-Wextra", "-Werror", str(tests / PROBE.name), "-o", str(exe)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            ran = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(parse(ran.stdout)["MOTOR_DUTY_MAX"], "100")

    def test_out_of_range_values_stop_the_compile(self):
        cases = [
            ["-DMOTOR_DUTY_MAX=300U"],
            ["-DMOTOR_DUTY_MAX=0U"],
            ["-DMOTOR_MAX_RUN_MS=7000UL"],
            ["-DMOTOR_MAX_RUN_MS=400UL"],  # smaller than lead + ramp
            ["-DPLAYER_LED_BRIGHTNESS=300U"],
            ["-DSERVO_GAME_OVER_EXTEND_ANGLE=200U"],
            ["-DSETTING_AUDIO_VOLUME=31U"],
        ]
        for args in cases:
            with self.subTest(args=args):
                # The header defaults are bypassed by pre-defining the macro, so the
                # checks in game_settings.h must reject the bad value.
                name = args[0][2:].split("=")[0]
                value = args[0].split("=", 1)[1]
                patched = re.sub(
                    r"#define %s \S+" % name,
                    "#define %s %s" % (name, value),
                    SETTINGS.read_text(encoding="utf-8"),
                    count=1,
                )
                self.assertIn("%s %s" % (name, value), patched)
                with tempfile.TemporaryDirectory() as tmp:
                    (Path(tmp) / "game_settings.h").write_text(patched, encoding="utf-8")
                    src = Path(tmp) / "p.c"
                    src.write_text(
                        '#include "game_settings.h"\n' + "int main(void){return 0;}\n",
                        encoding="utf-8",
                    )
                    build = subprocess.run(
                        [GCC, "-std=c99", "-fsyntax-only", str(src)], capture_output=True, text=True
                    )
                    self.assertNotEqual(build.returncode, 0, "accepted bad value %s" % args)
                    self.assertIn("error", build.stderr)


if __name__ == "__main__":
    unittest.main()
