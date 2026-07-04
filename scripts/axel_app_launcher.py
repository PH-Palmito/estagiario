from __future__ import annotations

import contextlib
import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
LOG = ROOT / ".tmp" / "axel-app.log"


def main() -> None:
    ROOT.joinpath(".tmp").mkdir(exist_ok=True)
    sys.argv = [
        str(MAIN),
        "--voice",
        "--hotword",
        "--ui",
    ]
    with LOG.open("a", encoding="utf-8", buffering=1) as log:
        log.write("\n=== Axel app launcher ===\n")
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            runpy.run_path(str(MAIN), run_name="__main__")


if __name__ == "__main__":
    main()
