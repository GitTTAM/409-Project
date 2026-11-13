"""Read and display CFGs using the notation from class.

Declarations are optional: V/Variables, Sigma/Terminals, Start/S. Without V,
variables come from all left sides. Without Sigma, quoted tokens and individual
non-uppercase characters become terminals. Parentheses are literal symbols.
An exact declared symbol stays whole; other compact runs must split uniquely.
"""

import ast
import json
import re
from typing import Optional, Sequence, Tuple

from .model import Grammar, GrammarError, Production


EPSILON_MARKERS = frozenset(("epsilon", "eps", "\u03b5", "\u03f5"))
DECLARATIONS = {
    "v": "variables",
    "variables": "variables",
    "sigma": "terminals",
    "\u03a3": "terminals",
    "\u03c3": "terminals",
    "terminals": "terminals",
    "start": "start",
    "start_symbol": "start",
    "s": "start",
}


def _error(line: int, message: str) -> GrammarError:
    """Attach the input line number to a helpful error message."""
    return GrammarError("line {}: {}".format(line, message))


def _read_quoted_symbol(text: str, offset: int, line: int) -> Tuple[str, int]:
    """Read one quoted name and return the position just after its closing quote."""
    quote = text[offset]
    end = offset + 1
    while end < len(text):
        if text[end] == "\\":
            end += 2
            continue
        if text[end] == quote:
            literal = text[offset : end + 1]
            try:
                # literal_eval reads an escaped string; it does not run Python code.
                value = ast.literal_eval(literal)
            except (ValueError, SyntaxError):
                raise _error(
                    line, "invalid quoted symbol at column {}".format(offset + 1)
                ) from None
            if not isinstance(value, str):
                raise _error(line, "quoted symbols must be strings")
            return value, end + 1
        end += 1
    raise _error(line, "unterminated quote at column {}".format(offset + 1))


def _strip_comment(text: str, line: int) -> str:
    """Remove // comments, while keeping // inside quotes as a literal symbol."""
    offset = 0
    while offset < len(text):
        if text[offset] in "\"'":
            _, offset = _read_quoted_symbol(text, offset, line)
        elif text.startswith("//", offset):
            return text[:offset]
        else:
            offset += 1
    return text


def _split_alternatives(text: str, line: int) -> Sequence[str]:
    """Split at unquoted | characters, rejecting missing alternatives."""
    parts = []
    start = offset = 0
    while offset < len(text):
        if text[offset] in "\"'":
            _, offset = _read_quoted_symbol(text, offset, line)
        elif text[offset] == "|":
            parts.append(text[start:offset].strip())
            offset += 1
            start = offset
        else:
            offset += 1
    parts.append(text[start:].strip())
    if any(not part for part in parts):
        raise _error(line, "empty alternative; write epsilon explicitly")
    return parts


def _split_production(text: str, line: int) -> Optional[Tuple[str, str]]:
    """Find an unquoted arrow and separate the left and right sides."""
    offset = 0
    while offset < len(text):
        if text[offset] in "\"'":
            _, offset = _read_quoted_symbol(text, offset, line)
        elif text.startswith("->", offset):
            return text[:offset].strip(), text[offset + 2 :].strip()
        elif text[offset] == "\u2192":
            return text[:offset].strip(), text[offset + 1 :].strip()
        else:
            offset += 1
    return None


def _read_names(text: str, line: int, braces: bool = False) -> list:
    """Read whole names separated by spaces or commas, with optional {braces}."""
    text = text.strip()
    if braces and text.startswith("{"):
        if not text.endswith("}"):
            raise _error(line, "a declaration starting with { must end with }")
        text = text[1:-1]
    elif braces and text.endswith("}"):
        raise _error(line, "unexpected } in declaration")
    names = []
    offset = 0
    after_comma = False
    while offset < len(text):
        if text[offset].isspace():
            offset += 1
            continue
        if text[offset] == ",":
            if not names or after_comma:
                raise _error(line, "empty symbol in declaration")
            after_comma = True
            offset += 1
            continue
        if text[offset] in "\"'":
            value, offset = _read_quoted_symbol(text, offset, line)
            if (
                offset < len(text)
                and not text[offset].isspace()
                and text[offset] != ","
            ):
                raise _error(line, "separate declared names with spaces or commas")
        else:
            end = offset
            while end < len(text) and not text[end].isspace() and text[end] != ",":
                end += 1
            value, offset = text[offset:end], end
        names.append(value)
        after_comma = False
    if after_comma:
        raise _error(line, "empty symbol after final comma")
    return names


def _split_compact_symbols(
    run: str, variables, terminals, line: int
) -> Tuple[str, ...]:
    """Split a run like aSb, but ask for spaces if more than one split fits."""
    known_symbols = set(variables)
    if terminals is not None:
        known_symbols.update(terminals)
    if run in known_symbols:
        # A declared name such as AB stays one symbol. Write A B to split it.
        return (run,)

    symbols_by_first_character = {}
    for symbol in known_symbols:
        symbols_by_first_character.setdefault(symbol[0], []).append(symbol)

    # Start at the end and work backward. Each position keeps the possible
    # symbol sequences for the rest of the text. Two are enough to show ambiguity.
    parses_by_position = {len(run): [()]}
    for offset in range(len(run) - 1, -1, -1):
        matching_symbols = set()
        for symbol in symbols_by_first_character.get(run[offset], ()):
            if run.startswith(symbol, offset):
                matching_symbols.add(symbol)
        if terminals is None and not run[offset].isupper():
            matching_symbols.add(run[offset])
        parses = []
        for symbol in sorted(matching_symbols):
            for suffix in parses_by_position.get(offset + len(symbol), ()):
                candidate = (symbol,) + suffix
                if candidate not in parses:
                    parses.append(candidate)
                if len(parses) == 2:
                    break
            if len(parses) == 2:
                break
        parses_by_position[offset] = parses
    parses = parses_by_position.get(0, [])
    if not parses:
        raise _error(
            line,
            "cannot tokenize {!r}; declare its symbols in V/Sigma or separate names with spaces".format(
                run
            ),
        )
    if len(parses) > 1:
        raise _error(
            line, "ambiguous compact RHS {!r}; separate symbols with spaces".format(run)
        )
    return parses[0]


def _read_rhs(text: str, variables, terminals, line: int) -> Tuple[str, ...]:
    """Read one alternative as a tuple of symbols; epsilon becomes ()."""
    text = text.strip()
    if text in EPSILON_MARKERS or text in ("''", '""'):
        return ()
    if not text:
        raise _error(line, "empty alternative; write epsilon explicitly")
    tokens = []
    offset = 0
    while offset < len(text):
        if text[offset].isspace():
            offset += 1
            continue
        if text[offset] in "\"'":
            token, offset = _read_quoted_symbol(text, offset, line)
            if not token:
                raise _error(line, "epsilon must be the entire alternative")
            if (
                token not in variables
                and terminals is not None
                and token not in terminals
            ):
                raise _error(line, "undeclared quoted symbol {!r}".format(token))
            tokens.append(token)
            continue
        end = offset
        while end < len(text) and not text[end].isspace() and text[end] not in "\"'":
            end += 1
        run = text[offset:end]
        if (
            any(marker in run for marker in ("\u03b5", "\u03f5"))
            or run in EPSILON_MARKERS
        ):
            raise _error(
                line,
                "epsilon must be the entire alternative; quote a literal epsilon-like name",
            )
        if "->" in run or "\u2192" in run:
            raise _error(line, "extra production arrow; quote literal arrow symbols")
        tokens.extend(_split_compact_symbols(run, variables, terminals, line))
        offset = end
    return tuple(tokens)


def _read_document_lines(text: str):
    """Collect declarations and raw rules before trying to split RHS symbols."""
    declarations = {}
    raw_rules = []
    lhs_order = []
    current_lhs = None
    for number, raw_line in enumerate(text.lstrip("\ufeff").splitlines(), 1):
        line = _strip_comment(raw_line, number).strip()
        if not line:
            continue
        if line.startswith("|"):
            if current_lhs is None:
                raise _error(
                    number, "an alternative continuation needs a preceding production"
                )
            for alternative in _split_alternatives(line[1:], number):
                raw_rules.append((current_lhs, alternative, number))
            continue
        production = _split_production(line, number)
        if production is not None:
            left, right = production
            names = _read_names(left, number)
            if len(names) != 1:
                raise _error(number, "production LHS must be exactly one variable")
            current_lhs = names[0]
            if current_lhs not in lhs_order:
                lhs_order.append(current_lhs)
            for alternative in _split_alternatives(right, number):
                raw_rules.append((current_lhs, alternative, number))
            continue
        match = re.fullmatch(r"([^=:]+)\s*[=:]\s*(.*)", line)
        if match is None:
            raise _error(
                number, "expected a production (A -> RHS) or V/Sigma/Start declaration"
            )
        key = match.group(1).strip()
        field = DECLARATIONS.get(key.lower())
        if field is None:
            raise _error(
                number, "unknown declaration {!r}; use V, Sigma, or Start".format(key)
            )
        if raw_rules:
            raise _error(number, "declarations must appear before productions")
        if field in declarations:
            raise _error(number, "duplicate {} declaration".format(field))
        values = _read_names(match.group(2), number, braces=field != "start")
        if field == "start":
            if len(values) != 1:
                raise _error(number, "Start must name exactly one variable")
            declarations[field] = values[0]
        else:
            declarations[field] = values
    return declarations, raw_rules, lhs_order


def loads_lecture(text: str) -> Grammar:
    """Turn classroom notation into the same Grammar used by the JSON reader."""
    if not isinstance(text, str):
        raise GrammarError("lecture input must be text")

    # Read every left side first, so rules may refer to variables defined later.
    declarations, raw_rules, lhs_order = _read_document_lines(text)

    variables = declarations.get("variables", lhs_order)
    terminals = declarations.get("terminals")
    start = declarations.get("start", lhs_order[0] if lhs_order else None)
    if start is None:
        raise GrammarError(
            "no start variable; provide productions or an explicit Start declaration"
        )
    # Check names before splitting any RHS. A temporary grammar lets the shared
    # model catch duplicates, empty names, and variable/terminal overlap for us.
    declared_terminals = [] if terminals is None else terminals
    base = Grammar(variables, declared_terminals, [], start)
    rules = []
    inferred_terminals = set()
    for lhs, alternative, number in raw_rules:
        try:
            if lhs not in base.variables:
                raise GrammarError(
                    "production lhs {!r} is not a declared variable".format(lhs)
                )
            rhs = _read_rhs(alternative, base.variables, terminals, number)
            rules.append(Production(lhs, rhs))
            inferred_terminals.update(set(rhs) - base.variables)
        except GrammarError as error:
            if str(error).startswith("line "):
                raise
            raise _error(number, str(error)) from None
    if terminals is None:
        terminals = inferred_terminals
    return Grammar(base.variables, terminals, rules, start)


def _symbol_text(symbol: str) -> str:
    simple = re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*|[0-9#()+*./-]", symbol)
    if simple and symbol not in EPSILON_MARKERS and "//" not in symbol:
        return symbol
    return json.dumps(symbol, ensure_ascii=True)


def _rhs_text(rule: Production, grammar: Grammar, unicode_symbols: bool) -> str:
    if not rule.rhs:
        return "\u03b5" if unicode_symbols else "epsilon"
    pieces = [_symbol_text(symbol) for symbol in rule.rhs]
    compact = "".join(pieces)
    try:
        # Compact output is safe only if reading it again gives the same symbols.
        if _read_rhs(compact, grammar.variables, grammar.terminals, 1) == rule.rhs:
            return compact
    except GrammarError:
        pass
    return " ".join(pieces)


def dumps_lecture(grammar: Grammar, unicode_symbols: bool = True) -> str:
    """Write classroom notation that can be read back without losing information.

    Use spaces whenever compact output would change or ambiguously tokenize a
    sequence. Declarations preserve unused symbols and empty-language grammars.
    """
    lines = [
        "V = {" + ", ".join(_symbol_text(s) for s in sorted(grammar.variables)) + "}",
        "Sigma = {"
        + ", ".join(_symbol_text(s) for s in sorted(grammar.terminals))
        + "}",
        "Start = " + _symbol_text(grammar.start),
    ]
    order = sorted(grammar.variables, key=lambda name: (name != grammar.start, name))
    arrow = "\u2192" if unicode_symbols else "->"
    for variable in order:
        rules = sorted(rule for rule in grammar.productions if rule.lhs == variable)
        if rules:
            alternatives = " | ".join(
                _rhs_text(rule, grammar, unicode_symbols) for rule in rules
            )
            lines.append("{} {} {}".format(_symbol_text(variable), arrow, alternatives))
    return "\n".join(lines) + "\n"


def format_lecture(
    grammar: Grammar, title: str = "Grammar", unicode_symbols: bool = False
) -> str:
    """Add a title and rule count to the classroom grammar display."""
    lines = [
        title,
        "-" * len(title),
        "G = (V, Sigma, R, S)",
        dumps_lecture(grammar, unicode_symbols).rstrip(),
        "{} distinct rules; parentheses are literal terminals when declared.".format(
            len(grammar.productions)
        ),
    ]
    return "\n".join(lines)
