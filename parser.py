"""
Parser that recognizes CFG-like specification language

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

def recognize(text: str) -> bool:
    ...

    
def parse(text: str):
   tokens = lex(text)
   