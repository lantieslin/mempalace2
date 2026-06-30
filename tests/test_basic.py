"""Basic import tests for MemPalace2."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all modules can be imported."""
    import storage
    import checkpoint
    import archiver
    import summarizer
    import context_manager
    import mcp_server

    assert hasattr(storage, "Storage")
    assert hasattr(checkpoint, "CheckpointManager")
    assert hasattr(archiver, "Archiver")
    assert hasattr(summarizer, "Summarizer")
    assert hasattr(context_manager, "ContextManager")
    assert hasattr(mcp_server, "APP")

    print("All imports successful!")


def test_storage_types():
    """Test storage types."""
    from storage import SessionRecord, SummaryRecord, CheckpointRecord

    session = SessionRecord(
        session_id="test-123",
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00"
    )
    assert session.session_id == "test-123"
    print("Storage types OK")


def test_context_manager():
    """Test context manager buffer calculation."""
    from context_manager import ContextManager, TaskInfo

    ctx = ContextManager()

    status = ctx.get_status("new-session")
    assert status.should_trigger == False
    assert status.current_usage_pct == 0.0

    ctx.set_usage("test", 85.0)
    status = ctx.get_status("test")
    assert status.should_trigger == False

    ctx.set_usage("test", 91.0)
    status = ctx.get_status("test")
    assert status.should_trigger == True

    print("Context manager OK")


if __name__ == "__main__":
    test_imports()
    test_storage_types()
    test_context_manager()
    print("\nAll tests passed!")