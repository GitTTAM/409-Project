"""Check that the handoff files are real, readable output from Steven's stages."""

from pathlib import Path
import tempfile
import unittest

from cfg_toolkit import read_document
from cfg_toolkit.pipeline import run_pipeline
from tests.support import bounded_language
from tools.prepare_devin import EXAMPLES, ROOT, prepare_examples


class DevinExampleTests(unittest.TestCase):
    def test_saved_examples_roundtrip_and_preserve_original_words(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = prepare_examples(Path(folder) / "for_devin")
            self.assertEqual(len(paths), 3)
            for name, path in zip(EXAMPLES, paths):
                with self.subTest(example=name):
                    original = read_document(ROOT / "examples" / (name + ".json"))
                    expected = next(
                        step.grammar
                        for step in run_pipeline(original).snapshots
                        if step.stage == "remove_units"
                    )
                    saved = read_document(path)
                    self.assertEqual(saved, expected)
                    self.assertEqual(
                        bounded_language(saved), bounded_language(original)
                    )
                    self.assertFalse(saved.start_on_rhs)
                    self.assertFalse(
                        any(
                            len(r.rhs) == 1 and r.rhs[0] in saved.variables
                            for r in saved.productions
                        )
                    )


if __name__ == "__main__":
    unittest.main()
