import json
import os
import re
import time
from pathlib import Path
from typing import Callable


def save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_investment_snapshot_payload(
    path: Path,
    *,
    summary: str,
    metrics: list[str] | None = None,
    lines: list[str] | None = None,
    page_url: str = "",
    page_title: str = "",
    extra: dict | None = None,
    extract_metric_map: Callable[[list[str] | None, list[str] | None], dict[str, str]],
    sync_portfolio_snapshot_note: Callable[[dict], None],
) -> dict:
    payload = {
        "updated_at": time.time(),
        "summary": re.sub(r"\s+", " ", str(summary or "")).strip(),
        "metrics": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(metrics or []) if str(item or "").strip()],
        "lines": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(lines or [])[:30] if str(item or "").strip()],
        "page_url": str(page_url or "").strip(),
        "page_title": str(page_title or "").strip(),
    }
    if isinstance(extra, dict):
        payload.update(extra)
    if not isinstance(payload.get("metric_map"), dict):
        payload["metric_map"] = extract_metric_map(payload.get("metrics"), payload.get("lines"))

    current = load_json(path)
    if isinstance(current, dict):
        current_positions = current.get("asset_positions")
        new_positions = payload.get("asset_positions")
        if isinstance(current_positions, dict) and isinstance(new_positions, dict):
            current_count = len(current_positions)
            new_count = len(new_positions)
            unresolved = payload.get("unresolved_category_counts")
            looks_partial = bool(unresolved) or new_count < current_count
            if current_count > new_count and looks_partial:
                merged_positions = dict(current_positions)
                merged_positions.update(new_positions)
                payload["asset_positions"] = merged_positions

                for key in ("asset_fundamentals", "asset_dividend_events"):
                    old_map = current.get(key)
                    new_map = payload.get(key)
                    if isinstance(old_map, dict) and isinstance(new_map, dict):
                        merged_map = dict(old_map)
                        merged_map.update(new_map)
                        payload[key] = merged_map

                payload["partial_capture_merged"] = True
                payload["partial_capture_note"] = (
                    f"Atualização parcial preservou {current_count} posições anteriores "
                    f"e atualizou {new_count} posições capturadas agora."
                )
    save_json(path, payload)
    sync_portfolio_snapshot_note(payload)
    return payload


def load_investment_snapshot_payload(path: Path) -> dict:
    data = load_json(path)
    return data if isinstance(data, dict) else {}
