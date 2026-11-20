"""Devin's stage checks. Known fixtures let each function be tested on its own.

Helper names can differ from the fixture names. We check the resulting language
and rule conditions instead of requiring one particular set of helper names.
"""

from dataclasses import dataclass
import unittest

from cfg_toolkit import Grammar, loads_lecture
from cfg_toolkit.cnf_validator import derives_epsilon, validate_cnf
from cfg_toolkit.pipeline import run_pipeline, team_transforms
from cfg_toolkit.simplify_grammar import eliminate_ε_prods, eliminate_unit_prods
from tests.support import bounded_language


@dataclass(frozen=True)
class Example:
    name: str
    original: Grammar
    after_units: Grammar
    after_useless: Grammar
    after_terminals: Grammar
    final: Grammar


def _case(name, original, useless, terminals=None, binary=None):
    original = loads_lecture(original)
    prefix = run_pipeline(
        original,
        {"remove_epsilon": eliminate_ε_prods, "remove_units": eliminate_unit_prods},
    )
    return Example(
        name,
        original,
        prefix.snapshots[-1].grammar,
        loads_lecture(useless),
        loads_lecture(terminals or useless),
        loads_lecture(binary or terminals or useless),
    )


EXAMPLES = (
    _case(
        "Unreachable and unproductive symbols",
        "V={S,A,B,Dead,Ghost}\nSigma={a,b,x}\nStart=S\n"
        "S -> A B\nA -> a\nB -> b\nDead -> Dead\nGhost -> x",
        "S -> A B\nA -> a\nB -> b",
    ),
    _case(
        "Long right side",
        "S -> A B C D\nA -> a\nB -> b\nC -> c\nD -> d",
        "S -> A B C D\nA -> a\nB -> b\nC -> c\nD -> d",
        binary="S -> A Pair1\nPair1 -> B Pair2\nPair2 -> C D\n"
        "A -> a\nB -> b\nC -> c\nD -> d",
    ),
    _case(
        "Mixed terminals and whole names",
        'Expr -> "id" + Tail\nTail -> "id"',
        'Expr -> "id" + Tail\nTail -> "id"',
        'Expr -> Token Plus Tail\nToken -> "id"\nPlus -> +\nTail -> "id"',
        'Expr -> Token Pair\nPair -> Plus Tail\nToken -> "id"\n'
        'Plus -> +\nTail -> "id"',
    ),
    _case(
        "Existing helper names must survive",
        "S -> a A T_a X_1\nA -> a\nT_a -> b\nX_1 -> c",
        "S -> a A T_a X_1\nA -> a\nT_a -> b\nX_1 -> c",
        "S -> Fresh A T_a X_1\nFresh -> a\nA -> a\nT_a -> b\nX_1 -> c",
        "S -> Fresh Pair1\nPair1 -> A Pair2\nPair2 -> T_a X_1\n"
        "Fresh -> a\nA -> a\nT_a -> b\nX_1 -> c",
    ),
    _case(
        "Prepared start keeps epsilon",
        "S -> aSb | epsilon",
        "S_0 -> epsilon | aSb | ab\nS -> aSb | ab",
        "S_0 -> epsilon | Left S Right | Left Right\n"
        "S -> Left S Right | Left Right\nLeft -> a\nRight -> b",
        "S_0 -> epsilon | Left Pair | Left Right\n"
        "S -> Left Pair | Left Right\nPair -> S Right\nLeft -> a\nRight -> b",
    ),
    _case(
        "Empty language",
        "S -> A B\nA -> A\nB -> b",
        "V={S}\nSigma={}\nStart=S",
    ),
    _case("Epsilon only", "S -> epsilon", "S -> epsilon"),
)


def useful_symbols(grammar):
    """Test-only analysis; it does not remove or rewrite any grammar rules."""
    productive = set()
    while True:
        found = {
            rule.lhs
            for rule in grammar.productions
            if set(rule.rhs) <= productive | grammar.terminals
        }
        if found <= productive:
            break
        productive.update(found)
    reachable = {grammar.start}
    while True:
        found = {
            symbol
            for rule in grammar.productions
            if rule.lhs in reachable
            for symbol in rule.rhs
        }
        if found <= reachable:
            break
        reachable.update(found)
    return productive, reachable


class Role3Check(unittest.TestCase):
    def __init__(self, example, stage, functions):
        super().__init__("runTest")
        self.example = example
        self.stage = stage
        self.functions = functions

    def shortDescription(self):
        return self.example.name + " / " + self.stage

    def check_result(self, source, stage):
        before = (source.variables, source.terminals, source.productions, source.start)
        result = self.functions[stage](source)
        self.assertIsInstance(result, Grammar, "Return a Grammar, not None or a stub.")
        self.assertEqual(
            before,
            (source.variables, source.terminals, source.productions, source.start),
            "Input changed.",
        )
        self.assertEqual(result.start, source.start, "Keep the prepared start.")
        self.assertFalse(result.start_on_rhs)
        self.assertLessEqual(result.terminals, source.terminals)
        self.assertEqual(derives_epsilon(result), derives_epsilon(source))
        self.assertEqual(bounded_language(result), bounded_language(source))
        self.assertTrue(all(r.rhs or r.lhs == result.start for r in result.productions))
        self.assertFalse(
            any(
                len(r.rhs) == 1 and r.rhs[0] in result.variables
                for r in result.productions
            ),
            "Unit rules reintroduced.",
        )
        productive, reachable = useful_symbols(result)
        self.assertLessEqual(result.variables, productive | {result.start})
        self.assertLessEqual(result.variables | result.terminals, reachable)
        if stage == "remove_useless":
            self.assertEqual(
                result,
                self.example.after_useless,
                "Remove unreachable and unproductive symbols and their rules.",
            )
        else:
            self.assertLessEqual(source.variables, result.variables)
            self.assertTrue(
                all(
                    len(r.rhs) < 2 or set(r.rhs) <= result.variables
                    for r in result.productions
                ),
                "A long RHS contains a terminal.",
            )
        if stage == "binarize":
            report = validate_cnf(result, source=self.example.original)
            self.assertTrue(report.is_valid, report.issues)
        return result

    def runTest(self):
        case = self.example
        if self.stage == "pipeline":
            transforms = team_transforms()
            for stage in ("remove_useless", "replace_terminals", "binarize"):
                transforms[stage] = lambda grammar, step=stage: self.check_result(
                    grammar, step
                )
            result = run_pipeline(case.original, transforms)
            self.assertTrue(result.is_complete)
            self.assertFalse(result.pending)
            self.assertTrue(result.cnf_report.source_checked)
        else:
            source = {
                "remove_useless": case.after_units,
                "replace_terminals": case.after_useless,
                "binarize": case.after_terminals,
            }[self.stage]
            self.check_result(source, self.stage)


def make_suite(remove_useless, replace_terminals, binarize, examples=EXAMPLES):
    functions = {
        "remove_useless": remove_useless,
        "replace_terminals": replace_terminals,
        "binarize": binarize,
    }
    return unittest.TestSuite(
        Role3Check(case, stage, functions)
        for case in examples
        for stage in (*functions, "pipeline")
    )
