"""CNF checks for Matt Lawrence's integration and validation work.

Steven Yang and Devin Finn also help test and verify conversion results.
"""

from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

from .grammar_io import format_rule
from .model import Grammar, Production


def nullable_variables(grammar: Grammar) -> FrozenSet[str]:
    """Find every variable that can produce the empty word.

    Start with direct epsilon rules, then keep adding variables whose whole RHS
    can already disappear. Stop when another pass adds nothing. No rules change.
    """
    nullable = set()
    changed = True
    while changed:
        changed = False
        for rule in grammar.productions:
            # all() is true for an empty RHS, which includes direct epsilon rules.
            if rule.lhs not in nullable and all(
                symbol in nullable for symbol in rule.rhs
            ):
                nullable.add(rule.lhs)
                changed = True
    return frozenset(nullable)


def derives_epsilon(grammar: Grammar) -> bool:
    """Whether the start variable can produce the empty word."""
    return grammar.start in nullable_variables(grammar)


@dataclass(frozen=True)
class CnfIssue:
    """One failed check, with the offending rule when there is one."""

    code: str
    message: str
    rule: Optional[Production] = None


@dataclass(frozen=True)
class CnfReport:
    """The checked grammar, any problems, and whether a source was supplied."""

    grammar: Grammar
    issues: Tuple[CnfIssue, ...]
    source_checked: bool
    epsilon_in_source: Optional[bool]

    @property
    def is_valid(self) -> bool:
        return not self.issues


def validate_cnf(grammar: Grammar, source: Optional[Grammar] = None) -> CnfReport:
    """Allow A->BC, A->a, or start->epsilon, with start absent on every RHS.

    If a source grammar is given, also check that both grammars agree about
    producing epsilon. Without a source, start->epsilon passes the shape check.
    Passing these checks alone does not prove the two languages are equivalent.
    """
    issues = []
    for rule in sorted(grammar.productions):
        rhs = rule.rhs
        if grammar.start in rhs:
            issues.append(
                CnfIssue(
                    "START_ON_RHS",
                    "The start variable must not appear on any RHS.",
                    rule,
                )
            )
        if not rhs:
            if rule.lhs != grammar.start:
                issues.append(
                    CnfIssue(
                        "NONSTART_EPSILON",
                        "Only the start variable may produce epsilon.",
                        rule,
                    )
                )
        elif len(rhs) == 1:
            if rhs[0] not in grammar.terminals:
                issues.append(
                    CnfIssue(
                        "UNIT_RULE",
                        "A one-symbol RHS must be a terminal, not a variable.",
                        rule,
                    )
                )
        elif len(rhs) == 2:
            if not all(symbol in grammar.variables for symbol in rhs):
                issues.append(
                    CnfIssue(
                        "BINARY_TERMINAL",
                        "A two-symbol RHS must contain two variables.",
                        rule,
                    )
                )
        else:
            issues.append(
                CnfIssue(
                    "LONG_RULE", "CNF permits no RHS longer than two symbols.", rule
                )
            )
    source_epsilon = None
    if source is not None:
        source_epsilon = derives_epsilon(source)
        candidate_epsilon = derives_epsilon(grammar)
        if candidate_epsilon != source_epsilon:
            issues.append(
                CnfIssue(
                    "EPSILON_MEMBERSHIP_CHANGED",
                    "Epsilon membership differs from the source grammar (source: {}, candidate: {}).".format(
                        source_epsilon, candidate_epsilon
                    ),
                )
            )
    return CnfReport(grammar, tuple(issues), source is not None, source_epsilon)


def format_cnf_report(report: CnfReport) -> str:
    """Show pass/fail, explain any bad rules, and say what was actually checked."""
    lines = ["CNF checks: " + ("PASS" if report.is_valid else "FAIL")]
    for issue in report.issues:
        suffix = ""
        if issue.rule is not None:
            suffix = " [" + format_rule(issue.rule, report.grammar) + "]"
        lines.append("  {}: {}{}".format(issue.code, issue.message, suffix))
    if report.source_checked:
        lines.append(
            "Source epsilon membership checked: {}.".format(report.epsilon_in_source)
        )
    else:
        lines.append(
            "Structural checks only; supply --source to verify epsilon membership against an original grammar."
        )
    lines.append(
        "Rule shapes and epsilon checks do not prove full language equivalence."
    )
    return "\n".join(lines)
