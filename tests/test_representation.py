"""Check the shared grammar model, JSON input, and errors for invalid data."""

import copy
from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest

from cfg_toolkit import (
    Grammar,
    GrammarError,
    Production,
    dumps_grammar,
    format_grammar,
    from_dict,
    loads_grammar,
    read_grammar,
    to_dict,
    write_grammar,
)


ROOT = Path(__file__).resolve().parents[1]


def valid_data():
    """A small valid grammar to copy and change in input-validation tests."""
    return {
        "variables": ["Start", "Term"],
        "terminals": ["id"],
        "start": "Start",
        "productions": [
            {"lhs": "Start", "rhs": ["Term"]},
            {"lhs": "Term", "rhs": ["id"]},
        ],
    }


class RepresentationTests(unittest.TestCase):
    def test_g_tuple_and_multichar_tokens(self):
        grammar = from_dict(valid_data())
        self.assertEqual(grammar.variables, {"Start", "Term"})
        self.assertEqual(grammar.terminals, {"id"})
        self.assertEqual(grammar.start, "Start")
        self.assertIn(Production("Term", ("id",)), grammar.productions)
        self.assertNotIn(Production("Term", ("i", "d")), grammar.productions)

    def test_input_collections_cannot_mutate_a_grammar(self):
        data = valid_data()
        grammar = from_dict(data)
        before = dumps_grammar(grammar)
        data["variables"].append("Other")
        data["productions"][0]["rhs"].append("Other")
        self.assertEqual(dumps_grammar(grammar), before)
        with self.assertRaises(FrozenInstanceError):
            grammar.start = "Term"
        with self.assertRaises(AttributeError):
            grammar.variables.add("Other")

    def test_production_freezes_rhs_and_is_hashable(self):
        tokens = ["id"]
        rule = Production("Term", tokens)
        tokens.append("id")
        self.assertEqual(rule.rhs, ("id",))
        self.assertEqual(len({rule, Production("Term", ("id",))}), 1)

    def test_duplicate_rules_are_set_members_not_extra_rules(self):
        data = valid_data()
        data["productions"].append(copy.deepcopy(data["productions"][0]))
        self.assertEqual(len(from_dict(data).productions), 2)

    def test_epsilon_is_empty_rhs(self):
        data = valid_data()
        data["productions"].append({"lhs": "Start", "rhs": []})
        grammar = from_dict(data)
        self.assertIn(Production("Start", ()), grammar.productions)
        self.assertIn("Start -> epsilon", format_grammar(grammar))

    def test_empty_language_and_empty_alphabet_are_legal(self):
        grammar = Grammar(["S"], [], [], "S")
        self.assertIn("language is empty", format_grammar(grammar))
        self.assertEqual(loads_grammar(dumps_grammar(grammar)), grammar)

    def test_unused_or_unproductive_variables_are_legal_input(self):
        grammar = Grammar(["S", "Unused"], ["a"], [Production("S", ("a",))], "S")
        self.assertIn("Unused", grammar.variables)

    def test_roundtrip_and_deterministic_display(self):
        data = valid_data()
        grammar = from_dict(data)
        self.assertEqual(loads_grammar(dumps_grammar(grammar)), grammar)
        self.assertEqual(from_dict(to_dict(grammar)), grammar)
        data["variables"].reverse()
        data["productions"].reverse()
        self.assertEqual(format_grammar(from_dict(data)), format_grammar(grammar))

    def test_file_roundtrip_utf8_bom_and_symbols(self):
        grammar = Grammar(["\u0393"], ["+"], [Production("\u0393", ("+",))], "\u0393")
        self.assertIn('"\\u0393"', format_grammar(grammar))
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            path = Path(folder) / "grammar.json"
            path.write_text("\ufeff" + dumps_grammar(grammar), encoding="utf-8")
            self.assertEqual(read_grammar(path), grammar)
            write_grammar(grammar, path)
            self.assertEqual(read_grammar(path), grammar)

    def test_every_supplied_example_is_valid(self):
        for path in (ROOT / "examples").glob("*.json"):
            with self.subTest(path=path.name):
                self.assertIsInstance(read_grammar(path), Grammar)


class InvalidInputTests(unittest.TestCase):
    def assert_bad(self, data, message):
        with self.assertRaisesRegex(GrammarError, message):
            from_dict(data)

    def test_required_and_unknown_fields(self):
        data = valid_data()
        del data["start"]
        self.assert_bad(data, "missing fields: start")
        data = valid_data()
        data["start_symbol"] = "Start"
        self.assert_bad(data, "unknown fields: start_symbol")

    def test_root_and_collection_types(self):
        for data in ([], None, "grammar", 10):
            with self.subTest(data=data):
                self.assert_bad(data, "grammar must be an object")
        for field in ("variables", "terminals", "productions"):
            data = valid_data()
            data[field] = "not a list"
            self.assert_bad(data, "must be a JSON array")

    def test_empty_variables_and_undeclared_start(self):
        data = valid_data()
        data["variables"] = []
        self.assert_bad(data, "at least the start")
        data = valid_data()
        data["start"] = "Missing"
        self.assert_bad(data, "not a declared variable")

    def test_start_must_be_a_symbol(self):
        for start in (None, "", 2, ["Start"]):
            data = valid_data()
            data["start"] = start
            with self.subTest(start=start):
                self.assert_bad(data, "start must be a nonempty string")

    def test_alphabets_must_be_disjoint(self):
        data = valid_data()
        data["terminals"].append("Start")
        self.assert_bad(data, "must be disjoint")

    def test_duplicate_declarations_rejected(self):
        for field in ("variables", "terminals"):
            data = valid_data()
            data[field].append(data[field][0])
            self.assert_bad(data, "duplicate declarations")

    def test_bad_symbol_names_rejected(self):
        for symbol in ("", "a b", "\n", "a\t", "\x00", None, 1, "epsilon", "\u03b5"):
            data = valid_data()
            data["terminals"].append(symbol)
            with self.subTest(symbol=symbol), self.assertRaises(GrammarError):
                from_dict(data)

    def test_rhs_must_be_token_array_not_concatenated_text(self):
        for rhs in ("Term", "", None, {"Term": 1}):
            data = valid_data()
            data["productions"][0]["rhs"] = rhs
            self.assert_bad(data, "must be a token array")

    def test_undeclared_rhs_and_terminal_lhs_rejected(self):
        data = valid_data()
        data["productions"][0]["rhs"] = ["Missing"]
        self.assert_bad(data, "undeclared RHS symbols: Missing")
        data = valid_data()
        data["productions"][0]["lhs"] = "id"
        self.assert_bad(data, "lhs 'id' is not a declared variable")

    def test_production_fields_and_types(self):
        for item in (
            [],
            "Start -> Term",
            {"lhs": "Start"},
            {"lhs": "Start", "rhs": [], "extra": 1},
        ):
            data = valid_data()
            data["productions"] = [item]
            with self.subTest(item=item), self.assertRaises(GrammarError):
                from_dict(data)

    def test_pseudo_epsilon_cannot_be_mixed_with_symbols(self):
        data = valid_data()
        data["productions"][0]["rhs"] = ["epsilon", "id"]
        self.assert_bad(data, "epsilon is represented by an empty RHS")

    def test_bad_json_reports_line_and_column(self):
        with self.assertRaisesRegex(GrammarError, "line 2, column"):
            loads_grammar('{\n "variables": [}')

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(GrammarError, "duplicate JSON field 'start'"):
            loads_grammar('{"start":"A","start":"B"}')
        with self.assertRaisesRegex(GrammarError, "duplicate JSON field 'rhs'"):
            loads_grammar('{"rule":{"rhs":[],"rhs":["a"]}}')

    def test_direct_api_does_not_bypass_validation(self):
        cases = (
            lambda: Production("S", "AB"),
            lambda: Grammar("Start", [], [], "Start"),
            lambda: Grammar(["S"], [], ["S -> a"], "S"),
            lambda: Grammar(["S"], [], [Production("S", ("a",))], "S"),
        )
        for build in cases:
            with self.assertRaises(GrammarError):
                build()

    def test_missing_file_and_invalid_encoding_are_explained(self):
        with tempfile.TemporaryDirectory(dir=str(ROOT)) as folder:
            path = Path(folder) / "missing.json"
            with self.assertRaisesRegex(GrammarError, "missing.json"):
                read_grammar(path)
            path.write_bytes(b"\xff\xff")
            with self.assertRaises(GrammarError):
                read_grammar(path)


if __name__ == "__main__":
    unittest.main()
