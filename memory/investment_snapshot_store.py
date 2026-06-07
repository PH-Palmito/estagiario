import json
import os
import re
import time
from collections.abc import Callable
from pathlib import Path

INVESTMENT_HISTORY_LIMIT = 260


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


def _parse_currency_value(text: str) -> float | None:
    cleaned = str(text or "").strip().lower().replace("r$", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_percent_value(text: str) -> float | None:
    cleaned = str(text or "").strip().replace("%", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _crypto_balance_value(payload: dict) -> float | None:
    positions = payload.get("asset_positions")
    if not isinstance(positions, dict):
        return None
    total = 0.0
    found = False
    for position in positions.values():
        if not isinstance(position, dict):
            continue
        category = str(position.get("category") or "").strip().lower()
        if not category.startswith("cript"):
            continue
        value = _parse_currency_value(position.get("balance"))
        if value is None:
            continue
        total += value
        found = True
    return total if found else None


def _history_sample(payload: dict) -> dict | None:
    metric_map = payload.get("metric_map")
    if not isinstance(metric_map, dict):
        return None
    updated_at = float(payload.get("updated_at") or time.time())
    patrimonio = _parse_currency_value(metric_map.get("patrimonio"))
    rentabilidade = _parse_percent_value(metric_map.get("rentabilidade"))
    variacao = _parse_percent_value(metric_map.get("variacao"))
    crypto_balance = _crypto_balance_value(payload)
    if patrimonio is None and rentabilidade is None and crypto_balance is None:
        return None
    sample = {
        "date": time.strftime("%Y-%m-%d", time.localtime(updated_at)),
        "updated_at": updated_at,
    }
    if patrimonio is not None:
        sample["patrimonio_value"] = patrimonio
        sample["patrimonio"] = metric_map.get("patrimonio")
    if rentabilidade is not None:
        sample["rentabilidade_percent"] = rentabilidade
    if variacao is not None:
        sample["variacao_percent"] = variacao
    if crypto_balance is not None:
        sample["crypto_balance_value"] = crypto_balance
    return sample


def append_investment_snapshot_history(path: Path, payload: dict) -> None:
    sample = _history_sample(payload)
    if not sample:
        return
    history_path = path.with_name("investment_snapshot_history.json")
    current = load_json(history_path)
    items = current.get("items") if isinstance(current, dict) else None
    history = [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    sample_date = str(sample.get("date") or "")
    history = [item for item in history if str(item.get("date") or "") != sample_date]
    history.append(sample)
    history.sort(key=lambda item: (str(item.get("date") or ""), float(item.get("updated_at") or 0)))
    history = history[-INVESTMENT_HISTORY_LIMIT:]
    save_json(history_path, {"items": history})


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
    append_investment_snapshot_history(path, payload)
    sync_portfolio_snapshot_note(payload)
    return payload


def load_investment_snapshot_payload(path: Path) -> dict:
    data = load_json(path)
    return data if isinstance(data, dict) else {}
