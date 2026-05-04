from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.obsidian_sync import load_vault_context
from memory.vault_bootstrap import bootstrap_obsidian_knowledge


def main():
    ok = bootstrap_obsidian_knowledge()
    context = load_vault_context()
    print(
        json.dumps(
            {
                "ok": bool(ok),
                "notes": sorted(list(context.keys())),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
