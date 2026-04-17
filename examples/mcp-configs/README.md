# MCP Configuration Examples

## Claude Code

Copy `claude-code.json` content into your Claude Code MCP settings:
- File: `~/.claude/claude_desktop_config.json` or via Claude Code settings

## Cursor

Copy `cursor.json` content into your Cursor MCP config:
- File: `~/.cursor/mcp.json`

## Other MCP Clients

Any MCP-compatible client can use the stdio transport. The command is:

```
uv run --directory C:\Code\devops-agent devops-agent serve
```

Adjust the `--directory` path to wherever you cloned this repo.

## After Installing

The MCP server exposes these tools:
- `list_task_configs` — see available task types
- `list_tasks` — see task status
- `run_task` — execute a task from activation YAML
- `resume_task` — resume a waiting task
- `cancel_task` — cancel a task
- `get_task_state` — inspect task state
- `get_task_screenshots` — get screenshot paths
- `validate_config` — validate any config file
