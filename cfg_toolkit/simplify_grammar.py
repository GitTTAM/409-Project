import itertools

from cfg_toolkit.model import Grammar, Production


def eliminate_ε_prods(grammar: Grammar) -> Grammar:
    # separate epsilon rules from others
    epsilon_rules = set()
    other_rules = set()
    for r in grammar.productions:
        if r.lhs != grammar.start and r.rhs == ():
            epsilon_rules.add(r)
        else:
            other_rules.add(r)

    removed_already = set(epsilon_rules)  # ε-rules removed already
    while epsilon_rules:
        e_rule = epsilon_rules.pop()
        tmp = set()
        # substitute lhs into other rules
        for o_rule in other_rules:
            for new_rule in sub_with_ε(var=e_rule.lhs, rule=o_rule):
                if new_rule.rhs or new_rule.lhs == grammar.start:
                    tmp.add(new_rule)
                elif new_rule not in removed_already:
                    epsilon_rules.add(new_rule)
        other_rules.update(tmp)
        removed_already.add(e_rule)

    return Grammar(
        grammar.variables, grammar.terminals, frozenset(other_rules), grammar.start
    )


def sub_with_ε(var: str, rule: Production):
    # get indices of all variables to replace
    indices = [i for i, v in enumerate(rule.rhs) if v == var]
    for r in range(1, len(indices) + 1):
        # choose r indices to replace
        for replace in itertools.combinations(indices, r):
            new_rhs = tuple(
                v for i, v in enumerate(rule.rhs) if i not in replace
            )  # replace with ε same as delete
            yield Production(rule.lhs, new_rhs)


def eliminate_unit_prods(grammar: Grammar) -> Grammar:
    # separate unit rules from others
    unit_rules = []
    other_rules = []
    for r in grammar.productions:
        if len(r.rhs) == 1 and r.rhs[0] in grammar.variables:
            unit_rules.append(r)
        else:
            other_rules.append(r)

    removed_already = set(unit_rules)  # unit-rules removed already
    while unit_rules:
        u_rule = unit_rules.pop()
        for o_rule in other_rules:
            # A -> B, B -> xyz => A -> xyz
            if u_rule.rhs == o_rule.lhs:
                new_rule = Production(u_rule.lhs, o_rule.rhs)
                if len(new_rule.rhs) == 1 and new_rule not in removed_already:
                    unit_rules.append(new_rule)
                other_rules.append(new_rule)
        removed_already.add(u_rule)

    return Grammar(
        grammar.variables, grammar.terminals, frozenset(other_rules), grammar.start
    )
