from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
import unicodedata

from memory.supabase_sync import sync_memory_state_safely


TRAINING_PATH = Path("memory/training.json")
TARGET_DAYS = 170

MUSCLE_NAMES = {
    "chest": "peito",
    "back": "costas",
    "shoulders": "ombros",
    "biceps": "bíceps",
    "triceps": "tríceps",
    "forearms": "antebraço",
    "core": "core",
    "quads": "quadríceps",
    "hamstrings": "posterior",
    "calves": "panturrilha",
    "glutes": "glúteos",
}

MUSCLE_ALIASES = {
    "braco": ["biceps", "triceps", "forearms"],
    "bracos": ["biceps", "triceps", "forearms"],
    "biceps": ["biceps"],
    "triceps": ["triceps"],
    "cotovelo": ["biceps", "triceps"],
    "antebraco": ["forearms"],
    "antebracos": ["forearms"],
    "punho": ["forearms"],
    "punhos": ["forearms"],
    "pegada": ["forearms"],
    "costas": "back",
    "dorsal": "back",
    "lombar": "back",
    "peito": "chest",
    "ombro": "shoulders",
    "ombros": "shoulders",
    "deltoide": "shoulders",
    "deltoides": "shoulders",
    "abdomen": "core",
    "abdomem": "core",
    "core": "core",
    "barriga": "core",
    "perna": ["quads", "hamstrings", "calves", "glutes"],
    "pernas": ["quads", "hamstrings", "calves", "glutes"],
    "quadriceps": ["quads"],
    "coxa": ["quads", "hamstrings"],
    "posterior": ["hamstrings"],
    "posteriores": ["hamstrings"],
    "isquiotibiais": ["hamstrings"],
    "panturrilha": ["calves"],
    "panturrilhas": ["calves"],
    "gluteo": ["glutes"],
    "gluteos": ["glutes"],
    "quadril": ["glutes"],
    "joelho": ["quads", "hamstrings"],
}

LEGACY_MUSCLE_GROUPS = {
    "arms": ["biceps", "triceps", "forearms"],
    "legs": ["quads", "hamstrings", "calves", "glutes"],
}

WEEKLY_PLAN = [
    {
        "day": 1,
        "label": "Segunda",
        "title": "Costas + Bíceps + Core",
        "focus": "Barra assistida, remadas, pegada e core com controle.",
        "muscles": ["back", "biceps", "forearms", "core"],
        "warmup": [
            ["Mobilidade de ombro", "2 minutos"],
            ["Scapular pull-up na barra", "2x8"],
            ["Alongamento dinâmico", "costas e braços"],
        ],
        "exercises": [
            ["Pull-up assistido com superband", "4 séries de 4 a 8 repetições"],
            ["Chin-up assistido com superband", "3 séries de 4 a 8 repetições; pega mais bíceps"],
            ["Australian pull-up", "3 séries de 8 a 12 usando barra baixa, paraletes ou adaptação segura"],
            ["Remada com superband", "3 séries de 12 a 15"],
            ["Hollow Body Hold", "4 séries de 15 a 30 segundos"],
            ["Dead Hang na barra", "3 séries de 15 a 30 segundos"],
        ],
    },
    {
        "day": 2,
        "label": "Terça",
        "title": "Empurrar + L-sit",
        "focus": "Flexões, dips, pike push-up, L-sit e punhos sem forçar.",
        "muscles": ["chest", "shoulders", "triceps", "core"],
        "warmup": [
            ["Rotação de punhos", "1 minuto"],
            ["Flexão inclinada leve", "2x10"],
            ["Elevação escapular nas paraletes", "2x8"],
        ],
        "exercises": [
            ["Flexão normal", "4 séries de 8 a 15"],
            ["Dips nas paraletes baixas", "3 séries de 6 a 10; se ficar difícil, pés apoiados no chão"],
            ["Flexão nas paraletes", "3 séries de 8 a 12 com maior amplitude e controle"],
            ["Pike Push-up", "3 séries de 5 a 10"],
            ["L-sit tuck nas paraletes", "5 séries de 8 a 20 segundos"],
            ["Planche lean leve", "3 séries de 10 a 20 segundos; sem forçar demais o punho"],
        ],
    },
    {
        "day": 3,
        "label": "Quarta",
        "title": "Descanso",
        "focus": "Recuperação ativa leve, sem treino pesado.",
        "muscles": [],
        "warmup": [],
        "exercises": [
            ["Caminhada leve", "opcional"],
            ["Alongamento", "ombro, costas e quadril"],
            ["Mobilidade de punho", "leve, sem carga"],
            ["Nada pesado", "dia para recuperar"],
        ],
    },
    {
        "day": 4,
        "label": "Quinta",
        "title": "Pernas + Abdômen",
        "focus": "Búlgaro, agachamento com superband, panturrilha e abdômen.",
        "muscles": ["quads", "hamstrings", "calves", "glutes", "core"],
        "warmup": [
            ["Agachamento livre", "2x15"],
            ["Mobilidade de quadril", "2 minutos"],
            ["Elevação de panturrilha leve", "1x20"],
        ],
        "exercises": [
            ["Agachamento Búlgaro", "4 séries de 8 a 12 cada perna"],
            ["Agachamento com superband", "3 séries de 12 a 15"],
            ["Avanço/lunge", "3 séries de 10 cada perna"],
            ["Elevação de panturrilha", "5 séries de 15 a 25"],
            ["Leg Raise na barra ou no chão", "4 séries de 8 a 12"],
            ["Prancha", "3 séries de 30 a 60 segundos"],
        ],
    },
    {
        "day": 5,
        "label": "Sexta",
        "title": "Costas + Braços + Pegada",
        "focus": "Dia técnico, mais leve que segunda, com bíceps, postura e pegada.",
        "muscles": ["back", "biceps", "forearms", "shoulders"],
        "warmup": [],
        "exercises": [
            ["Chin-up assistido com superband", "4 séries de 4 a 8"],
            ["Australian pull-up pegada supinada", "4 séries de 8 a 12"],
            ["Rosca bíceps com superband", "3 séries de 12 a 15"],
            ["Face pull com superband", "3 séries de 12 a 15; bom para postura e ombro"],
            ["Dead Hang", "3 séries de 20 a 40 segundos"],
            ["Hand Grip", "3 séries de 10 a 20 cada mão ou segurando fechado por 10 a 20 segundos"],
        ],
    },
    {
        "day": 6,
        "label": "Sábado",
        "title": "Skill + Ombro + Core",
        "focus": "Dia de calistenia skill sem destruir o corpo.",
        "muscles": ["shoulders", "triceps", "forearms", "core"],
        "warmup": [],
        "exercises": [
            ["Frog Stand", "5 tentativas de 10 a 20 segundos"],
            ["Handstand na parede", "4 séries de 20 a 40 segundos; se estiver voltando agora, faça com calma"],
            ["Pike Push-up", "4 séries de 5 a 10"],
            ["Shoulder taps em prancha", "3 séries de 10 a 20 toques"],
            ["Tuck L-sit nas paraletes", "4 séries de 8 a 20 segundos"],
            ["Hollow Body Hold", "3 séries de 20 a 30 segundos"],
            ["Prancha lateral", "3 séries de 20 a 40 segundos cada lado"],
        ],
    },
    {
        "day": 7,
        "label": "Domingo",
        "title": "Descanso total",
        "focus": "Sem treino. Só recuperação.",
        "muscles": [],
        "warmup": [],
        "exercises": [["Recuperação total", "sono, hidratação e descanso"]],
    },
]

PROGRESSION_GUIDE = [
    ["Semanas 1 e 2", "treine com calma e deixe 2 a 3 repetições sobrando em cada série"],
    ["Semanas 3 e 4", "aumente 1 ou 2 repetições, 5 a 10 segundos nas isometrias ou reduza a ajuda da superband"],
    ["Depois de 1 mês", "foque em barra fixa, L-sit, handstand, dips fortes ou front lever básico"],
]

DEFAULT_STATE = {
    "completed": [],
    "skipped": [],
    "injuries": {},
    "levels": {},
    "reminder": {"enabled": True, "time": "19:00", "last_notified_date": ""},
}


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def load_training_state() -> dict:
    data = _load_json(TRAINING_PATH)
    state = dict(DEFAULT_STATE)
    state.update(data)
    for key in ("completed", "skipped"):
        if not isinstance(state.get(key), list):
            state[key] = []
    for key in ("injuries", "levels", "reminder"):
        if not isinstance(state.get(key), dict):
            state[key] = dict(DEFAULT_STATE[key])
    reminder = dict(DEFAULT_STATE["reminder"])
    reminder.update(state.get("reminder") or {})
    state["reminder"] = reminder
    return state


def save_training_state(state: dict) -> dict:
    payload = load_training_state()
    payload.update(state or {})
    _save_json(TRAINING_PATH, payload)
    sync_memory_state_safely("training", payload, category="health")
    return payload


def _today(now: datetime | None = None) -> datetime:
    return now or datetime.now()


def _date_key(now: datetime | None = None) -> str:
    return _today(now).date().isoformat()


def workout_for_date(now: datetime | None = None) -> dict:
    date = _today(now)
    monday_based = date.weekday()
    return WEEKLY_PLAN[monday_based]


def workout_by_weekday_text(text: str) -> dict | None:
    workouts = workouts_by_weekday_text(text)
    return workouts[0] if workouts else None


def workouts_by_weekday_text(text: str) -> list[dict]:
    raw = _strip_accents(text).lower()
    weekdays = {
        "segunda": 0,
        "terca": 1,
        "quarta": 2,
        "quinta": 3,
        "sexta": 4,
        "sabado": 5,
        "domingo": 6,
    }
    found = []
    for label, index in weekdays.items():
        if re.search(rf"\b(?:treino\s+d[aeo]\s+|treino\s+de\s+|da\s+|de\s+)?{label}\b", raw):
            found.append(WEEKLY_PLAN[index])
    return found


def _remove_workout_reference(text: str, workout: dict) -> str:
    raw = str(text or "")
    label = _strip_accents(str(workout.get("label", ""))).lower()
    variants = {label}
    if label == "terca":
        variants.add("terça")
    if label == "sabado":
        variants.add("sábado")
    cleaned = raw
    for variant in variants:
        cleaned = re.sub(rf"\btreino\s+d[aeo]\s+{variant}\b", " ", cleaned, flags=re.I)
        cleaned = re.sub(rf"\btreino\s+de\s+{variant}\b", " ", cleaned, flags=re.I)
    return cleaned


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or ""))
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def parse_training_datetime(text: str, now: datetime | None = None) -> datetime:
    base = _today(now)
    raw = _strip_accents(text).lower()

    date_match = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", raw)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year_raw = date_match.group(3)
        year = int(year_raw) if year_raw else base.year
        if year < 100:
            year += 2000
        try:
            return base.replace(year=year, month=month, day=day)
        except ValueError:
            return base

    if re.search(r"\banteontem\b", raw):
        return base - timedelta(days=2)
    if re.search(r"\bontem\b", raw):
        return base - timedelta(days=1)
    if re.search(r"\bhoje\b", raw):
        return base

    weekdays = {
        "segunda": 0,
        "terca": 1,
        "terça": 1,
        "quarta": 2,
        "quinta": 3,
        "sexta": 4,
        "sabado": 5,
        "sábado": 5,
        "domingo": 6,
    }
    for label, weekday in weekdays.items():
        if re.search(rf"\b{label}\b", raw):
            diff = (base.weekday() - weekday) % 7
            if diff == 0 and re.search(r"\bpassad[ao]\b", raw):
                diff = 7
            return base - timedelta(days=diff)

    return base


def _active_injuries(state: dict, now: datetime | None = None) -> list[tuple[str, dict]]:
    today = _date_key(now)
    rows = []
    for muscle, injury in (state.get("injuries") or {}).items():
        if not isinstance(injury, dict):
            continue
        created_at = str(injury.get("created_at", "") or "0000-00-00")
        until = str(injury.get("until", ""))
        if created_at <= today <= until:
            rows.append((muscle, injury))
    return rows


def expand_muscles(muscles) -> list[str]:
    expanded = []
    for muscle in muscles or []:
        values = LEGACY_MUSCLE_GROUPS.get(str(muscle), [str(muscle)])
        for value in values:
            if value in MUSCLE_NAMES and value not in expanded:
                expanded.append(value)
    return expanded


def _blocked_muscles(workout: dict, state: dict, now: datetime | None = None) -> list[str]:
    injured = {expanded for muscle, _injury in _active_injuries(state, now) for expanded in expand_muscles([muscle])}
    workout_muscles = expand_muscles(workout.get("muscles", []))
    return [muscle for muscle in workout_muscles if muscle in injured]


def _is_completed(state: dict, date_key: str) -> bool:
    return any(item.get("date") == date_key for item in state.get("completed") or [] if isinstance(item, dict))


def fatigue_by_muscle(state: dict | None = None, now: datetime | None = None) -> dict:
    state = state or load_training_state()
    today = _date_key(now)
    result = {muscle: "sem dados" for muscle in MUSCLE_NAMES}
    for muscle, _injury in _active_injuries(state, now):
        for expanded in expand_muscles([muscle]):
            result[expanded] = "lesionado"

    completed = [item for item in state.get("completed") or [] if isinstance(item, dict)]
    for muscle in MUSCLE_NAMES:
        if result[muscle] == "lesionado":
            continue
        last = next((item for item in reversed(completed) if muscle in expand_muscles(item.get("muscles") or [])), None)
        if not last:
            continue
        try:
            diff = (datetime.fromisoformat(today) - datetime.fromisoformat(str(last.get("date")))).days
        except Exception:
            continue
        if diff <= 0:
            result[muscle] = "fadiga media"
        elif diff == 1:
            result[muscle] = "fadiga leve"
        else:
            result[muscle] = "recuperado"
    return result


def completed_this_year(state: dict | None = None, now: datetime | None = None) -> int:
    state = state or load_training_state()
    year = str(_today(now).year)
    dates = {
        str(item.get("date", ""))
        for item in state.get("completed") or []
        if isinstance(item, dict) and str(item.get("date", "")).startswith(year)
    }
    return len(dates)


def current_streak(state: dict | None = None, now: datetime | None = None) -> int:
    state = state or load_training_state()
    cursor = _today(now).date()
    streak = 0
    for _ in range(365):
        if not _is_completed(state, cursor.isoformat()):
            break
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def training_snapshot(now: datetime | None = None) -> dict:
    state = load_training_state()
    workout = workout_for_date(now)
    blocked = _blocked_muscles(workout, state, now)
    today_key = _date_key(now)
    today_entries = [
        item for item in state.get("completed") or []
        if isinstance(item, dict) and item.get("date") == today_key
    ]
    done = completed_this_year(state, now)
    return {
        "target_days": TARGET_DAYS,
        "completed_this_year": done,
        "remaining": max(0, TARGET_DAYS - done),
        "percent": min(100, round((done / TARGET_DAYS) * 100)),
        "streak": current_streak(state, now),
        "today": _date_key(now),
        "workout": workout,
        "blocked_muscles": blocked,
        "active_injuries": _active_injuries(state, now),
        "fatigue": fatigue_by_muscle(state, now),
        "reminder": state.get("reminder") or {},
        "progression": PROGRESSION_GUIDE,
        "completed_today": bool(today_entries),
        "today_entries": today_entries,
    }


def format_today_workout(now: datetime | None = None) -> str:
    snap = training_snapshot(now)
    workout = snap["workout"]
    blocked = snap["blocked_muscles"]
    status = "concluído" if snap["completed_today"] else "bloqueado" if blocked else "descanso" if not workout["muscles"] else "pronto"
    warmup = "; ".join(f"{name}: {detail}" for name, detail in workout.get("warmup", [])[:3]) or "sem aquecimento obrigatório"
    exercises = "; ".join(f"{name}: {detail}" for name, detail in workout.get("exercises", [])[:6])
    text = f"Hoje é {workout['label']}: {workout['title']}. Status: {status}. {workout['focus']} Aquecimento: {warmup}. Treino: {exercises}."
    if blocked:
        text += " Bloqueado por lesão em: " + ", ".join(MUSCLE_NAMES.get(muscle, muscle) for muscle in blocked) + "."
    return text


def mark_training_completed(now: datetime | None = None, allow_rest_day: bool = False) -> str:
    state = load_training_state()
    workout = workout_for_date(now)
    date_key = _date_key(now)
    if _is_completed(state, date_key):
        return f"O treino de {datetime.fromisoformat(date_key).strftime('%d/%m')} já está marcado como concluído."
    blocked = _blocked_muscles(workout, state, now)
    if blocked:
        return "Não vou marcar nem sugerir esse treino: existe lesão ativa em " + ", ".join(MUSCLE_NAMES.get(m, m) for m in blocked) + "."
    if not workout.get("muscles") and not allow_rest_day:
        return "Esse dia está como descanso no plano. Se você treinou mesmo assim, diga os grupos, por exemplo: treinei braços e costas hoje."

    completed = list(state.get("completed") or [])
    completed.append({
        "date": date_key,
        "plan_day": workout.get("day"),
        "title": workout.get("title"),
        "muscles": expand_muscles(workout.get("muscles") or []),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    state["completed"] = completed
    state["skipped"] = [item for item in state.get("skipped") or [] if item != date_key]
    save_training_state(state)
    done = completed_this_year(state, now)
    return f"Treino de {datetime.fromisoformat(date_key).strftime('%d/%m')} concluído: {workout['title']}. Progresso do ano: {done}/{TARGET_DAYS}."


def mark_planned_training_from_text(text: str, now: datetime | None = None) -> str:
    target = parse_training_datetime(text, now)
    return mark_training_completed(target)


def mark_named_workout_from_text(text: str, now: datetime | None = None) -> str:
    workout = workout_by_weekday_text(text)
    if not workout:
        return "Qual treino do cronograma voce fez? Pode dizer treino de segunda, terca, quinta, sexta ou sabado."

    without_workout_reference = _remove_workout_reference(text, workout)
    has_explicit_performed_date = bool(re.search(
        r"\b(hoje|ontem|anteontem|em|no dia|na segunda|na terca|na terça|na quarta|na quinta|na sexta|no sabado|no sábado|no domingo|\d{1,2}/\d{1,2})\b",
        _strip_accents(without_workout_reference).lower(),
    ))
    if has_explicit_performed_date or any(term in _strip_accents(text).lower() for term in {"fiz", "treinei"}):
        target = parse_training_datetime(without_workout_reference, now)
    else:
        target = parse_training_datetime(str(workout.get("label", "")), now)
    state = load_training_state()
    date_key = _date_key(target)
    blocked = _blocked_muscles(workout, state, target)
    if blocked:
        return "Não vou registrar esse treino: existe lesão ativa em " + ", ".join(MUSCLE_NAMES.get(m, m) for m in blocked) + "."
    if not workout.get("muscles"):
        return f"{workout['label']} e descanso no cronograma. Se treinou algo livre, diga os grupos musculares."

    existing = [
        item for item in state.get("completed") or []
        if isinstance(item, dict) and item.get("date") == date_key
    ]
    existing_signature = {
        (item.get("source", "planned"), item.get("plan_day"))
        for item in existing
    }
    if ("shifted", workout.get("day")) in existing_signature or ("planned", workout.get("day")) in existing_signature:
        return f"Esse treino já está registrado em {datetime.fromisoformat(date_key).strftime('%d/%m')}."

    completed = list(state.get("completed") or [])
    completed.append({
        "date": date_key,
        "plan_day": workout.get("day"),
        "title": workout.get("title"),
        "source": "shifted",
        "scheduled_label": workout.get("label"),
        "muscles": expand_muscles(workout.get("muscles") or []),
        "note": str(text or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    state["completed"] = completed
    state["skipped"] = [item for item in state.get("skipped") or [] if item != date_key]
    save_training_state(state)
    done = completed_this_year(state, now)
    return (
        f"Registrei o treino de {workout['label']} em {datetime.fromisoformat(date_key).strftime('%d/%m')}: "
        f"{workout['title']}. Progresso do ano: {done}/{TARGET_DAYS}."
    )


def mark_named_workouts_from_text(text: str, now: datetime | None = None) -> str:
    workouts = workouts_by_weekday_text(text)
    if len(workouts) <= 1:
        return mark_named_workout_from_text(text, now)

    results = []
    for workout in workouts:
        label = str(workout.get("label", "")).lower()
        command = f"treino de {label}"
        results.append(mark_named_workout_from_text(command, now))
    done = completed_this_year(now=now)
    return " ".join(results) + f" Total atual: {done}/{TARGET_DAYS}."


def parse_muscles(text: str) -> list[str]:
    normalized = re.sub(r"[^a-z0-9\s]", " ", _strip_accents(str(text or "")).lower())
    found = []
    for alias, muscles in MUSCLE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", normalized):
            values = muscles if isinstance(muscles, list) else [muscles]
            for muscle in expand_muscles(values):
                if muscle not in found:
                    found.append(muscle)
    return found


def mark_custom_training_from_text(text: str, now: datetime | None = None) -> str:
    muscles = parse_muscles(text)
    if not muscles:
        return "Quais grupos voce treinou? Pode dizer peito, costas, ombros, bíceps, tríceps, antebraço, core ou pernas."

    state = load_training_state()
    target = parse_training_datetime(text, now)
    workout = workout_for_date(target)
    blocked = [muscle for muscle in muscles if muscle in {item[0] for item in _active_injuries(state, target)}]
    if blocked:
        return "Não vou registrar treino em região lesionada: " + ", ".join(MUSCLE_NAMES.get(m, m) for m in blocked) + "."

    date_key = _date_key(target)
    existing = [
        item for item in state.get("completed") or []
        if isinstance(item, dict) and item.get("date") == date_key
    ]
    existing_muscles = {muscle for item in existing for muscle in expand_muscles(item.get("muscles", []))}
    new_muscles = [muscle for muscle in muscles if muscle not in existing_muscles]
    if not new_muscles:
        return "Esse treino livre ja esta registrado para hoje."

    completed = list(state.get("completed") or [])
    completed.append({
        "date": date_key,
        "plan_day": workout.get("day"),
        "title": "Treino livre",
        "source": "custom",
        "muscles": new_muscles,
        "note": str(text or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    state["completed"] = completed
    state["skipped"] = [item for item in state.get("skipped") or [] if item != date_key]
    save_training_state(state)
    done = completed_this_year(state, now)
    names = ", ".join(MUSCLE_NAMES.get(m, m) for m in new_muscles)
    return f"Registrei treino livre de {names} em {datetime.fromisoformat(date_key).strftime('%d/%m')}. Progresso do ano: {done}/{TARGET_DAYS}."


def skip_today_training(now: datetime | None = None) -> str:
    state = load_training_state()
    date_key = _date_key(now)
    if date_key not in state.get("skipped", []):
        state["skipped"] = list(state.get("skipped") or []) + [date_key]
        save_training_state(state)
    return "Marquei hoje como treino pulado."


def parse_muscle(text: str) -> str:
    muscles = parse_muscles(text)
    return muscles[0] if muscles else ""


def mark_injury_from_text(text: str, now: datetime | None = None) -> str:
    muscles = parse_muscles(text)
    if not muscles:
        return "Onde foi a lesão? Pode dizer bíceps, tríceps, antebraço, costas, peito, ombro, core ou perna."
    match = re.search(r"\b(\d{1,2})\s*(?:dia|dias)\b", str(text or "").lower())
    days = int(match.group(1)) if match else 3
    days = max(1, min(days, 30))
    until = (_today(now).date() + timedelta(days=days)).isoformat()
    state = load_training_state()
    injuries = dict(state.get("injuries") or {})
    for muscle in muscles:
        injuries[muscle] = {"created_at": _date_key(now), "until": until}
    state["injuries"] = injuries
    save_training_state(state)
    names = ", ".join(MUSCLE_NAMES[muscle] for muscle in muscles)
    return f"Marquei lesão em {names} até {datetime.fromisoformat(until).strftime('%d/%m')}. Vou bloquear treinos que usem essa região."


def clear_training_injuries() -> str:
    state = load_training_state()
    state["injuries"] = {}
    save_training_state(state)
    return "Limpei as lesões ativas do treino."


def set_training_reminder_from_text(text: str) -> str:
    match = re.search(r"\b(\d{1,2})(?::|h)?(\d{2})?\b", str(text or ""))
    if not match:
        return "Qual horario devo usar para o lembrete do treino?"
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return "Esse horario nao parece valido."
    state = load_training_state()
    reminder = dict(state.get("reminder") or {})
    reminder.update({"enabled": True, "time": f"{hour:02d}:{minute:02d}"})
    state["reminder"] = reminder
    save_training_state(state)
    return f"Lembrete diario de treino ajustado para {hour:02d}:{minute:02d}."


def consume_due_training_reminder(now: datetime | None = None) -> dict:
    now = _today(now)
    state = load_training_state()
    reminder = dict(state.get("reminder") or {})
    if not reminder.get("enabled"):
        return {}
    date_key = now.date().isoformat()
    if reminder.get("last_notified_date") == date_key:
        return {}
    try:
        hour, minute = [int(part) for part in str(reminder.get("time", "19:00")).split(":", 1)]
    except Exception:
        hour, minute = 19, 0
    if now.time() < now.replace(hour=hour, minute=minute, second=0, microsecond=0).time():
        return {}
    workout = workout_for_date(now)
    reminder["last_notified_date"] = date_key
    state["reminder"] = reminder
    save_training_state(state)
    if not workout.get("muscles"):
        text = f"Hoje é {workout['label']}: descanso. Recuperação também conta."
    else:
        text = f"Hora do treino: {workout['label']}, {workout['title']}. Quando terminar, diga: marcar treino concluído."
    return {"text": text, "workout": workout}


def format_training_status() -> str:
    snap = training_snapshot()
    workout = snap["workout"]
    fatigue = ", ".join(f"{MUSCLE_NAMES[m]}: {status}" for m, status in snap["fatigue"].items())
    injuries = snap["active_injuries"]
    injury_text = "sem lesões ativas"
    if injuries:
        injury_text = "; ".join(f"{MUSCLE_NAMES.get(m, m)} até {item.get('until')}" for m, item in injuries)
    return (
        f"Treino de hoje: {workout['label']}, {workout['title']}. "
        f"Meta anual: {snap['completed_this_year']}/{TARGET_DAYS}, faltam {snap['remaining']}. "
        f"Sequencia atual: {snap['streak']}. Lesoes: {injury_text}. Fadiga: {fatigue}."
    )


def format_muscle_status_from_text(text: str) -> str:
    muscles = parse_muscles(text)
    if not muscles:
        return format_training_status()

    snap = training_snapshot()
    fatigue = snap.get("fatigue") or {}
    injuries = {}
    for injury_muscle, item in snap.get("active_injuries") or []:
        for expanded in expand_muscles([injury_muscle]):
            if expanded in muscles:
                injuries[expanded] = item
    parts = []
    for muscle in muscles:
        name = MUSCLE_NAMES.get(muscle, muscle)
        status = fatigue.get(muscle, "sem dados")
        if muscle in injuries:
            status = f"lesionado até {injuries[muscle].get('until')}"
        parts.append(f"{name}: {status}")
    return "Status muscular: " + "; ".join(parts) + "."
