"""Run the team's conversion steps in order and keep a grammar after each step.

Matt Lawrence integrates Steven Yang's and Devin Finn's functions through STAGES.
Matt leads validation and testing, with testing help from Steven and Devin.
Each function takes a Grammar and returns a new Grammar. Until those functions
are ready, the pipeline stops at the first missing step and lists what is left.
"""

from dataclasses import dataclass
from typing import Callable, Mapping, Optional, Tuple

from .cnf_validator import CnfReport, validate_cnf
from .model import Grammar
from .start_symbol import prepare_start
from .simplify_grammar import eliminate_ε_prods, eliminate_unit_prods


Transform = Callable[[Grammar], Grammar]
# These names are the keys teammates use when registering their functions.
STAGES = (
    ("remove_epsilon", "Steven Yang: remove epsilon productions"),
    ("remove_units", "Steven Yang: remove unit productions"),
    ("remove_useless", "Devin Finn: remove useless symbols"),
    ("replace_terminals", "Devin Finn: replace terminals in long RHSs"),
    ("binarize", "Devin Finn: split long RHSs into binary rules"),
)


def team_transforms():
    """The real functions connected so far. Add Devin's three functions here."""
    return {
        "remove_epsilon": eliminate_ε_prods,
        "remove_units": eliminate_unit_prods,
    }


@dataclass(frozen=True)
class Snapshot:
    """One saved step, ready for the CLI or a future interface to display."""

    stage: str
    title: str
    grammar: Grammar
    explanation: str = ""


@dataclass(frozen=True)
class PipelineResult:
    """All finished steps, the steps still needed, and the final CNF check."""

    snapshots: Tuple[Snapshot, ...]
    pending: Tuple[str, ...]
    cnf_report: Optional[CnfReport]

    @property
    def is_complete(self) -> bool:
        """Complete means every step ran and the resulting grammar passed CNF checks."""
        return (
            not self.pending
            and self.cnf_report is not None
            and self.cnf_report.is_valid
        )


def run_pipeline(
    grammar: Grammar, transforms: Optional[Mapping[str, Transform]] = None
) -> PipelineResult:
    """Run registered functions in assignment order.

    With no mapping, run the available team functions. An explicit mapping
    selects exactly those stages; {} runs only input and start preparation.
    Keep the prepared start name and do not add terminals.
    """
    transforms = team_transforms() if transforms is None else dict(transforms)
    unknown_stages = set(transforms) - {stage for stage, _ in STAGES}
    if unknown_stages:
        raise ValueError(
            "unknown integration stages: {}".format(", ".join(sorted(unknown_stages)))
        )
    for stage, function in transforms.items():
        if not callable(function):
            raise TypeError("stage {} must be callable".format(stage))
    prepared = prepare_start(grammar)
    snapshots = [
        Snapshot("original", "1. Original grammar", grammar),
        Snapshot(
            "prepare_start",
            "2. New-start handling",
            prepared.grammar,
            prepared.explanation,
        ),
    ]
    current = prepared.grammar
    for index, (stage, title) in enumerate(STAGES):
        if stage not in transforms:
            pending = tuple(name for name, _ in STAGES[index:])
            return PipelineResult(tuple(snapshots), pending, None)

        next_grammar = transforms[stage](current)
        if not isinstance(next_grammar, Grammar):
            raise TypeError("stage {} must return a validated Grammar".format(stage))
        if next_grammar.start != current.start:
            raise ValueError(
                "stage {} must preserve the prepared start variable".format(stage)
            )
        if not next_grammar.terminals <= grammar.terminals:
            raise ValueError(
                "stage {} introduced an undeclared source terminal".format(stage)
            )
        current = next_grammar
        snapshots.append(Snapshot(stage, "{}. {}".format(index + 3, title), current))
    # Even if all functions ran, the result still has to pass the CNF validator.
    report = validate_cnf(current, source=grammar)
    snapshots.append(
        Snapshot("final", "8. Final grammar (validate before accepting)", current)
    )
    return PipelineResult(tuple(snapshots), (), report)
