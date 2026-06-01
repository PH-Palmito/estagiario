from __future__ import annotations

import re
from pathlib import Path

MEMORY_DIR = Path("memory")
CORE_MEMORY_PATH = MEMORY_DIR / "core_memory.md"
USER_PROFILE_PATH = MEMORY_DIR / "user_profile.md"
MAX_SECTION_CHARS = 1200

DEFAULT_CORE_MEMORY = """# Memoria Curta do Axel

## Identidade operacional
- Axel e um assistente local-first para Windows, focado em voz, automacao, navegador, memoria, carteira e apoio diario.
- O modo de voz deve ser rapido, direto e seguro; tarefas longas devem ir para fluxos em segundo plano ou para Codex.

## Prioridades arquiteturais
- Manter comandos diretos locais sempre que possivel.
- Usar Gemini como primeira opcao remota, NVIDIA NIM como segunda opcao remota e Ollama como retaguarda local.
- Evoluir ideias do Hermes Agent com memoria curta curada, busca de sessoes, skills, toolsets e AxelBrain.

## Regras de contexto
- Esta memoria deve ficar curta, estavel e confiavel.
- Preferir fatos duradouros a eventos passageiros.
"""

DEFAULT_USER_PROFILE = """# Perfil Curto do Operador

## Preferencias de resposta
- Responder em portugues do Brasil.
- Ser direto, natural e util, especialmente no modo voz.

## Preferencias operacionais
- Priorizar evolucao pratica do Axel sem quebrar o uso diario.
- Tratar chaves e dados pessoais como segredos.

## Projetos ativos
- Axel: assistente local com automacao de desktop, voz, memoria, navegador, investimentos e UI.
"""


def ensure_curated_memory_files() -> None:
    MEMORY_DIR.mkdir(exist_ok=True)
    if not CORE_MEMORY_PATH.exists():
        CORE_MEMORY_PATH.write_text(DEFAULT_CORE_MEMORY.rstrip() + "\n", encoding="utf-8")
    if not USER_PROFILE_PATH.exists():
        USER_PROFILE_PATH.write_text(DEFAULT_USER_PROFILE.rstrip() + "\n", encoding="utf-8")


def _clean_markdown(text: str, max_chars: int = MAX_SECTION_CHARS) -> str:
    lines = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        line = re.sub(r"\s+", " ", line)
        if line:
            lines.append(line)

    compact = " ".join(lines).strip()
    if len(compact) > max_chars:
        compact = compact[: max_chars - 3].rstrip() + "..."
    return compact


def load_curated_memory() -> dict:
    ensure_curated_memory_files()
    try:
        core = CORE_MEMORY_PATH.read_text(encoding="utf-8")
    except Exception:
        core = ""
    try:
        user = USER_PROFILE_PATH.read_text(encoding="utf-8")
    except Exception:
        user = ""
    return {
        "core": _clean_markdown(core),
        "user": _clean_markdown(user),
    }


def format_curated_memory() -> str:
    memory = load_curated_memory()
    core = str(memory.get("core", "")).strip() or "Indisponivel."
    user = str(memory.get("user", "")).strip() or "Indisponivel."
    return f"Memoria curta do Axel: {core}\nPerfil curto do operador: {user}"
