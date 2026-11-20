# Devin: start here

Matt's input and start setup and Steven's epsilon and unit removal are connected.
Your part starts with the grammar after `remove_units`.
Use **Python 3.14, 64-bit**. No extra packages needed.

## Your three functions

Add `cfg_toolkit/cnf_transforms.py` with:

```python
from cfg_toolkit import Grammar, Production

def remove_useless(grammar: Grammar) -> Grammar:
    raise NotImplementedError("Remove unproductive and unreachable symbols")

def replace_terminals(grammar: Grammar) -> Grammar:
    raise NotImplementedError("Replace terminals inside longer right sides")

def binarize(grammar: Grammar) -> Grammar:
    raise NotImplementedError("Split right sides longer than two")
```

Replace those bodies with your work. These are interface examples; no placeholder
functions are connected to the app.

Each function gets a checked, frozen `Grammar`. Build and return a new one.
Use tuples of whole names: `("A", "B")` means two symbols; `("AB",)` means one.
Epsilon is `()`. Keep `grammar.start` and preserve its epsilon rule when present.
Keep the start off right sides. Avoid reintroducing unit rules.

For helper names, check both `grammar.variables` and `grammar.terminals`.
Do not overwrite existing names such as `T_a`, `X_1`, or a terminal with that name.
You can choose your own helper naming scheme; the tests allow that.

## What each step should do

1. **Remove useless symbols.** Find productive variables first, discard rules
   involving unproductive variables, then find reachable symbols in what remains.
   Remove unused terminals too. For an empty language, keep the start declared
   with no productions and no terminals.
2. **Replace terminals.** A terminal alone, such as `A -> id`, stays alone.
   In a longer right side, use a variable that produces that whole terminal.
3. **Binarize.** Split every right side longer than two into binary rules.
   Keep terminal rules and the optional start epsilon rule.

The final rules should be `A -> B C`, `A -> a`, or an allowed start epsilon rule.

## Inputs and checks

Three actual outputs from Steven's steps are in [examples/for_devin/](examples/for_devin/):

| Input | What needs work |
| --- | --- |
| `01_nullable_blocks.cfg` | Mixed terminal/variable right sides after nullable removal |
| `02_start_on_rhs.cfg` | Prepared start with epsilon and length-three right sides |
| `03_multichar_unit.cfg` | Whole terminal `id`, operator `+`, and longer rules |

Refresh those files with `python3.14 tools/prepare_devin.py`.
You can also use **Save result** in the GUI or CLI `--save-result for_devin.cfg`.

Run from the project folder:

```powershell
python3.14 -m unittest discover -s tests -v
python3.14 tools/check_role2.py
python3.14 tools/check_role3.py --list-cases
python3.14 tools/check_role3.py
```

The role 3 runner checks seven grammars: useless symbols, long rules, mixed
terminals, name collisions, epsilon under a fresh start, empty language, and
epsilon-only language. Each gets four checks: the three functions separately
and then the full pipeline. **28 checks total.**

Your module is still pending in this handoff. Status `2` means it could not be
loaded, `1` means a check failed, and `0` means these cases passed. Normal tests
check the handoff fixtures with known answers; they do not claim your code passed.

If your names differ, the runner accepts a module name and `--useless`,
`--terminals`, and `--binary` overrides.

## Connect it once checks pass

In `cfg_toolkit/pipeline.py`, import your three functions and add them to
`team_transforms()` under these exact keys:

```python
"remove_useless": remove_useless,
"replace_terminals": replace_terminals,
"binarize": binarize,
```

The CLI and GUI use that mapping. Matt will finish the display/status wording,
final integration tests, demo, and report with testing help from you and Steven.
Right now their wording intentionally says your steps are pending.

The pipeline checks the final CNF structure and epsilon membership. The tests
also compare words through four terminal tokens. These checks find bugs; they
do not prove equivalence for every word. Keep your own focused tests too.
