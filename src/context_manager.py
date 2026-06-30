"""Context Manager - tracks context usage and triggers archival.

Monitors token usage and triggers save when threshold is reached.
"""

import uuid
from datetime import datetime
from typing import Optional, Callable, Awaitable
from pydantic import BaseModel


class ContextStatus(BaseModel):
    """Current context usage status."""
    session_id: str
    current_usage_pct: float
    threshold_pct: float = 90.0
    buffer_pct: float = 5.0
    max_allowed_pct: float = 95.0
    should_trigger: bool
    dynamic_buffer: float


class TaskInfo(BaseModel):
    """Information about the current task for buffer calculation."""
    task_type: str
    estimated_duration: str
    can_interrupt: bool


class ContextManager:
    """Manages context tracking and archival triggering.

    Monitors context usage and determines when to trigger archival.
    Uses dynamic buffering based on current task characteristics.
    """

    def __init__(
        self,
        threshold_pct: float = 90.0,
        base_buffer_pct: float = 5.0,
        min_buffer_pct: float = 2.0,
        max_buffer_pct: float = 10.0
    ):
        self.threshold_pct = threshold_pct
        self.base_buffer_pct = base_buffer_pct
        self.min_buffer_pct = min_buffer_pct
        self.max_buffer_pct = max_buffer_pct

        self._sessions: dict[str, float] = {}
        self._task_info: dict[str, TaskInfo | None] = {}

    def set_usage(self, session_id: str, usage_pct: float) -> None:
        """Update current context usage for a session."""
        self._sessions[session_id] = usage_pct

    def set_task_info(self, session_id: str, task_info: TaskInfo | None) -> None:
        """Set current task information for buffer calculation."""
        self._task_info[session_id] = task_info

    def get_status(self, session_id: str) -> ContextStatus:
        """Get current context status for a session."""
        current_pct = self._sessions.get(session_id, 0.0)
        task_info = self._task_info.get(session_id)

        dynamic_buffer = self._calculate_dynamic_buffer(task_info, current_pct)
        max_allowed = self.threshold_pct + dynamic_buffer

        return ContextStatus(
            session_id=session_id,
            current_usage_pct=current_pct,
            threshold_pct=self.threshold_pct,
            buffer_pct=dynamic_buffer,
            max_allowed_pct=max_allowed,
            should_trigger=current_pct >= self.threshold_pct,
            dynamic_buffer=dynamic_buffer
        )

    def _calculate_dynamic_buffer(
        self,
        task_info: TaskInfo | None,
        current_pct: float
    ) -> float:
        """Calculate dynamic buffer based on task characteristics.

        Longer-running or critical tasks get more buffer.
        """
        if task_info is None:
            return self.base_buffer_pct

        buffer = self.base_buffer_pct

        if task_info.task_type in ("file_write", "refactor", "debugging"):
            buffer += 2.0

        if task_info.estimated_duration in ("long", "very_long"):
            buffer += 1.5

        if not task_info.can_interrupt:
            buffer += 1.0

        overshoot = max(0.0, current_pct - self.threshold_pct)
        if overshoot > 3.0:
            buffer = min(buffer + overshoot, self.max_buffer_pct)

        return max(buffer, self.min_buffer_pct)

    def should_archive(self, session_id: str) -> tuple[bool, str]:
        """Determine if archiving should be triggered.

        Returns: (should_archive, reason)
        """
        status = self.get_status(session_id)

        if not status.should_trigger:
            return False, "threshold_not_reached"

        if status.current_usage_pct >= status.max_allowed_pct:
            return True, "max_buffer_exceeded"

        return False, "waiting_for_task_completion"

    def register_session(self, session_id: str) -> None:
        """Register a new session for tracking."""
        if session_id not in self._sessions:
            self._sessions[session_id] = 0.0
            self._task_info[session_id] = None

    def unregister_session(self, session_id: str) -> None:
        """Unregister a session."""
        self._sessions.pop(session_id, None)
        self._task_info.pop(session_id, None)

    async def wait_for_task_completion(
        self,
        session_id: str,
        check_interval: float = 0.5,
        max_wait: float = 60.0
    ) -> bool:
        """Wait for current task to complete before archiving.

        This is a simple polling implementation.
        In production, this could be event-driven.
        """
        import asyncio
        start_time = datetime.utcnow().timestamp()

        while True:
            task_info = self._task_info.get(session_id)
            if task_info is None or task_info.can_interrupt:
                return True

            elapsed = datetime.utcnow().timestamp() - start_time
            if elapsed >= max_wait:
                return False

            await asyncio.sleep(check_interval)