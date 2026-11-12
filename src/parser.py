"""
Parser that recognizes CFG-like specification language.

All words are considered variable names unless wrapped in single quotes,
or match an operator, in which case they are terminals. Whitespace is
ignored. E.g. 'class' is a single terminal literal.

The only operators are production [->], parentheses [()], and alternation [|].

Snippet:
    Term -> Term '+' Factor | Factor
    Factor -> Factor '*' Expression
            | Expression
    Expression -> '(' Term ') | 'a'

EBNF:
    Grammar     ::= Rule { NL Rule }
    Rule        ::= Name WS? "->" WS? Alternative
    Alternative ::= Sequence { WS? "|" WS? Sequence }
    Sequence    ::= Item { WS Item }
    Item        ::= Name | Terminal | "(" Alternative ")"
    Name        ::= <letter> { <letter> | <digit> | "_" }
    Terminal    ::= "'" { <any-char> } "'"
    WS          ::= { " " | "\t" } // whitespace
    NL          ::= "\n" | "\r\n" // newline
"""

from cfg import CFG


def recognize(text: str) -> bool: ...


def compile(text: str) -> CFG: ...
