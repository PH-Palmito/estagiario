import json
import math
import tkinter as tk
import time
from io import BytesIO
from datetime import datetime
from pathlib import Path

from memory.ui_commands import enqueue_ui_command
from memory.ui_state import load_ui_state, update_ui_state

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

try:
    import requests
except Exception:
    requests = None

try:
    from tools.spotify_api import spotify_current_playback
except Exception:
    spotify_current_playback = None

try:
    from tools.weather_tools import get_weather_snapshot
except Exception:
    get_weather_snapshot = None

try:
    from memory.investment_snapshot import load_investment_snapshot
except Exception:
    load_investment_snapshot = None


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
TODO_PATH = MEMORY_DIR / "todo.md"
ROUTINES_PATH = MEMORY_DIR / "routines.json"
MACROS_PATH = MEMORY_DIR / "macros.json"
PROFILE_PATH = MEMORY_DIR / "profile.json"
AUTO_ADVANCES_PATH = MEMORY_DIR / "auto_advances.json"
PATCH_PROPOSALS_PATH = MEMORY_DIR / "patch_proposals.json"
ACTION_CANDIDATES_PATH = MEMORY_DIR / "action_candidates.json"
EXECUTION_PACKAGES_PATH = MEMORY_DIR / "execution_packages.json"
IMPLEMENTATION_HANDOFF_PATH = MEMORY_DIR / "implementation_handoff.json"
HANDOFF_APPLICATIONS_PATH = MEMORY_DIR / "handoff_applications.json"
HANDOFF_VALIDATION_PATH = MEMORY_DIR / "handoff_validation.json"
HANDOFF_RETRY_PLAN_PATH = MEMORY_DIR / "handoff_retry_plan.json"
CODEX_IMPLEMENTATION_REQUEST_PATH = MEMORY_DIR / "codex_implementation_request.json"
APPROVAL_GATE_PATH = MEMORY_DIR / "approval_gate.json"
VERIFICATION_RUNS_PATH = MEMORY_DIR / "verification_runs.json"
CODEX_BRIDGE_PATH = MEMORY_DIR / "codex_bridge.json"
CODEX_CHANNEL_PATH = MEMORY_DIR / "codex_channel.json"
CODEX_OUTBOX_PATH = MEMORY_DIR / "codex_outbox.json"
CODEX_INBOX_PATH = MEMORY_DIR / "codex_inbox.json"
SELF_EVOLUTION_PATH = MEMORY_DIR / "self_evolution.json"
BOTTLENECKS_PATH = MEMORY_DIR / "bottlenecks.json"
OPERATIONAL_CONTEXT_PATH = MEMORY_DIR / "operational_context.json"

BG = "#070c14"
BG_ALT = "#0b1220"
PANEL = "#0d131f"
PANEL_ALT = "#101827"
CARD = "#111827"
CARD_ALT = "#151f31"
ACCENT = "#60a5fa"
ACCENT_2 = "#2563eb"
ACCENT_3 = "#93c5fd"
ACCENT_MAGENTA = "#d946ef"
ACCENT_WARN = "#38bdf8"
TEXT = "#edf2ff"
TEXT_SOFT = "#8ea0ba"
TEXT_DIM = "#617087"
GRID = "#273244"
LINE = "#243044"
LINE_STRONG = "#2f5f98"
GOOD = "#54e6c2"
BUSY = "#65b7ff"
RESPOND = "#a9e8ff"
ALERT = "#ff7d96"

PANEL_ICONS = {
    "text": "\u270e",
    "audio": "\u25cc",
    "midia": "\u266a",
    "tempo": "\u2601",
    "invest": "\u2197",
    "mapas": "\u2316",
    "contexto": "\u2318",
    "comandos": "\u2691",
}

COMMAND_GROUPS = [
    (
        "Midia",
        [
            ("\u23ee", "Anterior", "musica anterior", True),
            ("\u25b6", "Play/Pause", "pausar ou continuar musica", True),
            ("\u23ed", "Proxima", "proxima musica", True),
            ("\u2212", "Volume -", "diminuir volume", True),
            ("\u25c9", "Mutar", "mutar volume", True),
            ("+", "Volume +", "aumentar volume", True),
            ("\u266a", "Spotify", "abre o spotify", True),
        ],
    ),
    (
        "Interface",
        [
            ("\u25cc", "Mostrar HUD", "mostrar hud", False),
            ("\u25cc", "Ocultar HUD", "fechar hud", False),
            ("\u2318", "Contexto", "status da interface", False),
            ("\u21bb", "Repetir", "repetir", False),
        ],
    ),
    (
        "Modos",
        [
            ("\u25cf", "Conversa", "quero conversar", False),
            ("\u25cb", "Parar conversa", "parar conversa", False),
            ("\u270e", "Ditado", "modo ditado", False),
            ("\u2715", "Parar ditado", "parar ditado", False),
        ],
    ),
    (
        "Dados",
        [
            ("\u2601", "Clima", "como esta o clima", False),
            ("\u2197", "Invest", "resumo da carteira", False),
            ("\u25cc", "Tela", "o que tem na tela", False),
            ("\u2316", "Mapa", "mostrar mapa", False),
        ],
    ),
]


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_todo_lines(limit: int = 6) -> list[str]:
    try:
        lines = TODO_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    items = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ["):
            items.append(stripped)
    return items[:limit]


def _load_routine_names(limit: int = 4) -> list[str]:
    return list(_load_json(ROUTINES_PATH).keys())[:limit]


def _load_macro_names(limit: int = 4) -> list[str]:
    return list(_load_json(MACROS_PATH).keys())[:limit]


def _load_profile_summary() -> list[str]:
    profile = _load_json(PROFILE_PATH)
    if not profile:
        return ["Operador sem perfil carregado."]

    lines = []
    nome = profile.get("nome")
    curso = profile.get("curso")
    faculdade = profile.get("faculdade")
    if nome:
        lines.append(f"Operador: {nome}")
    if curso and faculdade:
        lines.append(f"{curso} - {faculdade}")

    foco = profile.get("foco_profissional") or []
    if foco:
        lines.append("Foco: " + ", ".join(str(item) for item in foco[:4]))

    projetos = profile.get("projetos") or {}
    if projetos:
        lines.append("Projetos: " + ", ".join(str(name) for name in list(projetos.keys())[:3]))

    return lines[:5] or ["Perfil carregado."]


def _load_operational_context_lines(limit: int = 6) -> list[str]:
    data = _load_json(OPERATIONAL_CONTEXT_PATH)
    if not isinstance(data, dict):
        return []

    lines = []
    focus = str(data.get("current_focus", "")).strip()
    if focus:
        lines.append(f"Foco: {focus}")

    recent_apps = data.get("recent_apps") if isinstance(data.get("recent_apps"), list) else []
    recent_sites = data.get("recent_sites") if isinstance(data.get("recent_sites"), list) else []
    recent_topics = data.get("recent_topics") if isinstance(data.get("recent_topics"), list) else []

    if recent_apps:
        lines.append("Apps: " + ", ".join(str(item) for item in recent_apps[:4]))
    if recent_sites:
        lines.append("Sites: " + ", ".join(str(item) for item in recent_sites[:4]))
    if recent_topics:
        lines.append("Topicos: " + ", ".join(str(item) for item in recent_topics[:5]))

    return lines[:limit]


def _load_auto_advances(limit: int = 6) -> list[str]:
    data = _load_json(AUTO_ADVANCES_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []

    lines = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if title and reason:
            lines.append(f"- {title}\n  {reason}")
        elif title:
            lines.append(f"- {title}")
    return lines


def _load_codex_bridge_lines(limit: int = 6) -> list[str]:
    data = _load_json(CODEX_BRIDGE_PATH)
    if not isinstance(data, dict):
        return []

    lines = []
    title = str(data.get("title", "")).strip()
    reason = str(data.get("reason", "")).strip()
    if title:
        lines.append(f"Pedido: {title}")
    if reason:
        lines.append(reason)

    prompt = str(data.get("prompt", "")).strip()
    if prompt:
        prompt_lines = [line.strip() for line in prompt.splitlines() if line.strip()]
        for line in prompt_lines[: max(0, limit - len(lines))]:
            lines.append(line)
    return lines[:limit]


def _load_codex_channel_lines(limit: int = 6) -> list[str]:
    data = _load_json(CODEX_CHANNEL_PATH)
    if not isinstance(data, dict):
        return []
    title = str(data.get("title", "")).strip()
    trigger = str(data.get("trigger", "")).strip()
    urgency = str(data.get("urgency", "")).strip()
    status = str(data.get("status", "")).strip()
    next_action = str(data.get("next_action", "")).strip()
    should_notify = bool(data.get("should_notify"))
    notify_reason = str(data.get("notify_reason", "")).strip()
    lines = []
    if title:
        lines.append(f"Canal Codex: {title}")
    if status:
        lines.append(f"Estado: {status} | urgencia: {urgency or 'normal'}")
    if should_notify:
        lines.append("Sugestao ativa: acionar Codex")
    if trigger:
        lines.append(f"Gatilho: {trigger}")
    if notify_reason and len(lines) < limit:
        lines.append(notify_reason)
    if next_action and len(lines) < limit:
        lines.append(next_action)
    return lines[:limit]


def _load_codex_outbox_lines(limit: int = 6) -> list[str]:
    data = _load_json(CODEX_OUTBOX_PATH)
    if not isinstance(data, dict):
        return []
    pending = data.get("pending") if isinstance(data.get("pending"), list) else []
    sent = data.get("sent") if isinstance(data.get("sent"), list) else []
    lines = [f"Fila Codex: {len(pending)} pendente(s), {len(sent)} entregue(s)"]
    if pending:
        first = pending[0] if isinstance(pending[0], dict) else {}
        title = str(first.get("title", "")).strip()
        urgency = str(first.get("urgency", "")).strip()
        if title:
            lines.append(f"Proxima: {title}")
        if urgency:
            lines.append(f"Urgencia: {urgency}")
    return lines[:limit]


def _load_codex_inbox_lines(limit: int = 5) -> list[str]:
    data = _load_json(CODEX_INBOX_PATH)
    if not isinstance(data, dict):
        return []
    items = data.get("items") if isinstance(data.get("items"), list) else []
    if not items:
        return []
    lines = [f"Inbox Codex: {len(items)} resposta(s) registrada(s)"]
    latest = items[-1] if isinstance(items[-1], dict) else {}
    kind = str(latest.get("kind", "")).strip()
    text = str(latest.get("text", "")).strip()
    if kind:
        lines.append(f"Ultimo tipo: {kind}")
    if text:
        lines.append(text)
    return lines[:limit]


def _load_self_evolution_lines(limit: int = 6) -> list[str]:
    data = _load_json(SELF_EVOLUTION_PATH)
    if not isinstance(data, dict):
        return []
    steps = data.get("steps") or []
    if not isinstance(steps, list):
        return []
    lines = []
    focus = str(data.get("current_focus", "")).strip()
    if focus:
        lines.append(f"Foco: {focus}")
    for step in steps[: max(0, limit - len(lines))]:
        if not isinstance(step, dict):
            continue
        status = str(step.get("status", "")).strip()
        title = str(step.get("title", "")).strip()
        if title:
            lines.append(f"{status}: {title}")
    return lines[:limit]


def _load_bottleneck_lines(limit: int = 4) -> list[str]:
    data = _load_json(BOTTLENECKS_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    lines = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        count = int(item.get("count", 0) or 0)
        if title:
            lines.append(f"Gargalo: {title} ({count})")
            examples = item.get("examples") if isinstance(item.get("examples"), list) else []
            assistant_signals = item.get("assistant_signals") if isinstance(item.get("assistant_signals"), list) else []
            if examples:
                lines.append(f"Exemplo: {str(examples[0])[:90]}")
            elif assistant_signals:
                lines.append(f"Sinal: {str(assistant_signals[0])[:90]}")
    return lines


def _load_patch_proposal_lines(limit: int = 3) -> list[str]:
    data = _load_json(PATCH_PROPOSALS_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    lines = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        files = item.get("files") or []
        if title:
            lines.append(f"Patch: {title}")
            if files:
                lines.append("Arquivos: " + ", ".join(str(file) for file in files[:3]))
    return lines[: max(1, limit * 2)]


def _load_action_candidate_lines(limit: int = 4) -> list[str]:
    data = _load_json(ACTION_CANDIDATES_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    lines = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        status = str(item.get("status", "pending")).strip()
        files = item.get("files") or []
        if title:
            lines.append(f"Acao: {status} | {title}")
            if files and len(lines) < limit:
                lines.append("Alvos: " + ", ".join(str(file) for file in files[:3]))
    return lines[:limit]


def _load_execution_package_lines(limit: int = 4) -> list[str]:
    data = _load_json(EXECUTION_PACKAGES_PATH)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status", "")).strip()
    title = str(data.get("title", "")).strip()
    files = data.get("files") if isinstance(data.get("files"), list) else []
    if not status:
        return []
    lines = [f"Execucao: {status}"]
    if title:
        lines.append(f"Plano: {title}")
    if files:
        lines.append("Alvos: " + ", ".join(str(file) for file in files[:3]))
    return lines[:limit]


def _load_implementation_handoff_lines(limit: int = 4) -> list[str]:
    data = _load_json(IMPLEMENTATION_HANDOFF_PATH)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status", "")).strip()
    title = str(data.get("title", "")).strip()
    files = data.get("files") if isinstance(data.get("files"), list) else []
    if not status:
        return []
    lines = [f"Handoff: {status}"]
    if title:
        lines.append(f"Alvo: {title}")
    if files:
        lines.append("Arquivos: " + ", ".join(str(file) for file in files[:3]))
    return lines[:limit]


def _load_handoff_application_lines(limit: int = 4) -> list[str]:
    data = _load_json(HANDOFF_APPLICATIONS_PATH)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status", "")).strip()
    handoff = data.get("handoff") or {}
    title = str(handoff.get("title", "")).strip()
    note = str(data.get("last_note", "")).strip()
    if not status:
        return []
    lines = [f"Aplicacao: {status}"]
    if title:
        lines.append(f"Handoff: {title}")
    if note:
        lines.append(f"Nota: {note}")
    return lines[:limit]


def _load_handoff_validation_lines(limit: int = 4) -> list[str]:
    data = _load_json(HANDOFF_VALIDATION_PATH)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status", "")).strip()
    title = str(data.get("title", "")).strip()
    checklist = data.get("checklist") if isinstance(data.get("checklist"), list) else []
    if not status or status == "blocked":
        return []
    lines = [f"Validacao: {status}"]
    if title:
        lines.append(f"Alvo: {title}")
    if checklist:
        lines.append("Teste: " + str(checklist[0])[:96])
    return lines[:limit]


def _load_handoff_retry_lines(limit: int = 4) -> list[str]:
    data = _load_json(HANDOFF_RETRY_PLAN_PATH)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status", "")).strip()
    title = str(data.get("title", "")).strip()
    evidence = data.get("evidence") if isinstance(data.get("evidence"), list) else []
    if not status or status == "blocked":
        return []
    lines = [f"Nova tentativa: {status}"]
    if title:
        lines.append(title)
    if evidence:
        lines.append("Pista: " + str(evidence[0])[:96])
    return lines[:limit]


def _load_codex_implementation_request_lines(limit: int = 4) -> list[str]:
    data = _load_json(CODEX_IMPLEMENTATION_REQUEST_PATH)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status", "")).strip()
    title = str(data.get("title", "")).strip()
    files = data.get("files") if isinstance(data.get("files"), list) else []
    if not status:
        return []
    lines = [f"Pedido Codex: {status}"]
    if title:
        lines.append(f"Implementar: {title}")
    if files:
        lines.append("Alvos: " + ", ".join(str(file) for file in files[:3]))
    return lines[:limit]


def _load_approval_lines(limit: int = 4) -> list[str]:
    data = _load_json(APPROVAL_GATE_PATH)
    if not isinstance(data, dict):
        return []
    proposal = data.get("proposal") or {}
    title = str(proposal.get("title", "")).strip()
    status = str(data.get("status", "none")).strip()
    note = str(data.get("decision_note", "")).strip()
    if not title:
        return []
    lines = [f"Aprovacao: {status}", f"Proposta: {title}"]
    if note:
        lines.append(f"Nota: {note}")
    return lines[:limit]


def _load_verification_lines(limit: int = 4) -> list[str]:
    data = _load_json(VERIFICATION_RUNS_PATH)
    if not isinstance(data, dict):
        return []
    status = str(data.get("status", "idle")).strip()
    proposal = data.get("proposal") or {}
    title = str(proposal.get("title", "")).strip()
    attempts = int(data.get("attempts", 0) or 0)
    note = str(data.get("last_note", "")).strip()
    if not title and status == "idle":
        return []
    lines = [f"Verificacao: {status}"]
    if title:
        lines.append(f"Alvo: {title}")
    if attempts:
        lines.append(f"Tentativas: {attempts}")
    if note:
        lines.append(f"Nota: {note}")
    return lines[:limit]


class AssistantHud:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Axel")
        self.root.geometry("1360x820+60+42")
        self.root.minsize(1120, 720)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.angle = 0.0
        self.scan_offset = 0
        self.last_state = {}
        self.quick_buttons = []
        self.panels = {}
        self.panel_buttons = {}
        self.media_art_image = None
        self.media_art_url = ""
        self.media_snapshot = {}
        self.media_last_fetch = 0.0
        self.weather_last_fetch = 0.0
        self.weather_snapshot = None
        self.investment_last_fetch = 0.0
        self.panel_defaults = {
            "text": {"x": 34, "y": 34, "width": 460, "height": 316},
            "audio": {"x": 34, "y": 370, "width": 360, "height": 246},
            "midia": {"x": 410, "y": 330, "width": 420, "height": 410},
            "tempo": {"x": 410, "y": 34, "width": 360, "height": 238},
            "invest": {"x": 34, "y": 640, "width": 420, "height": 300},
            "mapas": {"x": 480, "y": 640, "width": 360, "height": 260},
            "contexto": {"x": 860, "y": 34, "width": 460, "height": 560},
            "comandos": {"x": 870, "y": 90, "width": 420, "height": 640},
        }
        self.drag_state = {}

        self._build_layout()
        self._refresh_state()
        self._animate()

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.stage = tk.Frame(self.root, bg=BG)
        self.stage.grid(row=0, column=0, sticky="nsew")

        self.canvas = tk.Canvas(self.stage, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._build_widget_panels()
        self._build_dock()
        self._build_settings_button()

    def _build_widget_panels(self):
        self.text_panel = self._floating_panel("text", x=34, y=34, width=460, height=316)
        self._build_text_panel(self.text_panel)

        self.audio_panel = self._floating_panel("audio", x=34, y=370, width=360, height=246)
        self._build_audio_panel(self.audio_panel)

        self.media_panel = self._floating_panel("midia", x=410, y=330, width=420, height=410)
        self._build_media_panel(self.media_panel)

        self.weather_panel = self._floating_panel("tempo", x=410, y=34, width=360, height=238)
        self._build_weather_panel(self.weather_panel)

        self.invest_panel = self._floating_panel("invest", x=34, y=640, width=420, height=300)
        self._build_invest_panel(self.invest_panel)

        self.maps_panel = self._floating_panel("mapas", x=480, y=640, width=360, height=260)
        self._build_maps_panel(self.maps_panel)

        self.context_panel = self._floating_panel("contexto", x=860, y=34, width=460, height=560)
        self._build_context_panel(self.context_panel)

        self.commands_panel = self._floating_panel("comandos", x=870, y=90, width=420, height=640)
        self._build_commands_panel(self.commands_panel)

    def _build_dock(self):
        dock = tk.Frame(self.stage, bg="#0b1220", highlightthickness=1, highlightbackground=LINE)
        dock.place(relx=0.5, rely=1.0, anchor="s", y=-24)

        for key, label in [
            ("text", "Texto"),
            ("midia", "Midia"),
            ("tempo", "Tempo"),
            ("invest", "Invest"),
            ("mapas", "Mapas"),
        ]:
            button = tk.Button(
                dock,
                text=f"{PANEL_ICONS.get(key, '*')}  {label}",
                command=lambda name=key: self._toggle_panel(name),
                bg="#0b1220",
                fg=TEXT_SOFT,
                activebackground=CARD,
                activeforeground=TEXT,
                relief="flat",
                font=("Segoe UI Semibold", 10),
                padx=18,
                pady=12,
            )
            button.pack(side="left", padx=(3, 3), pady=3)
            self.panel_buttons[key] = button

    def _build_settings_button(self):
        settings = tk.Frame(self.stage, bg=BG)
        settings.place(relx=1.0, x=-24, y=24, anchor="ne")
        button = tk.Button(
            settings,
            text="\u2699",
            command=self._toggle_settings_menu,
            bg="#0b1220",
            fg=TEXT_SOFT,
            activebackground=CARD,
            activeforeground=TEXT,
            relief="flat",
            font=("Segoe UI Symbol", 12),
            padx=12,
            pady=9,
        )
        button.pack(side="top", anchor="e")
        self.settings_menu = tk.Frame(settings, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        for key, label in [("audio", "Audio"), ("contexto", "Contexto"), ("comandos", "Comandos")]:
            item = tk.Button(
                self.settings_menu,
                text=f"{PANEL_ICONS.get(key, '*')}  {label}",
                command=lambda name=key: self._toggle_panel(name),
                bg=PANEL,
                fg=TEXT_SOFT,
                activebackground=CARD,
                activeforeground=TEXT,
                relief="flat",
                font=("Segoe UI Semibold", 10),
                padx=16,
                pady=9,
                anchor="w",
            )
            item.pack(fill="x")
            self.panel_buttons[key] = item

    def _toggle_settings_menu(self):
        if self.settings_menu.winfo_ismapped():
            self.settings_menu.pack_forget()
            return
        self.settings_menu.pack(side="top", anchor="e", pady=(8, 0))

    def _floating_panel(self, key, x, y, width, height):
        panel = tk.Frame(self.stage, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        panel.axel_panel_key = key
        panel.place(x=x, y=y, width=width, height=height)
        panel.place_forget()
        self.panels[key] = panel
        return panel

    def _panel_position(self, key):
        defaults = dict(self.panel_defaults.get(key) or {})
        positions = load_ui_state().get("panel_positions")
        saved = positions.get(key) if isinstance(positions, dict) else None
        if isinstance(saved, dict):
            for field in ("x", "y"):
                try:
                    defaults[field] = int(saved[field])
                except Exception:
                    pass
        return self._clamp_panel_position(key, defaults)

    def _clamp_panel_position(self, key, position):
        pos = dict(position)
        width = int(pos.get("width") or self.panel_defaults[key]["width"])
        height = int(pos.get("height") or self.panel_defaults[key]["height"])
        stage_width = max(self.stage.winfo_width(), self.root.winfo_width(), width + 68)
        stage_height = max(self.stage.winfo_height(), self.root.winfo_height(), height + 92)
        pos["width"] = width
        pos["height"] = height
        pos["x"] = max(12, min(int(pos.get("x") or 0), stage_width - width - 12))
        pos["y"] = max(12, min(int(pos.get("y") or 0), stage_height - height - 76))
        return pos

    def _toggle_panel(self, key):
        panel = self.panels.get(key)
        if not panel:
            return
        if panel.winfo_ismapped():
            panel.place_forget()
            self.panel_buttons[key].config(bg=CARD, fg=TEXT_SOFT)
            return
        panel.place(**self._panel_position(key))
        self.panel_buttons[key].config(bg="#1d4ed8", fg=TEXT)

    def _start_panel_drag(self, key, event):
        panel = self.panels.get(key)
        if not panel:
            return
        info = panel.place_info()
        self.drag_state = {
            "key": key,
            "start_x": event.x_root,
            "start_y": event.y_root,
            "panel_x": int(float(info.get("x") or 0)),
            "panel_y": int(float(info.get("y") or 0)),
        }

    def _drag_panel(self, event):
        key = self.drag_state.get("key")
        panel = self.panels.get(key)
        if not key or not panel:
            return
        base = self.panel_defaults[key]
        position = {
            "x": self.drag_state["panel_x"] + event.x_root - self.drag_state["start_x"],
            "y": self.drag_state["panel_y"] + event.y_root - self.drag_state["start_y"],
            "width": base["width"],
            "height": base["height"],
        }
        panel.place(**self._clamp_panel_position(key, position))

    def _end_panel_drag(self, event=None):
        key = self.drag_state.get("key")
        panel = self.panels.get(key)
        if not key or not panel:
            self.drag_state = {}
            return
        info = panel.place_info()
        state = load_ui_state()
        positions = state.get("panel_positions") if isinstance(state.get("panel_positions"), dict) else {}
        positions[key] = {
            "x": int(float(info.get("x") or 0)),
            "y": int(float(info.get("y") or 0)),
        }
        update_ui_state({"panel_positions": positions})
        self.drag_state = {}

    def _panel_title(self, parent, title):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(16, 10))
        key = getattr(parent, "axel_panel_key", "")
        title_label = tk.Label(
            row,
            text=f"{PANEL_ICONS.get(key, '*')}  {title}" if key else title,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 12),
        )
        title_label.pack(side="left", anchor="w")
        topbar = tk.Frame(row, bg=PANEL)
        topbar.pack(side="right", anchor="e")
        for color in ("#f87171", "#facc15", "#34d399"):
            tk.Label(topbar, text="", bg=color, width=2, height=1).pack(side="left", padx=(4, 0))
        if key:
            for widget in (row, title_label, topbar):
                widget.bind("<ButtonPress-1>", lambda event, name=key: self._start_panel_drag(name, event))
                widget.bind("<B1-Motion>", self._drag_panel)
                widget.bind("<ButtonRelease-1>", self._end_panel_drag)

    def _build_text_panel(self, parent):
        self._panel_title(parent, "Texto")
        entry_row = tk.Frame(parent, bg=PANEL)
        entry_row.pack(fill="x", padx=16, pady=(0, 12))
        self.text_entry = tk.Entry(
            entry_row,
            bg="#111827",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 11),
            highlightthickness=1,
            highlightbackground=LINE,
            highlightcolor=LINE_STRONG,
        )
        self.text_entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.text_entry.bind("<Return>", self._submit_text_command)
        tk.Button(
            entry_row,
            text="\u21b5",
            command=self._submit_text_command,
            bg="#2563eb",
            fg=TEXT,
            activebackground="#60a5fa",
            activeforeground=BG,
            relief="flat",
            font=("Segoe UI Semibold", 14),
            padx=16,
        ).pack(side="left", padx=(8, 0))

        self.heard_value = self._text_block(parent, "ULTIMA FALA", PANEL, wrap=390, height=54)
        self.response_value = self._text_block(parent, "ULTIMA RESPOSTA", PANEL, wrap=390, height=72)
        self.history_text = self._panel_list(parent, None, None, "HISTORICO")

    def _build_audio_panel(self, parent):
        self._panel_title(parent, "Audio")
        grid = tk.Frame(parent, bg=PANEL)
        grid.pack(fill="x", padx=12, pady=(0, 10))
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)
        self.status_value = self._metric_card(grid, 0, 0, "STATUS")
        self.mode_value = self._metric_card(grid, 0, 1, "MODO")
        self.activity_value = self._metric_card(grid, 1, 0, "ATIVIDADE")
        self.hotword_value = self._metric_card(grid, 1, 1, "ESCUTA")
        self.channel_value = self._metric_card(grid, 2, 0, "CANAL")
        self.signal_value = self._metric_card(grid, 2, 1, "SINAL")

    def _build_media_panel(self, parent):
        self._panel_title(parent, "Midia")
        top = tk.Frame(parent, bg=PANEL)
        top.pack(fill="x", padx=18, pady=(0, 16))

        self.media_art_canvas = tk.Canvas(
            top,
            width=132,
            height=132,
            bg=CARD,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.media_art_canvas.pack(side="left")
        self._draw_album_placeholder()

        meta = tk.Frame(top, bg=PANEL)
        meta.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.media_track_value = tk.Label(
            meta,
            text="Nada tocando",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 12),
            anchor="w",
            justify="left",
            wraplength=220,
        )
        self.media_track_value.pack(fill="x", anchor="w")
        self.media_artist_value = tk.Label(
            meta,
            text="Spotify / sistema",
            bg=PANEL,
            fg=TEXT_SOFT,
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=220,
        )
        self.media_artist_value.pack(fill="x", anchor="w", pady=(6, 0))
        self.media_status_value = tk.Label(
            meta,
            text="Aguardando metadados",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=220,
        )
        self.media_status_value.pack(fill="x", anchor="w", pady=(12, 0))

        main_row = tk.Frame(parent, bg=PANEL)
        main_row.pack(fill="x", padx=18, pady=(0, 10))
        for label, command in [
            ("\u23ee", "musica anterior"),
            ("\u25b6", "pausar ou continuar musica"),
            ("\u23ed", "proxima musica"),
        ]:
            self._media_button(main_row, label, command).pack(side="left", fill="x", expand=True, padx=4)

        volume_row = tk.Frame(parent, bg=PANEL)
        volume_row.pack(fill="x", padx=18, pady=(0, 10))
        for label, command in [
            ("\u2212", "diminuir volume"),
            ("\u25c9", "mutar volume"),
            ("+", "aumentar volume"),
        ]:
            self._media_button(volume_row, label, command).pack(side="left", fill="x", expand=True, padx=4)

        app_row = tk.Frame(parent, bg=PANEL)
        app_row.pack(fill="x", padx=18, pady=(0, 14))
        self._media_button(app_row, "\u266a", "abre o spotify").pack(side="left", fill="x", expand=True, padx=4)
        self._command_button(app_row, "\u25cc", "o que tem na tela").pack(side="left", fill="x", expand=True, padx=4)

        self.media_hint_value = tk.Label(
            parent,
            text="Capa real via Spotify. Fallback neural quando nao houver metadados.",
            bg=CARD,
            fg=TEXT_SOFT,
            font=("Segoe UI", 9),
            justify="left",
            anchor="nw",
            wraplength=350,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.media_hint_value.pack(fill="x", padx=18)

    def _media_button(self, parent, label, command):
        return tk.Button(
            parent,
            text=label,
            command=lambda cmd=command: self._queue_command(cmd, source="hud_media", silent=True),
            bg="#151f31",
            fg=TEXT,
            activebackground="#2563eb",
            activeforeground=BG,
            relief="flat",
            font=("Segoe UI Symbol", 14),
            padx=10,
            pady=8,
        )

    def _command_button(self, parent, label, command, source: str = "hud", silent: bool = False):
        return tk.Button(
            parent,
            text=label,
            command=lambda cmd=command, cmd_source=source, is_silent=silent: self._queue_command(
                cmd,
                source=cmd_source,
                silent=is_silent,
            ),
            bg="#151f31",
            fg=TEXT,
            activebackground="#2563eb",
            activeforeground=BG,
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padx=10,
            pady=9,
        )

    def _build_weather_panel(self, parent):
        self._panel_title(parent, "Tempo")
        hero = tk.Frame(parent, bg=PANEL)
        hero.pack(fill="x", padx=18, pady=(0, 12))
        self.weather_temp_value = tk.Label(
            hero,
            text="-- C",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 34),
            anchor="w",
        )
        self.weather_temp_value.pack(side="left", anchor="w")
        meta = tk.Frame(hero, bg=PANEL)
        meta.pack(side="left", fill="both", expand=True, padx=(14, 0))
        self.weather_place_value = tk.Label(meta, text="Clima local", bg=PANEL, fg=TEXT, font=("Segoe UI Semibold", 11), anchor="w")
        self.weather_place_value.pack(fill="x")
        self.weather_desc_value = tk.Label(meta, text="Aguardando consulta", bg=PANEL, fg=TEXT_SOFT, font=("Segoe UI", 10), anchor="w", wraplength=220, justify="left")
        self.weather_desc_value.pack(fill="x", pady=(4, 0))
        grid = tk.Frame(parent, bg=PANEL)
        grid.pack(fill="x", padx=12, pady=(0, 10))
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1)
        self.weather_feels_value = self._metric_card(grid, 0, 0, "SENSA")
        self.weather_rain_value = self._metric_card(grid, 0, 1, "CHUVA")
        self.weather_wind_value = self._metric_card(grid, 0, 2, "VENTO")

    def _build_invest_panel(self, parent):
        self._panel_title(parent, "Invest")
        grid = tk.Frame(parent, bg=PANEL)
        grid.pack(fill="x", padx=12, pady=(0, 10))
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)
        self.invest_total_value = self._metric_card(grid, 0, 0, "PATRIMONIO")
        self.invest_return_value = self._metric_card(grid, 0, 1, "RETORNO")
        self.invest_income_value = self._metric_card(grid, 1, 0, "PROVENTOS")
        self.invest_update_value = self._metric_card(grid, 1, 1, "SNAPSHOT")
        self.invest_text = self._panel_list(parent, None, None, "SINAIS")

    def _build_maps_panel(self, parent):
        self._panel_title(parent, "Mapas")
        self.maps_status_value = tk.Label(
            parent,
            text="Modulo preparado para rotas, lugares e tempo de deslocamento.",
            bg=CARD,
            fg=TEXT_SOFT,
            font=("Segoe UI", 10),
            justify="left",
            anchor="nw",
            wraplength=300,
            padx=14,
            pady=12,
            highlightthickness=1,
            highlightbackground=LINE,
        )
        self.maps_status_value.pack(fill="x", padx=18, pady=(0, 14))
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=18, pady=(0, 10))
        for label, command in [
            ("\u2316  Mapa", "mostrar mapa"),
            ("\u25cc  Tela", "o que tem na tela"),
        ]:
            self._command_button(row, label, command).pack(side="left", fill="x", expand=True, padx=4)

    def _build_commands_panel(self, parent):
        self._panel_title(parent, "Comandos")
        status_grid = tk.Frame(parent, bg=PANEL)
        status_grid.pack(fill="x", padx=12, pady=(0, 10))
        for column in range(2):
            status_grid.grid_columnconfigure(column, weight=1)
        self.commands_voice_value = self._metric_card(status_grid, 0, 0, "VOZ")
        self.commands_mode_value = self._metric_card(status_grid, 0, 1, "MODO")

        shell = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        shell.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        tk.Label(
            shell,
            text="ATIVOS",
            bg=CARD,
            fg=TEXT_DIM,
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w", padx=14, pady=(12, 4))

        canvas = tk.Canvas(shell, bg=CARD, highlightthickness=0)
        scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CARD)
        content.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(content_window, width=event.width))
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 0), pady=(0, 10))
        scrollbar.pack(side="right", fill="y", pady=(0, 10))

        for group, commands in COMMAND_GROUPS:
            tk.Label(
                content,
                text=group.upper(),
                bg=CARD,
                fg=ACCENT_3,
                font=("Segoe UI Semibold", 8),
            ).pack(anchor="w", padx=14, pady=(12, 4))
            for icon, label, command, silent in commands:
                self._command_row(content, icon, label, command, silent=silent)

    def _draw_album_placeholder(self):
        canvas = getattr(self, "media_art_canvas", None)
        if not canvas:
            return
        canvas.delete("all")
        size = 132
        canvas.create_rectangle(0, 0, size, size, fill="#06182d", outline="")
        for step in range(0, size, 16):
            color = "#0d2f55" if step % 32 == 0 else "#0a2543"
            canvas.create_line(step, 0, step, size, fill=color)
            canvas.create_line(0, step, size, step, fill=color)
        center = size // 2
        for radius, color in [(50, "#123f6e"), (34, ACCENT_2), (18, ACCENT)]:
            canvas.create_oval(center - radius, center - radius, center + radius, center + radius, outline=color, width=2)
        for index in range(10):
            phase = self.angle * 1.4 + index * 0.7
            x = center + math.cos(phase) * (18 + index * 3)
            y = center + math.sin(phase * 1.2) * (14 + index * 2)
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=ACCENT_3, outline="")
        canvas.create_text(center, center + 48, text="AXEL", fill=TEXT_SOFT, font=("Segoe UI Semibold", 9))

    def _set_album_art(self, image_url: str):
        if not image_url or image_url == self.media_art_url:
            return
        if not requests or Image is None or ImageTk is None:
            self.media_art_url = image_url
            return
        try:
            response = requests.get(image_url, timeout=8)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGB")
            image = image.resize((132, 132))
            self.media_art_image = ImageTk.PhotoImage(image)
            self.media_art_canvas.delete("all")
            self.media_art_canvas.create_image(0, 0, anchor="nw", image=self.media_art_image)
            self.media_art_url = image_url
        except Exception:
            self.media_art_url = ""
            self.media_art_image = None
            self._draw_album_placeholder()

    def _refresh_media_metadata(self):
        now = time.time()
        if now - self.media_last_fetch < 12:
            return
        self.media_last_fetch = now
        snapshot = None
        if spotify_current_playback:
            snapshot = spotify_current_playback()
        if not snapshot:
            self.media_snapshot = {}
            self.media_track_value.config(text="Nada tocando")
            self.media_artist_value.config(text="Spotify / sistema")
            self.media_status_value.config(text="Capa neural ativa")
            if self.media_art_url:
                self.media_art_url = ""
                self.media_art_image = None
                self._draw_album_placeholder()
            return

        self.media_snapshot = snapshot
        track = snapshot.get("name") or "Faixa sem nome"
        artists = snapshot.get("artists") or "Artista desconhecido"
        album = snapshot.get("album") or "Album desconhecido"
        status = "tocando" if snapshot.get("is_playing") else "pausado"
        self.media_track_value.config(text=track)
        self.media_artist_value.config(text=f"{artists}\n{album}")
        self.media_status_value.config(text=status)
        self._set_album_art(str(snapshot.get("image_url") or ""))

    def _refresh_weather_metadata(self):
        now = time.time()
        if now - self.weather_last_fetch < 900:
            return
        self.weather_last_fetch = now
        if not get_weather_snapshot:
            self.weather_temp_value.config(text="-- C")
            self.weather_desc_value.config(text="Clima indisponivel")
            return
        try:
            snapshot = get_weather_snapshot()
        except Exception:
            self.weather_temp_value.config(text="-- C")
            self.weather_desc_value.config(text="Nao consegui consultar agora")
            return
        self.weather_snapshot = snapshot
        temp = "--" if snapshot.temperature_c is None else str(round(snapshot.temperature_c))
        feels = "--" if snapshot.apparent_temperature_c is None else f"{round(snapshot.apparent_temperature_c)} C"
        rain = "--" if snapshot.rain_chance_percent is None else f"{round(snapshot.rain_chance_percent)}%"
        wind = "--" if snapshot.wind_kmh is None else f"{round(snapshot.wind_kmh)} km/h"
        self.weather_temp_value.config(text=f"{temp} C")
        self.weather_place_value.config(text=snapshot.location_label or "Clima local")
        self.weather_desc_value.config(text=snapshot.weather_label)
        self.weather_feels_value.config(text=feels)
        self.weather_rain_value.config(text=rain)
        self.weather_wind_value.config(text=wind)

    def _metric_from_snapshot(self, snapshot: dict, key: str) -> str:
        metric_map = snapshot.get("metric_map") if isinstance(snapshot.get("metric_map"), dict) else {}
        value = str(metric_map.get(key) or "").strip()
        if value:
            return value
        for line in list(snapshot.get("metrics") or []) + list(snapshot.get("lines") or []):
            text = str(line or "")
            if key.lower() in text.lower():
                return text[:42]
        return "--"

    def _refresh_investment_metadata(self):
        now = time.time()
        if now - self.investment_last_fetch < 30:
            return
        self.investment_last_fetch = now
        snapshot = load_investment_snapshot() if load_investment_snapshot else {}
        if not snapshot:
            self.invest_total_value.config(text="--")
            self.invest_return_value.config(text="--")
            self.invest_income_value.config(text="--")
            self.invest_update_value.config(text="sem dados")
            self._set_text_widget(self.invest_text, ["Snapshot ainda nao carregado."])
            return
        self.invest_total_value.config(text=self._metric_from_snapshot(snapshot, "patrimonio"))
        self.invest_return_value.config(text=self._metric_from_snapshot(snapshot, "rentabilidade"))
        self.invest_income_value.config(text=self._metric_from_snapshot(snapshot, "proventos"))
        updated_at = float(snapshot.get("updated_at") or 0)
        updated_label = time.strftime("%d/%m %H:%M", time.localtime(updated_at)) if updated_at else "--"
        self.invest_update_value.config(text=updated_label)
        lines = []
        summary = str(snapshot.get("summary") or "").strip()
        if summary:
            lines.append(summary[:220])
        positions = snapshot.get("asset_positions") if isinstance(snapshot.get("asset_positions"), dict) else {}
        if positions:
            tickers = list(positions.keys())[:5]
            lines.append("Ativos: " + ", ".join(tickers))
        breakdown = snapshot.get("category_breakdown") if isinstance(snapshot.get("category_breakdown"), dict) else {}
        if breakdown:
            lines.append("Classes: " + ", ".join(f"{k}: {v}" for k, v in list(breakdown.items())[:4]))
        self._set_text_widget(self.invest_text, lines or ["Snapshot salvo, sem resumo compacto."])

    def _build_context_panel(self, parent):
        self._panel_title(parent, "Contexto")
        grid = tk.Frame(parent, bg=PANEL)
        grid.pack(fill="x", padx=12, pady=(0, 10))
        for column in range(2):
            grid.grid_columnconfigure(column, weight=1)
        self.time_value = self._metric_card(grid, 0, 0, "HORARIO")
        self.name_value = self._metric_card(grid, 0, 1, "ASSISTENTE")
        self.mic_value = self._metric_card(grid, 1, 0, "MICROFONE")
        self.profile_value = self._metric_card(grid, 1, 1, "PERFIL")
        self.style_value = self._metric_card(grid, 2, 0, "ESTILO")
        self.command_value = self._metric_card(grid, 2, 1, "ULTIMO COMANDO")

        lists = tk.Frame(parent, bg=PANEL)
        lists.pack(fill="both", expand=True, padx=12, pady=(0, 14))
        lists.grid_columnconfigure(0, weight=1)
        lists.grid_columnconfigure(1, weight=1)
        lists.grid_rowconfigure(0, weight=1)
        lists.grid_rowconfigure(1, weight=1)
        lists.grid_rowconfigure(2, weight=1)
        self.profile_text = self._panel_list(lists, 0, 0, "OPERADOR")
        self.routines_value = self._panel_list(lists, 0, 1, "ROTINAS")
        self.macros_value = self._panel_list(lists, 1, 0, "MACROS")
        self.todo_value = self._panel_list(lists, 1, 1, "AVANCOS")
        self.console_text = self._panel_list(lists, 2, 0, "CODEX")

    def _metric_card(self, parent, row, column, title, panel=None):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6, ipadx=12, ipady=12)
        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x", pady=(0, 2))
        tk.Label(top, text=title, bg=CARD, fg=TEXT_DIM, font=("Segoe UI Semibold", 8)).pack(side="left", anchor="w")
        value = tk.Label(
            card,
            text="--",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI Semibold", 11),
            wraplength=180,
            justify="left",
            anchor="w",
        )
        value.pack(anchor="w", pady=(8, 0))
        return value

    def _text_block(self, parent, title, panel_bg, wrap=500, height=70):
        box = tk.Frame(parent, bg=panel_bg)
        box.pack(fill="x", padx=18, pady=(0, 12))
        title_row = tk.Frame(box, bg=panel_bg)
        title_row.pack(fill="x")
        tk.Label(
            title_row,
            text=title,
            bg=panel_bg,
            fg=TEXT_DIM,
            font=("Segoe UI Semibold", 9),
        ).pack(side="left", anchor="w")
        body = tk.Label(
            box,
            text="--",
            justify="left",
            anchor="nw",
            bg=CARD,
            fg=TEXT,
            wraplength=wrap,
            font=("Segoe UI", 11),
            padx=14,
            pady=12,
            height=max(2, height // 26),
            highlightthickness=1,
            highlightbackground=LINE,
        )
        body.pack(anchor="w", fill="x", pady=(8, 0))
        return body

    def _panel_list(self, parent, row, column, title):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        if row is None or column is None:
            card.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        else:
            card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        header = tk.Frame(card, bg=CARD)
        header.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(
            header,
            text=title,
            bg=CARD,
            fg=TEXT_DIM,
            font=("Segoe UI Semibold", 9),
        ).pack(side="left", anchor="w")

        text = tk.Text(
            card,
            bg=CARD,
            fg=TEXT,
            relief="flat",
            wrap="word",
            font=("Segoe UI", 9),
            height=8,
            padx=14,
            pady=8,
        )
        text.pack(fill="both", expand=True, padx=0, pady=(0, 8))
        text.configure(state="disabled")
        return text

    def _status_palette(self, status: str) -> tuple[str, str]:
        status = str(status or "").upper()
        if status in {"RESPOSTA", "CONVERSA"}:
            return "#a9e8ff", "#38bdf8"
        if status in {"COMANDO", "ATIVA"}:
            return "#60a5fa", "#93c5fd"
        if status == "DITADO":
            return "#54e6c2", "#60a5fa"
        if status == "PAUSADA":
            return "#35506d", "#617087"
        return "#2563eb", "#60a5fa"

    def _activity_label(self, state: dict) -> str:
        status = str(state.get("status", "")).upper()
        if status in {"RESPOSTA", "CONVERSA"}:
            return "respondendo"
        if status in {"COMANDO", "ATIVA"}:
            return "escutando"
        if status == "DITADO":
            return "ditando"
        if status == "PAUSADA":
            return "pausado"
        return "pronto"

    def _signal_label(self, state: dict) -> str:
        status = str(state.get("status", "")).upper()
        if status in {"RESPOSTA", "CONVERSA"}:
            return "alto"
        if status in {"COMANDO", "ATIVA", "DITADO"}:
            return "estavel"
        if status == "PAUSADA":
            return "silencioso"
        return "standby"

    def _draw_brain_core(self, cx, cy, primary, secondary, intensity, scale=1.14):
        nodes = [
            (-82, -44), (-54, -84), (-18, -58), (18, -86), (58, -48), (84, -6),
            (52, 36), (18, 72), (-24, 54), (-64, 22), (-96, -8), (-42, -8),
            (0, -22), (42, -8), (2, 28),
        ]
        nodes = [(x * scale, y * scale) for x, y in nodes]
        links = [
            (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8),
            (8, 9), (9, 10), (10, 0), (0, 11), (11, 12), (12, 13), (13, 5),
            (11, 14), (14, 13), (9, 14), (2, 12), (4, 13), (8, 14),
        ]

        self.canvas.create_oval(cx - 132, cy - 118, cx + 12, cy + 110, outline="#222831", width=1)
        self.canvas.create_oval(cx - 12, cy - 118, cx + 132, cy + 110, outline="#222831", width=1)

        for index, (start, end) in enumerate(links):
            x1, y1 = nodes[start]
            x2, y2 = nodes[end]
            phase = self.angle * (1.7 + intensity) + index * 0.72
            color = secondary if math.sin(phase) > 0.22 - intensity * 0.2 else GRID
            width = 1 + int(math.sin(phase) > 0.72 - intensity * 0.15)
            bend = 18 * math.sin(phase * 0.7)
            self.canvas.create_line(
                cx + x1,
                cy + y1,
                cx + (x1 + x2) / 2,
                cy + (y1 + y2) / 2 + bend,
                cx + x2,
                cy + y2,
                fill=color,
                width=width,
                smooth=True,
            )

        for index, (x, y) in enumerate(nodes):
            phase = self.angle * (2.1 + intensity) + index * 0.86
            radius = 3.5 + intensity * 2.2 + max(0, math.sin(phase)) * 2.4
            fill = primary if math.sin(phase) > -0.15 else secondary
            self.canvas.create_oval(cx + x - radius, cy + y - radius, cx + x + radius, cy + y + radius, fill=fill, outline="")

    def _draw_background_grid(self, width, height):
        self.canvas.create_rectangle(0, 0, width, height, fill=BG, outline="")
        for radius, color in [
            (520, "#09111f"),
            (390, "#091221"),
            (270, "#08101d"),
        ]:
            self.canvas.create_oval(
                -radius * 0.55,
                -radius * 0.52,
                radius * 1.15,
                radius * 1.05,
                fill=color,
                outline="",
            )
        right_radius = 430
        self.canvas.create_oval(
            width - right_radius * 0.55,
            -right_radius * 0.45,
            width + right_radius * 0.75,
            right_radius * 0.9,
            fill="#061522",
            outline="",
        )

        grid_bottom = int(height * 0.9)
        for x in range(0, width, 38):
            color = "#0d1726" if x % 76 else "#111d30"
            self.canvas.create_line(x, 0, x, grid_bottom, fill=color)
        for y in range(0, grid_bottom, 38):
            color = "#0d1726" if y % 76 else "#111d30"
            self.canvas.create_line(0, y, width, y, fill=color)

        fade_start = int(height * 0.58)
        for index in range(10):
            y0 = fade_start + index * 32
            self.canvas.create_rectangle(0, y0, width, y0 + 18, fill=BG, outline="")
        self.canvas.create_oval(
            width // 2 - 360,
            height // 2 - 280,
            width // 2 + 360,
            height // 2 + 280,
            outline="#0d1828",
            width=1,
        )

    def _command_row(self, parent, icon, label, command, silent=False):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=14, pady=4)
        badge = tk.Label(
            row,
            text=icon,
            bg="#0b1220",
            fg=ACCENT_3,
            font=("Segoe UI Symbol", 12),
            width=3,
            height=1,
        )
        badge.pack(side="left", padx=(0, 10), ipady=6)
        text = tk.Frame(row, bg=CARD)
        text.pack(side="left", fill="x", expand=True)
        tk.Label(
            text,
            text=label,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI Semibold", 9),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            text,
            text=command,
            bg=CARD,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))
        self._command_button(
            row,
            "\u21b5",
            command,
            source="hud_command_list",
            silent=silent,
        ).pack(side="right", padx=(10, 0))

    def _draw_ambient_particles(self, cx, cy, primary, secondary, intensity):
        for index in range(14):
            phase = self.angle * (0.35 + intensity * 0.12) + index * 0.62
            radius = 260 + (index % 4) * 34 + 8 * math.sin(phase * 1.7)
            x = cx + math.cos(phase) * radius
            y = cy + math.sin(phase * 0.83) * (radius * 0.52)
            size = 1.1 + (index % 3) * 0.35
            color = secondary if index % 4 == 0 else "#1d3d63"
            self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline="")
            if index % 5 == 0:
                tail = 16 + intensity * 10
                self.canvas.create_line(x - tail, y, x - tail * 0.35, y, fill="#123050", width=1)

    def _draw_dotted_ring(self, cx, cy, radius, color, active_color, intensity):
        count = 96
        spin = self.angle * (0.22 + intensity * 0.16)
        for index in range(count):
            if index % 2:
                continue
            phase = (math.tau * index / count) + spin
            tick = 2.0 + (index % 6 == 0) * 1.4
            x = cx + math.cos(phase) * radius
            y = cy + math.sin(phase) * radius
            fill = active_color if math.sin(self.angle * 1.4 + index * 0.31) > 0.65 - intensity * 0.22 else color
            self.canvas.create_oval(x - tick, y - tick, x + tick, y + tick, fill=fill, outline="")

    def _draw_target_brackets(self, cx, cy, radius, primary, secondary, intensity):
        offset = radius + 76
        corner = 58
        color = "#123050"
        hot = secondary if intensity > 0.6 else primary
        for sx, sy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            x = cx + sx * offset
            y = cy + sy * offset * 0.62
            self.canvas.create_line(x, y, x - sx * corner, y, fill=color, width=1)
            self.canvas.create_line(x, y, x, y - sy * corner, fill=color, width=1)
            self.canvas.create_line(x - sx * 12, y, x - sx * 28, y, fill=hot, width=2)
            self.canvas.create_line(x, y - sy * 12, x, y - sy * 28, fill=hot, width=2)

        scan = 42 * math.sin(self.angle * (0.9 + intensity * 0.4))
        self.canvas.create_line(cx - offset + 112, cy + scan, cx - radius - 26, cy + scan, fill="#1d3d63", width=1)
        self.canvas.create_line(cx + radius + 26, cy - scan, cx + offset - 112, cy - scan, fill="#1d3d63", width=1)

    def _draw_hex_cluster(self, cx, cy, primary, secondary, intensity):
        side = 16
        spacing_x = side * 1.55
        spacing_y = side * 1.36
        cells = [(-1, -1), (0, -1), (1, -1), (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
        for index, (col, row) in enumerate(cells):
            x = cx + col * spacing_x + (row % 2) * spacing_x * 0.5
            y = cy + row * spacing_y
            phase = self.angle * (1.1 + intensity * 0.4) + index * 0.8
            outline = secondary if math.sin(phase) > 0.1 else "#263348"
            fill = "#101827" if index != 4 else "#17244a"
            points = []
            for step in range(6):
                ang = math.radians(60 * step + 30)
                points.extend((x + math.cos(ang) * side, y + math.sin(ang) * side))
            self.canvas.create_polygon(points, fill=fill, outline=outline)
            if math.sin(phase) > 0.65:
                self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=primary, outline="")

    def _draw_core(self, state):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 500)
        height = max(self.canvas.winfo_height(), 240)

        primary, secondary = self._status_palette(state.get("status", ""))
        status = str(state.get("status", "INATIVO")).upper()
        speed = 1.0
        intensity = 0.35
        if status in {"RESPOSTA", "CONVERSA"}:
            speed = 1.6
            intensity = 1.0
        elif status == "DITADO":
            speed = 1.3
            intensity = 0.78
        elif status in {"COMANDO", "ATIVA"}:
            intensity = 0.66

        self._draw_background_grid(width, height)

        cx = width // 2
        cy = height // 2 - 28
        self._draw_ambient_particles(cx, cy, primary, secondary, intensity)
        pulse = (7 + intensity * 8) * math.sin(self.angle * speed)
        outer = 158 + pulse
        mid = 112 + pulse * 0.45
        inner = 18 + pulse * 0.14

        self._draw_target_brackets(cx, cy, outer, primary, secondary, intensity)
        self.canvas.create_oval(cx - outer, cy - outer, cx + outer, cy + outer, outline="#171a20", width=1)
        self.canvas.create_oval(cx - outer - 28, cy - outer - 28, cx + outer + 28, cy + outer + 28, outline="#08243f", width=1)
        self._draw_dotted_ring(cx, cy, outer + 18, "#17405f", secondary, intensity)
        self.canvas.create_oval(cx - mid, cy - mid, cx + mid, cy + mid, outline=secondary, width=2)
        self._draw_hex_cluster(cx, cy, primary, secondary, intensity)
        self._draw_brain_core(cx, cy, primary, secondary, intensity)
        self.canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner, fill=primary, outline="")

        self.canvas.create_arc(
            cx - 118,
            cy - 118,
            cx + 118,
            cy + 118,
            start=26 + self.angle * 8,
            extent=92 + int((math.sin(self.angle * speed * 1.2) + 1) * 34),
            style="arc",
            outline=primary,
            width=3,
        )
        self.canvas.create_arc(
            cx - 162,
            cy - 162,
            cx + 162,
            cy + 162,
            start=220 - self.angle * 6,
            extent=48,
            style="arc",
            outline=secondary,
            width=3,
        )
        magenta_phase = math.sin(self.angle * (1.1 + intensity))
        if magenta_phase > -0.2:
            self.canvas.create_arc(
                cx - 176,
                cy - 176,
                cx + 176,
                cy + 176,
                start=318 - self.angle * 10,
                extent=32 + int(max(0, magenta_phase) * 28),
                style="arc",
                outline=ACCENT_MAGENTA,
                width=2,
            )
        for index in range(8):
            phase = self.angle * (1.35 + intensity) + index * 0.78
            radius = 194 + 12 * math.sin(phase)
            dot_x = cx + math.cos(phase) * radius
            dot_y = cy + math.sin(phase * 0.86) * (radius * 0.62)
            size = 1.5 + intensity * 1.5
            self.canvas.create_oval(dot_x - size, dot_y - size, dot_x + size, dot_y + size, fill=secondary, outline="")
            if index % 2 == 0:
                self.canvas.create_line(cx, cy, dot_x, dot_y, fill="#0e395f", width=1)

        self.canvas.create_text(cx, cy + 184, text="Axel", fill=TEXT, font=("Segoe UI Semibold", 30))
        for side in (-1, 1):
            x = cx + side * 252
            for index in range(7):
                y = cy - 44 + index * 15
                wave = max(0.12, math.sin(self.angle * (1.25 + intensity) + index * 0.65 + side))
                bar_width = 18 + 30 * wave
                self.canvas.create_line(x, y, x + side * bar_width, y, fill="#1d3d63", width=2)
                if index % 2 == 0:
                    self.canvas.create_line(x, y + 5, x + side * (bar_width * 0.52), y + 5, fill=secondary, width=1)

        meter_width = 180
        meter_x = cx - meter_width // 2
        meter_y = cy + 254
        self.canvas.create_rectangle(meter_x, meter_y, meter_x + meter_width, meter_y + 3, fill=GRID, outline="")
        level = 0.25
        if status in {"ATIVA", "COMANDO"}:
            level = 0.62 + 0.12 * math.sin(self.angle * speed * 2.5)
        elif status in {"RESPOSTA", "CONVERSA"}:
            level = 0.84 + 0.08 * math.sin(self.angle * speed * 3.0)
        elif status == "DITADO":
            level = 0.75 + 0.10 * math.sin(self.angle * speed * 2.2)
        fill_width = int(meter_width * max(0.08, min(0.98, level)))
        self.canvas.create_rectangle(meter_x, meter_y, meter_x + fill_width, meter_y + 3, fill=secondary, outline="")

    def _set_text_widget(self, widget, lines: list[str]):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", "\n".join(lines) if lines else "--")
        widget.configure(state="disabled")

    def _queue_command(self, command: str, source: str = "hud", silent: bool = False):
        enqueue_ui_command(command, source=source, silent=silent)
        self.text_entry.delete(0, "end")

    def _submit_text_command(self, event=None):
        command = self.text_entry.get().strip()
        if not command:
            return "break"
        self._queue_command(command)
        return "break"

    def _refresh_state(self):
        state = load_ui_state()
        if not state.get("visible", False):
            self.close()
            return

        self.last_state = state
        self.status_value.config(text=state.get("status", "--"))
        self.mode_value.config(text=str(state.get("mode", "--")).upper())
        self.activity_value.config(text=self._activity_label(state))
        self.channel_value.config(text="painel + voz" if state.get("visible") else "voz")
        self.hotword_value.config(text="ativa" if state.get("hotword_enabled") else "manual")
        self.signal_value.config(text=self._signal_label(state))
        self.heard_value.config(text=state.get("last_heard") or "--")
        self.response_value.config(text=state.get("last_response") or "--")
        self.command_value.config(text=state.get("last_command") or "--")
        self.mic_value.config(text=state.get("microphone") or "--")
        self.profile_value.config(text=state.get("voice_profile") or "--")
        self.style_value.config(text=state.get("assistant_style") or "--")
        self.name_value.config(text=state.get("assistant_name") or "Axel")
        self.time_value.config(text=datetime.now().strftime("%H:%M:%S"))
        self.commands_voice_value.config(text="hotword" if state.get("hotword_enabled") else "manual")
        if state.get("conversation_mode"):
            self.commands_mode_value.config(text="conversa")
        elif state.get("dictation_mode"):
            self.commands_mode_value.config(text="ditado")
        else:
            self.commands_mode_value.config(text="comando")
        if not self.media_snapshot:
            self.media_status_value.config(text=f"Ultimo comando: {state.get('last_command') or '--'}")
        self._refresh_media_metadata()
        self._refresh_weather_metadata()
        self._refresh_investment_metadata()

        history_lines = []
        for item in state.get("history", [])[-8:]:
            role = str(item.get("role", "system")).strip().upper()
            label = "VOCE" if role == "USER" else "AXEL" if role == "ASSISTANT" else role
            history_lines.append(f"{label}: {item.get('text', '')}")
        self._set_text_widget(self.history_text, history_lines)

        routines = [f"- {name}" for name in _load_routine_names()] or ["- Nenhuma rotina salva ainda."]
        macros = [f"- {name}" for name in _load_macro_names()] or ["- Nenhuma macro salva ainda."]
        todos = _load_auto_advances() or _load_todo_lines() or ["- [ ] Sem proximos avancos anotados."]
        console_lines = _load_codex_channel_lines(limit=4)
        outbox_lines = _load_codex_outbox_lines(limit=3)
        if outbox_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(outbox_lines)
        inbox_lines = _load_codex_inbox_lines(limit=3)
        if inbox_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(inbox_lines)
        bridge_lines = _load_codex_bridge_lines(limit=3)
        if bridge_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(bridge_lines)
        bottleneck_lines = _load_bottleneck_lines(limit=3)
        patch_lines = _load_patch_proposal_lines(limit=2)
        action_lines = _load_action_candidate_lines(limit=3)
        execution_lines = _load_execution_package_lines(limit=3)
        handoff_lines = _load_implementation_handoff_lines(limit=3)
        application_lines = _load_handoff_application_lines(limit=3)
        handoff_validation_lines = _load_handoff_validation_lines(limit=3)
        handoff_retry_lines = _load_handoff_retry_lines(limit=3)
        implementation_request_lines = _load_codex_implementation_request_lines(limit=3)
        approval_lines = _load_approval_lines(limit=3)
        verification_lines = _load_verification_lines(limit=4)
        evolution_lines = _load_self_evolution_lines(limit=4)
        if bottleneck_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(bottleneck_lines)
        if patch_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(patch_lines)
        if action_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(action_lines)
        if execution_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(execution_lines)
        if handoff_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(handoff_lines)
        if application_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(application_lines)
        if handoff_validation_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(handoff_validation_lines)
        if handoff_retry_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(handoff_retry_lines)
        if implementation_request_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(implementation_request_lines)
        if approval_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(approval_lines)
        if verification_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(verification_lines)
        if evolution_lines:
            if console_lines:
                console_lines.append("")
            console_lines.extend(evolution_lines)
        if not console_lines:
            console_lines = [
                f"Conversa: {'ativa' if state.get('conversation_mode') else 'off'}",
                f"Ditado: {'ativo' if state.get('dictation_mode') else 'off'}",
                f"Hotword: {'ativo' if state.get('hotword_enabled') else 'manual'}",
                "",
                "Use o campo de texto acima para enviar comandos.",
            ]
        profile_lines = _load_profile_summary()
        operational_lines = _load_operational_context_lines(limit=4)
        if operational_lines:
            profile_lines.extend([""] + operational_lines)

        self._set_text_widget(self.routines_value, routines)
        self._set_text_widget(self.macros_value, macros)
        self._set_text_widget(self.todo_value, todos)
        self._set_text_widget(self.console_text, console_lines)
        self._set_text_widget(self.profile_text, profile_lines)

        self._draw_core(state)
        self.root.after(240, self._refresh_state)

    def _animate(self):
        state = self.last_state or {}
        speed = 1.0
        if state.get("status") in {"RESPOSTA", "CONVERSA"}:
            speed = 1.9
        elif state.get("status") == "DITADO":
            speed = 1.45

        self.angle += 0.06 * speed
        self.scan_offset = (self.scan_offset + max(1, int(speed * 2))) % 240
        if self.last_state:
            self._draw_core(self.last_state)
        if not self.media_art_url:
            self._draw_album_placeholder()
        self.root.after(38, self._animate)

    def close(self):
        try:
            update_ui_state({"visible": False})
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    AssistantHud().run()


if __name__ == "__main__":
    main()

