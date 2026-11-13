"""Load Steven Yang's module and check its real Grammar results.

Run from the project folder:
    python3.14 tools/check_role2.py src.simplify_grammar

No implementation is bundled here. A missing module returns 2; failed checks
return 1. Neither counts as a passing simplification run.
"""

import argparse
import importlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.role2_contract import EXAMPLES, make_suite


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", nargs="?", help="Module holding both functions")
    parser.add_argument("--epsilon", default="eliminate_ε_prods")
    parser.add_argument("--units", default="eliminate_unit_prods")
    parser.add_argument("--list-cases", action="store_true")
    options = parser.parse_args(arguments)
    if options.list_cases:
        for case in EXAMPLES:
            print(case.name)
        return 0
    if not options.module:
        parser.error("give a module name, such as src.simplify_grammar")
    try:
        module = importlib.import_module(options.module)
        functions = [getattr(module, name) for name in (options.epsilon, options.units)]
        if not all(callable(function) for function in functions):
            raise TypeError("Both transformation names must refer to functions.")
    except (ImportError, AttributeError, TypeError, SyntaxError) as error:
        print("Role 2 checks could not start: {}".format(error), file=sys.stderr)
        print("No simplification checks passed. See INTEGRATION.md.", file=sys.stderr)
        return 2
    print(
        "Checking {} with Python {}".format(options.module, sys.version.split()[0]),
        flush=True,
    )
    result = unittest.TextTestRunner(verbosity=2).run(make_suite(*functions))
    if result.wasSuccessful():
        print(
            "Role 2 cases passed. Devin's stages and full CNF conversion remain pending."
        )
        print(
            "Words were compared through four tokens; this is not a proof of equivalence."
        )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
