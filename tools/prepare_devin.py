"""Save three real grammars after Steven's steps, ready for Devin to use."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cfg_toolkit import dumps_lecture, read_document
from cfg_toolkit.pipeline import run_pipeline


EXAMPLES = ("01_nullable_blocks", "02_start_on_rhs", "03_multichar_unit")


def prepare_examples(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for name in EXAMPLES:
        original = read_document(ROOT / "examples" / (name + ".json"))
        result = run_pipeline(original)
        # Pick this named snapshot so rerunning later cannot accidentally save
        # the final CNF output as an example of Steven's intermediate result.
        grammar = next(
            step.grammar for step in result.snapshots if step.stage == "remove_units"
        )
        path = output / (name + ".cfg")
        path.write_text(dumps_lecture(grammar), encoding="utf-8")
        paths.append(path)
    return paths


def main():
    for path in prepare_examples(ROOT / "examples" / "for_devin"):
        print("Saved " + path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
