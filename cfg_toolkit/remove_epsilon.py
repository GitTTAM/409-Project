from cfg_toolkit.model import Grammar, Production


def eliminate_ε_prods(grammar: Grammar) -> Grammar:
    new_prods = set(grammar.productions)
    eprods = filter(lambda p: p.lhs != grammar.start and p.rhs == (), new_prods)
    for eprod in eprods:
        new_prods.remove(eprod)
        for prod in new_prods:
            if eprod.lhs in prod.rhs:
                new_rhs = tuple(s for s in prod.rhs if s != eprod.lhs)
                new_prods.add(Production(prod.lhs, new_rhs))

    return Grammar(
        grammar.variables, grammar.terminals, frozenset(new_prods), grammar.start
    )


def eliminate_unit_prods(grammar: Grammar) -> Grammar:
    raise NotImplementedError("Implement unit removal here")
