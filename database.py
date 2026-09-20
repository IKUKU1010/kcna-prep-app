"""
Database layer for the KCNA Exam Prep app.
Uses SQLite via the built-in sqlite3 module — zero external DB setup required.
"""
import sqlite3
import json
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kcna.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS bundles (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    num_questions INTEGER NOT NULL DEFAULT 60,
    duration_minutes INTEGER NOT NULL DEFAULT 70
);

CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    question TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct TEXT NOT NULL,
    explanation TEXT NOT NULL,
    domain TEXT NOT NULL,
    competency TEXT NOT NULL,
    FOREIGN KEY (bundle_id) REFERENCES bundles(id)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id INTEGER NOT NULL,
    candidate_name TEXT DEFAULT 'Candidate',
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    time_taken_seconds INTEGER,
    total_questions INTEGER NOT NULL,
    correct_count INTEGER,
    score INTEGER,
    passed INTEGER,
    answers_json TEXT,
    domain_breakdown_json TEXT,
    status TEXT NOT NULL DEFAULT 'in_progress',
    FOREIGN KEY (bundle_id) REFERENCES bundles(id)
);

CREATE INDEX IF NOT EXISTS idx_questions_bundle ON questions(bundle_id);
CREATE INDEX IF NOT EXISTS idx_attempts_bundle ON attempts(bundle_id);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row):
    return dict(row) if row else None


# ---------- Bundles ----------

def upsert_bundle(bundle_id, name, description, num_questions=60, duration_minutes=70):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO bundles (id, name, description, num_questions, duration_minutes)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, description=excluded.description,
                 num_questions=excluded.num_questions, duration_minutes=excluded.duration_minutes""",
            (bundle_id, name, description, num_questions, duration_minutes),
        )


def get_bundles():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bundles ORDER BY id").fetchall()
        return [row_to_dict(r) for r in rows]


def get_bundle(bundle_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM bundles WHERE id = ?", (bundle_id,)).fetchone()
        return row_to_dict(row)


def clear_questions_for_bundle(bundle_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM questions WHERE bundle_id = ?", (bundle_id,))


def insert_question(bundle_id, position, question, options, correct, explanation, domain, competency):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO questions
               (bundle_id, position, question, options_json, correct, explanation, domain, competency)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (bundle_id, position, question, json.dumps(options), correct, explanation, domain, competency),
        )


def get_questions_for_bundle(bundle_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM questions WHERE bundle_id = ? ORDER BY position", (bundle_id,)
        ).fetchall()
        out = []
        for r in rows:
            d = row_to_dict(r)
            d["options"] = json.loads(d.pop("options_json"))
            out.append(d)
        return out


def get_question(question_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if not row:
            return None
        d = row_to_dict(row)
        d["options"] = json.loads(d.pop("options_json"))
        return d


# ---------- Attempts ----------

def create_attempt(bundle_id, started_at, total_questions, candidate_name="Candidate"):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO attempts (bundle_id, candidate_name, started_at, total_questions, status)
               VALUES (?, ?, ?, ?, 'in_progress')""",
            (bundle_id, candidate_name, started_at, total_questions),
        )
        return cur.lastrowid


def get_attempt(attempt_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
        return row_to_dict(row)


def submit_attempt(attempt_id, submitted_at, time_taken_seconds, correct_count,
                    total_questions, score, passed, answers, domain_breakdown):
    with get_conn() as conn:
        conn.execute(
            """UPDATE attempts SET
                 submitted_at = ?, time_taken_seconds = ?, correct_count = ?,
                 total_questions = ?, score = ?, passed = ?, answers_json = ?,
                 domain_breakdown_json = ?, status = 'completed'
               WHERE id = ?""",
            (submitted_at, time_taken_seconds, correct_count, total_questions, score,
             1 if passed else 0, json.dumps(answers), json.dumps(domain_breakdown), attempt_id),
        )


def get_history(limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT attempts.*, bundles.name as bundle_name
               FROM attempts JOIN bundles ON attempts.bundle_id = bundles.id
               WHERE attempts.status = 'completed'
               ORDER BY attempts.submitted_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [row_to_dict(r) for r in rows]


def bundle_has_questions(bundle_id):
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM questions WHERE bundle_id = ?", (bundle_id,)).fetchone()
        return row["c"] > 0


def prune_bundles(keep_count):
    """Remove any bundles (and their questions/attempts) with id > keep_count.
    Used when the configured bundle count shrinks between runs."""
    with get_conn() as conn:
        stale_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM bundles WHERE id > ?", (keep_count,)
        ).fetchall()]
        for bid in stale_ids:
            conn.execute("DELETE FROM attempts WHERE bundle_id = ?", (bid,))
            conn.execute("DELETE FROM questions WHERE bundle_id = ?", (bid,))
            conn.execute("DELETE FROM bundles WHERE id = ?", (bid,))


def bundle_count():
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM bundles").fetchone()
        return row["c"]
