# Hooking the team's code together

This guide is for adding the Steven Yang and Devin Finn modules. The input and
start-variable code is ready, and the pipeline has a place for each conversion
step. We still need to connect and check the actual transformation functions.

## Team roles

| Role | Lead | Responsibility |
| --- | --- | --- |
| 1 | Matt Lawrence | Grammar representation, input, validation, display, and start preparation |
| 2 | Steven Yang | Epsilon and unit-production removal |
| 3 | Devin Finn | Useless-symbol removal, terminal replacement, and binary rules |
| 4 | Matt Lawrence | Integration, CNF validation, test coordination, docs, and final demo |

Steven Yang and Devin Finn also help with test cases, intermediate/final-output
checks, and regression testing under role 4. Matt keeps the lead for that role.

The flow is:

```text
Grammar file -> Read and validate -> Prepare start -> Steven Yang -> Devin Finn -> CNF check
```

## The main idea

Every step gets a `Grammar` and returns a new `Grammar`.

The team is using **Python 3.14, 64-bit**. Use `python3.14` in the commands below
to select it when other versions are installed. Steven's draft minimum of 3.12
allows 3.14 too. The checks here use `unittest`, so pytest is not required.

The input file can be classroom notation or JSON. Both readers create the same
object, so the conversion functions don't need to deal with file formats.

```python
from cfg_toolkit import read_document

grammar = read_document("examples/lecture/05_nullable_units.cfg")
for rule in sorted(grammar.productions):
    print(rule.lhs, rule.rhs)
```

Use `read_document()` for either format. `read_grammar()` is still available
for code that specifically expects JSON.

## Steven's starting point

Use the existing reader and model instead of maintaining a second set of types:

```python
from cfg_toolkit import Grammar, Production, loads_lecture, nullable_variables

grammar = loads_lecture('S -> A A\nA -> a | epsilon')
nullable = nullable_variables(grammar)  # frozenset({'S', 'A'})
```

In `src/simplify_grammar.py`, import `Grammar` from `cfg_toolkit` and keep these
two function names from the draft branch:

```python
def eliminate_ε_prods(grammar: Grammar) -> Grammar:
    raise NotImplementedError("Implement epsilon removal here")

def eliminate_unit_prods(grammar: Grammar) -> Grammar:
    raise NotImplementedError("Implement unit removal here")
```

These signatures show where Steven's work goes; the functions are not implemented
in this folder. Keep `src/simplify_grammar.py` beside `cfg_toolkit/`, then run
commands from the project root so `src` and `cfg_toolkit` can both be imported.

Use `loads_lecture(text)` wherever the draft uses `parser.compile(text)`.
It returns a `Grammar` or raises `GrammarError`, so a stub returning `None`
cannot pass as a parsed grammar. Parentheses are literal terminals in our
notation. The draft parser describes them as grouping; don't mix those meanings.

The draft fields become:

| Draft | Shared model |
| --- | --- |
| `cfg.start_variable.name` | `grammar.start` |
| `cfg.rules` | `grammar.productions` |
| `rule.lhs.name` | `rule.lhs` |
| Expression tree on the right | `rule.rhs`, a tuple of symbol names |
| Alternation object | Separate `Production` objects |

This also removes the `cfg` versus `src.cfg` import mismatch from the shared
path. `Production` is hashable, so sets of rules work. `("A", "B")` stores a
sequence directly, and `()` stores epsilon. Keep using these shared types when
building results; a separate `CFG` class will fail the pipeline's type check.

### Run the role 2 checks

```powershell
python3.14 tools/check_role2.py --list-cases
python3.14 tools/check_role2.py src.simplify_grammar
```

If function names differ, pass `--epsilon your_function --units your_function`.
No code is copied from GitHub by this command; it imports the local module.

| Case | What it catches |
| --- | --- |
| Repeated nullable symbols | Both occurrences in `S -> A A` may disappear; duplicate outcomes collapse |
| Indirect epsilon | Nullable status travels through `A -> C -> epsilon` |
| Unit cycle with an exit | All variables in the cycle inherit the terminal rule |
| Epsilon under the prepared start | `S_0` keeps epsilon; the old `S` loses its epsilon rule |
| Already simplified | Valid rules survive unchanged |
| Epsilon only | The empty word is not lost |
| Unit cycle with no terminal word | The result has no productions, rather than a made-up word |
| Three nullable occurrences and whole token names | Long right sides and the single terminal `id` stay intact |

Each case checks epsilon removal, unit removal, and their pipeline connection:
**24 checks total**. Unit removal also gets a known epsilon result so it can be
tested independently. The expected rules are in [tests/role2_contract.py](tests/role2_contract.py).

For example, after removing epsilon from `S -> A A; A -> a | epsilon`, expect:

```text
S -> A A | A | epsilon
A -> a
```

After removing units, expect:

```text
S -> A A | a | epsilon
A -> a
```

These checks expect epsilon and unit removal as separate steps. Leave useless
symbol cleanup for Devin. They compare actual `Grammar` results and exact rules,
keep earlier inputs unchanged, check epsilon, and compare words through four
terminal tokens with `tests/support.py`. Finite word checks are not a proof.

Exit status `0` means the role 2 cases passed, `1` means checks failed, and `2`
means the module or functions could not be loaded. Missing implementations are
pending, never counted as passes. The normal test command checks the fixtures
and verifies that bad stubs fail; it does not claim Steven's functions passed.

To connect just Steven's finished functions:

```python
from cfg_toolkit.pipeline import run_pipeline
from src.simplify_grammar import eliminate_ε_prods, eliminate_unit_prods

result = run_pipeline(grammar, {
    "remove_epsilon": eliminate_ε_prods,
    "remove_units": eliminate_unit_prods,
})
```

It stops at Devin's first missing stage and keeps full conversion marked pending.

## What's in a Grammar?

| Field | What's inside |
| --- | --- |
| `grammar.variables` | Variable names, like `S`, `A`, and `S0` |
| `grammar.terminals` | Terminal names, like `a`, `b`, or `id` |
| `grammar.productions` | The set of `Production` objects |
| `grammar.start` | The current start variable's name |

A `Production` has a left side and a right side:

```python
from cfg_toolkit import Production

recursive_rule = Production("S", ("a", "S", "b"))
empty_rule = Production("S", ())
```

The right side is a tuple of whole symbol names. `ASA` from the slides becomes
`("A", "S", "A")`. Names like `S0`, `Expr`, and `X_a` stay whole. Epsilon is the
empty tuple `()`. Parentheses are terminals when they belong to the grammar.

The objects are frozen, which means you can't change them in place. Make your
updated collections, then return a new `Grammar`. This keeps the original and
earlier steps available for comparison.

The function interface is:

```python
from cfg_toolkit import Grammar

def transform(grammar: Grammar) -> Grammar:
    ...  # Put the actual transformation here.
```

When you build the result, pass its variables, terminals, productions, and start
to `Grammar(...)`. The constructor checks that they still form a valid CFG.

## A few rules everyone should follow

- Return a `Grammar` object. Keep printing and file reading outside the
  transformation function.
- Keep the prepared start variable. If it is `S_0`, don't switch it back to `S`.
- Pick helper names that don't already appear in either the variables or the
  terminals. Removing unused terminals is fine; adding new terminals isn't.
- Work with whole names. Don't turn `Expr` into four characters.
- Handle right sides of any length. The assignment puts epsilon removal before
  binarization, even though some slides show a different order.
- Keep epsilon only for the current start when the original language includes
  it. The example below explains why the current start matters.

## Who handles each step?

| Order | Pipeline key | Owner | Job |
| --- | --- | --- | --- |
| 1 | `original` | Matt Lawrence | Read, validate, and show the grammar |
| 2 | `prepare_start` | Matt Lawrence | Add a fresh start when needed |
| 3 | `remove_epsilon` | Steven Yang | Remove epsilon rules while keeping the language's empty word if needed |
| 4 | `remove_units` | Steven Yang | Remove unit rules, including the new start's unit rule |
| 5 | `remove_useless` | Devin Finn | Remove symbols that can't help generate a word from the start |
| 6 | `replace_terminals` | Devin Finn | Replace terminals inside right sides of length two or more |
| 7 | `binarize` | Devin Finn | Break right sides longer than two into binary rules |
| 8 | `final` | Matt Lawrence, with testing help from Steven Yang and Devin Finn | Show the result and run the CNF checks |

The first two steps are already built into `run_pipeline()`. You supply the five
functions in the middle. The pipeline runs them in the order shown here and
saves the grammar after each one.

## Connecting the functions

Once the teammate modules are ready, the setup looks like this. `student2` and
`student3` are example module names; use the actual names from the team's code.

```python
from cfg_toolkit import read_document
from cfg_toolkit.pipeline import run_pipeline
from student2 import remove_epsilon, remove_units
from student3 import remove_useless, replace_terminals, binarize

original = read_document("examples/lecture/05_nullable_units.cfg")
result = run_pipeline(original, {
    "remove_epsilon": remove_epsilon,
    "remove_units": remove_units,
    "remove_useless": remove_useless,
    "replace_terminals": replace_terminals,
    "binarize": binarize,
})
```

The dictionary keys need to match the table. Function names can be different;
just put the right function next to each key. Each function still needs to use
the shared `Grammar` interface.

If a function is missing, the pipeline stops at that step. It won't jump ahead
to a later function. The result gives you:

- `snapshots`: the grammars from the steps that actually ran, along with their
  stage names and titles.
- `pending`: the steps that haven't run yet.
- `cnf_report`: the final checks, once all transformation steps have run.
- `is_complete`: whether all steps ran and the final CNF checks passed.

A complete result still needs language tests. Passing the final shape checks
doesn't catch every possible mistake in a transformation.

## Epsilon and the new start

Suppose the original grammar is:

```text
S -> aSb | epsilon
```

Matt Lawrence prepares it as:

```text
S_0 -> S
S -> aSb | epsilon
```

Steven Yang needs to preserve epsilon for `S_0`, remove the old `S -> epsilon`,
and later remove the unit rule `S_0 -> S`. If Matt Lawrence didn't need a new start,
the original start keeps that responsibility.

`nullable_variables(grammar)` tells you which variables can produce epsilon.
`derives_epsilon(grammar)` checks the start. Both live in `cnf_validator.py` and
can be reused as helpers. They analyze the grammar; the actual removal is still
Steven Yang's job.

## Testing the pieces together

From the project folder, run:

```powershell
python3.14 -m unittest discover -s tests -v
```

Some useful files to start with:

| Example | What to watch for |
| --- | --- |
| `examples/lecture/03_matching.cfg` | Epsilon survives under the prepared start |
| `examples/lecture/05_nullable_units.cfg` | `A` and `B` are nullable, but `S` isn't; repeated `A` occurrences need handling |
| `examples/lecture/02_arithmetic.cfg` | Operators, literal parentheses, unit rules, and longer right sides |
| `examples/06_empty_language.json` | The grammar stays valid even when it generates no words |
| `examples/07_epsilon_only.json` | The language contains only the empty word |

`examples/lecture/06_matching_final_cnf.cfg` is copied from the professor's final
example. It is a known result for testing the checker. Compare it with
`examples/lecture/03_matching.cfg`.

## Matt Lawrence: final integration and testing

Matt leads this work. Steven and Devin help design and run tests and check the
intermediate and final grammars. These assignments do not mean the full
conversion is finished yet.

Once the real transformation functions are connected:

1. Print the grammar after every step and check that each step did its job.
2. Run `validate_cnf(final, source=original)` so the checker also catches epsilon
   being lost or added incorrectly.
3. Compare generated words before and after conversion. The helper in
   `tests/support.py` handles a chosen maximum word length, including epsilon
   and cycles. These checks catch bugs; they don't prove full equivalence.
4. Save at least three full conversion runs, including inputs with epsilon and
   unit rules. Refresh `sample_runs/` once those runs work end to end.
5. Finish the project report, contribution statement, and final demo.

The checker covers CNF rule shapes, start placement, and optional source epsilon
membership. Checks for useless symbols and each intermediate transformation
belong in the integration tests too.

## Where the desktop window fits

Run `python3.14 gui.py` or double-click `start_gui.bat`. It is another way to use
the same functions for Matt Lawrence's part:

```text
Editor -> loads_lecture() -> Grammar -> prepare_start() -> comparison + save
```

The GUI currently calls `prepare_start()` directly. It does not register or run
Steven Yang and Devin Finn transformations. Its output is a start-prepared CFG, and the missing
conversion steps stay marked pending.

The GUI uses classroom notation and saves `.cfg` files. Users paste rules or
load a built-in example; there is no file-opening or format-selection control.

- `cfg_toolkit/gui.py` handles widgets, dialogs, and the current input/results.
- `cfg_toolkit/gui_support.py` adds correction tips and finds new rule lines
  for highlighting. It keeps the parser's original error message.
- `cfg_toolkit/learning.py` holds the explanations and source references. The
  source viewer finds functions by name, so line numbers can change safely.

Adding a practice example is a `(label, relative path)` entry in `EXAMPLES` in
`gui.py`. Put your grammar in `examples/practice/`; keep the six professor-based
files as their original reference examples. Add a focused test for the behavior
your new example is meant to check.

To add a lesson, use another `Lesson` entry in `learning.py`. Point it to an
actual implementation and test with `CodeReference(path, name)`. The lesson
tests check that those references still exist.

When Matt Lawrence connects Steven Yang's and Devin Finn's modules, use `run_pipeline()` for the full
run and display its snapshots. Keep file parsing and grammar transformations
outside the widget code. Do not treat the current start-prepared result as the
finished CNF conversion.
