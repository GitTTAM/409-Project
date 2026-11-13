"""Choose a file format. Both readers return the same Grammar type."""

from pathlib import Path

from .grammar_io import loads_grammar, write_grammar
from .lecture import dumps_lecture, loads_lecture
from .model import Grammar, GrammarError


FORMATS = ("auto", "json", "lecture")
LECTURE_SUFFIXES = frozenset((".cfg", ".txt", ".grammar"))


def detect_format(text: str, path=None) -> str:
    """Trust a known file extension first; otherwise look at the first character."""
    suffix = Path(path).suffix.lower() if path is not None else ""
    if suffix == ".json":
        return "json"
    if suffix in LECTURE_SUFFIXES:
        return "lecture"
    if text.lstrip("\ufeff \r\n\t").startswith("{"):
        return "json"
    return "lecture"


def loads_document(text: str, input_format: str = "auto", path=None) -> Grammar:
    """Read text using the requested format, or detect it when set to auto."""
    if input_format not in FORMATS:
        raise GrammarError("input format must be auto, json, or lecture")
    if not isinstance(text, str):
        raise GrammarError("grammar document must be text")
    if input_format == "auto":
        input_format = detect_format(text, path)
    if input_format == "json":
        return loads_grammar(text.lstrip("\ufeff"))
    return loads_lecture(text)


def read_document(path, input_format: str = "auto") -> Grammar:
    """Read a grammar file and include its path if anything goes wrong."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
        return loads_document(text, input_format, path)
    except (OSError, UnicodeError, GrammarError) as error:
        raise GrammarError("{}: {}".format(path, error)) from None


def write_document(grammar: Grammar, path) -> None:
    """Save classroom notation for .cfg/.txt/.grammar files, JSON for other names."""
    if Path(path).suffix.lower() in LECTURE_SUFFIXES:
        Path(path).write_text(dumps_lecture(grammar), encoding="utf-8")
    else:
        write_grammar(grammar, path)
