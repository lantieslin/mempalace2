"""Storage layer for MemPalace2.

Minimal SQLite schema for session management, summaries, and checkpoints.
"""

import aiosqlite
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


DATABASE_PATH = Path(__file__).parent.parent / "data" / "memories.db"


class SessionRecord(BaseModel):
    """Session metadata record."""
    session_id: str
    created_at: str
    updated_at: str
    archived: bool = False
    trigger_reason: Optional[str] = None


class SummaryRecord(BaseModel):
    """Summary metadata record."""
    summary_id: str
    session_id: str
    created_at: str
    task: str
    decisions: list[str]
    pending: list[str]
    key_artifacts: list[str]
    context_for_continue: str


class CheckpointRecord(BaseModel):
    """Checkpoint metadata record."""
    checkpoint_id: str
    session_id: str
    created_at: str
    checkpoint_type: str
    interrupted_task: Optional[str] = None
    pending_actions: list[str] = []


class Storage:
    """Async SQLite storage for MemPalace2."""

    def __init__(self, db_path: Path = DATABASE_PATH):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Create tables if not exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    archived INTEGER DEFAULT 0,
                    trigger_reason TEXT
                );

                CREATE TABLE IF NOT EXISTS summaries (
                    summary_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    task TEXT NOT NULL,
                    decisions TEXT NOT NULL,
                    pending TEXT NOT NULL,
                    key_artifacts TEXT NOT NULL,
                    context_for_continue TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    checkpoint_type TEXT NOT NULL,
                    interrupted_task TEXT,
                    pending_actions TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_summaries_session ON summaries(session_id);
                CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id);
            """)
            await db.commit()

    async def create_session(self, session_id: str) -> SessionRecord:
        """Create a new session record."""
        now = datetime.utcnow().isoformat()
        record = SessionRecord(
            session_id=session_id,
            created_at=now,
            updated_at=now
        )
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO sessions (session_id, created_at, updated_at)
                   VALUES (?, ?, ?)""",
                (record.session_id, record.created_at, record.updated_at)
            )
            await db.commit()
        return record

    async def update_session(
        self,
        session_id: str,
        archived: bool = False,
        trigger_reason: Optional[str] = None
    ) -> None:
        """Update session metadata."""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE sessions
                   SET updated_at = ?, archived = ?, trigger_reason = ?
                   WHERE session_id = ?""",
                (now, int(archived), trigger_reason, session_id)
            )
            await db.commit()

    async def get_session(self, session_id: str) -> Optional[SessionRecord]:
        """Get session by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return SessionRecord(**dict(row))
        return None

    async def list_sessions(self, limit: int = 50) -> list[SessionRecord]:
        """List recent sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [SessionRecord(**dict(row)) for row in rows]

    async def save_summary(self, summary: SummaryRecord) -> None:
        """Save a summary record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO summaries
                   (summary_id, session_id, created_at, task, decisions,
                    pending, key_artifacts, context_for_continue)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    summary.summary_id,
                    summary.session_id,
                    summary.created_at,
                    summary.task,
                    json.dumps(summary.decisions),
                    json.dumps(summary.pending),
                    json.dumps(summary.key_artifacts),
                    summary.context_for_continue
                )
            )
            await db.commit()

    async def get_summary(self, session_id: str) -> Optional[SummaryRecord]:
        """Get most recent summary for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM summaries
                   WHERE session_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    data["decisions"] = json.loads(data["decisions"])
                    data["pending"] = json.loads(data["pending"])
                    data["key_artifacts"] = json.loads(data["key_artifacts"])
                    return SummaryRecord(**data)
        return None

    async def save_checkpoint(self, checkpoint: CheckpointRecord) -> None:
        """Save a checkpoint record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO checkpoints
                   (checkpoint_id, session_id, created_at, checkpoint_type,
                    interrupted_task, pending_actions)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    checkpoint.checkpoint_id,
                    checkpoint.session_id,
                    checkpoint.created_at,
                    checkpoint.checkpoint_type,
                    checkpoint.interrupted_task,
                    json.dumps(checkpoint.pending_actions)
                )
            )
            await db.commit()

    async def get_checkpoint(self, session_id: str) -> Optional[CheckpointRecord]:
        """Get most recent checkpoint for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM checkpoints
                   WHERE session_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    data["pending_actions"] = json.loads(data["pending_actions"])
                    return CheckpointRecord(**data)
        return None

    async def search_summaries(self, query: str, limit: int = 5) -> list[SummaryRecord]:
        """Search summaries by task content (substring match)."""
        results = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM summaries ORDER BY created_at DESC"
            ) as cursor:
                async for row in cursor:
                    if query.lower() in row["task"].lower():
                        data = dict(row)
                        data["decisions"] = json.loads(data["decisions"])
                        data["pending"] = json.loads(data["pending"])
                        data["key_artifacts"] = json.loads(data["key_artifacts"])
                        results.append(SummaryRecord(**data))
                        if len(results) >= limit:
                            break
        return results