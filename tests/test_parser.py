import pytest

from src.parser import recognize


@pytest.mark.parametrize(
    "grammar",
    [
        "S -> 'a'",
        "S -> 'a' | 'b'",
        "Expr -> Expr '+' Term | Term\nTerm -> 'a' | 'b'",
        "Start -> '(' Expr ')' | 'a'\nExpr -> Expr '+' Expr | 'a'",
    ],
)
def test_recognize_valid_toy_cfg(grammar: str) -> None:
    assert recognize(grammar) is True
