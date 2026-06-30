"""MemPalace2 MCP Server.

Exposes tools for conversation archival, summarization, and seamless resume.
"""

import uuid
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .storage import Storage
from .archiver import Archiver
from .checkpoint import CheckpointManager
from .summarizer import Summarizer, SummaryInput
from .context_manager import ContextManager


APP = Server("mempalace2")


@APP.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="save_session",
            description="Archive current conversation session",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "messages": {"type": "array"},
                    "trigger_reason": {"type": "string"},
                    "last_user_message_id": {"type": "string"}
                },
                "required": ["session_id", "messages", "last_user_message_id"]
            }
        ),
        Tool(
            name="restore_session",
            description="Restore a session from archive with checkpoint and summary",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="generate_summary",
            description="Create a summary for the current session (called by agent)",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "task": {"type": "string"},
                    "decisions": {"type": "array", "items": {"type": "string"}},
                    "pending": {"type": "array", "items": {"type": "string"}},
                    "key_artifacts": {"type": "array", "items": {"type": "string"}},
                    "context_for_continue": {"type": "string"}
                },
                "required": ["session_id", "task", "decisions", "pending", "key_artifacts", "context_for_continue"]
            }
        ),
        Tool(
            name="checkpoint_state",
            description="Create a checkpoint of current agent state",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "interrupted_task": {"type": "string"},
                    "pending_actions": {"type": "array", "items": {"type": "string"}},
                    "agent_state": {"type": "object"}
                },
                "required": ["session_id", "interrupted_task", "pending_actions", "agent_state"]
            }
        ),
        Tool(
            name="get_context_status",
            description="Get current context usage status",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"}
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="update_context_usage",
            description="Update context usage percentage",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "usage_pct": {"type": "number"}
                },
                "required": ["session_id", "usage_pct"]
            }
        ),
        Tool(
            name="search_memories",
            description="Search past memories and summaries",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_archived",
            description="List archived sessions",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 50}
                }
            }
        )
    ]


@APP.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    storage = Storage()
    await storage.initialize()
    archiver = Archiver()
    checkpoint_mgr = CheckpointManager()
    summarizer = Summarizer(storage)
    ctx_mgr = ContextManager()

    if name == "save_session":
        session_id = arguments["session_id"]
        messages = arguments["messages"]
        trigger_reason = arguments.get("trigger_reason", "manual")
        last_user_msg_id = arguments["last_user_message_id"]

        archive = await archiver.archive(session_id, messages, trigger_reason, last_user_msg_id)
        await storage.update_session(session_id, archived=True, trigger_reason=trigger_reason)

        return [TextContent(
            type="text",
            text=f"Session archived. Archive ID: {archive.archive_id}, Messages: {archive.message_count}"
        )]

    elif name == "restore_session":
        session_id = arguments["session_id"]

        checkpoint = await checkpoint_mgr.load(session_id)
        summary = await summarizer.get(session_id)
        archives = await archiver.get_session_archives(session_id)

        result = {
            "checkpoint": checkpoint.model_dump() if checkpoint else None,
            "summary": summary.model_dump() if summary else None,
            "recent_archives": [a.model_dump() for a in archives[:3]]
        }

        return [TextContent(type="text", text=str(result))]

    elif name == "generate_summary":
        summary_input = SummaryInput(
            session_id=arguments["session_id"],
            task=arguments["task"],
            decisions=arguments["decisions"],
            pending=arguments["pending"],
            key_artifacts=arguments["key_artifacts"],
            context_for_continue=arguments["context_for_continue"]
        )
        result = await summarizer.create(summary_input)
        return [TextContent(
            type="text",
            text=f"Summary created: {result.summary_id}"
        )]

    elif name == "checkpoint_state":
        checkpoint = await checkpoint_mgr.create(
            session_id=arguments["session_id"],
            checkpoint_type="interrupt",
            interrupted_task=arguments["interrupted_task"],
            pending_actions=arguments["pending_actions"],
            agent_state=arguments["agent_state"]
        )
        return [TextContent(
            type="text",
            text=f"Checkpoint created: {checkpoint.checkpoint_id}"
        )]

    elif name == "get_context_status":
        session_id = arguments["session_id"]
        status = ctx_mgr.get_status(session_id)
        return [TextContent(
            type="text",
            text=f"Usage: {status.current_usage_pct:.1f}%, Threshold: {status.threshold_pct}%, "
                 f"Buffer: {status.dynamic_buffer:.1f}%, Should trigger: {status.should_trigger}"
        )]

    elif name == "update_context_usage":
        session_id = arguments["session_id"]
        usage_pct = arguments["usage_pct"]
        ctx_mgr.set_usage(session_id, usage_pct)

        should_arch, reason = ctx_mgr.should_archive(session_id)
        return [TextContent(
            type="text",
            text=f"Usage updated to {usage_pct:.1f}%. Archive decision: {reason}"
        )]

    elif name == "search_memories":
        results = await summarizer.search(arguments["query"], arguments.get("limit", 5))
        if not results:
            return [TextContent(type="text", text="No matching memories found")]
        return [TextContent(
            type="text",
            text="\n---\n".join([
                f"Session: {r.session_id}\nTask: {r.task}\nPending: {r.pending}\nContext: {r.context_for_continue}"
                for r in results
            ])
        )]

    elif name == "list_archived":
        sessions = await storage.list_sessions(arguments.get("limit", 50))
        return [TextContent(
            type="text",
            text="\n".join([
                f"{s.session_id} | {s.created_at} | Archived: {s.archived}"
                for s in sessions
            ]) or "No sessions found"
        )]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await APP.run(
            read_stream,
            write_stream,
            APP.create_initialization_options()
        )