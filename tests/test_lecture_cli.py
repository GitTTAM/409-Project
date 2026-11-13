"""Check classroom commands, mixed file formats, and older Windows consoles."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

from cfg_toolkit import prepare_start, read_document, read_grammar


ROOT = Path(__file__).resolve().parents[1]


class LectureCliTests(unittest.TestCase):
    def run_cli(self, *arguments, text=None, ascii_output=False):
        """Use a known output encoding so console behavior is repeatable."""
        encoding = "ascii" if ascii_output else "utf-8"
        environment = dict(os.environ, PYTHONIOENCODING=encoding)
        return subprocess.run(
            [sys.executable, "main.py"] + list(arguments),
            cwd=str(ROOT),
            input=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding=encoding,
            env=environment,
            check=False,
        )

    def test_classroom_file_defaults_to_lecture_display(self):
        result = self.run_cli("examples/lecture/05_nullable_units.cfg")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S \u2192 ASA | aB", result.stdout)
        self.assertIn("Start = S_0", result.stdout)

    def test_json_can_use_classroom_display_and_classroom_can_use_tokens(self):
        lecture = self.run_cli("examples/02_start_on_rhs.json", "--display", "lecture")
        tokens = self.run_cli("examples/lecture/03_matching.cfg", "--display", "tokens")
        self.assertEqual(lecture.returncode, 0, lecture.stderr)
        self.assertIn("S \u2192 \u03b5 | aSb", lecture.stdout)
        self.assertEqual(tokens.returncode, 0, tokens.stderr)
        self.assertIn('S -> "a" S "b"', tokens.stdout)

    def test_unicode_classroom_stdin_auto_detection(self):
        result = self.run_cli("--stdin", text="S \u2192 aSb | \u03b5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S \u2192 \u03b5 | aSb", result.stdout)

    def test_save_prepared_in_classroom_or_json(self):
        source = ROOT / "examples" / "lecture" / "03_matching.cfg"
        expected = prepare_start(read_document(source)).grammar
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            for suffix in (".cfg", ".json"):
                target = Path(folder) / ("prepared" + suffix)
                result = self.run_cli(str(source), "--save-prepared", str(target))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(read_document(target), expected)
                if suffix == ".json":
                    self.assertEqual(read_grammar(target), expected)

    def test_cnf_lecture_candidate_with_lecture_or_json_source(self):
        for source in (
            "examples/lecture/03_matching.cfg",
            "examples/02_start_on_rhs.json",
        ):
            result = self.run_cli(
                "--check-cnf",
                "examples/lecture/06_matching_final_cnf.cfg",
                "--source",
                source,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("CNF checks: PASS", result.stdout)
            self.assertIn("Source epsilon membership checked: True", result.stdout)

    def test_six_lecture_demo_runs_are_explicit_about_conversion_pending(self):
        result = self.run_cli("--demo-lecture")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DEMO 6 OF 6", result.stdout)
        self.assertEqual(
            result.stdout.count("Matt Lawrence (grammar input): COMPLETE"), 6
        )
        self.assertEqual(result.stdout.count("not a final CNF result"), 6)

    def test_ambiguity_is_readable_error_without_success_output(self):
        text = "V={S,A,B,C,AB}\nSigma={a}\nStart=S\nS -> ABCa"
        result = self.run_cli("--stdin", text=text)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ambiguous compact RHS", result.stderr)
        self.assertIn("line 4", result.stderr)
        self.assertNotIn("Matt Lawrence (grammar input): COMPLETE", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_ascii_console_uses_readable_ascii_math(self):
        result = self.run_cli("examples/lecture/03_matching.cfg", ascii_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("S -> epsilon | aSb", result.stdout)
        self.assertNotIn("\\u03b5", result.stdout)

    def test_explicit_format_and_incompatible_demo_arguments(self):
        result = self.run_cli("--stdin", "--format", "lecture", text="S -> a")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_cli("--demo-lecture", "--format", "json")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
