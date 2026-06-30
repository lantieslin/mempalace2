"""Checkpoint management for preserving interrupted agent state."""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


DATA_DIR = Path(__file__).parent.parent / "data"
CHECKPOINTS_DIR = DATA_DIR / "checkpoints"


class CheckpointData(BaseModel):
    """Full checkpoint data stored on disk."""
    checkpoint_id: str
    session_id: str
    created_at: str
    checkpoint_type: str
    interrupted_task: str
    pending_actions: list[str]
    agent_state: dict


class CheckpointManager:
    """Manages state checkpoints for session interruption/recovery."""

    def __init__(self, base_dir: Path = CHECKPOINTS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _session_dir(self, session_id: str) -> Path:
        """Get directory for a session's checkpoints."""
        return self.base_dir / session_id

    async def create(
        self,
        session_id: str,
        checkpoint_type: str,
        interrupted_task: str,
        pending_actions: list[str],
        agent_state: dict
    ) -> CheckpointData:
        """Create a new checkpoint."""
        checkpoint = CheckpointData(
            checkpoint_id=str(uuid.uuid4()),
            session_id=session_id,
            created_at=datetime.utcnow().isoformat(),
            checkpoint_type=checkpoint_type,
            interrupted_task=interrupted_task,
            pending_actions=pending_actions,
            agent_state=agent_state
        )

        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = session_dir / f"{checkpoint.checkpoint_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint.model_dump(), f, ensure_ascii=False, indent=2)

        return checkpoint

    async def load(self, session_id: str) -> Optional[CheckpointData]:
        """Load the most recent checkpoint for a session."""
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return None

        checkpoints = list(session_dir.glob("*.json"))
        if not checkpoints:
            return None

        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        with open(latest, encoding="utf-8") as f:
            data = json.load(f)
            return CheckpointData(**data)

    async def list_checkpoints(self, session_id: str) -> list[CheckpointData]:
        """List all checkpoints for a session."""
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            return []

        checkpoints = []
        for cf in sorted(session_dir.glob("*.json"), key=lambda p: p.stat().st_mtime):
            with open(cf, encoding="utf-8") as f:
                data = json.load(f)
                checkpoints.append(CheckpointData(**data))
        return checkpoints