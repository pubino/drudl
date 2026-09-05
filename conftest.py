"""Make the extensionless `drudl` CLI importable as a module for tests.

The tool is invoked as `python drudl <url>`, so the script carries no .py
extension and a plain `from drudl import ...` cannot find it. Loading it here
by path registers it in sys.modules before the tests import it.
"""

import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

_SCRIPT = Path(__file__).parent / "drudl"

if "drudl" not in sys.modules:
    _spec = spec_from_loader("drudl", SourceFileLoader("drudl", str(_SCRIPT)))
    _module = module_from_spec(_spec)
    _spec.loader.exec_module(_module)
    sys.modules["drudl"] = _module
