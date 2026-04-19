# devops-agent

Local, Windows-only MCP tool that executes DevOps tasks composed by developers. Cursor, Claude Code, or any MCP-compatible client is the calling agent.

## Quick Start

```bash
# Install
uv sync

# Install Playwright browsers
uv run python scripts/install_playwright_browsers.py

# Initialize (creates dirs, sample configs, warms Edge profile)
uv run devops-agent init

# Verify everything works
uv run devops-agent doctor
```

## Triggering a Task

### Option 1: CLI with an activation file

Create an activation YAML that references a task-config and supplies variables:

```yaml
# my-activation.yaml
task_config: run-develop-pipeline
variables: {}
```

Then run:

```bash
uv run devops-agent run my-activation.yaml
```

### Option 2: CLI — quick run (no activation file needed for zero-variable tasks)

```bash
uv run devops-agent run --help
```

### Option 3: MCP — via Claude Code or Cursor

Once the MCP server is connected, the agent exposes tools your AI assistant can call directly:

```
list_task_configs    — see available task types
run_task             — execute a task (pass inline YAML or activation file path)
list_tasks           — check task status
get_task_state       — inspect full state of a task
resume_task          — resume a blocked/waiting task
cancel_task          — cancel a running or waiting task
get_task_screenshots — get screenshot paths from a task run
validate_config      — validate any config file
```

Example — trigger from Claude Code conversation:

> "Run the mobile-app-develop-runner pipeline"

The assistant calls `run_task` with:
```yaml
task_config: run-develop-pipeline
variables: {}
```

### Option 4: Drop a file into pending/

Place an activation YAML into `~/.devops-agent/tasks/pending/` — the watchdog picks it up automatically when the server is running.

## MCP Integration

### Claude Code

```bash
claude mcp add devops-agent -- uv run --directory C:\Code\devops-agent devops-agent serve
```

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "devops-agent": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\Code\\devops-agent", "devops-agent", "serve"]
    }
  }
}
```

## Architecture

- **22 step primitives** — shell, git, browser, OS, OCR, PR, deploy, monitor, notify
- **YAML-driven** — global configs + composable task-configs + activation files
- **Pause-and-notify on failure** — human decides recovery
- **Single-task-at-a-time** — no concurrency in v1
- **All state on disk** — `.state.json` files, inspectable and diffable

## Documentation

- **[User Workflow Guide](docs/user-workflow.md)** (start here)
- [Getting Started](docs/getting-started.md)
- [Step Primitives Reference](docs/step-primitives.md)
- [Authoring Task Configs](docs/authoring-type-configs.md) (dev-facing)
- [Authoring Global Configs](docs/authoring-globals.md) (platform-eng-facing)

## CLI

```
devops-agent init                  # One-time setup — creates dirs, sample configs, warms Edge profile
devops-agent init --skip-browser   # Init without opening Edge for login
devops-agent doctor                # Run health checks (Git Bash, Edge, configs, OCR, DPI)
devops-agent validate <path>       # Validate any config/task-config/activation YAML
devops-agent run <activation.yaml> # Run a task from an activation file
devops-agent resume <task-id>      # Resume a blocked/waiting task from its checkpoint
devops-agent cancel <task-id>      # Move a task to failed state
devops-agent list                  # List all tasks across all phases
devops-agent list -s in_progress   # List only in-progress tasks
devops-agent logs <task-id>        # Pretty-print a task's full state JSON
devops-agent serve                 # Run MCP server over stdio (for Claude Code / Cursor)
```

## Stack

Python 3.11 | uv | FastMCP | Playwright | mss | pywin32 | PyAutoGUI | RapidOCR | Pydantic v2 | structlog | watchdog | httpx | typer
