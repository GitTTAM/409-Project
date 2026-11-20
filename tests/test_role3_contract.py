"""Verify Devin's fixtures and failure checks. His real functions stay pending."""

from contextlib import redirect_stderr
import io
import unittest
from unittest.mock import patch

from tests import role3_contract as contract
from tests.support import bounded_language
from tools import check_role3


def known_answer(stage):
    def lookup(grammar):
        for case in contract.EXAMPLES:
            source, answer = {
                "remove_useless": (case.after_units, case.after_useless),
                "replace_terminals": (case.after_useless, case.after_terminals),
                "binarize": (case.after_terminals, case.final),
            }[stage]
            if grammar == source:
                return answer
        raise AssertionError("No fixture answer for this grammar")

    return lookup


class Role3HandoffTests(unittest.TestCase):
    def run_checks(self, functions, examples=contract.EXAMPLES):
        output = io.StringIO()
        result = unittest.TextTestRunner(stream=output).run(
            contract.make_suite(*functions, examples=examples)
        )
        return result, output.getvalue()

    def test_known_answers_pass_all_stage_and_pipeline_checks(self):
        functions = [
            known_answer(stage)
            for stage in ("remove_useless", "replace_terminals", "binarize")
        ]
        result, output = self.run_checks(functions)
        self.assertTrue(result.wasSuccessful(), output)
        self.assertEqual(result.testsRun, 4 * len(contract.EXAMPLES))
        self.assertFalse(result.skipped)

    def test_fixtures_preserve_the_original_words(self):
        for case in contract.EXAMPLES:
            with self.subTest(case=case.name):
                expected = bounded_language(case.original)
                for grammar in (
                    case.after_units,
                    case.after_useless,
                    case.after_terminals,
                    case.final,
                ):
                    self.assertEqual(bounded_language(grammar), expected)

    def test_none_stubs_cannot_pass(self):
        result, output = self.run_checks([lambda grammar: None] * 3)
        self.assertEqual(len(result.failures), 4 * len(contract.EXAMPLES), output)
        self.assertFalse(result.errors)

    def test_noop_binary_function_fails_for_a_long_rule(self):
        functions = [
            known_answer("remove_useless"),
            known_answer("replace_terminals"),
            lambda grammar: grammar,
        ]
        examples = tuple(
            case for case in contract.EXAMPLES if case.name == "Long right side"
        )
        result, output = self.run_checks(functions, examples)
        self.assertEqual(len(result.failures), 2, output)

    def test_missing_module_reports_pending_and_nonzero_status(self):
        output = io.StringIO()
        with redirect_stderr(output), patch(
            "tools.check_role3.importlib.import_module",
            side_effect=ModuleNotFoundError("not ready"),
        ):
            self.assertEqual(check_role3.main([]), 2)
        self.assertIn("No role 3 checks passed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
