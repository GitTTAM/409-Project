"""Run Steven's real functions, including cases outside the hand-written fixtures."""

import io
import random
import unittest

from cfg_toolkit import Grammar, Production, dumps_lecture, prepare_start
from cfg_toolkit.pipeline import run_pipeline
from cfg_toolkit.simplify_grammar import eliminate_ε_prods, eliminate_unit_prods
from tests.role2_contract import EXAMPLES, make_suite
from tests.support import bounded_language


class SimplificationTests(unittest.TestCase):
    def test_real_functions_pass_every_role2_stage_check(self):
        output = io.StringIO()
        result = unittest.TextTestRunner(stream=output).run(
            make_suite(eliminate_ε_prods, eliminate_unit_prods)
        )
        self.assertEqual(result.testsRun, len(EXAMPLES) * 3)
        self.assertTrue(result.wasSuccessful(), output.getvalue())
        self.assertFalse(result.skipped)

    def test_default_pipeline_stops_only_when_devins_work_is_needed(self):
        for case in EXAMPLES:
            with self.subTest(case=case.name):
                result = run_pipeline(case.original)
                self.assertEqual(
                    [step.stage for step in result.snapshots],
                    ["original", "prepare_start", "remove_epsilon", "remove_units"],
                )
                self.assertEqual(result.snapshots[-1].grammar, case.after_units)
                self.assertEqual(
                    result.pending, ("remove_useless", "replace_terminals", "binarize")
                )
                self.assertFalse(result.is_complete)

    def test_fixed_generated_grammars_preserve_words_and_stage_conditions(self):
        # A fixed seed gives the same 250 inputs on each run. Include empty
        # rules, cycles, mixed terminals, and right sides longer than two.
        generator = random.Random(409)
        symbols = ("S", "A", "B", "a", "b")
        for number in range(250):
            rules = {
                Production(
                    generator.choice(symbols[:3]),
                    tuple(
                        generator.choice(symbols) for _ in range(generator.randrange(5))
                    ),
                )
                for _ in range(generator.randrange(1, 12))
            }
            original = Grammar(symbols[:3], symbols[3:], rules, "S")
            with self.subTest(number=number, grammar=dumps_lecture(original)):
                expected = bounded_language(original, 3)
                prepared = prepare_start(original).grammar
                epsilon = eliminate_ε_prods(prepared)
                result = eliminate_unit_prods(epsilon)
                for current in (epsilon, result):
                    self.assertEqual(bounded_language(current, 3), expected)
                    self.assertFalse(current.start_on_rhs)
                    self.assertTrue(
                        all(
                            r.rhs or r.lhs == current.start for r in current.productions
                        )
                    )
                self.assertFalse(
                    any(
                        len(r.rhs) == 1 and r.rhs[0] in result.variables
                        for r in result.productions
                    )
                )
                self.assertEqual(eliminate_ε_prods(epsilon), epsilon)
                self.assertEqual(eliminate_unit_prods(result), result)


if __name__ == "__main__":
    unittest.main()
