from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class SetupItem:
    name: str
    status: str
    detail: str
    required: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "required": self.required,
        }


def _env(env: Mapping[str, str], *names: str) -> str:
    for name in names:
        value = str(env.get(name, "")).strip()
        if value:
            return value
    return ""


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _item(name: str, ok: bool, ok_detail: str, missing_detail: str, *, required: bool = True) -> SetupItem:
    if ok:
        return SetupItem(name=name, status="ok", detail=ok_detail, required=required)
    return SetupItem(name=name, status="acao", detail=missing_detail, required=required)


def build_setup_snapshot(
    root: Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    module_available=_module_available,
    python_version: tuple[int, int, int] | None = None,
) -> dict:
    project_dir = root or Path(__file__).resolve().parents[1]
    environment = env or os.environ
    version = python_version or sys.version_info[:3]

    required: list[SetupItem] = [
        _item(
            "Python",
            version >= (3, 11, 0),
            f"{version[0]}.{version[1]}.{version[2]} pronto",
            "use Python 3.11 ou superior",
        ),
        _item(
            "Arquivo .env",
            (project_dir / ".env").exists(),
            ".env encontrado",
            "copie .env.example para .env e ajuste suas chaves",
        ),
        _item(
            "Ollama",
            bool(_env(environment, "AXEL_OLLAMA_BASE_URL", "OLLAMA_BASE_URL")) or True,
            "URL padrao/configurada para Ollama",
            "configure AXEL_OLLAMA_BASE_URL",
        ),
        _item(
            "Modelo local de texto",
            bool(_env(environment, "AXEL_OLLAMA_TEXT_MODEL", "OLLAMA_TEXT_MODEL")) or True,
            "modelo local padrao/configurado",
            "configure AXEL_OLLAMA_TEXT_MODEL",
        ),
        _item(
            "Dependencias de voz",
            module_available("sounddevice") and module_available("faster_whisper"),
            "sounddevice e faster_whisper importaveis",
            "instale dependencias de voz do requirements.txt",
        ),
        _item(
            "HUD",
            module_available("PySide6"),
            "PySide6 importavel",
            "instale PySide6 para usar --ui",
        ),
        _item(
            "Navegador",
            module_available("playwright"),
            "Playwright importavel",
            "instale Playwright para automacao de navegador",
        ),
        _item(
            "OCR",
            module_available("rapidocr_onnxruntime") and module_available("PIL"),
            "RapidOCR e Pillow importaveis",
            "instale rapidocr_onnxruntime e Pillow",
        ),
    ]

    optional: list[SetupItem] = [
        _item(
            "Gemini",
            bool(_env(environment, "AXEL_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")),
            "chave configurada",
            "opcional: configure AXEL_GEMINI_API_KEY para raciocinio remoto",
            required=False,
        ),
        _item(
            "NVIDIA NIM",
            bool(_env(environment, "AXEL_NVIDIA_API_KEY", "NVIDIA_API_KEY", "NVIDIA_API_TOKEN")),
            "chave configurada",
            "opcional: configure AXEL_NVIDIA_API_KEY como fallback remoto",
            required=False,
        ),
        _item(
            "Telegram",
            bool(_env(environment, "AXEL_TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"))
            and bool(_env(environment, "AXEL_TELEGRAM_ALLOWED_CHAT_IDS", "TELEGRAM_ALLOWED_CHAT_IDS")),
            "token e allowlist configurados",
            "opcional: configure token e AXEL_TELEGRAM_ALLOWED_CHAT_IDS",
            required=False,
        ),
        _item(
            "Spotify",
            bool(_env(environment, "AXEL_SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_ID")),
            "client id configurado",
            "opcional: configure credenciais do Spotify",
            required=False,
        ),
        _item(
            "BRAPI",
            bool(_env(environment, "AXEL_BRAPI_TOKEN", "BRAPI_TOKEN")),
            "token configurado",
            "opcional: configure AXEL_BRAPI_TOKEN para dados de mercado",
            required=False,
        ),
        _item(
            "Supabase",
            bool(_env(environment, "AXEL_SUPABASE_REST_URL", "SUPABASE_REST_URL", "NEXT_PUBLIC_SUPABASE_URL")),
            "URL configurada",
            "opcional: configure Supabase para sincronizacao de memoria",
            required=False,
        ),
        _item(
            "Obsidian",
            bool(_env(environment, "AXEL_OBSIDIAN_VAULT_PATH", "OBSIDIAN_VAULT_PATH")),
            "vault configurado",
            "opcional: configure AXEL_OBSIDIAN_VAULT_PATH",
            required=False,
        ),
    ]

    blockers = [item for item in required if item.status != "ok"]
    return {
        "status": "pronto" if not blockers else "precisa de configuracao",
        "root": str(project_dir),
        "required": [item.to_dict() for item in required],
        "optional": [item.to_dict() for item in optional],
        "blockers": [item.to_dict() for item in blockers],
    }


def format_setup_report(snapshot: dict | None = None) -> str:
    data = snapshot or build_setup_snapshot()
    parts = [f"Setup do Axel: {data.get('status', 'indefinido')}."]
    blockers = data.get("blockers") or []
    if blockers:
        parts.append(f"Pendencias obrigatorias: {len(blockers)}.")
    else:
        parts.append("Base obrigatoria pronta.")

    required = data.get("required") or []
    optional = data.get("optional") or []
    if required:
        rows = [f"{item.get('name')}: {item.get('status')} ({item.get('detail')})" for item in required]
        parts.append("Obrigatorios: " + " ; ".join(rows) + ".")
    if optional:
        configured = [str(item.get("name")) for item in optional if item.get("status") == "ok"]
        missing = [str(item.get("name")) for item in optional if item.get("status") != "ok"]
        parts.append("Opcionais prontos: " + (", ".join(configured) if configured else "nenhum") + ".")
        parts.append("Opcionais pendentes: " + (", ".join(missing) if missing else "nenhum") + ".")
    if blockers:
        first = blockers[0]
        parts.append(f"Proximo passo: {first.get('name')}: {first.get('detail')}.")
    else:
        parts.append("Proximo passo: rode --doctor ou inicie com --voice --hotword --ui.")
    return " ".join(parts)
