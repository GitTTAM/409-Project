"""Run Devin Finn's functions once his module is available. Exit 2 means pending."""

import argparse
import importlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.role3_contract import EXAMPLES, make_suite


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", nargs="?", default="cfg_toolkit.cnf_transforms")
    parser.add_argument("--useless", default="remove_useless")
    parser.add_argument("--terminals", default="replace_terminals")
    parser.add_argument("--binary", default="binarize")
    parser.add_argument("--list-cases", action="store_true")
    options = parser.parse_args(arguments)
    if options.list_cases:
        for case in EXAMPLES:
            print(case.name)
        return 0
    try:
        module = importlib.import_module(options.module)
        functions = [
            getattr(module, name)
            for name in (options.useless, options.terminals, options.binary)
        ]
        if not all(callable(function) for function in functions):
            raise TypeError("All three names must refer to functions.")
    except (ImportError, AttributeError, TypeError, SyntaxError) as error:
        print("Role 3 checks could not start: {}".format(error), file=sys.stderr)
        print("No role 3 checks passed. See DEVIN_HANDOFF.md.", file=sys.stderr)
        return 2
    result = unittest.TextTestRunner(verbosity=2).run(make_suite(*functions))
    if result.wasSuccessful():
        print("Role 3 stage and pipeline checks passed for these fixtures.")
        print(
            "Words were checked through four tokens; this is not a full equivalence proof."
        )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
