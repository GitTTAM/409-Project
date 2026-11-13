"""Add a fresh start variable when the current start appears on a right side."""

from dataclasses import dataclass
from typing import Optional

from .model import Grammar, Production


@dataclass(frozen=True)
class StartPreparation:
    """Keep the original, prepared result, and a message explaining what changed."""

    original: Grammar
    grammar: Grammar
    added: bool
    new_start: Optional[str]
    explanation: str


def prepare_start(grammar: Grammar) -> StartPreparation:
    """Add S_new -> S_old only when the old start appears on a right side.

    Our CNF rules keep the start off every RHS, even if it can produce epsilon.
    If it already stays off the right sides, return the original grammar.
    Steven Yang will remove the temporary unit rule later.
    """
    if not grammar.start_on_rhs:
        return StartPreparation(
            grammar,
            grammar,
            False,
            None,
            "The start variable does not occur on any RHS; no new start is needed.",
        )
    # Avoid both variable and terminal names when choosing S_0, S_1, and so on.
    used_names = grammar.variables | grammar.terminals
    suffix = 0
    new_start = "{}_{}".format(grammar.start, suffix)
    while new_start in used_names:
        suffix += 1
        new_start = "{}_{}".format(grammar.start, suffix)
    prepared = Grammar(
        grammar.variables | {new_start},
        grammar.terminals,
        grammar.productions | {Production(new_start, (grammar.start,))},
        new_start,
    )
    return StartPreparation(
        grammar,
        prepared,
        True,
        new_start,
        "The old start occurs on an RHS. Added fresh start {} and rule {} -> {}. "
        "This preserves every terminal word, including epsilon. The temporary unit rule "
        "will be removed by Steven Yang.".format(new_start, new_start, grammar.start),
    )
