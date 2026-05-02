from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests

from config import (
    OBSIDIAN_SYNC_ENABLED,
    OBSIDIAN_VAULT_PATH,
    SUPABASE_MEMORY_TABLE,
    SUPABASE_REST_URL,
)
from memory.current_topic import save_current_topic
from memory.obsidian_sync import obsidian_sync_ready
from memory.supabase_sync import fetch_memory_state, supabase_sync_ready, upsert_memory_state


def check_obsidian() -> dict:
    if not OBSIDIAN_SYNC_ENABLED:
        return {
            "ok": False,
            "kind": "obsidian_disabled",
            "message": "Espelhamento do Obsidian está desativado no .env.",
        }

    if not obsidian_sync_ready():
        return {
            "ok": False,
            "kind": "obsidian_unavailable",
            "message": "Vault do Obsidian não está disponível.",
        }

    payload = {
        "topic": "Teste de integração",
        "summary": "Verificação local do espelho Obsidian.",
        "source": "diagnostic",
        "lines": ["primeira linha", "segunda linha"],
        "checked_at": time.time(),
    }
    saved = save_current_topic(payload)
    vault_label = OBSIDIAN_VAULT_PATH or str(ROOT / "memory" / "obsidian_vault")
    return {
        "ok": True,
        "kind": "obsidian_ok",
        "message": f"Obsidian ok. Vault em {vault_label}.",
        "topic": saved.get("topic", ""),
    }


def check_supabase() -> dict:
    if not supabase_sync_ready():
        return {
            "ok": False,
            "kind": "supabase_not_configured",
            "message": "Supabase não está configurado completamente no .env.",
        }

    key = "healthcheck"
    payload = {
        "status": "ok",
        "source": "check_memory_integrations.py",
        "checked_at": time.time(),
    }

    try:
        upsert_memory_state(key=key, payload=payload, category="healthcheck")
        row = fetch_memory_state(key=key)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 0
        body = ""
        try:
            body = exc.response.text if exc.response is not None else ""
        except Exception:
            body = ""
        if status == 404:
            return {
                "ok": False,
                "kind": "supabase_table_missing",
                "message": (
                    f"Supabase respondeu 404 para a tabela '{SUPABASE_MEMORY_TABLE}'. "
                    "Crie a tabela com o SQL em docs/supabase-schema.sql."
                ),
                "url": SUPABASE_REST_URL,
            }
        if status in {401, 403}:
            return {
                "ok": False,
                "kind": "supabase_auth_error",
                "message": f"Supabase rejeitou a autenticação com status {status}.",
                "details": body[:300],
            }
        return {
            "ok": False,
            "kind": "supabase_http_error",
            "message": f"Supabase retornou erro HTTP {status}.",
            "details": body[:300],
        }
    except requests.RequestException as exc:
        return {
            "ok": False,
            "kind": "supabase_network_error",
            "message": f"Falha de rede ao falar com o Supabase: {exc}",
        }
    except Exception as exc:
        return {
            "ok": False,
            "kind": "supabase_unknown_error",
            "message": f"Erro inesperado ao testar Supabase: {exc}",
        }

    return {
        "ok": True,
        "kind": "supabase_ok",
        "message": f"Supabase ok. Escrita e leitura em '{SUPABASE_MEMORY_TABLE}' funcionando.",
        "row": row,
    }


def main():
    result = {
        "supabase": check_supabase(),
        "obsidian": check_obsidian(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
