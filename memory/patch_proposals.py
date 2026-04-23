import json
import os
import time
from pathlib import Path

from memory.bottlenecks import load_bottlenecks


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
PATCH_PROPOSALS_PATH = MEMORY_DIR / "patch_proposals.json"


PATCH_LIBRARY = {
    "voice_understanding": {
        "title": "Fortalecer entendimento de voz e correcoes de fala",
        "why": "O Axel esta falhando em comandos por transcricao imperfeita e precisa ficar mais tolerante a fala real.",
        "files": [
            "main.py",
            "core/voice_command_classifier.py",
            "memory/voice_corrections.py",
            "voice/windows_voice.py",
        ],
        "changes": [
            "Adicionar aliases e rotas protegidas para comandos sensiveis.",
            "Aprender correcoes com base em frases mal reconhecidas recorrentes.",
            "Refinar o segundo passe de transcricao curta em portugues.",
        ],
        "risk": "Baixo a medio, porque pode ampliar demais a interpretacao se os gatilhos ficarem soltos.",
    },
    "execution_error": {
        "title": "Reduzir falhas na execucao de acoes",
        "why": "As intencoes chegam ao executor, mas algumas acoes ainda quebram ou param no meio.",
        "files": [
            "core/executor.py",
            "tools/system_tools.py",
            "tools/browser_tools.py",
        ],
        "changes": [
            "Melhorar tratamento de excecao e mensagens de erro contextualizadas.",
            "Adicionar novas tentativas e verificacoes de resultado apos a execucao.",
            "Salvar sinais de falha no detector de gargalos para futura correcao.",
        ],
        "risk": "Medio, porque retries mal calibrados podem repetir acoes indesejadas.",
    },
    "screen_reading": {
        "title": "Melhorar leitura de tela com foco no conteudo util",
        "why": "A leitura de paginas ainda perde partes relevantes e as vezes traz ruido ou contexto incompleto.",
        "files": [
            "tools/browser_tools.py",
            "ui/assistant_hud.py",
            "main.py",
        ],
        "changes": [
            "Priorizar conteudo principal, blocos centrais e sinais de dominio/contexto.",
            "Refinar filtros de ruido para menus, rodape, copyright e links crus.",
            "Adicionar fallback progressivo antes de declarar falha de leitura.",
        ],
        "risk": "Baixo, porque a mudanca e incremental e facil de validar no uso.",
    },
    "app_control": {
        "title": "Aumentar robustez no controle de aplicativos e janelas",
        "why": "Abrir, fechar e focar apps ainda tem pontos frageis em nomes, aliases e verificacao de janela.",
        "files": [
            "tools/system_tools.py",
            "core/router.py",
            "memory/aliases.py",
        ],
        "changes": [
            "Expandir aliases de aplicativos e validacao por nome de processo e titulo de janela.",
            "Verificar se o app realmente abriu ou fechou antes de responder sucesso.",
            "Registrar apps mais usados pelo operador para priorizar o matching.",
        ],
        "risk": "Medio, porque regras de app podem conflitar com sites e smart open.",
    },
}


def _save_json(path: Path, payload: dict):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def generate_patch_proposals(limit: int = 4) -> list[dict]:
    bottlenecks = load_bottlenecks()
    proposals = []

    for bottleneck in bottlenecks[:limit]:
        if not isinstance(bottleneck, dict):
            continue
        kind = str(bottleneck.get("kind", "")).strip()
        base = PATCH_LIBRARY.get(kind)
        if not base:
            continue

        proposals.append(
            {
                "kind": kind,
                "priority": int(bottleneck.get("count", 0) or 0),
                "title": base["title"],
                "why": base["why"],
                "files": list(base["files"]),
                "changes": list(base["changes"]),
                "risk": base["risk"],
                "examples": list(bottleneck.get("examples", [])[:3]),
            }
        )

    if not proposals:
        proposals.append(
            {
                "kind": "general",
                "priority": 0,
                "title": "Lapidar robustez geral do Axel",
                "why": "Ainda nao ha gargalos fortes suficientes para uma proposta mais especifica.",
                "files": ["main.py", "ui/assistant_hud.py"],
                "changes": [
                    "Continuar instrumentando o historico para detectar melhor os proximos pontos fracos.",
                    "Manter a ponte com o Codex atualizada com dados do uso recente.",
                ],
                "risk": "Baixo.",
                "examples": [],
            }
        )

    proposals.sort(key=lambda item: item.get("priority", 0), reverse=True)
    return proposals[: max(1, int(limit))]


def save_patch_proposals(limit: int = 4) -> list[dict]:
    proposals = generate_patch_proposals(limit=limit)
    payload = {
        "generated_at": time.time(),
        "items": proposals,
    }
    _save_json(PATCH_PROPOSALS_PATH, payload)
    return proposals


def load_patch_proposals() -> list[dict]:
    if PATCH_PROPOSALS_PATH.exists():
        try:
            data = json.loads(PATCH_PROPOSALS_PATH.read_text(encoding="utf-8"))
            items = data.get("items") if isinstance(data, dict) else None
            if isinstance(items, list) and items:
                return items
        except Exception:
            pass
    return save_patch_proposals()

