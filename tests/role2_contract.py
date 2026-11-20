"""Checks Steven can run against his real epsilon and unit-removal functions.

tools/check_role2.py runs every case against the real functions. The ordinary
test suite also runs them, so unit and pipeline checks cannot quietly disappear.
"""

from dataclasses import dataclass
import unittest

from cfg_toolkit import Grammar, dumps_lecture, loads_lecture, prepare_start
from cfg_toolkit.cnf_validator import derives_epsilon
from cfg_toolkit.pipeline import run_pipeline
from tests.support import bounded_language


@dataclass(frozen=True)
class Example:
    name: str
    original: Grammar
    prepared: Grammar
    after_epsilon: Grammar
    after_units: Grammar
    words: frozenset


def _example(name, original, epsilon_rules, unit_rules, words):
    original = loads_lecture(original)
    prepared = prepare_start(original).grammar
    # Reuse the declarations, including variables left without rules. Removing
    # those useless variables belongs to Devin's later step.
    declarations = "\n".join(dumps_lecture(prepared).splitlines()[:3])
    return Example(
        name,
        original,
        prepared,
        loads_lecture(declarations + "\n" + epsilon_rules),
        loads_lecture(declarations + "\n" + unit_rules),
        frozenset(words),
    )


EXAMPLES = (
    _example(
        "Repeated nullable symbols",
        "S -> A A\nA -> a | epsilon",
        "S -> A A | A | epsilon\nA -> a",
        "S -> A A | a | epsilon\nA -> a",
        {(), ("a",), ("a", "a")},
    ),
    _example(
        "Epsilon cycle",
        "S -> A A\nA -> a | B\nB -> A | epsilon",
        "S -> A A | A | epsilon\nA -> a | B\nB -> A",
        "S -> A A | a | epsilon\nA -> a\nB -> a",
        {(), ("a",), ("a", "a")},
    ),
    _example(
        "Indirect epsilon",
        "S -> A B\nA -> C\nC -> epsilon\nB -> b",
        "S -> A B | B\nA -> C\nB -> b",
        "S -> A B | b\nB -> b",
        {("b",)},
    ),
    _example(
        "Unit cycle with an exit",
        "S -> A\nA -> B\nB -> A | b",
        "S -> A\nA -> B\nB -> A | b",
        "S -> b\nA -> b\nB -> b",
        {("b",)},
    ),
    _example(
        "Epsilon under the prepared start",
        "S -> aSb | epsilon",
        "S_0 -> S | epsilon\nS -> aSb | ab",
        "S_0 -> aSb | ab | epsilon\nS -> aSb | ab",
        {(), ("a", "b"), ("a", "a", "b", "b")},
    ),
    _example(
        "Already simplified",
        "S -> a",
        "S -> a",
        "S -> a",
        {("a",)},
    ),
    _example(
        "Epsilon only",
        "S -> epsilon",
        "S -> epsilon",
        "S -> epsilon",
        {()},
    ),
    _example(
        "Unit cycle with no terminal word",
        "S -> A\nA -> S",
        "S_0 -> S\nS -> A\nA -> S",
        "",
        set(),
    ),
    _example(
        "Three nullable occurrences and whole token names",
        'Begin -> Item Item Item\nItem -> "id" | epsilon',
        "Begin -> Item Item Item | Item Item | Item | epsilon\nItem -> id",
        "Begin -> Item Item Item | Item Item | id | epsilon\nItem -> id",
        {(), ("id",), ("id", "id"), ("id", "id", "id")},
    ),
)


class Role2Check(unittest.TestCase):
    """One named case and stage; the actual functions are supplied by the runner."""

    def __init__(self, example, stage, remove_epsilon, remove_units):
        super().__init__("runTest")
        self.example = example
        self.stage = stage
        self.remove_epsilon = remove_epsilon
        self.remove_units = remove_units

    def shortDescription(self):
        return self.example.name + " / " + self.stage

    def check_result(self, function, source, expected, stage):
        before = (source.variables, source.terminals, source.productions, source.start)
        result = function(source)
        self.assertIsInstance(result, Grammar, "Return a Grammar, not None or a stub.")
        self.assertEqual(
            (source.variables, source.terminals, source.productions, source.start),
            before,
            "The input grammar must stay unchanged.",
        )
        self.assertEqual(result.start, source.start, "Keep the prepared start name.")
        self.assertFalse(result.start_on_rhs, "The prepared start must stay off RHSs.")
        self.assertLessEqual(result.variables, source.variables)
        self.assertLessEqual(result.terminals, source.terminals)
        self.assertEqual(result.productions, expected.productions, "Unexpected rules.")
        self.assertEqual(derives_epsilon(result), derives_epsilon(source))
        self.assertEqual(bounded_language(result), bounded_language(source))
        self.assertTrue(
            all(rule.rhs or rule.lhs == result.start for rule in result.productions),
            "Only the current start may have an epsilon rule.",
        )
        if stage == "units":
            self.assertFalse(
                any(
                    len(rule.rhs) == 1 and rule.rhs[0] in result.variables
                    for rule in result.productions
                ),
                "Unit rules remain, possibly inside a cycle.",
            )
        return result

    def runTest(self):
        case = self.example
        if self.stage == "epsilon":
            self.check_result(
                self.remove_epsilon, case.prepared, case.after_epsilon, "epsilon"
            )
        elif self.stage == "units":
            # Give this test the known epsilon result, so an epsilon bug does
            # not hide whether unit removal works on its own.
            self.check_result(
                self.remove_units, case.after_epsilon, case.after_units, "units"
            )
        else:

            def epsilon_step(grammar):
                return self.check_result(
                    self.remove_epsilon, grammar, case.after_epsilon, "epsilon"
                )

            def unit_step(grammar):
                return self.check_result(
                    self.remove_units, grammar, case.after_units, "units"
                )

            result = run_pipeline(
                case.original,
                {"remove_epsilon": epsilon_step, "remove_units": unit_step},
            )
            self.assertEqual(
                result.snapshots[-1].grammar.productions, case.after_units.productions
            )
            self.assertEqual(
                result.pending, ("remove_useless", "replace_terminals", "binarize")
            )
            self.assertIsNone(result.cnf_report)
            self.assertFalse(result.is_complete)


def make_suite(remove_epsilon, remove_units, examples=EXAMPLES):
    """Run each function separately, then both through Matt's pipeline."""
    return unittest.TestSuite(
        Role2Check(case, stage, remove_epsilon, remove_units)
        for case in examples
        for stage in ("epsilon", "units", "pipeline")
    )
