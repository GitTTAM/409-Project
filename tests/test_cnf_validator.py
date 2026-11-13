"""Try each CNF rule shape, plus epsilon preservation and recursive grammars."""

from pathlib import Path
import unittest

from cfg_toolkit import Grammar, Production, read_grammar
from cfg_toolkit.cnf_validator import (
    derives_epsilon,
    format_cnf_report,
    nullable_variables,
    validate_cnf,
)


ROOT = Path(__file__).resolve().parents[1]


class CnfValidatorTests(unittest.TestCase):
    def test_known_cnf_accepted_without_modifying_it(self):
        grammar = read_grammar(ROOT / "examples" / "04_already_cnf.json")
        report = validate_cnf(grammar, source=grammar)
        self.assertTrue(report.is_valid)
        self.assertIs(report.grammar, grammar)
        self.assertTrue(report.source_checked)
        self.assertFalse(report.epsilon_in_source)

    def test_start_epsilon_accepted_when_in_source(self):
        grammar = read_grammar(ROOT / "examples" / "05_cnf_with_epsilon.json")
        self.assertTrue(validate_cnf(grammar, source=grammar).is_valid)

    def test_unit_rule_rejected(self):
        grammar = Grammar(
            ["S", "A"], ["a"], [Production("S", ("A",)), Production("A", ("a",))], "S"
        )
        self.assertIn(
            "UNIT_RULE", {issue.code for issue in validate_cnf(grammar).issues}
        )

    def test_mixed_and_two_terminal_binary_rules_rejected(self):
        for rhs in (("a", "A"), ("A", "a"), ("a", "a")):
            with self.subTest(rhs=rhs):
                grammar = Grammar(["S", "A"], ["a"], [Production("S", rhs)], "S")
                self.assertIn(
                    "BINARY_TERMINAL",
                    {issue.code for issue in validate_cnf(grammar).issues},
                )

    def test_long_rule_rejected(self):
        grammar = Grammar(["S", "A"], [], [Production("S", ("A", "A", "A"))], "S")
        self.assertIn(
            "LONG_RULE", {issue.code for issue in validate_cnf(grammar).issues}
        )

    def test_nonstart_epsilon_and_start_on_rhs_rejected(self):
        grammar = Grammar(
            ["S", "A"], ["a"], [Production("S", ("A", "S")), Production("A", ())], "S"
        )
        self.assertEqual(
            {issue.code for issue in validate_cnf(grammar).issues},
            {"NONSTART_EPSILON", "START_ON_RHS"},
        )

    def test_epsilon_gained_or_lost_rejected_against_source(self):
        no_epsilon = read_grammar(ROOT / "examples" / "04_already_cnf.json")
        has_epsilon = read_grammar(ROOT / "examples" / "05_cnf_with_epsilon.json")
        for candidate, source in ((no_epsilon, has_epsilon), (has_epsilon, no_epsilon)):
            with self.subTest(source_epsilon=derives_epsilon(source)):
                report = validate_cnf(candidate, source)
                self.assertFalse(report.is_valid)
                self.assertIn(
                    "EPSILON_MEMBERSHIP_CHANGED",
                    {issue.code for issue in report.issues},
                )

    def test_nullable_analysis_handles_indirect_epsilon_and_cycles(self):
        grammar = Grammar(
            ["S", "A", "B", "C"],
            ["a"],
            [
                Production("S", ("A", "B")),
                Production("A", ("B",)),
                Production("B", ("A",)),
                Production("B", ()),
                Production("C", ("a",)),
            ],
            "S",
        )
        self.assertEqual(nullable_variables(grammar), {"S", "A", "B"})
        self.assertTrue(derives_epsilon(grammar))

    def test_unproductive_cycle_is_not_nullable(self):
        grammar = Grammar(
            ["S", "A"], [], [Production("S", ("A",)), Production("A", ("S",))], "S"
        )
        self.assertEqual(nullable_variables(grammar), set())

    def test_no_source_does_not_claim_epsilon_permission_verified(self):
        grammar = read_grammar(ROOT / "examples" / "05_cnf_with_epsilon.json")
        report = validate_cnf(grammar)
        self.assertTrue(report.is_valid)
        self.assertFalse(report.source_checked)
        self.assertIn("Structural checks only", format_cnf_report(report))

    def test_report_identifies_offending_rule_and_equivalence_limit(self):
        grammar = read_grammar(ROOT / "examples" / "03_multichar_unit.json")
        text = format_cnf_report(validate_cnf(grammar))
        self.assertIn("Expr -> Term", text)
        self.assertIn("do not prove full language equivalence", text)
        self.assertIn("CNF checks: FAIL", text)

    def test_empty_language_and_epsilon_only_cnf_are_both_accepted(self):
        for name in ("06_empty_language.json", "07_epsilon_only.json"):
            grammar = read_grammar(ROOT / "examples" / name)
            with self.subTest(name=name):
                self.assertTrue(validate_cnf(grammar, source=grammar).is_valid)


if __name__ == "__main__":
    unittest.main()
