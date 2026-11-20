"""Steven Yang's epsilon removal and the team's checked unit-rule removal."""

import itertools

from cfg_toolkit.model import Grammar, Production


def eliminate_ε_prods(grammar: Grammar) -> Grammar:
    """Drop nullable occurrences and keep epsilon only for the prepared start.

    Call prepare_start() first. Its start cannot appear on a right side, so
    keeping that start's epsilon rule cannot leave other nullable occurrences.
    """
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
    """Yield rules made by omitting any nonempty selection of this variable."""
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
    """Follow unit chains, then copy each reachable variable's non-unit rules.

    For A -> B -> C, A inherits C's ordinary rules as well as B's. The visited
    set also stops cycles such as A -> B -> A. Unused variables stay for Devin.
    """
    unit_targets = {variable: set() for variable in grammar.variables}
    ordinary = {variable: set() for variable in grammar.variables}
    for rule in grammar.productions:
        if len(rule.rhs) == 1 and rule.rhs[0] in grammar.variables:
            unit_targets[rule.lhs].add(rule.rhs[0])
        else:
            ordinary[rule.lhs].add(rule.rhs)

    rules = set()
    for variable in grammar.variables:
        reachable = {variable}
        pending = [variable]
        while pending:
            current = pending.pop()
            for target in unit_targets[current] - reachable:
                reachable.add(target)
                pending.append(target)
        for target in reachable:
            rules.update(Production(variable, rhs) for rhs in ordinary[target])
    return Grammar(grammar.variables, grammar.terminals, rules, grammar.start)
