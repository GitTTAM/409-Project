"""Check classroom syntax, clear errors, and saving then reading a grammar back."""

from pathlib import Path
import random
import tempfile
import unittest

from cfg_toolkit import (
    Grammar,
    GrammarError,
    Production,
    dumps_grammar,
    dumps_lecture,
    format_lecture,
    loads_document,
    loads_lecture,
    read_document,
    write_document,
)


ROOT = Path(__file__).resolve().parents[1]


class LectureParserTests(unittest.TestCase):
    def test_bare_classroom_rules_infer_symbols_and_first_start(self):
        grammar = loads_lecture("S -> ASA | aB\nA -> B | S\nB -> b | epsilon")
        self.assertEqual(grammar.variables, {"S", "A", "B"})
        self.assertEqual(grammar.terminals, {"a", "b"})
        self.assertEqual(grammar.start, "S")
        self.assertIn(Production("S", ("A", "S", "A")), grammar.productions)
        self.assertIn(Production("B", ()), grammar.productions)

    def test_declarations_keep_unused_symbols_and_explicit_start(self):
        grammar = loads_lecture(
            "Variables: A S Dead\nTerminals: a b\nStart: S\nA -> a\nS -> A"
        )
        self.assertEqual(grammar.variables, {"A", "S", "Dead"})
        self.assertEqual(grammar.terminals, {"a", "b"})
        self.assertEqual(grammar.start, "S")

    def test_unicode_arrow_sigma_and_epsilon_spellings(self):
        for marker in ("epsilon", "eps", "\u03b5", "\u03f5", "''", '""'):
            with self.subTest(marker=marker):
                grammar = loads_lecture(
                    "V = {S}\n\u03a3 = {a, b}\nS = S\nS \u2192 aSb | " + marker
                )
                self.assertEqual(
                    grammar.productions,
                    {Production("S", ("a", "S", "b")), Production("S", ())},
                )

    def test_multiword_names_and_single_quoted_terminals(self):
        grammar = loads_lecture("Expr -> Expr '+' Term | Term\nTerm -> 'id'")
        self.assertEqual(grammar.variables, {"Expr", "Term"})
        self.assertEqual(grammar.terminals, {"+", "id"})
        self.assertIn(Production("Expr", ("Expr", "+", "Term")), grammar.productions)

    def test_parentheses_are_literal_terminals(self):
        grammar = loads_lecture("F -> (E) | a\nE -> F")
        self.assertIn(Production("F", ("(", "E", ")")), grammar.productions)
        self.assertTrue({"(", ")"} <= grammar.terminals)

    def test_helper_names_and_declared_multichar_terminals_stay_whole(self):
        grammar = loads_lecture(
            "V={S0,S,Z1,X_a}\nSigma={id,a}\nStart=S0\nS0 -> X_aZ1\nS -> id\nZ1 -> S\nX_a -> a"
        )
        self.assertIn(Production("S0", ("X_a", "Z1")), grammar.productions)
        self.assertIn(Production("S", ("id",)), grammar.productions)

    def test_hash_terminal_and_quoted_comment_or_alternation_symbols(self):
        grammar = loads_lecture("// heading\nS -> # | '//' | '|' // trailing comment")
        self.assertEqual(grammar.terminals, {"#", "//", "|"})
        self.assertEqual(len(grammar.productions), 3)

    def test_continuations_and_repeated_rules(self):
        grammar = loads_lecture("S -> a\n | b\n | epsilon\nS -> a")
        self.assertEqual(
            grammar.productions,
            {Production("S", ("a",)), Production("S", ("b",)), Production("S", ())},
        )

    def test_empty_language_and_epsilon_only_with_explicit_headers(self):
        empty = loads_lecture("V={S}\nSigma={}\nStart=S")
        self.assertEqual(empty.productions, set())
        self.assertEqual(empty.terminals, set())
        only_epsilon = loads_lecture("V={S}\nSigma={}\nStart=S\nS -> epsilon")
        self.assertEqual(only_epsilon.productions, {Production("S", ())})

    def test_exact_declared_symbol_wins_and_spaces_force_separate_symbols(self):
        grammar = loads_lecture(
            "V={S,A,B,AB}\nSigma={a}\nStart=S\nS -> AB | A B\nA -> a\nB -> a\nAB -> a"
        )
        self.assertIn(Production("S", ("AB",)), grammar.productions)
        self.assertIn(Production("S", ("A", "B")), grammar.productions)

    def test_ambiguous_compact_run_requires_spaces(self):
        header = "V={S,A,B,C,AB}\nSigma={a}\nStart=S\n"
        with self.assertRaisesRegex(GrammarError, "ambiguous compact RHS"):
            loads_lecture(header + "S -> ABCa")
        grammar = loads_lecture(header + "S -> AB C a | A B C a")
        self.assertEqual(len(grammar.productions), 2)

    def test_declared_digit_terminal_can_make_helper_sequence_ambiguous(self):
        header = "V={S,S0}\nSigma={0}\nStart=S\n"
        with self.assertRaisesRegex(GrammarError, "ambiguous compact RHS"):
            loads_lecture(header + "S -> S0S")
        self.assertIn(
            Production("S", ("S0", "S")),
            loads_lecture(header + "S -> S0 S").productions,
        )

    def test_unknown_symbol_and_unknown_uppercase_are_rejected(self):
        for text in (
            "S -> Missing",
            "V={S}\nSigma={a}\nStart=S\nS -> b",
            "V={S}\nSigma={a}\nStart=S\nS -> 'b'",
        ):
            with self.subTest(text=text), self.assertRaises(GrammarError):
                loads_lecture(text)

    def test_epsilon_cannot_be_mixed_into_a_sequence(self):
        for rhs in ("a \u03b5", "\u03b5a", "a ''", "epsilon a", "eps S"):
            with self.subTest(rhs=rhs), self.assertRaisesRegex(
                GrammarError, "epsilon must be the entire alternative"
            ):
                loads_lecture("S -> " + rhs)

    def test_bare_e_is_an_ordinary_terminal(self):
        grammar = loads_lecture("S -> e")
        self.assertEqual(grammar.productions, {Production("S", ("e",))})

    def test_missing_alternative_or_arrow_reports_line(self):
        for line in ("S ->", "S -> a |", "S -> | a", "S -> a || b", "S a", "| a"):
            with self.subTest(line=line), self.assertRaisesRegex(
                GrammarError, "line 1:"
            ):
                loads_lecture(line)

    def test_bad_declarations_are_rejected(self):
        cases = (
            "V={S,S}\nS -> a",
            "V={S}\nSigma={S}\nS -> S",
            "Start=A\nS -> a",
            "V={S}\nV={S}\nS -> a",
            "V={S,,A}\nS -> a",
            "V={S,}\nS -> a",
            "V={S\nS -> a",
            "V={S}\nStart=S A\nS -> a",
            "Unknown={S}\nS -> a",
            "S -> a\nSigma={a}",
            "V={S}\nSigma={a}\nStart=S\nA -> a",
        )
        for text in cases:
            with self.subTest(text=text), self.assertRaises(GrammarError):
                loads_lecture(text)

    def test_bad_quotes_and_extra_arrow_rejected(self):
        for text in ("S -> 'a", 'S -> "a', "S -> 'a' -> b", "S A -> a"):
            with self.subTest(text=text), self.assertRaisesRegex(
                GrammarError, "line 1:"
            ):
                loads_lecture(text)

    def test_empty_document_needs_a_start(self):
        with self.assertRaisesRegex(GrammarError, "no start variable"):
            loads_lecture("// only a comment")


class LectureFormattingTests(unittest.TestCase):
    def test_classroom_output_groups_alternatives_and_remains_parseable(self):
        grammar = loads_lecture("S -> aSb | epsilon")
        text = dumps_lecture(grammar)
        self.assertIn("S \u2192 \u03b5 | aSb", text)
        self.assertEqual(loads_lecture(text), grammar)
        self.assertIn("S -> epsilon | aSb", format_lecture(grammar))

    def test_ambiguous_compaction_falls_back_to_spaces(self):
        grammar = Grammar(
            ["S", "A", "B", "AB"],
            ["a"],
            [Production("S", ("A", "B")), Production("AB", ("a",))],
            "S",
        )
        text = dumps_lecture(grammar, unicode_symbols=False)
        self.assertIn("S -> A B", text)
        self.assertEqual(loads_lecture(text), grammar)

    def test_quotes_preserve_punctuation_unicode_and_reserved_text_tokens(self):
        terminals = [
            "|",
            "//",
            "->",
            ",",
            "{",
            "}",
            "'",
            '"',
            "\\",
            "eps",
            "\u03f5",
            "\u03a9",
        ]
        grammar = Grammar(
            ["\u0393", "Unused"],
            terminals,
            [Production("\u0393", tuple(terminals)), Production("\u0393", ())],
            "\u0393",
        )
        self.assertEqual(loads_lecture(dumps_lecture(grammar)), grammar)

    def test_empty_and_epsilon_only_documents_roundtrip(self):
        for rules in ([], [Production("S", ())]):
            grammar = Grammar(["S"], [], rules, "S")
            self.assertEqual(loads_lecture(dumps_lecture(grammar)), grammar)

    def test_deterministic_grammar_roundtrips_with_overlapping_names(self):
        # A fixed seed gives us varied grammars while keeping failures repeatable.
        rng = random.Random(409)
        variables = ["S", "S0", "A", "B", "AB", "Expr"]
        terminals = ["a", "b", "ab", "+", "(", ")", "id", "|", "//", "eps"]
        alphabet = variables + terminals
        for case in range(80):
            rules = [
                Production(
                    rng.choice(variables),
                    tuple(rng.choice(alphabet) for unused in range(rng.randrange(6))),
                )
                for unused in range(8)
            ]
            grammar = Grammar(variables, terminals, rules, "S")
            with self.subTest(case=case):
                text = dumps_lecture(grammar)
                self.assertEqual(loads_lecture(text), grammar)
                self.assertEqual(dumps_lecture(loads_lecture(text)), text)


class DocumentIoTests(unittest.TestCase):
    def test_json_and_classroom_auto_detection_share_model(self):
        grammar = loads_lecture("S -> aSb | epsilon")
        self.assertEqual(loads_document(dumps_grammar(grammar)), grammar)
        self.assertEqual(loads_document(dumps_lecture(grammar)), grammar)
        with self.assertRaisesRegex(GrammarError, "input format"):
            loads_document("S -> a", "unknown")

    def test_file_roundtrips_for_both_formats_and_bom(self):
        grammar = loads_lecture("S -> aSb | epsilon")
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            for suffix in (".cfg", ".txt", ".grammar", ".json"):
                path = Path(folder) / ("grammar" + suffix)
                write_document(grammar, path)
                self.assertEqual(read_document(path), grammar)
            path = Path(folder) / "bom.cfg"
            path.write_text("\ufeff" + dumps_lecture(grammar), encoding="utf-8")
            self.assertEqual(read_document(path), grammar)

    def test_explicit_format_overrides_extension(self):
        grammar = loads_lecture("S -> a")
        self.assertEqual(
            loads_document(dumps_grammar(grammar), "json", "input.cfg"), grammar
        )
        self.assertEqual(loads_document("S -> a", "lecture", "input.json"), grammar)


if __name__ == "__main__":
    unittest.main()
