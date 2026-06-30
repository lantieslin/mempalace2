# MemPalace2

Context preservation and seamless resume for AI agents.

Inspired by [MemPalace](https://github.com/MemPalace/mempalace).

## Features

- **Auto-archive**: Automatically saves conversation when context reaches 90% threshold
- **Dynamic buffer**: Adjusts buffer space based on task length
- **Copy-on-write**: Isolated session copies for concurrent access
- **Agent-triggered summarization**: Agent decides when to generate summaries
- **Seamless resume**: Restore sessions with checkpoint, summary, and history

## Architecture

```
┌──────────────────────────────────────┐
│           AI Agent                    │
└──────────────┬───────────────────────┘
               │ MCP
               ▼
┌──────────────────────────────────────┐
│          MemPalace2 MCP Server        │
├──────────────────────────────────────┤
│  Archiver  │  Summarizer  │ Context │
└────────────┴───────────────┴─────────┘
               │
               ▼
┌──────────────────────────────────────┐
│     SQLite + JSON File Storage        │
└──────────────────────────────────────┘
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `save_session` | Archive current conversation |
| `restore_session` | Restore session with checkpoint + summary |
| `generate_summary` | Create a summary (agent-triggered) |
| `checkpoint_state` | Create a state checkpoint |
| `get_context_status` | Get current context usage |
| `update_context_usage` | Update context usage percentage |
| `search_memories` | Search past memories |
| `list_archived` | List archived sessions |

## Installation

```bash
pip install aiosqlite pydantic mcp
```

## Running

```bash
python -m src
```

## Project Structure

```
mempalace2/
├── src/
│   ├── storage.py        # SQLite storage
│   ├── archiver.py       # Conversation archiving
│   ├── checkpoint.py     # State checkpoints
│   ├── summarizer.py     # Summary generation
│   ├── context_manager.py # Context tracking
│   └── mcp_server.py     # MCP server
├── data/                 # Data directory
│   ├── memories.db
│   ├── verbatim/
│   ├── checkpoints/
│   └── sessions/
└── tests/
```

## License

MIT