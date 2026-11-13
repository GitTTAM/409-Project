"""The shared grammar and rule types. Both check their input when created."""

from dataclasses import dataclass
from typing import FrozenSet, Tuple


class GrammarError(ValueError):
    """An input problem we can explain to the user without a traceback."""


def check_symbol(value, label: str) -> None:
    """Check one symbol name; label says where it came from if it is invalid."""
    if not isinstance(value, str) or not value:
        raise GrammarError("{} must be a nonempty string".format(label))
    if not value.isprintable() or any(char.isspace() for char in value):
        raise GrammarError(
            "{} must contain no whitespace or control characters".format(label)
        )
    if value in ("epsilon", "\u03b5"):
        raise GrammarError(
            "{}: epsilon is represented by an empty RHS [], not a symbol".format(label)
        )


def symbol_set(values, label: str) -> FrozenSet[str]:
    """Check declared names, then store them as a set that cannot be changed."""
    if not isinstance(values, (list, tuple, set, frozenset)):
        raise GrammarError(
            "{} must be a collection of symbol names, not a string".format(label)
        )
    for index, value in enumerate(values):
        check_symbol(value, "{}[{}]".format(label, index))
    normalized = frozenset(values)
    if len(normalized) != len(values):
        raise GrammarError("{} contains duplicate declarations".format(label))
    return normalized


@dataclass(frozen=True, order=True)
class Production:
    """One rule: lhs is a variable, rhs is a sequence of whole symbol names.

    For example, Production("S", ("a", "S", "b")) means S -> aSb.
    Use () for epsilon. A name like "id" is one symbol, not two characters.
    """

    lhs: str
    rhs: Tuple[str, ...]

    def __post_init__(self) -> None:
        check_symbol(self.lhs, "production lhs")
        if not isinstance(self.rhs, (list, tuple)):
            raise GrammarError(
                "production rhs must be a token list/tuple; use [] for epsilon"
            )
        for index, symbol in enumerate(self.rhs):
            check_symbol(symbol, "production rhs[{}]".format(index))
        # Normalize once during setup. The frozen rule cannot change afterward.
        object.__setattr__(self, "rhs", tuple(self.rhs))


@dataclass(frozen=True)
class Grammar:
    """A checked grammar shared by every module in the project.

    The symbol and rule sets cannot change after setup. To transform a grammar,
    build and return a new Grammar instead of editing the old one.
    Unused variables and empty rule/terminal sets are valid input; Devin Finn
    handles useless symbols later.
    """

    variables: FrozenSet[str]
    terminals: FrozenSet[str]
    productions: FrozenSet[Production]
    start: str

    def __post_init__(self) -> None:
        variables = symbol_set(self.variables, "variables")
        terminals = symbol_set(self.terminals, "terminals")
        if not variables:
            raise GrammarError("variables must contain at least the start variable")
        overlap = variables & terminals
        if overlap:
            raise GrammarError(
                "variables and terminals must be disjoint; overlap: {}".format(
                    ", ".join(sorted(overlap))
                )
            )
        check_symbol(self.start, "start")
        if self.start not in variables:
            raise GrammarError(
                "start {!r} is not a declared variable".format(self.start)
            )
        if not isinstance(self.productions, (list, tuple, set, frozenset)):
            raise GrammarError("productions must be a collection of Production objects")
        for index, rule in enumerate(self.productions):
            if not isinstance(rule, Production):
                raise GrammarError("productions[{}] must be a Production".format(index))
            if rule.lhs not in variables:
                raise GrammarError(
                    "production lhs {!r} is not a declared variable".format(rule.lhs)
                )
            unknown_symbols = set(rule.rhs) - variables - terminals
            if unknown_symbols:
                raise GrammarError(
                    "rule for {!r} contains undeclared RHS symbols: {}".format(
                        rule.lhs, ", ".join(sorted(unknown_symbols))
                    )
                )
        # Freeze only after every rule passes. Earlier pipeline stages can then
        # keep their original grammar without later stages changing it.
        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "terminals", terminals)
        object.__setattr__(self, "productions", frozenset(self.productions))

    @property
    def start_on_rhs(self) -> bool:
        """Whether start preparation needs to add a fresh start variable."""
        return any(self.start in rule.rhs for rule in self.productions)
