from src.parser import compile
from src.simplify_grammar import eliminate_unit_prods, eliminate_ε_prods


class Test_Epsilon_Production_Elimination:
    def test_unchanged_if_no_ε_prods(self):
        cfg = compile("S -> 'a'")
        assert cfg == eliminate_ε_prods(cfg)

        cfg = compile("S -> 'a'\nS -> 'bb'\nA -> SA | 'c'")
        assert cfg == eliminate_ε_prods(cfg)

    def test_unchanged_if_ε_in_start(self):
        cfg = compile("S -> ''")
        assert cfg == eliminate_ε_prods(cfg)

        cfg = compile("S -> 'a' | ''")
        assert cfg == eliminate_ε_prods(cfg)

    def test_remove_single_ε_prods(self): ...

    def test_remove_multiple_ε_prods(self): ...

    def test_remove_ε_prods_requiring_multiple_passes(self): ...


class Test_Unit_Production_Elimination:
    def test_unchanged_if_no_unit_prods(self):
        cfg = compile("S -> '('S')'S | ''")
        assert cfg == eliminate_unit_prods(cfg)

        cfg = compile("S -> 'a'\nS -> 'bb'\nA -> SA | 'c'")
        assert cfg == eliminate_unit_prods(cfg)

    def test_eliminate_unit_prods(self): ...
