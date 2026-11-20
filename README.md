# 409 CFG

Enter a grammar, prepare its start, and remove epsilon and unit rules.

## Team

| Member | Assigned work | Testing |
| --- | --- | --- |
| Matt Lawrence | Roles 1 and 4: grammar input, start preparation, integration, validation, docs, and demo | Leads testing |
| Steven Yang | Role 2: remove epsilon and unit productions | Helps with test cases and verification |
| Devin Finn | Role 3: remove useless symbols, replace terminals, and split long rules | Helps with test cases and verification |

## Run

Double-click **start_gui.bat**, or run:

```powershell
cd "C:\Users\mlawrence\Python Projects\Personal\409 CFG"
python3.14 gui.py
```

Use Python 3.14 with Tkinter. No extra packages needed.

## Use

1. Type or paste grammar rules, or choose an example and click **Load example**.
2. Click **Run** to check input, prepare the start, and run Steven's steps.
3. Click **Save result** to save the grammar ready for Devin as a `.cfg` file.

**Save input** saves your editor text. **Clear** empties the editor and results.
Editing the input clears old results, so saved output always matches the current grammar.

![Grammar workspace](sample_runs/gui_workspace.png)

## Grammar notation

```text
V = {S}
Sigma = {a, b}
Start = S
S -> aSb | epsilon
```

- `V` lists variables; `Sigma` lists terminals; `Start` names the start.
- `|` separates alternatives. `epsilon` means the empty word.
- Use spaces when names could be confused: `A B` is two symbols; `AB` can be one declared name.

For a quick grammar, just enter `S -> aSb | epsilon`.

Green marks new or changed rules. Blue marks changed declarations. If input is invalid,
the message explains what to fix and highlights the line when available.

## Learn the code

**Help > Walkthrough** follows the current grammar through the real functions.
**Help > Practice** has five short lessons, source/test viewers, and exercises.
Close Help to return to your input and results.

See [Matt Lawrence's walkthrough](STUDENT1_WALKTHROUGH.md) for the practice guide.
Teammates adding conversion code can use [INTEGRATION.md](INTEGRATION.md).
Devin can start with [DEVIN_HANDOFF.md](DEVIN_HANDOFF.md).

## Current progress

Matt's input and start setup and Steven's simplification run together in the
CLI and GUI. Each CLI run shows the grammar after every finished step.
Devin's three CNF steps are still pending. The current result is his input,
not a finished CNF conversion.

## Tests and saved runs

```powershell
python3.14 -m unittest discover -s tests -v
```

Desktop tests need Tkinter and a display. They skip when either is unavailable.

Examples are in `examples/`; saved output and screenshots are in [sample_runs/](sample_runs/).

Run Steven's complete checks (nine grammars, three checks each):

```powershell
python3.14 tools/check_role2.py
```

List Devin's cases, then run his checks once his module is ready:

```powershell
python3.14 tools/check_role3.py --list-cases
python3.14 tools/check_role3.py
```

Missing code returns status 2 and counts as pending. A failed check returns 1.
The normal suite also checks Steven's real functions against 250 generated
grammars and checks that unfinished or broken functions cannot pass the handoff tests.

To refresh runs and rebuild the ZIP:

```powershell
python3.14 tools/generate_evidence.py
python3.14 tools/package_handoff.py
```

For the command-line version:

```powershell
python3.14 main.py examples/lecture/03_matching.cfg
python3.14 main.py examples/02_start_on_rhs.json --save-result for_devin.cfg
```

The older `--save-prepared` option still saves only the start-setup step.
Three ready-made inputs for Devin are in [examples/for_devin/](examples/for_devin/).

