# Getting Started

## Prerequisites

- Windows 10/11
- Python 3.11+
- Git for Windows (provides Git Bash)
- Microsoft Edge

## Installation

```bash
# Clone the repo
git clone <repo-url> devops-agent
cd devops-agent

# Install with uv
uv sync

# Or install as a tool
uv tool install .
```

## Initial Setup

```bash
# Create dirs, check prerequisites, warm Edge profile
devops-agent init
```

During init:
1. Directory structure is created at `~/.devops-agent/`
2. Git Bash and Edge are verified
3. If `login_targets` are configured, Edge opens for you to authenticate against each target
4. A headless sanity check verifies sessions are warm

## Configuration

Create these files in `~/.devops-agent/`:

### `config.yaml` — Agent behavior
```yaml
work_dir: "~/.devops-agent/work"
edge_profile_dir: "~/.devops-agent/edge-profile"
default_merge_detection: poll
poll_interval_seconds: 60
poll_timeout_seconds: 3600
log_level: INFO
login_targets:
  - "https://login.microsoftonline.com"
  - "https://dev.azure.com"
```

### `repos.yaml` — Repository registry
```yaml
repos:
  my-service:
    clone_url: "https://dev.azure.com/org/project/_git/my-service"
    platform: azure_devops
    pr_create_url_template: "https://dev.azure.com/org/project/_git/my-service/pullrequestcreate?sourceRef=${branch_name}"
    default_reviewers: ["team-lead@example.com"]
```

### `environments.yaml` — Deploy targets
```yaml
environments:
  staging:
    deploy_portal_url: "https://portal.azure.com/#resource/my-staging-app"
    deploy_trigger: portal_click
    health_checks:
      - url: "https://staging.example.com/health"
        expected_status: 200
```

### `notifications.yaml` — Channels and templates
```yaml
channels:
  dev-deploys:
    url: "https://app.slack.com/client/T12345/C12345"
    platform: slack

templates:
  task_blocked: "Task ${task_id} blocked at step '${failed_step}': ${error_message}"
  task_complete: "Task ${task_id} completed successfully"
```

## Creating a Task Config

Task configs go in `~/.devops-agent/task-configs/`. Example:

```yaml
name: deploy-hotfix
description: "Create branch, commit fix, PR, deploy"
references:
  repo: my-service
  env: staging
steps:
  - step: git.clone
    params:
      url: "${clone_url}"
  - step: git.branch
    params:
      branch: "hotfix/${branch_suffix}"
  - step: shell.run
    params:
      command: "${fix_command}"
  - step: git.commit
    params:
      message: "${commit_message}"
  - step: git.push
    params:
      branch: "hotfix/${branch_suffix}"
```

## Running a Task

Create an activation file:

```yaml
# my-hotfix.yaml
task_config: deploy-hotfix
variables:
  branch_suffix: "fix-123"
  fix_command: "sed -i 's/old/new/' config.json"
  commit_message: "fix(config): update value"
```

Then run:

```bash
devops-agent run my-hotfix.yaml
```

## MCP Integration

### Claude Code
Add to `~/.claude/claude_desktop_config.json`:
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

### Cursor
Add to `~/.cursor/mcp.json` with the same format.

## CLI Commands

| Command | Description |
|---------|-------------|
| `devops-agent init` | One-time setup |
| `devops-agent doctor` | Run health checks |
| `devops-agent validate <path>` | Validate a config file |
| `devops-agent run <activation>` | Run a task |
| `devops-agent resume <task-id>` | Resume a blocked task |
| `devops-agent cancel <task-id>` | Cancel a task |
| `devops-agent list` | List all tasks |
| `devops-agent logs <task-id>` | Show task state |
| `devops-agent serve` | Run MCP server (stdio) |
