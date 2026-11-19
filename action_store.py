
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = PROJECT_ROOT / "data" / "ledgerlens_actions.sqlite3"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    return conn


def initialize_action_store():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY,
                entity TEXT NOT NULL,
                type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                trigger TEXT NOT NULL,
                financial_value REAL,
                financial_value_label TEXT,
                action TEXT NOT NULL,
                automation TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                period TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS action_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                notes TEXT,
                changed_at TEXT NOT NULL,
                FOREIGN KEY(action_id) REFERENCES actions(id)
            )
        """)


def upsert_generated_actions(entity, generated_actions):
    now = datetime.now(timezone.utc).isoformat()
    entity = entity.upper()

    with _connect() as conn:
        for action in generated_actions:
            conn.execute("""
                INSERT INTO actions (
                    id, entity, type, severity, title, trigger,
                    financial_value, financial_value_label, action,
                    automation, status, period, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    severity = excluded.severity,
                    title = excluded.title,
                    trigger = excluded.trigger,
                    financial_value = excluded.financial_value,
                    financial_value_label = excluded.financial_value_label,
                    action = excluded.action,
                    automation = excluded.automation,
                    updated_at = excluded.updated_at
            """, (
                action["id"],
                entity,
                action["type"],
                action["severity"],
                action["title"],
                action["trigger"],
                action.get("financial_value"),
                action.get("financial_value_label"),
                action["action"],
                action.get("automation"),
                action["period"],
                now,
                now
            ))


def get_actions(entity=None, status=None):
    query = "SELECT * FROM actions"
    conditions = []
    params = []

    if entity:
        conditions.append("entity = ?")
        params.append(entity.upper())

    if status:
        conditions.append("status = ?")
        params.append(status)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY updated_at DESC"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def update_action_status(action_id, new_status, notes=""):
    allowed_statuses = {
        "open",
        "in_progress",
        "completed",
        "dismissed"
    }

    if new_status not in allowed_statuses:
        raise ValueError("Invalid action status.")

    now = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        current = conn.execute(
            "SELECT status FROM actions WHERE id = ?",
            (action_id,)
        ).fetchone()

        if current is None:
            return None

        old_status = current["status"]

        conn.execute("""
            UPDATE actions
            SET status = ?, updated_at = ?,
                notes = CASE
                    WHEN ? = '' THEN notes
                    ELSE ?
                END
            WHERE id = ?
        """, (new_status, now, notes, notes, action_id))

        conn.execute("""
            INSERT INTO action_history (
                action_id, old_status, new_status, notes, changed_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (action_id, old_status, new_status, notes, now))

    return {
        "id": action_id,
        "old_status": old_status,
        "new_status": new_status,
        "updated_at": now
    }


def get_action_history(action_id):
    with _connect() as conn:
        rows = conn.execute("""
            SELECT *
            FROM action_history
            WHERE action_id = ?
            ORDER BY changed_at DESC
        """, (action_id,)).fetchall()

    return [dict(row) for row in rows]
