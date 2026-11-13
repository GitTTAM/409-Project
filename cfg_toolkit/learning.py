"""Short explanations and practice prompts tied to Matt Lawrence's grammar input code."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import unittest

from .document_io import loads_document
from .model import Grammar
from .start_symbol import StartPreparation, prepare_start


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CodeReference:
    """A function the learner can open without leaving the program."""

    path: str
    name: str


@dataclass(frozen=True)
class Lesson:
    title: str
    question: str
    answer: str
    exercise: str
    code: CodeReference
    test: CodeReference


LESSONS = (
    Lesson(
        "1. Whole symbol names",
        'Why does ("A", "B") differ from ("AB",)?',
        '("A", "B") contains two symbols. ("AB",) contains one symbol whose '
        'name is AB. The comma makes it a one-item tuple; ("AB") alone is a '
        "string. A declared name stays whole, so write A B when you want two "
        "variables. For S -> A B, A -> a, B -> b, the result can be ab. "
        "For S -> AB, AB -> a, it can be a instead.",
        'Load "Whole names: A B vs AB". Predict its words, then change '
        "S -> A B | AB to S -> A B. Click Run, then open Help > Walkthrough step 2. "
        "Explain which word was removed. Save your own input file.",
        CodeReference("cfg_toolkit/model.py", "Production"),
        CodeReference(
            "tests/test_lecture.py",
            "LectureParserTests.test_exact_declared_symbol_wins_and_spaces_force_separate_symbols",
        ),
    ),
    Lesson(
        "2. The empty word",
        "Why does epsilon become ()?",
        "Epsilon means zero symbols. An empty tuple () stores that directly; "
        'A tuple like ("e",) stores one terminal named e '
        "and is not empty. The classroom reader translates epsilon, eps, and "
        "the supported epsilon characters into ().",
        'Load "Recursive grammar". Find the empty tuple in Help > Walkthrough step 2. '
        "Change epsilon to e, add e to Sigma, validate, and explain why the "
        "grammar now has another terminal. Restore the example afterward.",
        CodeReference("cfg_toolkit/lecture.py", "_read_rhs"),
        CodeReference(
            "tests/test_lecture.py",
            "LectureParserTests.test_bare_e_is_an_ordinary_terminal",
        ),
    ),
    Lesson(
        "3. Keep earlier steps intact",
        "Why do grammar objects stay unchanged between steps?",
        "We need the original grammar for comparison and later language checks. "
        "Grammar and Production are frozen dataclasses, with frozen sets and "
        "tuple right sides. A transformation builds a new Grammar instead of "
        "editing the old one. Start preparation can safely return the same "
        "object when no change is needed.",
        "Open the immutability test below. Add your own check that the "
        "original start is still S after the prepared grammar uses S_0. Run "
        "the test and explain why both objects need to remain available.",
        CodeReference("cfg_toolkit/model.py", "Grammar"),
        CodeReference(
            "tests/test_start_symbol.py",
            "StartSymbolTests.test_original_is_unchanged_and_preparation_is_idempotent",
        ),
    ),
    Lesson(
        "4. A fresh start",
        "When do we need a new start variable?",
        "For this project, the start must stay off every right side. "
        "S -> aSb needs a fresh start because S appears on the right. "
        "We add S_0 -> S and keep all old rules. If S_0 is taken by a variable "
        "or terminal, we try S_1, then S_2. An isolated start does not need "
        "a wrapper, even when it produces epsilon. Steven Yang removes the "
        "temporary unit rule later.",
        'Load "No new start needed", predict the result, and prepare it. '
        'Then load "Recursive grammar" and repeat. For a small code change, '
        "add a test with a start named Begin and a name collision Begin_0.",
        CodeReference("cfg_toolkit/start_symbol.py", "prepare_start"),
        CodeReference(
            "tests/test_start_symbol.py",
            "StartSymbolTests.test_name_collision_checks_variables_and_terminals",
        ),
    ),
    Lesson(
        "5. Catch a wrong result",
        "How does a test catch an incorrect result?",
        "A test compares a required property with the actual result. "
        "The start test uses self.assertFalse(result.grammar.start_on_rhs). "
        "If a broken implementation returns the original recursive grammar, "
        "the expression is True and the assertion fails. The test also checks "
        "the new start name and the exact added rule. Passing one assertion "
        "does not prove every part of the transformation is correct.",
        "Run the test demonstration below. Open the real test, explain each "
        "assertion, then add a case where the start occurs twice on one RHS. "
        "Keep any intentional broken result inside a separate scratch exercise.",
        CodeReference("cfg_toolkit/model.py", "Grammar.start_on_rhs"),
        CodeReference(
            "tests/test_start_symbol.py",
            "StartSymbolTests.test_recursive_nullable_start_gets_fresh_wrapper",
        ),
    ),
)


@dataclass(frozen=True)
class WalkthroughStep:
    title: str
    text: str
    code: CodeReference


def tuple_view(grammar: Grammar) -> str:
    """Show how classroom rules become whole-name tuples in memory."""
    lines = [
        "Variables = frozenset({!r})".format(sorted(grammar.variables)),
        "Terminals = frozenset({!r})".format(sorted(grammar.terminals)),
        "Start = {!r}".format(grammar.start),
        "",
    ]
    rules = sorted(
        grammar.productions,
        key=lambda rule: (rule.lhs != grammar.start, rule.lhs, rule.rhs),
    )
    for rule in rules:
        lines.append("Production({!r}, {!r})".format(rule.lhs, rule.rhs))
    if not rules:
        lines.append("No productions: this grammar generates no terminal words.")
    return "\n".join(lines)


def walkthrough_steps(
    grammar: Optional[Grammar], preparation: Optional[StartPreparation]
) -> Tuple[WalkthroughStep, ...]:
    """Explain the current workspace, including steps that have not run yet."""
    symbols = "Click Run on the editor input to see its actual symbol tuples here."
    validation = "Validation has not run for the current input."
    start = "Click Run to prepare the start for the current grammar."
    if grammar is not None:
        symbols = tuple_view(grammar)
        validation = (
            "Validation passed for {} variables, {} terminals, and {} distinct rules.\n\n"
            "The model checked disjoint symbol names, a declared start variable, "
            "a variable on every left side, and declared names on every right side.\n\n"
            "Empty or unused rule sets are allowed. A valid CFG is not necessarily CNF."
        ).format(
            len(grammar.variables), len(grammar.terminals), len(grammar.productions)
        )
    if preparation is not None:
        start = (
            preparation.explanation
            + "\n\nOriginal start: {}\nPrepared start: {}".format(
                preparation.original.start, preparation.grammar.start
            )
        )
    return (
        WalkthroughStep(
            "1. Read the input",
            "Type grammar rules such as S -> aSb | epsilon.\n\n"
            "loads_lecture() reads the rules and creates a Grammar object.",
            CodeReference("cfg_toolkit/lecture.py", "loads_lecture"),
        ),
        WalkthroughStep(
            "2. Store whole symbols",
            symbols,
            CodeReference("cfg_toolkit/model.py", "Production"),
        ),
        WalkthroughStep(
            "3. Check the grammar",
            validation,
            CodeReference("cfg_toolkit/model.py", "Grammar.__post_init__"),
        ),
        WalkthroughStep(
            "4. Prepare the start",
            start,
            CodeReference("cfg_toolkit/start_symbol.py", "prepare_start"),
        ),
    )


def read_code(reference: CodeReference, root: Path = ROOT) -> Tuple[str, int, int]:
    """Read a source file and find a named class/function, including class methods."""
    root = root.resolve()
    path = (root / reference.path).resolve()
    if root not in path.parents:
        raise ValueError("Source reference must stay inside the project folder.")
    text = path.read_text(encoding="utf-8-sig")
    body = ast.parse(text).body
    node = None
    for name in reference.name.split("."):
        node = next(
            (
                item
                for item in body
                if isinstance(item, (ast.ClassDef, ast.FunctionDef))
                and item.name == name
            ),
            None,
        )
        if node is None:
            raise ValueError(
                "Cannot find {} in {}".format(reference.name, reference.path)
            )
        body = node.body
    return text, node.lineno, node.end_lineno


def run_start_check_demo() -> str:
    """Use a real unittest assertion on a deliberately wrong result, then the real one."""
    original = loads_document("S -> aSb | epsilon")
    correct = prepare_start(original).grammar
    lines = [
        "Input: S -> aSb | epsilon",
        "",
        "Assertion: self.assertFalse(result.grammar.start_on_rhs)",
        "",
    ]
    for label, candidate in (
        ("Deliberately wrong: return the original", original),
        ("Actual prepare_start() result", correct),
    ):
        try:
            unittest.TestCase().assertFalse(candidate.start_on_rhs)
        except AssertionError as error:
            lines.append(
                "{}\nFAIL: {}\nS still appears on a right side.\n".format(label, error)
            )
        else:
            lines.append(
                "{}\nPASS: the prepared start {} stays off every RHS.\n".format(
                    label, candidate.start
                )
            )
    lines.append(
        "This demonstration leaves the real implementation unchanged. Open the test to see its other assertions."
    )
    return "\n".join(lines)
