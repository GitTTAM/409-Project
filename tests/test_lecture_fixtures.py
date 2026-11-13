"""Check the six grammars from class and compare the short words they produce."""

from pathlib import Path
import unittest

from cfg_toolkit import (
    Production,
    dumps_grammar,
    dumps_lecture,
    loads_document,
    prepare_start,
    read_document,
)
from cfg_toolkit.cnf_validator import nullable_variables, validate_cnf
from support import bounded_language


DIRECTORY = Path(__file__).resolve().parents[1] / "examples" / "lecture"


class ProfessorFixtureTests(unittest.TestCase):
    def test_all_six_transcribed_grammars_have_expected_rules(self):
        cases = (
            ("01_marker.cfg", 3),
            ("02_arithmetic.cfg", 6),
            ("03_matching.cfg", 2),
            ("04_concatenation.cfg", 3),
            ("05_nullable_units.cfg", 6),
            ("06_matching_final_cnf.cfg", 7),
        )
        for name, count in cases:
            with self.subTest(name=name):
                grammar = read_document(DIRECTORY / name)
                self.assertEqual(len(grammar.productions), count)
                self.assertEqual(loads_document(dumps_grammar(grammar)), grammar)
                self.assertEqual(loads_document(dumps_lecture(grammar)), grammar)

    def test_start_preparation_preserves_each_bounded_language(self):
        for path in DIRECTORY.glob("*.cfg"):
            original = read_document(path)
            prepared = prepare_start(original)
            with self.subTest(name=path.name):
                self.assertEqual(
                    bounded_language(original, 4), bounded_language(prepared.grammar, 4)
                )
                self.assertFalse(prepared.grammar.start_on_rhs)
                self.assertEqual(
                    prepared.added, path.name != "06_matching_final_cnf.cfg"
                )

    def test_professor_final_cnf_passes_validator_and_source_comparison(self):
        original = read_document(DIRECTORY / "03_matching.cfg")
        final = read_document(DIRECTORY / "06_matching_final_cnf.cfg")
        self.assertTrue(validate_cnf(final, source=original).is_valid)
        expected = {
            (),
            ("a", "b"),
            ("a", "a", "b", "b"),
            ("a", "a", "a", "b", "b", "b"),
        }
        self.assertEqual(bounded_language(original, 6), expected)
        self.assertEqual(bounded_language(final, 6), expected)

    def test_repeated_nullable_variables_do_not_make_start_nullable(self):
        grammar = read_document(DIRECTORY / "05_nullable_units.cfg")
        self.assertIn(Production("S", ("A", "S", "A")), grammar.productions)
        self.assertEqual(nullable_variables(grammar), {"A", "B"})
        self.assertNotIn((), bounded_language(grammar, 4))

    def test_arithmetic_preserves_literal_parentheses(self):
        grammar = read_document(DIRECTORY / "02_arithmetic.cfg")
        self.assertIn(Production("F", ("(", "E", ")")), grammar.productions)
        words = bounded_language(grammar, 5)
        for text in ("a", "(a)", "a+a", "a*a", "a+a*a"):
            self.assertIn(tuple(text), words)
        for text in ("aa", "+a", "(a", "a)"):
            self.assertNotIn(tuple(text), words)

    def test_concatenation_fixture_contains_both_balanced_patterns(self):
        grammar = read_document(DIRECTORY / "04_concatenation.cfg")
        self.assertEqual(
            bounded_language(grammar, 4),
            {(), ("a", "b"), ("a", "a", "b", "b"), ("a", "b", "a", "b")},
        )


if __name__ == "__main__":
    unittest.main()
