"""Build the short words a grammar can produce, for use in tests.

Words are tuples of whole terminal names, so "id" counts as one token.
Keep adding words until nothing changes, including through cycles and nullable
variables. Comparing short words is useful evidence, not a full equivalence proof.
"""


def bounded_language(grammar, max_tokens=4):
    """Return all terminal words up to max_tokens long, without changing grammar."""
    words_by_variable = {variable: set() for variable in grammar.variables}
    while True:
        changed = False
        for rule in grammar.productions:
            words = {()}
            for symbol in rule.rhs:
                if symbol in grammar.terminals:
                    suffixes = {(symbol,)}
                else:
                    suffixes = words_by_variable[symbol]

                # Extend the partial words with each word this symbol can produce.
                extended_words = set()
                for left in words:
                    for right in suffixes:
                        if len(left) + len(right) <= max_tokens:
                            extended_words.add(left + right)
                words = extended_words
                if not words:
                    break
            before = len(words_by_variable[rule.lhs])
            words_by_variable[rule.lhs].update(words)
            if before != len(words_by_variable[rule.lhs]):
                changed = True
        if not changed:
            return words_by_variable[grammar.start]
