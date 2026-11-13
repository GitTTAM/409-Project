"""Check the handoff tests themselves; Steven's implementation is still pending.

Known answers below are fixture lookups, not conversion code. Broken callbacks
show that a stub or lost epsilon cannot get a false passing result.
"""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from cfg_toolkit import Production
from cfg_toolkit.cnf_validator import nullable_variables
from tests import role2_contract as contract
from tests.support import bounded_language
from tools import check_role2


def known_answer(stage):
    def lookup(grammar):
        for case in contract.EXAMPLES:
            source = case.prepared if stage == "epsilon" else case.after_epsilon
            if grammar == source:
                return case.after_epsilon if stage == "epsilon" else case.after_units
        raise AssertionError("No known answer for this fixture")

    return lookup


class Role2HandoffTests(unittest.TestCase):
    def run_checks(self, epsilon, units, examples=contract.EXAMPLES):
        output = io.StringIO()
        result = unittest.TextTestRunner(stream=output).run(
            contract.make_suite(epsilon, units, examples)
        )
        return result, output.getvalue()

    def test_expected_rules_preserve_the_listed_words_and_epsilon(self):
        for case in contract.EXAMPLES:
            with self.subTest(case=case.name):
                for grammar in (
                    case.original,
                    case.prepared,
                    case.after_epsilon,
                    case.after_units,
                ):
                    self.assertEqual(bounded_language(grammar), case.words)
                self.assertEqual(
                    {
                        rule.lhs
                        for rule in case.after_epsilon.productions
                        if not rule.rhs
                    },
                    {case.prepared.start} if () in case.words else set(),
                )
        indirect = contract.EXAMPLES[1]
        self.assertEqual(nullable_variables(indirect.prepared), {"A", "C"})

    def test_all_checks_accept_the_known_stage_answers(self):
        result, output = self.run_checks(known_answer("epsilon"), known_answer("units"))
        self.assertTrue(result.wasSuccessful(), output)
        self.assertEqual(result.testsRun, 24)
        self.assertFalse(result.skipped)

    def test_none_stubs_fail_every_check(self):
        result, output = self.run_checks(lambda grammar: None, lambda grammar: None)
        self.assertEqual(len(result.failures), 24, output)
        self.assertFalse(result.errors)
        self.assertIn("Return a Grammar", output)

    def test_noop_functions_fail_when_nullable_rules_need_removal(self):
        result, output = self.run_checks(
            lambda grammar: grammar, lambda grammar: grammar, contract.EXAMPLES[:1]
        )
        self.assertEqual(len(result.failures), 3, output)

    def test_losing_prepared_start_epsilon_is_rejected(self):
        def lose_epsilon(grammar):
            correct = known_answer("epsilon")(grammar)
            return replace(
                correct,
                productions=correct.productions - {Production(correct.start, ())},
            )

        result, output = self.run_checks(
            lose_epsilon, known_answer("units"), contract.EXAMPLES[3:4]
        )
        self.assertEqual(len(result.failures), 2, output)

    def test_unit_cycle_noop_is_rejected_even_when_epsilon_step_is_correct(self):
        result, output = self.run_checks(
            known_answer("epsilon"), lambda grammar: grammar, contract.EXAMPLES[2:3]
        )
        self.assertEqual(len(result.failures), 2, output)

    def test_runner_fails_clearly_for_missing_module_or_function(self):
        for error in (
            ModuleNotFoundError("No module named 'cfg'"),
            AttributeError("missing eliminate_unit_prods"),
        ):
            output = io.StringIO()
            with self.subTest(error=error), redirect_stderr(output), patch(
                "tools.check_role2.importlib.import_module", side_effect=error
            ):
                self.assertEqual(check_role2.main(["src.simplify_grammar"]), 2)
                self.assertIn("No simplification checks passed", output.getvalue())

    def test_runner_returns_failure_for_none_functions(self):
        module = SimpleNamespace(eliminate_unit_prods=lambda grammar: None)
        setattr(module, "eliminate_ε_prods", lambda grammar: None)
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output), patch(
            "tools.check_role2.importlib.import_module", return_value=module
        ):
            self.assertEqual(check_role2.main(["src.simplify_grammar"]), 1)
        self.assertIn("FAILED (failures=24)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
