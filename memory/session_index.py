from __future__ import annotations

import sqlite3
import time
from datetime import datetime
from pathlib import Path

SESSION_INDEX_PATH = Path("memory/session_index.sqlite3")
SESSION_ID = datetime.now().strftime("%Y%m%d-%H%M%S")


def _connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or SESSION_INDEX_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_session_index(path: Path | None = None) -> None:
    conn = _connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS session_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS session_turns_fts
            USING fts5(text, role UNINDEXED, source UNINDEXED, turn_id UNINDEXED)
            """
        )
        conn.commit()
    finally:
        conn.close()


def index_turn(
    role: str,
    text: str,
    *,
    source: str = "conversation",
    session_id: str | None = None,
    path: Path | None = None,
) -> int | None:
    content = str(text or "").strip()
    if len(content) < 2:
        return None

    init_session_index(path)
    now = time.time()
    conn = _connect(path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO session_turns (session_id, role, text, source, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(session_id or SESSION_ID),
                str(role or "unknown").strip() or "unknown",
                content,
                str(source or "conversation").strip() or "conversation",
                now,
            ),
        )
        turn_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO session_turns_fts (text, role, source, turn_id)
            VALUES (?, ?, ?, ?)
            """,
            (content, str(role or "unknown").strip() or "unknown", str(source or "conversation").strip() or "conversation", turn_id),
        )
        conn.commit()
        return turn_id
    finally:
        conn.close()


def index_exchange(
    user_text: str,
    assistant_text: str,
    *,
    source: str = "conversation",
    session_id: str | None = None,
    path: Path | None = None,
) -> None:
    sid = session_id or SESSION_ID
    index_turn("Usuario", user_text, source=source, session_id=sid, path=path)
    index_turn("Axel", assistant_text, source=source, session_id=sid, path=path)


def _fts_query(query: str) -> str:
    terms = []
    for token in str(query or "").replace('"', " ").split():
        token = token.strip(".,;:!?()[]{}")
        if len(token) >= 3:
            terms.append(f'"{token}"')
    return " OR ".join(terms)


def search_session_turns(query: str, limit: int = 5, *, path: Path | None = None) -> list[dict]:
    fts_query = _fts_query(query)
    if not fts_query:
        return []

    init_session_index(path)
    conn = _connect(path)
    try:
        rows = conn.execute(
            """
            SELECT
                t.id,
                t.session_id,
                t.role,
                t.text,
                t.source,
                t.created_at,
                bm25(session_turns_fts) AS rank
            FROM session_turns_fts
            JOIN session_turns t ON t.id = session_turns_fts.turn_id
            WHERE session_turns_fts MATCH ?
            ORDER BY rank, t.created_at DESC
            LIMIT ?
            """,
            (fts_query, max(1, int(limit))),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": int(row["id"]),
            "session_id": str(row["session_id"]),
            "role": str(row["role"]),
            "text": str(row["text"]),
            "source": str(row["source"]),
            "created_at": float(row["created_at"]),
            "rank": float(row["rank"]),
        }
        for row in rows
    ]


def format_session_search(query: str, limit: int = 4) -> str:
    matches = search_session_turns(query, limit=limit)
    if not matches:
        return "Nao encontrei conversas antigas sobre isso."

    rows = []
    for item in matches:
        role = str(item.get("role", "")).strip() or "unknown"
        text = str(item.get("text", "")).strip()
        if len(text) > 220:
            text = text[:217].rstrip() + "..."
        rows.append(f"{role}: {text}")
    return "Encontrei isto nas sessoes antigas: " + " | ".join(rows)


def format_relevant_session_memory(query: str, limit: int = 3) -> str:
    matches = search_session_turns(query, limit=limit)
    if not matches:
        return "Nenhuma sessao antiga relevante encontrada."
    rows = []
    for item in matches:
        role = str(item.get("role", "")).strip() or "unknown"
        text = str(item.get("text", "")).strip()
        if len(text) > 180:
            text = text[:177].rstrip() + "..."
        rows.append(f"{role}: {text}")
    return "Sessoes antigas relevantes: " + " | ".join(rows)
