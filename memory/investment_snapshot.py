import json
import os
import re
import time
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
INVESTMENT_SNAPSHOT_PATH = MEMORY_DIR / "investment_snapshot.json"

VALUE_RE = re.compile(
    r"[-+]?\d+(?:,\d+)?\s*%|(?:r\$\s*)?[-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})",
    re.IGNORECASE,
)

LABEL_HINTS = {
    "patrimonio": ("patrimonio total", "patrimonio", "patrimônio total", "patrimônio"),
    "valor investido": ("valor investido",),
    "valor atual": ("valor atual",),
    "rentabilidade": ("rentabilidade",),
    "proventos": ("proventos", "dividendos"),
    "saldo": ("saldo",),
    "lucro": ("lucro",),
    "prejuizo": ("prejuizo", "prejuízo"),
    "aporte": ("aporte",),
    "preco medio": ("preco medio", "preço médio", "preço medio"),
    "cotacao": ("cotacao", "cotação"),
}


def _save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or "").strip().lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = re.sub(r"[^\w\s%$.,:-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _format_timestamp(timestamp: float) -> str:
    if not timestamp:
        return "data desconhecida"
    return time.strftime("%d/%m/%Y às %H:%M", time.localtime(timestamp))


def _extract_metric_map(metrics: list[str] | None, lines: list[str] | None) -> dict[str, str]:
    metric_map: dict[str, str] = {}
    candidates = list(metrics or []) + list(lines or [])

    for raw_line in candidates:
        line = re.sub(r"\s+", " ", str(raw_line or "")).strip()
        if not line:
            continue
        normalized = _normalize(line)
        values = VALUE_RE.findall(line)
        if not values:
            continue

        for canonical, hints in LABEL_HINTS.items():
            if canonical in metric_map:
                continue
            if any(hint in normalized for hint in hints):
                metric_map[canonical] = values[0].strip()
                break

    return metric_map


def save_investment_snapshot(
    summary: str,
    metrics: list[str] | None = None,
    lines: list[str] | None = None,
    page_url: str = "",
    page_title: str = "",
):
    payload = {
        "updated_at": time.time(),
        "summary": re.sub(r"\s+", " ", str(summary or "")).strip(),
        "metrics": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(metrics or []) if str(item or "").strip()],
        "lines": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(lines or [])[:30] if str(item or "").strip()],
        "page_url": str(page_url or "").strip(),
        "page_title": str(page_title or "").strip(),
    }
    payload["metric_map"] = _extract_metric_map(payload.get("metrics"), payload.get("lines"))
    _save_json(INVESTMENT_SNAPSHOT_PATH, payload)
    return payload


def load_investment_snapshot() -> dict:
    data = _load_json(INVESTMENT_SNAPSHOT_PATH)
    return data if isinstance(data, dict) else {}


def format_investment_snapshot_summary() -> str:
    snapshot = load_investment_snapshot()
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary", "")).strip()
    metric_map = snapshot.get("metric_map") or {}

    if not updated_at and not summary:
        return (
            "Ainda não tenho uma carteira salva localmente. "
            "Abra o Investidor10 uma vez e peça para atualizar os investimentos."
        )

    key_order = (
        "patrimonio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
    )
    highlights = [f"{label}: {metric_map[label]}" for label in key_order if metric_map.get(label)]
    if highlights:
        return (
            f"Carteira salva em {_format_timestamp(updated_at)}. "
            + "; ".join(highlights)
            + ". Dados locais, podem estar desatualizados."
        )

    if summary:
        return (
            f"Carteira salva em {_format_timestamp(updated_at)}. "
            + summary
            + " Dados locais, podem estar desatualizados."
        )

    return f"Tenho um snapshot salvo em {_format_timestamp(updated_at)}, mas ainda com poucos dados úteis extraídos."


def answer_investment_snapshot_question(question: str) -> str:
    snapshot = load_investment_snapshot()
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary", "")).strip()
    metric_map = snapshot.get("metric_map") or {}
    normalized = _normalize(question)

    if not updated_at and not summary:
        return (
            "Ainda não tenho dados locais da sua carteira. "
            "Peça para abrir ou atualizar o Investidor10 primeiro."
        )

    if any(token in normalized for token in ("quando", "atualizado", "atualizacao", "atualização", "salvo", "snapshot")):
        return f"A última atualização local da carteira foi em {_format_timestamp(updated_at)}."

    question_map = {
        "patrimonio": ("patrimonio", "patrimônio"),
        "valor investido": ("valor investido", "quanto investi", "tenho investido"),
        "valor atual": ("valor atual", "quanto vale", "valor da carteira"),
        "rentabilidade": ("rentabilidade", "rendeu", "retorno"),
        "proventos": ("proventos", "dividendos"),
        "saldo": ("saldo",),
        "lucro": ("lucro",),
        "prejuizo": ("prejuizo", "prejuízo"),
        "aporte": ("aporte", "aportes"),
        "preco medio": ("preco medio", "preço médio", "preço medio"),
        "cotacao": ("cotacao", "cotação"),
    }

    for canonical, hints in question_map.items():
        if any(hint in normalized for hint in hints):
            value = metric_map.get(canonical)
            if value:
                return (
                    f"Pelo último snapshot salvo, {canonical} está em {value}. "
                    f"Atualizado em {_format_timestamp(updated_at)}."
                )
            if canonical == "patrimonio" and metric_map.get("valor atual"):
                return (
                    "Não encontrei patrimônio explícito no último snapshot, "
                    f"mas o valor atual salvo está em {metric_map['valor atual']}. "
                    f"Atualizado em {_format_timestamp(updated_at)}."
                )
            break

    if summary:
        return (
            f"Pelo último snapshot salvo em {_format_timestamp(updated_at)}, "
            + summary
            + " Se quiser algo mais atual, peça para atualizar a carteira."
        )

    return (
        f"Tenho um snapshot salvo em {_format_timestamp(updated_at)}, "
        "mas não encontrei essa informação de forma confiável nele."
    )
