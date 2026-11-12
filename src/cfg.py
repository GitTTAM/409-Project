from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key


@dataclass
class Variable:
    name: str

    def __str__(self):
        return self.name


@dataclass
class Terminal:
    name: str

    def __str__(self):
        return f"'{self.name}'"


@dataclass
class Alternation:
    lhs: Expression
    rhs: Expression

    def __str__(self):
        return f"{self.lhs} | {self.rhs}"


Expression = Variable | Terminal | Alternation


@dataclass
class Rule:
    lhs: Variable
    rhs: Expression

    def __str__(self):
        return f"{self.lhs} -> {self.rhs}"


@dataclass
class CFG:
    start_variable: Variable
    rules: set[Rule]

    def __str__(self):
        # partial sort rules; axiom productions appear first
        cmp = lambda r1, r2: (
            int(r1 == self.start_variable) - int(r2 == self.start_variable)
        )
        return "\n".join(map(str, sorted(self.rules, key=cmp_to_key(cmp))))
