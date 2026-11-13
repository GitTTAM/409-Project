"""Save fresh demo output and test results in sample_runs.

Add another (output name, input file, expected exit status) entry to CASES
when a new example should be included in the handoff.
"""

from pathlib import Path
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "sample_runs"
CASES = (
    ("01_nullable_blocks", "examples/01_nullable_blocks.json", 0),
    ("02_start_on_rhs", "examples/02_start_on_rhs.json", 0),
    ("03_multichar_unit", "examples/03_multichar_unit.json", 0),
    ("04_invalid_undeclared", "examples/invalid/undeclared_symbol.json", 2),
    ("lecture_01_marker", "examples/lecture/01_marker.cfg", 0),
    ("lecture_02_arithmetic", "examples/lecture/02_arithmetic.cfg", 0),
    ("lecture_03_matching", "examples/lecture/03_matching.cfg", 0),
    ("lecture_04_concatenation", "examples/lecture/04_concatenation.cfg", 0),
    ("lecture_05_nullable_units", "examples/lecture/05_nullable_units.cfg", 0),
    ("lecture_06_final_cnf_fixture", "examples/lecture/06_matching_final_cnf.cfg", 0),
    ("practice_token_names", "examples/practice/token_names.cfg", 0),
    ("practice_isolated_start", "examples/practice/isolated_start.cfg", 0),
    ("practice_ambiguous_input", "examples/practice/ambiguous.cfg", 2),
)


def execute(arguments, expected):
    """Run a command with this Python and check its exit status before saving it."""
    completed = subprocess.run(
        [sys.executable] + arguments,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    # Some examples should fail: invalid input returns 2, and failed CNF returns 1.
    if completed.returncode != expected:
        raise RuntimeError(
            "{} returned {}, expected {}:\n{}".format(
                " ".join(arguments), completed.returncode, expected, completed.stdout
            )
        )
    header = (
        "Command: python3.14 {}\nPython: {} ({}-bit)\n"
        "Actual interpreter: {}\nExit status: {}\n\n"
    ).format(
        " ".join(arguments),
        sys.version.split()[0],
        8 * struct.calcsize("P"),
        sys.executable,
        completed.returncode,
    )
    return header + completed.stdout


def main():
    OUTPUT.mkdir(exist_ok=True)
    for name, filename, status in CASES:
        original = (ROOT / filename).read_text(encoding="utf-8")
        label = "JSON" if filename.endswith(".json") else "LECTURE NOTATION"
        output = "INPUT {}: {}\n{}\nPROGRAM OUTPUT\n{}".format(
            label, filename, original, execute(["main.py", filename], status)
        )
        (OUTPUT / (name + ".txt")).write_text(output, encoding="utf-8")
        print("Saved sample_runs/{}.txt".format(name), flush=True)
    for name, arguments, status in (
        ("05_cnf_pass", ["main.py", "--check-cnf", "examples/04_already_cnf.json"], 0),
        (
            "06_cnf_fail",
            ["main.py", "--check-cnf", "examples/03_multichar_unit.json"],
            1,
        ),
        (
            "lecture_cnf_check",
            [
                "main.py",
                "--check-cnf",
                "examples/lecture/06_matching_final_cnf.cfg",
                "--source",
                "examples/lecture/03_matching.cfg",
            ],
            0,
        ),
        ("test_results", ["-m", "unittest", "discover", "-s", "tests", "-v"], 0),
        ("role2_cases", ["tools/check_role2.py", "--list-cases"], 0),
        ("role2_pending", ["tools/check_role2.py", "src.simplify_grammar"], 2),
    ):
        (OUTPUT / (name + ".txt")).write_text(
            execute(arguments, status), encoding="utf-8"
        )
        print("Saved sample_runs/{}.txt".format(name), flush=True)


if __name__ == "__main__":
    main()
