#!/usr/bin/env python3
"""Tabula Rerum entry point.

  python3 run.py                 # offline, from recorded fixtures, no key, no network
  python3 run.py --live          # live keyless CMC
  python3 run.py --port 9000
  python3 run.py --days 90
  python3 run.py --test          # run the test suite and exit
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

USAGE = __doc__


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if "--test" in argv:
        return subprocess.call(
            [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"])
    from tabula.server import main as serve
    return serve([a for a in argv if a not in ("--test",)])


if __name__ == "__main__":
    print(USAGE, file=sys.stderr)
    raise SystemExit(main())
