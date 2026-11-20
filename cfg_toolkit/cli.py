"""Read command options, then hand the grammar work to the toolkit modules."""

import argparse
from pathlib import Path
import sys

from .cnf_validator import format_cnf_report, validate_cnf
from .document_io import detect_format, loads_document, read_document, write_document
from .grammar_io import format_grammar
from .lecture import format_lecture
from .model import GrammarError
from .pipeline import STAGES, run_pipeline


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ("01_nullable_blocks.json", "02_start_on_rhs.json", "03_multichar_unit.json")
LECTURE_EXAMPLES = (
    "01_marker.cfg",
    "02_arithmetic.cfg",
    "03_matching.cfg",
    "04_concatenation.cfg",
    "05_nullable_units.cfg",
    "06_matching_final_cnf.cfg",
)


def _formatter(display: str):
    """Choose a display function that also works in older Windows consoles."""
    if display != "lecture":
        return format_grammar

    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "\u2192\u03b5".encode(encoding)
        unicode_symbols = True
    except (UnicodeError, LookupError):
        unicode_symbols = False

    def show_lecture(grammar, title):
        return format_lecture(grammar, title, unicode_symbols)

    return show_lecture


def _choose_display(requested: str, input_format: str) -> str:
    if requested != "auto":
        return requested
    if input_format == "lecture":
        return "lecture"
    return "tokens"


def render_setup(grammar, display: str = "tokens") -> str:
    """Show every available step and list the stages still missing."""
    result = run_pipeline(grammar)
    formatter = _formatter(display)
    parts = []
    for snapshot in result.snapshots:
        parts.append(formatter(snapshot.grammar, snapshot.title))
        if snapshot.explanation:
            parts.append(snapshot.explanation)
    parts.append("Matt Lawrence (grammar input): COMPLETE for this input.")
    parts.append("Steven Yang (epsilon and unit removal): COMPLETE for this input.")
    parts.append(
        "Conversion status: PENDING transformations from Devin Finn; this is not a final CNF result."
    )
    labels = dict(STAGES)
    parts.extend("  Pending: " + labels[stage] for stage in result.pending)
    return "\n\n".join(parts)


def _build_parser() -> argparse.ArgumentParser:
    """Keep command options in one place so new ones are easy to find."""
    parser = argparse.ArgumentParser(
        description="Option 1: read a grammar, prepare its start, and remove epsilon and unit rules."
    )
    parser.add_argument(
        "grammar", nargs="?", help="path to a JSON or classroom grammar file"
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--demo",
        action="store_true",
        help="show three demonstration runs for Matt Lawrence's part",
    )
    modes.add_argument(
        "--demo-lecture",
        action="store_true",
        help="show all six professor-based grammar fixtures",
    )
    modes.add_argument(
        "--stdin",
        action="store_true",
        help="read JSON or classroom notation from standard input",
    )
    modes.add_argument(
        "--check-cnf", metavar="FILE", help="validate an existing grammar's CNF shape"
    )
    parser.add_argument(
        "--source",
        metavar="FILE",
        help="original grammar for --check-cnf epsilon comparison",
    )
    saves = parser.add_mutually_exclusive_group()
    saves.add_argument(
        "--save-prepared",
        metavar="FILE",
        help="save prepared grammar; .cfg/.txt/.grammar use lecture notation, otherwise JSON",
    )
    saves.add_argument(
        "--save-result",
        metavar="FILE",
        help="save the latest completed step as input for Devin's work",
    )
    parser.add_argument(
        "--format",
        choices=("auto", "json", "lecture"),
        default="auto",
        help="primary input format (default: detect by extension/content)",
    )
    parser.add_argument(
        "--display",
        choices=("auto", "tokens", "lecture"),
        default="auto",
        help="output notation (default: follows input format)",
    )
    return parser


def _check_arguments(parser, args) -> None:
    """Catch option combinations that argparse cannot check by itself."""
    if args.grammar and (
        args.demo or args.demo_lecture or args.stdin or args.check_cnf
    ):
        parser.error(
            "a grammar file cannot be combined with a demo, --stdin, or --check-cnf"
        )
    if args.source and not args.check_cnf:
        parser.error("--source requires --check-cnf")
    saving = args.save_prepared or args.save_result
    if saving and (args.demo or args.demo_lecture or args.check_cnf):
        parser.error("saving requires a grammar file or --stdin")
    if saving and not (args.grammar or args.stdin):
        parser.error("saving requires a grammar file or --stdin")
    if (args.demo or args.demo_lecture) and args.format != "auto":
        parser.error(
            "--format applies to a grammar file or --stdin; demos select their fixture formats"
        )


def _run_cnf_check(args) -> int:
    candidate = read_document(args.check_cnf, args.format)
    source = read_document(args.source) if args.source else None
    report = validate_cnf(candidate, source)

    input_format = args.format
    if input_format == "auto":
        text = Path(args.check_cnf).read_text(encoding="utf-8-sig")
        input_format = detect_format(text, args.check_cnf)
    display = _choose_display(args.display, input_format)
    print(_formatter(display)(candidate, "Candidate CNF grammar"))
    print()
    print(format_cnf_report(report))
    return 0 if report.is_valid else 1


def _run_demos(args) -> int:
    directory = ROOT / "examples"
    filenames = EXAMPLES
    input_format = "json"
    if args.demo_lecture:
        directory = directory / "lecture"
        filenames = LECTURE_EXAMPLES
        input_format = "lecture"

    display = _choose_display(args.display, input_format)
    for index, filename in enumerate(filenames, 1):
        path = directory / filename
        relative = path.relative_to(ROOT).as_posix()
        print("DEMO {} OF {} | {}".format(index, len(filenames), relative))
        print(render_setup(read_document(path), display))
        print("\n" + "=" * 76 + "\n")
    return 0


def _run_input(args) -> int:
    if args.stdin:
        text = sys.stdin.read()
    else:
        text = Path(args.grammar).read_text(encoding="utf-8-sig")

    input_format = args.format
    if input_format == "auto":
        input_format = detect_format(text, args.grammar)
    grammar = loads_document(text, input_format)
    display = _choose_display(args.display, input_format)

    # Check before printing success or writing anything to the output file.
    output = args.save_prepared or args.save_result
    if output and args.grammar:
        source_path = Path(args.grammar).resolve()
        output_path = Path(output).resolve()
        if source_path == output_path:
            raise GrammarError(
                "output must not overwrite the input grammar; choose another file"
            )

    print(render_setup(grammar, display))
    if args.save_prepared:
        prepared = run_pipeline(grammar, {}).snapshots[-1].grammar
        write_document(prepared, args.save_prepared)
        print("\nSaved start-prepared grammar to {}".format(args.save_prepared))
    if args.save_result:
        current = run_pipeline(grammar).snapshots[-1].grammar
        write_document(current, args.save_result)
        print("\nSaved grammar after unit removal to {}".format(args.save_result))
    return 0


def main(argv=None) -> int:
    """Route a command and return its exit status: 0 success, 1 failed CNF, 2 error."""
    # Redirected Windows output may use a code page that cannot print every name.
    # Show unsupported characters as escapes instead of crashing.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    parser = _build_parser()
    args = parser.parse_args(argv)
    _check_arguments(parser, args)
    if not (
        args.grammar or args.demo or args.demo_lecture or args.stdin or args.check_cnf
    ):
        parser.print_help()
        return 0

    try:
        if args.check_cnf:
            return _run_cnf_check(args)
        if args.demo or args.demo_lecture:
            return _run_demos(args)
        return _run_input(args)
    except (GrammarError, OSError, UnicodeError) as error:
        print("Input/output error: {}".format(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
