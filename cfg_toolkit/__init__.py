"""Shared imports for the team: Grammar, Production, readers, and start setup.

Teammates can use ``from cfg_toolkit import Grammar, Production`` without
needing to know which module holds each type.
"""

from .grammar_io import (
    dumps_grammar,
    format_grammar,
    from_dict,
    loads_grammar,
    read_grammar,
    to_dict,
    write_grammar,
)
from .model import Grammar, GrammarError, Production
from .start_symbol import StartPreparation, prepare_start
from .lecture import dumps_lecture, format_lecture, loads_lecture
from .document_io import loads_document, read_document, write_document
from .cnf_validator import derives_epsilon, nullable_variables

__all__ = [
    "Grammar",
    "GrammarError",
    "Production",
    "StartPreparation",
    "prepare_start",
    "dumps_grammar",
    "format_grammar",
    "from_dict",
    "loads_grammar",
    "read_grammar",
    "to_dict",
    "write_grammar",
    "dumps_lecture",
    "format_lecture",
    "loads_lecture",
    "loads_document",
    "read_document",
    "write_document",
    "derives_epsilon",
    "nullable_variables",
]
