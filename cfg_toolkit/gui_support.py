"""Small display helpers for the desktop window; grammar work stays in the toolkit."""

from dataclasses import dataclass
import re
from typing import Optional, FrozenSet

from .lecture import dumps_lecture
from .model import Grammar
from .start_symbol import StartPreparation


@dataclass(frozen=True)
class InputProblem:
    message: str
    hint: str
    line: Optional[int] = None
    column: Optional[int] = None

    def display(self, text: str) -> str:
        lines = [self.message]
        source_lines = text.splitlines()
        if self.line is not None and 1 <= self.line <= len(source_lines):
            source = source_lines[self.line - 1]
            lines.extend(("", "Line {}: {}".format(self.line, source)))
            if self.column is not None:
                lines.append(
                    " " * (len("Line {}: ".format(self.line)) + self.column - 1) + "^"
                )
        lines.extend(("", "Try this: " + self.hint))
        return "\n".join(lines)


def explain_input_error(error: Exception) -> InputProblem:
    """Keep the parser's exact message and add a small, concrete correction tip."""
    message = str(error)
    location = re.search(r"\bline (\d+)(?:, column (\d+))?", message)
    line = int(location.group(1)) if location else None
    column_match = re.search(r"\bcolumn (\d+)", message)
    column = int(column_match.group(1)) if column_match else None
    hint = "Check the names in V, Sigma, and Start."
    if "ambiguous compact RHS" in message:
        hint = "Add spaces: S -> A B C a. A B is two symbols; a declared AB is one."
    elif "empty alternative" in message or "epsilon must be the entire" in message:
        hint = "Write epsilon explicitly: S -> a | epsilon."
    elif "invalid JSON" in message:
        hint = "Enter grammar rules, for example S -> aSb | epsilon."
    elif "quote" in message:
        hint = "Close the quote, for example Term -> 'id'."
    elif (
        "undeclared" in message
        or "cannot tokenize" in message
        or "not a declared variable" in message
    ):
        hint = "Check spelling and add any missing name to V or Sigma."
    elif "no start variable" in message:
        hint = "Enter a rule such as S -> aSb | epsilon."
    elif "production" in message or "arrow" in message:
        hint = "Write a rule such as S -> aSb | epsilon."
    elif "duplicate" in message:
        hint = "Declare each name and header only once."
    elif "disjoint" in message:
        hint = "Use different names for variables and terminals."
    return InputProblem(message, hint, line, column)


def added_rule_lines(preparation: StartPreparation) -> FrozenSet[str]:
    """Find exact classroom output lines that contain newly added productions."""
    added = preparation.grammar.productions - preparation.original.productions
    if not added:
        return frozenset()
    grammar = Grammar(
        preparation.grammar.variables,
        preparation.grammar.terminals,
        added,
        preparation.grammar.start,
    )
    return frozenset(dumps_lecture(grammar).splitlines()[3:])
