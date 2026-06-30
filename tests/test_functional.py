"""Functional test for MemPalace2 core components."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage import Storage, SessionRecord
from checkpoint import CheckpointManager
from archiver import Archiver
from context_manager import ContextManager, TaskInfo


async def test_storage():
    """Test storage operations."""
    storage = Storage()
    await storage.initialize()

    session = await storage.create_session("test-session-1")
    assert session.session_id == "test-session-1"
    assert session.archived == False

    await storage.update_session("test-session-1", archived=True, trigger_reason="threshold")
    updated = await storage.get_session("test-session-1")
    assert updated.archived == True
    assert updated.trigger_reason == "threshold"

    print("Storage test passed!")


async def test_checkpoint():
    """Test checkpoint creation."""
    mgr = CheckpointManager()

    checkpoint = await mgr.create(
        session_id="test-session-2",
        checkpoint_type="interrupt",
        interrupted_task="Writing test file",
        pending_actions=["verify", "commit"],
        agent_state={"cursor": "line 50", "file": "test.py"}
    )

    assert checkpoint.session_id == "test-session-2"
    assert checkpoint.interrupted_task == "Writing test file"

    loaded = await mgr.load("test-session-2")
    assert loaded.checkpoint_id == checkpoint.checkpoint_id

    print("Checkpoint test passed!")


async def test_archiver():
    """Test conversation archiving."""
    archiver = Archiver()

    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    archive = await archiver.archive(
        session_id="test-session-3",
        messages=messages,
        trigger_reason="threshold_90pct",
        last_user_message_id="msg_001"
    )

    assert archive.session_id == "test-session-3"
    assert archive.message_count == 2

    loaded = await archiver.load_archive(archive.archive_id)
    assert loaded["messages"] == messages

    print("Archiver test passed!")


async def test_context_manager():
    """Test context tracking and threshold detection."""
    ctx = ContextManager()

    ctx.set_usage("test", 85.0)
    status = ctx.get_status("test")
    assert status.should_trigger == False

    ctx.set_usage("test", 92.0)
    status = ctx.get_status("test")
    assert status.should_trigger == True

    ctx.set_task_info("test", TaskInfo(
        task_type="file_write",
        estimated_duration="long",
        can_interrupt=False
    ))
    status = ctx.get_status("test")
    assert status.dynamic_buffer >= 3.5

    print("Context manager test passed!")


async def main():
    await test_storage()
    await test_checkpoint()
    await test_archiver()
    await test_context_manager()
    print("\nAll functional tests passed!")


if __name__ == "__main__":
    asyncio.run(main())