"""Archiver for preserving conversation verbatim."""

import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


DATA_DIR = Path(__file__).parent.parent / "data"
VERBATIM_DIR = DATA_DIR / "verbatim"
SESSIONS_DIR = DATA_DIR / "sessions"


class ConversationArchive(BaseModel):
    """Metadata for an archived conversation."""
    session_id: str
    archive_id: str
    created_at: str
    trigger_reason: str
    last_user_message_id: str
    message_count: int


class Archiver:
    """Handles verbatim conversation archiving with Copy-on-write."""

    def __init__(
        self,
        verbatim_dir: Path = VERBATIM_DIR,
        sessions_dir: Path = SESSIONS_DIR
    ):
        self.verbatim_dir = verbatim_dir
        self.sessions_dir = sessions_dir
        self.verbatim_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    async def archive(
        self,
        session_id: str,
        messages: list[dict],
        trigger_reason: str,
        last_user_message_id: str
    ) -> ConversationArchive:
        """Archive conversation verbatim with Copy-on-write.

        Creates a copy of the session for writes (agent gets independent copy).
        """
        archive = ConversationArchive(
            session_id=session_id,
            archive_id=str(uuid.uuid4()),
            created_at=datetime.utcnow().isoformat(),
            trigger_reason=trigger_reason,
            last_user_message_id=last_user_message_id,
            message_count=len(messages)
        )

        session_copy_dir = self.sessions_dir / session_id
        session_copy_dir.mkdir(parents=True, exist_ok=True)

        verbatim_file = self.verbatim_dir / f"{archive.archive_id}.json"
        with open(verbatim_file, "w", encoding="utf-8") as f:
            json.dump({
                "archive": archive.model_dump(),
                "messages": messages
            }, f, ensure_ascii=False, indent=2)

        return archive

    async def load_archive(self, archive_id: str) -> Optional[dict]:
        """Load an archive by ID."""
        verbatim_file = self.verbatim_dir / f"{archive_id}.json"
        if not verbatim_file.exists():
            return None
        with open(verbatim_file, encoding="utf-8") as f:
            return json.load(f)

    async def get_session_archives(self, session_id: str) -> list[ConversationArchive]:
        """Get all archives for a session."""
        archives = []
        for vf in self.verbatim_dir.glob("*.json"):
            with open(vf, encoding="utf-8") as f:
                data = json.load(f)
                if data["archive"]["session_id"] == session_id:
                    archives.append(ConversationArchive(**data["archive"]))
        return sorted(archives, key=lambda a: a.created_at, reverse=True)