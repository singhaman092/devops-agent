# User Workflow Guide

Step-by-step guide for setting up and using devops-agent on your machine.

---

## Phase 1: Install

### Prerequisites

- Windows 10/11
- Python 3.11+ ([python.org/downloads](https://www.python.org/downloads/))
- Git for Windows ([git-scm.com](https://git-scm.com/download/win)) — provides Git Bash
- Microsoft Edge (pre-installed on Windows)

### Step 1: Install uv (Python package manager)

Open a terminal (PowerShell or Command Prompt) and run:

```bash
pip install uv
```

Verify it installed:
```bash
uv --version
```

If `pip` isn't found, install Python first from [python.org](https://www.python.org/downloads/) and make sure "Add to PATH" is checked during install.

### Step 2: Clone the repo and install dependencies

```bash
cd C:\Code
git clone <repo-url> devops-agent
cd devops-agent
uv sync
```

Replace `<repo-url>` with the URL your team provided.

### Step 3: Install Playwright browsers

```bash
uv run python scripts/install_playwright_browsers.py
```

### Step 4: Create config directory

```bash
uv run devops-agent init --skip-browser
```

This creates `~/.devops-agent/` with sample config files.

### Step 5: Verify

```bash
uv run devops-agent doctor
```

You should see all green OKs.

---

## Phase 2: Add your repo + authenticate

Tell your AI assistant (Cursor or Claude Code) your repo URL:

> "Set up devops-agent for https://bitbucket.org/myteam/my-api"

The AI calls `setup_repo` which automatically:
- Detects the platform (Bitbucket, GitHub, GitLab, Azure DevOps)
- Generates PR creation and view URL templates
- Adds the repo to `repos.yaml`
- Creates a pipeline/actions environment in `environments.yaml`
- Adds login targets to `config.yaml`

**Supported platforms** — just give the repo URL:
```
https://bitbucket.org/workspace/repo
https://github.com/org/repo
https://gitlab.com/group/repo
https://dev.azure.com/org/project/_git/repo
```

If you need notifications, tell the AI:

> "Also set up Slack notifications to https://app.slack.com/client/T12345/C12345"

### Now authenticate

The AI will tell you login targets were added. Run init to log in:

```bash
uv run devops-agent init
```

What happens:
1. Edge opens with login pages for your platform (one tab per login target)
2. **You log in to each tab** (SSO, username/password, 2FA — whatever your platform needs)
3. **Verify the last tab shows your repo page (not a 404 or login form)**
4. Come back to the terminal and press Enter
5. Agent saves the browser profile (cookies, sessions)
6. Agent verifies sessions are warm with a headless check

**If the headless check fails**: run `uv run devops-agent init` again and make sure each tab shows the logged-in page before pressing Enter.

You can add more repos later by telling the AI again — it will add login targets and tell you to re-run init.

---

## Phase 4: Connect your AI assistant

### Claude Code

```bash
claude mcp add devops-agent -- uv run --directory C:\Code\devops-agent devops-agent serve
```

### Cursor

Create or edit `~/.cursor/mcp.json`:

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

Restart Cursor after saving.

### Verify

- **Claude Code**: `claude mcp list` — should show `devops-agent: Connected`
- **Cursor**: ask "List devops-agent task configs" — should call the MCP tool

---

## Phase 5: Tell the AI what you want

Just describe what you need in natural language:

> "Create a task config that triggers the develop pipeline for my-api"

> "Set up a task that creates a PR from develop to main for my-api"

> "Build a task to deploy my-api to staging and verify health checks pass"

The AI will:
1. Use `screenshot_url` to see your pipeline/PR page
2. Use `inspect_page` to find the right selectors
3. Create a task config with `create_task_config`
4. Test it with `run_task`
5. If it fails, read the error with `debug_task`, fix, and retry

You don't write YAML. The AI does.

---

## Phase 6: Run your tasks

Once the AI has built a working task config, you can trigger it anytime:

### From the AI

> "Run the develop pipeline"

### From CLI

```bash
echo "task_config: run-develop-pipeline" > run.yaml
echo "variables: {}" >> run.yaml
uv run devops-agent run run.yaml
```

### Check status

```bash
uv run devops-agent list                    # see all tasks
uv run devops-agent logs <task-id>          # full state JSON
```

### If a task fails

Tell the AI: *"The last task failed, debug it and fix"*

Or manually:
```bash
uv run devops-agent logs <task-id>          # see the error
```
Screenshots are saved in `~/.devops-agent/work/<task-id>/screenshots/`.

---

## Notifications (optional)

If you want the agent to post to Slack/Teams when tasks complete or fail, tell the AI:

> "Add a Slack notification channel for dev-deploys at https://app.slack.com/client/T12345/C12345"

Or edit `~/.devops-agent/notifications.yaml`:

```yaml
channels:
  dev-deploys:
    url: "https://app.slack.com/client/T12345/C12345"
    platform: slack

templates:
  task_blocked: "Task ${task_id} blocked at step '${failed_step}': ${error_message}"
  task_complete: "Task ${task_id} completed successfully"
  pr_created: "PR created: ${pr_url}"
  deploy_succeeded: "Deploy to ${env} succeeded"
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `doctor` says Git Bash not found | Install Git for Windows |
| Init auth doesn't persist | Log in fully on each tab before pressing Enter. Re-run init. |
| "Repository not found" on private repos | Session expired. Run `uv run devops-agent init` again. |
| Task fails with "element intercepts pointer events" | AI should use `browser.eval` with JS click instead of `browser.click`. Tell it to debug. |
| Task fails with "element is not enabled" | A prerequisite step didn't complete. Tell AI to debug. |
| MCP server "Failed to connect" | Kill stale process: `taskkill /F /IM devops-agent.exe`, re-register MCP. |
| Cursor modifies agent source code | Make sure `.cursorrules` is in the repo root. It tells Cursor to use MCP tools. |

---

## File Reference

| Path | What | Who manages |
|------|------|-------------|
| `~/.devops-agent/config.yaml` | Agent behavior + login targets | `setup_repo` tool / you |
| `~/.devops-agent/repos.yaml` | Repository registry | `setup_repo` tool |
| `~/.devops-agent/environments.yaml` | Deploy targets | `setup_repo` tool |
| `~/.devops-agent/notifications.yaml` | Slack/Teams channels + templates | You (optional) |
| `~/.devops-agent/task-configs/*.yaml` | Task workflows | AI assistant |
| `~/.devops-agent/edge-profile/` | Browser cookies/sessions | Created by `init` |
| `~/.devops-agent/work/<task-id>/` | Task working trees + screenshots | Created at runtime |
| `<repo>/.cursorrules` | Cursor behavior guide | Checked into repo |
| `<repo>/CLAUDE.md` | Claude Code behavior guide | Checked into repo |
