from __future__ import annotations

import sqlite3
from pathlib import Path


WEB_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version      INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    applied_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id                  TEXT PRIMARY KEY,
    shop_id             TEXT NOT NULL,
    session_key         TEXT NOT NULL,
    customer_token      TEXT NOT NULL UNIQUE,
    stage               TEXT NOT NULL,
    artifact_dir        TEXT NOT NULL,
    pending_answer      TEXT,
    preflight_json      TEXT,
    turn1_question      TEXT,
    turn2_planner_json  TEXT,
    turn3_planner_json  TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    interview_completed_at TEXT,
    production_completed_at TEXT,
    approved_at         TEXT
);

CREATE TABLE IF NOT EXISTS media_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    kind            TEXT NOT NULL,
    role            TEXT NOT NULL,
    filename        TEXT NOT NULL,
    relative_path   TEXT NOT NULL,
    mime_type       TEXT,
    file_size       INTEGER,
    duration_sec    REAL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS session_messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    sender          TEXT NOT NULL,
    message_type    TEXT NOT NULL,
    turn_index      INTEGER,
    text            TEXT,
    relative_path   TEXT,
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS session_artifacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    artifact_type   TEXT NOT NULL,
    relative_path   TEXT NOT NULL,
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS session_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    data_json       TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);
"""


def connect_database(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> Path:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect_database(database_path)
    try:
        connection.executescript(WEB_SCHEMA)
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
            (1, "web_phase1"),
        )
        connection.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (?, ?)",
            (2, "web_phase8_session_events"),
        )
        connection.commit()
    finally:
        connection.close()
    return database_path
