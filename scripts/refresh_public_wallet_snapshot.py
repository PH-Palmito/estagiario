import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from memory.public_wallet_refresh import refresh_public_wallet_snapshot


def main():
    snapshot = refresh_public_wallet_snapshot(force=True)
    payload = {
        "ok": True,
        "summary": snapshot.get("summary", ""),
        "updated_at": snapshot.get("updated_at"),
        "source": snapshot.get("source", ""),
        "wallet_name": snapshot.get("wallet_name", ""),
    }
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
