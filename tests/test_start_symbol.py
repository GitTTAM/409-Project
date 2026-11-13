"""Check when a fresh start is needed, name collisions, and language preservation."""

from pathlib import Path
import unittest

from cfg_toolkit import Grammar, Production, prepare_start, read_grammar
from support import bounded_language


ROOT = Path(__file__).resolve().parents[1]


class StartSymbolTests(unittest.TestCase):
    def test_no_wrapper_for_isolated_start_even_when_nullable(self):
        original = read_grammar(ROOT / "examples" / "01_nullable_blocks.json")
        result = prepare_start(original)
        self.assertFalse(result.added)
        self.assertIs(result.grammar, original)
        self.assertIsNone(result.new_start)

    def test_recursive_nullable_start_gets_fresh_wrapper(self):
        original = read_grammar(ROOT / "examples" / "02_start_on_rhs.json")
        result = prepare_start(original)
        self.assertTrue(result.added)
        self.assertEqual(result.new_start, "S_0")
        self.assertEqual(result.grammar.start, "S_0")
        self.assertIn(Production("S_0", ("S",)), result.grammar.productions)
        self.assertEqual(
            result.grammar.productions - original.productions,
            {Production("S_0", ("S",))},
        )
        self.assertFalse(result.grammar.start_on_rhs)

    def test_name_collision_checks_variables_and_terminals(self):
        grammar = Grammar(
            ["S", "S_0"],
            ["S_1", "a"],
            [Production("S", ("S",)), Production("S", ("a",))],
            "S",
        )
        result = prepare_start(grammar)
        self.assertEqual(result.new_start, "S_2")
        self.assertEqual(result.grammar.terminals, grammar.terminals)

    def test_start_in_any_rhs_position_is_detected(self):
        for rhs in (("S", "A"), ("A", "S"), ("a", "S", "a"), ("S", "S")):
            with self.subTest(rhs=rhs):
                grammar = Grammar(
                    ["S", "A"],
                    ["a"],
                    [Production("A", rhs), Production("S", ("a",))],
                    "S",
                )
                self.assertTrue(prepare_start(grammar).added)

    def test_original_is_unchanged_and_preparation_is_idempotent(self):
        original = read_grammar(ROOT / "examples" / "02_start_on_rhs.json")
        before = (
            original.variables,
            original.terminals,
            original.productions,
            original.start,
        )
        once = prepare_start(original)
        twice = prepare_start(once.grammar)
        self.assertEqual(
            (
                original.variables,
                original.terminals,
                original.productions,
                original.start,
            ),
            before,
        )
        self.assertIs(once.original, original)
        self.assertFalse(twice.added)
        self.assertEqual(once.grammar, twice.grammar)

    def test_all_examples_preserve_bounded_terminal_languages(self):
        for path in (ROOT / "examples").glob("*.json"):
            original = read_grammar(path)
            prepared = prepare_start(original).grammar
            with self.subTest(path=path.name):
                self.assertEqual(bounded_language(original), bounded_language(prepared))

    def test_epsilon_only_and_empty_languages_survive(self):
        empty = Grammar(["S"], [], [Production("S", ("S",))], "S")
        epsilon = Grammar(
            ["S"], [], [Production("S", ("S",)), Production("S", ())], "S"
        )
        self.assertEqual(bounded_language(prepare_start(empty).grammar), set())
        self.assertEqual(bounded_language(prepare_start(epsilon).grammar), {()})

    def test_cycles_and_nullable_variables_preserve_language(self):
        grammar = Grammar(
            ["S", "A", "B"],
            ["a"],
            [
                Production("S", ("A", "B")),
                Production("A", ("S",)),
                Production("A", ()),
                Production("B", ("a",)),
                Production("B", ()),
            ],
            "S",
        )
        self.assertEqual(
            bounded_language(grammar),
            {(), ("a",), ("a", "a"), ("a", "a", "a"), ("a", "a", "a", "a")},
        )
        self.assertEqual(
            bounded_language(grammar), bounded_language(prepare_start(grammar).grammar)
        )


if __name__ == "__main__":
    unittest.main()
