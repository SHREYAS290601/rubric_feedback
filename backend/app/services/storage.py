from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any
from uuid import UUID

from app.models import FeedbackResponse, RatingRequest, UsageEvent


def _default_db_path() -> Path:
    configured_path = os.getenv("SQLITE_DB_PATH")
    if configured_path:
        return Path(configured_path)
    if os.getenv("VERCEL"):
        return Path("/tmp/feedback_mvp.sqlite3")
    return Path(__file__).resolve().parents[2] / "feedback_mvp.sqlite3"


DB_PATH = _default_db_path()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_sessions (
                session_id TEXT PRIMARY KEY,
                readiness_level TEXT NOT NULL,
                overall_summary TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NULL,
                event_name TEXT NOT NULL,
                properties TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback_ratings (
                rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                usefulness_rating INTEGER NOT NULL,
                comment TEXT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_feedback(response: FeedbackResponse) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO feedback_sessions (session_id, readiness_level, overall_summary)
            VALUES (?, ?, ?)
            """,
            (str(response.session_id), response.readiness_level.value, response.overall_summary),
        )


def save_event(event: UsageEvent) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO usage_events (session_id, event_name, properties)
            VALUES (?, ?, ?)
            """,
            (str(event.session_id) if event.session_id else None, event.event_name, str(event.properties)),
        )


def save_rating(rating: RatingRequest) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO feedback_ratings (session_id, usefulness_rating, comment)
            VALUES (?, ?, ?)
            """,
            (str(rating.session_id), rating.usefulness_rating, rating.comment),
        )


def get_session_exists(session_id: UUID) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM feedback_sessions WHERE session_id = ?",
            (str(session_id),),
        ).fetchone()
    return row is not None


def health_snapshot() -> dict[str, Any]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        sessions = conn.execute("SELECT COUNT(*) FROM feedback_sessions").fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
        ratings = conn.execute("SELECT COUNT(*) FROM feedback_ratings").fetchone()[0]
    return {"status": "ok", "sessions": sessions, "events": events, "ratings": ratings}
