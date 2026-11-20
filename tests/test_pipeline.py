"""Check the handoff between stages while teammates' conversions are pending."""

from pathlib import Path
import unittest

from cfg_toolkit import Grammar, Production, read_grammar
from cfg_toolkit.pipeline import STAGES, run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def unchanged(grammar):
    """Stand in for a teammate function when testing with an already-CNF grammar."""
    return grammar


class IntegrationContractTests(unittest.TestCase):
    def test_missing_teammates_stop_after_student1(self):
        original = read_grammar(ROOT / "examples" / "02_start_on_rhs.json")
        result = run_pipeline(original, {})
        self.assertEqual(
            [snapshot.stage for snapshot in result.snapshots],
            ["original", "prepare_start"],
        )
        self.assertEqual(result.pending, tuple(name for name, title in STAGES))
        self.assertIsNone(result.cnf_report)
        self.assertFalse(result.is_complete)

    def test_later_stage_is_not_run_before_missing_earlier_stage(self):
        calls = []
        grammar = read_grammar(ROOT / "examples" / "04_already_cnf.json")
        result = run_pipeline(grammar, {"binarize": lambda g: calls.append(g)})
        self.assertEqual(calls, [])
        self.assertFalse(result.is_complete)

    def test_partial_prefix_keeps_intermediate_snapshot(self):
        grammar = read_grammar(ROOT / "examples" / "04_already_cnf.json")
        result = run_pipeline(grammar, {"remove_epsilon": unchanged})
        self.assertEqual(result.snapshots[-1].stage, "remove_epsilon")
        self.assertEqual(result.pending[0], "remove_units")

    def test_stage_order_snapshots_and_final_validation_on_already_cnf(self):
        original = read_grammar(ROOT / "examples" / "04_already_cnf.json")
        calls = []

        def stage(name):
            def transform(grammar):
                calls.append(name)
                return grammar

            return transform

        result = run_pipeline(original, {name: stage(name) for name, title in STAGES})
        self.assertEqual(calls, [name for name, title in STAGES])
        self.assertEqual(len(result.snapshots), 8)
        self.assertTrue(result.is_complete)
        self.assertTrue(result.cnf_report.source_checked)

    def test_noop_stubs_cannot_claim_non_cnf_input_converted(self):
        original = read_grammar(ROOT / "examples" / "03_multichar_unit.json")
        result = run_pipeline(original, {name: unchanged for name, title in STAGES})
        self.assertFalse(result.pending)
        self.assertFalse(result.is_complete)
        self.assertFalse(result.cnf_report.is_valid)

    def test_bad_adapter_name_type_and_result_rejected(self):
        grammar = read_grammar(ROOT / "examples" / "04_already_cnf.json")
        with self.assertRaisesRegex(ValueError, "unknown integration stages"):
            run_pipeline(grammar, {"epsilon_typo": unchanged})
        with self.assertRaisesRegex(TypeError, "must be callable"):
            run_pipeline(grammar, {"remove_epsilon": None})
        with self.assertRaisesRegex(TypeError, "must return a validated Grammar"):
            run_pipeline(grammar, {"remove_epsilon": lambda g: {}})

    def test_adapter_cannot_replace_start_or_invent_terminal(self):
        grammar = read_grammar(ROOT / "examples" / "04_already_cnf.json")
        with self.assertRaisesRegex(ValueError, "preserve the prepared start"):
            run_pipeline(
                grammar,
                {
                    "remove_epsilon": lambda g: Grammar(
                        g.variables, g.terminals, g.productions, "A"
                    )
                },
            )
        with self.assertRaisesRegex(ValueError, "undeclared source terminal"):
            run_pipeline(
                grammar,
                {
                    "remove_epsilon": lambda g: Grammar(
                        g.variables, g.terminals | {"new"}, g.productions, g.start
                    )
                },
            )


if __name__ == "__main__":
    unittest.main()
