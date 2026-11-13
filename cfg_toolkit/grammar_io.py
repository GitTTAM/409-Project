"""Read saved JSON grammars and display each rule with its symbols separated."""

import json
from pathlib import Path
import re

from .model import Grammar, GrammarError, Production


FIELDS = {"variables", "terminals", "productions", "start"}


def exact_keys(value, expected, label: str) -> None:
    """Reject missing or misspelled fields instead of silently ignoring them."""
    if not isinstance(value, dict):
        raise GrammarError("{} must be an object".format(label))
    missing = expected - value.keys()
    unknown = value.keys() - expected
    if missing or unknown:
        details = []
        if missing:
            details.append("missing fields: " + ", ".join(sorted(missing)))
        if unknown:
            details.append("unknown fields: " + ", ".join(sorted(map(str, unknown))))
        raise GrammarError("{}: {}".format(label, "; ".join(details)))


def from_dict(data) -> Grammar:
    """Check the JSON structure, then let Grammar check the symbol and rule names."""
    exact_keys(data, FIELDS, "grammar")
    for name in ("variables", "terminals", "productions"):
        if not isinstance(data[name], list):
            raise GrammarError("{} must be a JSON array".format(name))
    rules = []
    for index, item in enumerate(data["productions"]):
        label = "productions[{}]".format(index)
        exact_keys(item, {"lhs", "rhs"}, label)
        if not isinstance(item["rhs"], list):
            raise GrammarError(
                "{}.rhs must be a token array; use [] for epsilon".format(label)
            )
        try:
            rules.append(Production(item["lhs"], item["rhs"]))
        except GrammarError as error:
            raise GrammarError("{}: {}".format(label, error)) from None
    return Grammar(data["variables"], data["terminals"], rules, data["start"])


def _unique_object(pairs):
    """Stop JSON from silently replacing a field that was written twice."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise GrammarError("duplicate JSON field {!r}".format(key))
        result[key] = value
    return result


def loads_grammar(text: str) -> Grammar:
    """Read JSON text and turn syntax errors into readable GrammarError messages."""
    if not isinstance(text, str):
        raise GrammarError("grammar input must be JSON text")
    try:
        data = json.loads(text, object_pairs_hook=_unique_object)
    except json.JSONDecodeError as error:
        raise GrammarError(
            "invalid JSON at line {}, column {}: {}".format(
                error.lineno, error.colno, error.msg
            )
        ) from None
    return from_dict(data)


def read_grammar(path) -> Grammar:
    """Read a JSON file; include its path in any error message."""
    try:
        # Accept UTF-8 files with or without the BOM used by some Windows editors.
        return loads_grammar(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, GrammarError) as error:
        raise GrammarError("{}: {}".format(path, error)) from None


def to_dict(grammar: Grammar) -> dict:
    """Use sorted lists so saving the same grammar produces the same JSON."""
    return {
        "variables": sorted(grammar.variables),
        "terminals": sorted(grammar.terminals),
        "start": grammar.start,
        "productions": [
            {"lhs": rule.lhs, "rhs": list(rule.rhs)}
            for rule in sorted(grammar.productions)
        ],
    }


def dumps_grammar(grammar: Grammar) -> str:
    """Return indented JSON text with a final newline."""
    return json.dumps(to_dict(grammar), indent=2, ensure_ascii=True) + "\n"


def write_grammar(grammar: Grammar, path) -> None:
    """Save a grammar as UTF-8 JSON."""
    Path(path).write_text(dumps_grammar(grammar), encoding="utf-8")


def display_symbol(symbol: str, terminal: bool = False) -> str:
    """Quote terminals and unusual names so the display stays unambiguous."""
    if not terminal and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", symbol):
        return symbol
    return json.dumps(symbol, ensure_ascii=True)


def format_rule(rule: Production, grammar: Grammar) -> str:
    right = (
        " ".join(
            display_symbol(symbol, symbol in grammar.terminals) for symbol in rule.rhs
        )
        or "epsilon"
    )
    return "{} -> {}".format(display_symbol(rule.lhs), right)


def format_grammar(grammar: Grammar, title: str = "Grammar") -> str:
    """Show the four grammar parts, with the start variable's rules listed first."""
    lines = [title, "-" * len(title), "G = (V, Sigma, R, S)"]
    lines.append(
        "V = {" + ", ".join(display_symbol(s) for s in sorted(grammar.variables)) + "}"
    )
    lines.append(
        "Sigma = {"
        + ", ".join(display_symbol(s, True) for s in sorted(grammar.terminals))
        + "}"
    )
    lines.append("S = " + display_symbol(grammar.start))
    lines.append("R ({} distinct rules):".format(len(grammar.productions)))
    if not grammar.productions:
        lines.append("  (no productions; the language is empty)")
    order = sorted(
        grammar.productions,
        key=lambda rule: (rule.lhs != grammar.start, rule.lhs, rule.rhs),
    )
    for rule in order:
        lines.append("  " + format_rule(rule, grammar))
    lines.append(
        "Notation: epsilon is the empty RHS []; quoted names are terminals (or escaped variable names)."
    )
    return "\n".join(lines)
