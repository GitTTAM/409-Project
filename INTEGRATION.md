# Connecting the team's code

The app now runs Matt's input/start setup and Steven's two simplification steps.
Devin's CNF transformations are next. Use Python 3.14, 64-bit, for everyone.

## Team

| Member | Work |
| --- | --- |
| Matt Lawrence | Roles 1 and 4: input, representation, start setup, integration, CNF validation, testing lead, docs, demo |
| Steven Yang | Role 2: epsilon and unit removal; testing support |
| Devin Finn | Role 3: useless symbols, terminal replacement, binary rules; testing support |

## Current flow

```text
Read -> Prepare start -> Remove epsilon -> Remove units -> Devin's steps -> CNF check
```

| Pipeline key | Function or owner | Status |
| --- | --- | --- |
| `original` | `loads_lecture()` or `read_document()` | Ready |
| `prepare_start` | `prepare_start()` | Ready |
| `remove_epsilon` | Steven's `eliminate_ε_prods()` | Connected |
| `remove_units` | `eliminate_unit_prods()` | Connected and checked |
| `remove_useless` | Devin Finn | Pending |
| `replace_terminals` | Devin Finn | Pending |
| `binarize` | Devin Finn | Pending |
| `final` | `validate_cnf()` | Runs after every transformation is connected |

Devin's exact interface, examples, and test commands are in
[DEVIN_HANDOFF.md](DEVIN_HANDOFF.md).

## One shared model

```python
from cfg_toolkit import Grammar, Production, loads_lecture, read_document

grammar = loads_lecture("S -> A A\nA -> a | epsilon")
rule = Production("S", ("A", "A"))
empty_rule = Production("S", ())
```

| Field | Meaning |
| --- | --- |
| `grammar.variables` | Frozen set of whole variable names |
| `grammar.terminals` | Frozen set of whole terminal names |
| `grammar.productions` | Frozen set of hashable `Production` objects |
| `grammar.start` | Current start name |
| `rule.lhs` | One variable name |
| `rule.rhs` | Tuple of whole symbol names; `()` is epsilon |

`("A", "B")` has two symbols. `("AB",)` has one. `id` can be one terminal.
Literal parentheses stay terminals. Alternatives become separate productions.
The classroom and JSON readers both produce this model; the GUI uses classroom
notation only. Transformation functions never need to parse files themselves.

Grammars stay unchanged between steps. Make updated collections and return
`Grammar(variables, terminals, productions, start)`. Its constructor validates
symbols and rule references. Returning the same object is fine when nothing changes.

## The pipeline

```python
from cfg_toolkit import read_document
from cfg_toolkit.pipeline import run_pipeline

original = read_document("examples/lecture/03_matching.cfg")
result = run_pipeline(original)
for step in result.snapshots:
    print(step.stage, step.grammar)
print(result.pending)
```

With no mapping, `run_pipeline()` uses `team_transforms()` from `pipeline.py`.
That mapping currently connects Steven's real functions. It stops before Devin's
first missing function. It does not fill in missing steps with no-op functions.

For an isolated check, pass an explicit dictionary. It replaces the default
mapping completely. `run_pipeline(original, {})` runs just input and start setup.
Each transformation must return a `Grammar`, preserve the prepared start, and
avoid adding terminals. Final structural validation runs only after all five
transformation functions have run.

The result contains:

- `snapshots`: original, start setup, and every transformation that actually ran.
- `pending`: remaining stage keys.
- `cnf_report`: final checks, or `None` while stages are missing.
- `is_complete`: every stage ran and final CNF checks passed.

Passing structural checks still needs language tests. It does not establish
full equivalence by itself.

## Epsilon and the prepared start

For `S -> aSb | epsilon`, start setup adds `S_0 -> S`.
Steven's epsilon removal moves the empty word to `S_0`. Unit removal then copies
S's non-unit rules to `S_0`, removing that temporary `S_0 -> S` rule.
The original grammar and the start-setup snapshot remain available for comparison.

`nullable_variables()` and `derives_epsilon()` are shared helpers exported from
`cfg_toolkit`. `tests/support.py` compares generated terminal words through a
chosen maximum length, including cycles and epsilon.

## What changed in the integration review

Steven's new module is `cfg_toolkit/simplify_grammar.py`; it uses the shared model.
His epsilon algorithm and added epsilon-cycle case are retained. The review also:

- Restored unit and pipeline cases that had been temporarily disabled.
- Fixed unit removal to follow complete chains and cycles. The draft compared
  the tuple right side with a string left side, preventing rule copying.
- Corrected the cycle fixture to keep `B -> a`, which follows from `B -> A -> a`.
- Removed debugging prints from the checks.
- Connected both functions to the default CLI and GUI run.

These are integration fixes and verification work, separate from the team's role assignments.

## Checks and evidence

```powershell
python3.14 -m unittest discover -s tests -v
python3.14 tools/check_role2.py
python3.14 tools/check_role3.py --list-cases
python3.14 tools/check_role3.py
```

Steven's real functions run against nine grammars, with epsilon, unit, and
pipeline checks for each: 27 checks. The normal suite also checks 250 fixed
generated grammars for stage conditions and word preservation through three tokens.

Devin's runner has seven grammars and 28 checks. Until his module is added,
its nonzero exit status reports pending work. The normal suite checks the handoff
tests using known fixture answers and broken callbacks; that is not a passing
run of Devin's implementation.

The GUI keeps **Run**, **Save input**, **Clear**, **Save result**, and **Help**.
Its left view shows the original; the right shows the result after Steven's steps.
**Help > Walkthrough** still explains Matt's input and start setup using real snapshots.
`--save-prepared` in the CLI keeps its original start-only meaning;
`--save-result` exports the current grammar for Devin.

Refresh deliverable evidence and the ZIP with:

```powershell
python3.14 tools/generate_evidence.py
python3.14 tools/package_handoff.py
```

## Matt's remaining role 4 work

After Devin's functions pass and are registered, run full conversion tests,
update pending-status wording, verify every intermediate step, and save at least
three complete conversion runs. Finish the report, contribution statement, and
demo with Steven's and Devin's testing help. Current saved runs stop after unit
removal; they are not presented as finished CNF conversions.
