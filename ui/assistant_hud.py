import json
import math
import tkinter as tk
from datetime import datetime
from pathlib import Path

from memory.ui_commands import enqueue_ui_command
from memory.ui_state import load_ui_state, update_ui_state


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
CODEX_IMPLEMENTATION_REQUEST_PATH = MEMORY_DIR / "codex_implementation_request.json"
APPROVAL_GATE_PATH = MEMORY_DIR / "approval_gate.json"
VERIFICATION_RUNS_PATH = MEMORY_DIR / "verification_runs.json"
CODEX_BRIDGE_PATH = MEMORY_DIR / "codex_bridge.json"
CODEX_CHANNEL_PATH = MEMORY_DIR / "codex_channel.json"
CODEX_OUTBOX_PATH = MEMORY_DIR / "codex_outbox.json"
CODEX_INBOX_PATH = MEMORY_DIR / "codex_inbox.json"
SELF_EVOLUTION_PATH = MEMORY_DIR / "self_evolution.json"
BOTTLENECKS_PATH = MEMORY_DIR / "bottlenecks.json"

BG = "#02070d"
BG_ALT = "#040c14"
PANEL = "#050d16"
PANEL_ALT = "#07111b"
CARD = "#08121c"
CARD_ALT = "#0c1a27"
ACCENT = "#62f5ff"
ACCENT_2 = "#63f7c8"
ACCENT_3 = "#89ffcf"
ACCENT_WARN = "#62f5ff"
TEXT = "#ddf6ff"
TEXT_SOFT = "#98bccd"
TEXT_DIM = "#688997"
GRID = "#173647"
GOOD = "#60ffb9"
BUSY = "#ffb86a"
RESPOND = "#ffd66f"
ALERT = "#ff7b97"


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
        self.root.title("Axel / Command Deck")
        self.root.geometry("1420x860+50+32")
        self.root.minsize(1220, 760)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.angle = 0.0
        self.scan_offset = 0
        self.last_state = {}
        self.quick_buttons = []

        self._build_layout()
        self._refresh_state()
        self._animate()

    def _build_layout(self):
        self.root.grid_columnconfigure(0, weight=12)
        self.root.grid_columnconfigure(1, weight=10)
        self.root.grid_rowconfigure(0, weight=1)

        self.left = tk.Frame(self.root, bg=PANEL, highlightthickness=1, highlightbackground=GRID)
        self.right = tk.Frame(self.root, bg=PANEL_ALT, highlightthickness=1, highlightbackground=GRID)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(14, 7), pady=14)
        self.right.grid(row=0, column=1, sticky="nsew", padx=(7, 14), pady=14)

        self._build_left_panel()
        self._build_right_panel()

    def _build_left_panel(self):
        header = tk.Frame(self.left, bg=PANEL)
        header.pack(fill="x", padx=18, pady=(18, 10))

        tk.Label(
            header,
            text="AXEL / CORE DECK",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI Semibold", 20),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Escuta, resposta, leitura de contexto e pulso operacional.",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        self.canvas = tk.Canvas(self.left, bg=PANEL, highlightthickness=0, height=270)
        self.canvas.pack(fill="x", padx=18, pady=(8, 10))

        status_row = tk.Frame(self.left, bg=PANEL)
        status_row.pack(fill="x", padx=18, pady=(0, 6))
        status_row.grid_columnconfigure(0, weight=1)
        status_row.grid_columnconfigure(1, weight=1)
        status_row.grid_columnconfigure(2, weight=1)
        self.status_value = self._metric_card(status_row, 0, 0, "STATUS")
        self.mode_value = self._metric_card(status_row, 0, 1, "MODO")
        self.activity_value = self._metric_card(status_row, 0, 2, "ATIVIDADE")

        signal_row = tk.Frame(self.left, bg=PANEL)
        signal_row.pack(fill="x", padx=18, pady=(0, 10))
        signal_row.grid_columnconfigure(0, weight=1)
        signal_row.grid_columnconfigure(1, weight=1)
        signal_row.grid_columnconfigure(2, weight=1)
        self.channel_value = self._metric_card(signal_row, 0, 0, "CANAL")
        self.hotword_value = self._metric_card(signal_row, 0, 1, "ESCUTA")
        self.signal_value = self._metric_card(signal_row, 0, 2, "SINAL")

        self.heard_value = self._text_block(self.left, "ULTIMA FALA", PANEL, wrap=650, height=70)
        self.response_value = self._text_block(self.left, "ULTIMA RESPOSTA", PANEL, wrap=650, height=92)

        lower_grid = tk.Frame(self.left, bg=PANEL)
        lower_grid.pack(fill="both", expand=True, padx=18, pady=(6, 18))
        lower_grid.grid_columnconfigure(0, weight=1)
        lower_grid.grid_columnconfigure(1, weight=1)
        lower_grid.grid_rowconfigure(0, weight=1)

        self.history_text = self._panel_list(lower_grid, 0, 0, "HISTORICO")
        self.profile_text = self._panel_list(lower_grid, 0, 1, "OPERADOR")

    def _build_right_panel(self):
        header = tk.Frame(self.right, bg=PANEL_ALT)
        header.pack(fill="x", padx=18, pady=(18, 10))

        tk.Label(
            header,
            text="AUXILIAR / INTEL CONSOLE",
            bg=PANEL_ALT,
            fg=ACCENT_WARN,
            font=("Segoe UI Semibold", 20),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Texto, atalhos, rotinas e proximos avancos do projeto.",
            bg=PANEL_ALT,
            fg=TEXT_DIM,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        top_grid = tk.Frame(self.right, bg=PANEL_ALT)
        top_grid.pack(fill="x", padx=18, pady=(12, 8))
        top_grid.grid_columnconfigure(0, weight=1)
        top_grid.grid_columnconfigure(1, weight=1)
        top_grid.grid_columnconfigure(2, weight=1)

        self.time_value = self._metric_card(top_grid, 0, 0, "HORARIO", panel=PANEL_ALT)
        self.mic_value = self._metric_card(top_grid, 0, 1, "MICROFONE", panel=PANEL_ALT)
        self.profile_value = self._metric_card(top_grid, 0, 2, "PERFIL", panel=PANEL_ALT)
        self.style_value = self._metric_card(top_grid, 1, 0, "ESTILO", panel=PANEL_ALT)
        self.command_value = self._metric_card(top_grid, 1, 1, "ULTIMO COMANDO", panel=PANEL_ALT)
        self.name_value = self._metric_card(top_grid, 1, 2, "ASSISTENTE", panel=PANEL_ALT)

        composer = tk.Frame(self.right, bg=PANEL_ALT)
        composer.pack(fill="x", padx=18, pady=(4, 10))
        tk.Label(
            composer,
            text="MODO TEXTO / PAINEL",
            bg=PANEL_ALT,
            fg=TEXT_DIM,
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w")

        entry_row = tk.Frame(composer, bg=PANEL_ALT)
        entry_row.pack(fill="x", pady=(8, 0))
        self.text_entry = tk.Entry(
            entry_row,
            bg=CARD,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.text_entry.pack(side="left", fill="x", expand=True, ipady=10)
        self.text_entry.bind("<Return>", self._submit_text_command)

        send_button = tk.Button(
            entry_row,
            text="ENVIAR",
            command=self._submit_text_command,
            bg=ACCENT_2,
            fg="#031018",
            activebackground=ACCENT,
            activeforeground="#031018",
            relief="flat",
            font=("Segoe UI Semibold", 10),
            padx=16,
        )
        send_button.pack(side="left", padx=(10, 0))

        shortcuts = tk.Frame(self.right, bg=PANEL_ALT)
        shortcuts.pack(fill="x", padx=18, pady=(2, 10))
        tk.Label(
            shortcuts,
            text="ATALHOS RAPIDOS",
            bg=PANEL_ALT,
            fg=TEXT_DIM,
            font=("Segoe UI Semibold", 9),
        ).pack(anchor="w")

        buttons_wrap = tk.Frame(shortcuts, bg=PANEL_ALT)
        buttons_wrap.pack(fill="x", pady=(8, 0))
        for label, command in [
            ("Tela", "o que tem na tela"),
            ("Detalha", "detalha"),
            ("Resuma", "resuma a tela"),
            ("Ditado", "modo ditado"),
            ("Chrome", "abre o chrome"),
            ("Spotify", "abre o spotify"),
        ]:
            button = tk.Button(
                buttons_wrap,
                text=label,
                command=lambda cmd=command: self._queue_command(cmd),
                bg=CARD_ALT,
                fg=TEXT,
                activebackground=ACCENT_2,
                activeforeground="#031018",
                relief="flat",
                font=("Segoe UI", 10),
                padx=10,
                pady=8,
            )
            button.pack(side="left", padx=(0, 8))
            self.quick_buttons.append(button)

        lower_grid = tk.Frame(self.right, bg=PANEL_ALT)
        lower_grid.pack(fill="both", expand=True, padx=18, pady=(4, 18))
        lower_grid.grid_columnconfigure(0, weight=1)
        lower_grid.grid_columnconfigure(1, weight=1)
        lower_grid.grid_rowconfigure(0, weight=1)
        lower_grid.grid_rowconfigure(1, weight=1)

        self.routines_value = self._panel_list(lower_grid, 0, 0, "ROTINAS")
        self.macros_value = self._panel_list(lower_grid, 0, 1, "MACROS")
        self.todo_value = self._panel_list(lower_grid, 1, 0, "PROXIMOS AVANCOS")
        self.console_text = self._panel_list(lower_grid, 1, 1, "PONTE CODEx")

    def _metric_card(self, parent, row, column, title, panel=None):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=GRID)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6, ipadx=8, ipady=8)
        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x", pady=(0, 2))
        tk.Label(top, text=title, bg=CARD, fg=TEXT_DIM, font=("Segoe UI Semibold", 8)).pack(side="left", anchor="w")
        deco = tk.Canvas(top, width=64, height=10, bg=CARD, highlightthickness=0)
        deco.pack(side="right")
        deco.create_line(0, 5, 48, 5, fill=GRID, width=1)
        deco.create_line(48, 5, 60, 5, fill=ACCENT_2, width=2)
        deco.create_oval(60, 3, 64, 7, fill=ACCENT, outline="")
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
        value.pack(anchor="w", pady=(6, 0))
        return value

    def _text_block(self, parent, title, panel_bg, wrap=500, height=70):
        box = tk.Frame(parent, bg=panel_bg)
        box.pack(fill="x", padx=18, pady=(0, 10))
        title_row = tk.Frame(box, bg=panel_bg)
        title_row.pack(fill="x")
        tk.Label(
            title_row,
            text=title,
            bg=panel_bg,
            fg=TEXT_DIM,
            font=("Segoe UI Semibold", 9),
        ).pack(side="left", anchor="w")
        title_canvas = tk.Canvas(title_row, width=90, height=10, bg=panel_bg, highlightthickness=0)
        title_canvas.pack(side="right")
        title_canvas.create_line(0, 5, 62, 5, fill=GRID)
        title_canvas.create_line(62, 5, 82, 5, fill=ACCENT_2, width=2)
        title_canvas.create_oval(82, 3, 88, 9, fill=ACCENT, outline="")
        body = tk.Label(
            box,
            text="--",
            justify="left",
            anchor="nw",
            bg=CARD,
            fg=TEXT,
            wraplength=wrap,
            font=("Segoe UI", 11),
            padx=12,
            pady=10,
            height=max(2, height // 26),
        )
        body.pack(anchor="w", fill="x", pady=(8, 0))
        return body

    def _panel_list(self, parent, row, column, title):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=GRID)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        header = tk.Frame(card, bg=CARD)
        header.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(
            header,
            text=title,
            bg=CARD,
            fg=TEXT_DIM,
            font=("Segoe UI Semibold", 9),
        ).pack(side="left", anchor="w")
        deco = tk.Canvas(header, width=84, height=10, bg=CARD, highlightthickness=0)
        deco.pack(side="right")
        deco.create_line(0, 5, 58, 5, fill=GRID)
        deco.create_line(58, 5, 78, 5, fill=ACCENT_2, width=2)
        deco.create_oval(78, 2, 84, 8, fill=ACCENT, outline="")

        text = tk.Text(
            card,
            bg=CARD,
            fg=TEXT,
            relief="flat",
            wrap="word",
            font=("Consolas", 9),
            height=8,
            padx=12,
            pady=6,
        )
        text.pack(fill="both", expand=True, padx=0, pady=(0, 8))
        text.configure(state="disabled")
        return text

    def _status_palette(self, status: str) -> tuple[str, str]:
        status = str(status or "").upper()
        if status in {"RESPOSTA", "CONVERSA"}:
            return RESPOND, BUSY
        if status in {"COMANDO", "ATIVA"}:
            return ACCENT, ACCENT_3
        if status == "DITADO":
            return GOOD, ACCENT
        if status == "PAUSADA":
            return ALERT, BUSY
        return ACCENT_2, ACCENT

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

    def _draw_core(self, state):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 500)
        height = max(self.canvas.winfo_height(), 240)

        primary, secondary = self._status_palette(state.get("status", ""))
        speed = 1.0
        if state.get("status") in {"RESPOSTA", "CONVERSA"}:
            speed = 1.6
        elif state.get("status") == "DITADO":
            speed = 1.3

        for x in range(0, width, 26):
            self.canvas.create_line(x, 0, x, height, fill="#0d2737")
        for y in range(self.scan_offset, height, 18):
            self.canvas.create_line(0, y, width, y, fill="#102b39")

        cx = 156
        cy = height // 2
        pulse = 8 * math.sin(self.angle * speed)
        outer = 96 + pulse
        mid = 70 + pulse * 0.5
        inner = 48 + pulse * 0.2

        self.canvas.create_oval(cx - outer, cy - outer, cx + outer, cy + outer, outline="#123849", width=2)
        self.canvas.create_oval(cx - mid, cy - mid, cx + mid, cy + mid, outline=secondary, width=3)
        self.canvas.create_oval(cx - inner, cy - inner, cx + inner, cy + inner, fill="#092430", outline=primary, width=2)

        for radius, step, color, size in (
            (116, 16, primary, 6),
            (88, 22, secondary, 5),
            (62, 26, primary, 4),
        ):
            for tick in range(0, 360, step):
                rad = math.radians(tick + self.angle * 8)
                x1 = cx + math.cos(rad) * radius
                y1 = cy + math.sin(rad) * radius
                x2 = cx + math.cos(rad) * (radius + size)
                y2 = cy + math.sin(rad) * (radius + size)
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=1)

        self.canvas.create_arc(
            cx - 108,
            cy - 108,
            cx + 108,
            cy + 108,
            start=18 + self.angle * 12,
            extent=120 + int((math.sin(self.angle * speed * 1.5) + 1) * 80),
            style="arc",
            outline=primary,
            width=4,
        )
        self.canvas.create_arc(
            cx - 84,
            cy - 84,
            cx + 84,
            cy + 84,
            start=210 - self.angle * 15,
            extent=95 + int((math.cos(self.angle * speed * 1.2) + 1) * 65),
            style="arc",
            outline=secondary,
            width=3,
        )
        self.canvas.create_arc(
            cx - 118,
            cy - 118,
            cx + 118,
            cy + 118,
            start=110 - self.angle * 10,
            extent=44,
            style="arc",
            outline=secondary,
            width=5,
        )
        self.canvas.create_arc(
            cx - 72,
            cy - 72,
            cx + 72,
            cy + 72,
            start=300 + self.angle * 12,
            extent=56,
            style="arc",
            outline=primary,
            width=4,
        )

        for i in range(8):
            orbit_angle = self.angle * speed * 0.8 + i * 0.75
            dot_x = cx + math.cos(orbit_angle) * (116 + (i % 2) * 8)
            dot_y = cy + math.sin(orbit_angle) * (116 + (i % 2) * 8)
            self.canvas.create_oval(dot_x - 2, dot_y - 2, dot_x + 2, dot_y + 2, fill=secondary, outline="")

        status = str(state.get("status", "INATIVO")).upper()
        mode = str(state.get("mode", "comando")).upper()
        self.canvas.create_text(cx, cy - 10, text=status, fill=TEXT, font=("Segoe UI Semibold", 17))
        self.canvas.create_text(cx, cy + 18, text=mode, fill=TEXT_SOFT, font=("Segoe UI", 10))

        info_x = 330
        self.canvas.create_text(info_x, 38, text="AXEL / ONLINE", fill=primary, anchor="w", font=("Segoe UI Semibold", 13))
        self.canvas.create_text(info_x, 68, text=f"Escuta: {state.get('status', '--')}", fill=TEXT, anchor="w", font=("Segoe UI", 11))
        self.canvas.create_text(info_x, 92, text=f"Modo: {state.get('mode', '--')}", fill=TEXT, anchor="w", font=("Segoe UI", 11))
        self.canvas.create_text(info_x, 116, text=f"Microfone: {str(state.get('microphone', '--'))[:38]}", fill=TEXT, anchor="w", font=("Segoe UI", 11))
        self.canvas.create_text(info_x, 140, text=f"Perfil: {state.get('voice_profile', '--')}", fill=TEXT, anchor="w", font=("Segoe UI", 11))
        self.canvas.create_text(info_x, 164, text=f"Estilo: {state.get('assistant_style', '--')}", fill=TEXT, anchor="w", font=("Segoe UI", 11))

        self.canvas.create_rectangle(info_x, 190, info_x + 168, 206, outline=GRID, width=1)
        level = 0.25
        if state.get("status") in {"ATIVA", "COMANDO"}:
            level = 0.62 + 0.12 * math.sin(self.angle * speed * 2.5)
        elif state.get("status") in {"RESPOSTA", "CONVERSA"}:
            level = 0.84 + 0.08 * math.sin(self.angle * speed * 3.0)
        elif state.get("status") == "DITADO":
            level = 0.75 + 0.10 * math.sin(self.angle * speed * 2.2)
        fill_width = int(164 * max(0.08, min(0.98, level)))
        self.canvas.create_rectangle(info_x + 2, 192, info_x + 2 + fill_width, 204, fill=secondary, outline="")
        self.canvas.create_text(info_x, 216, text="CANAL DE ATIVIDADE", fill=TEXT_DIM, anchor="w", font=("Segoe UI", 9))

        for i in range(5):
            y = 44 + i * 22
            self.canvas.create_line(width - 86, y, width - 22, y, fill=GRID)
            self.canvas.create_line(width - 86, y + 8, width - 34, y + 8, fill=primary if i % 2 == 0 else secondary)

        meter_x = width - 170
        meter_bottom = height - 30
        for i in range(10):
            base = 16 + i * 1.2
            bar_height = base + (math.sin(self.angle * speed * 2.2 + i * 0.52) + 1) * 24
            x0 = meter_x + i * 13
            color = primary if i % 2 == 0 else secondary
            self.canvas.create_rectangle(x0, meter_bottom - bar_height, x0 + 8, meter_bottom, fill=color, outline="")
        self.canvas.create_text(meter_x, meter_bottom + 10, text="PULSO DE ATIVIDADE", fill=TEXT_DIM, anchor="w", font=("Segoe UI", 9))

    def _set_text_widget(self, widget, lines: list[str]):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", "\n".join(lines) if lines else "--")
        widget.configure(state="disabled")

    def _queue_command(self, command: str):
        enqueue_ui_command(command)
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
        self.scan_offset = (self.scan_offset + max(1, int(speed * 2))) % 18
        if self.last_state:
            self._draw_core(self.last_state)
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
