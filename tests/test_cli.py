"""Check the JSON commands, saved output, and readable errors users will see."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

from cfg_toolkit import prepare_start, read_grammar
from cfg_toolkit.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments, text=None):
        """Run the real entry point and capture output for assertions."""
        return subprocess.run(
            [sys.executable, "main.py"] + list(arguments),
            cwd=str(ROOT),
            input=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def test_three_demo_runs_display_both_student1_stages(self):
        completed = self.run_cli("--demo")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            completed.stdout.count("Matt Lawrence (grammar input): COMPLETE"), 3
        )
        self.assertEqual(completed.stdout.count("1. Original grammar"), 3)
        self.assertEqual(completed.stdout.count("2. New-start handling"), 3)
        self.assertEqual(completed.stdout.count("not a final CNF result"), 3)
        self.assertIn("S_0 -> S", completed.stdout)

    def test_single_grammar_and_prepared_file_roundtrip(self):
        source = ROOT / "examples" / "02_start_on_rhs.json"
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            target = Path(folder) / "prepared.json"
            completed = self.run_cli(str(source), "--save-prepared", str(target))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                read_grammar(target), prepare_start(read_grammar(source)).grammar
            )

    def test_result_export_is_actual_output_for_devin(self):
        source = ROOT / "examples" / "02_start_on_rhs.json"
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            target = Path(folder) / "after_units.json"
            result = self.run_cli(str(source), "--save-result", str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            expected = run_pipeline(read_grammar(source)).snapshots[-1].grammar
            self.assertEqual(read_grammar(target), expected)
            self.assertIn(
                "Steven Yang (epsilon and unit removal): COMPLETE", result.stdout
            )
            self.assertNotIn("Pending: Steven", result.stdout)
            self.assertIn("Pending: Devin", result.stdout)

    def test_result_export_cannot_overwrite_input(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            target = Path(folder) / "input.json"
            original = (ROOT / "examples" / "02_start_on_rhs.json").read_bytes()
            target.write_bytes(original)
            result = self.run_cli(str(target), "--save-result", str(target))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_bytes(), original)

    def test_original_cannot_be_overwritten_by_prepared_output(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            target = Path(folder) / "input.json"
            original = (ROOT / "examples" / "02_start_on_rhs.json").read_bytes()
            target.write_bytes(original)
            completed = self.run_cli(str(target), "--save-prepared", str(target))
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(target.read_bytes(), original)
            self.assertIn("must not overwrite", completed.stderr)

    def test_json_stdin(self):
        text = (ROOT / "examples" / "03_multichar_unit.json").read_text(
            encoding="utf-8"
        )
        completed = self.run_cli("--stdin", text=text)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('Term -> "id"', completed.stdout)

    def test_bad_input_is_readable_and_never_claims_success(self):
        for arguments in (
            ("examples/invalid/undeclared_symbol.json",),
            ("does-not-exist.json",),
        ):
            with self.subTest(arguments=arguments):
                completed = self.run_cli(*arguments)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("Input/output error:", completed.stderr)
                self.assertNotIn("Traceback", completed.stderr)
                self.assertNotIn(
                    "Matt Lawrence (grammar input): COMPLETE", completed.stdout
                )

    def test_cnf_valid_invalid_and_source_comparison_exit_codes(self):
        good = self.run_cli("--check-cnf", "examples/04_already_cnf.json")
        bad = self.run_cli("--check-cnf", "examples/03_multichar_unit.json")
        epsilon_lost = self.run_cli(
            "--check-cnf",
            "examples/04_already_cnf.json",
            "--source",
            "examples/05_cnf_with_epsilon.json",
        )
        self.assertEqual(good.returncode, 0)
        self.assertIn("Structural checks only", good.stdout)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("UNIT_RULE", bad.stdout)
        self.assertEqual(epsilon_lost.returncode, 1)
        self.assertIn("EPSILON_MEMBERSHIP_CHANGED", epsilon_lost.stdout)

    def test_conflicting_and_incomplete_arguments_rejected(self):
        cases = (
            ("examples/04_already_cnf.json", "--demo"),
            ("--stdin", "--demo"),
            ("--source", "examples/04_already_cnf.json"),
            ("--demo", "--save-prepared", "out.json"),
            ("--save-prepared", "out.json"),
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.assertEqual(self.run_cli(*arguments).returncode, 2)

    def test_help_and_module_entry_point(self):
        help_result = self.run_cli()
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--save-prepared", help_result.stdout)
        completed = subprocess.run(
            [sys.executable, "-m", "cfg_toolkit", "examples/07_epsilon_only.json"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("S -> epsilon", completed.stdout)

    def test_unicode_start_and_errors_survive_ascii_console(self):
        data = {
            "variables": ["\u0393"],
            "terminals": ["a"],
            "start": "\u0393",
            "productions": [
                {"lhs": "\u0393", "rhs": ["a", "\u0393"]},
                {"lhs": "\u0393", "rhs": []},
            ],
        }
        environment = dict(os.environ, PYTHONIOENCODING="ascii")
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            path = Path(folder) / "unicode.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "main.py", str(path)],
                cwd=str(ROOT),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("\\u0393_0", completed.stdout)
            data["productions"][0]["rhs"] = ["\u03a9"]
            path.write_text(json.dumps(data), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "main.py", str(path)],
                cwd=str(ROOT),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("undeclared RHS symbols", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)


if __name__ == "__main__":
    unittest.main()
