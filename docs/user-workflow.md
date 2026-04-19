# User Workflow Guide

Step-by-step guide for setting up and using devops-agent on your machine.

---

## Phase 1: Install

### Prerequisites

- Windows 10/11
- Python 3.11+ ([python.org/downloads](https://www.python.org/downloads/))
- Git for Windows ([git-scm.com](https://git-scm.com/download/win)) — provides Git Bash
- Microsoft Edge (pre-installed on Windows)
- uv ([docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/)) — `pip install uv` if you don't have it

### Clone and install

```bash
git clone https://github.com/singhaman092/devops-agent.git
cd devops-agent
uv sync
uv run python scripts/install_playwright_browsers.py
```

### Verify

```bash
uv run devops-agent doctor
```

You should see all green OKs for Git Bash, Edge, RapidOCR, DPI.

---

## Phase 2: Configure your login targets

The agent uses a persistent Edge browser profile to stay logged in to your platforms.
You need to tell it which URLs to authenticate against.

### 2.1 Run init once to create the directory structure

```bash
uv run devops-agent init --skip-browser
```

This creates `~/.devops-agent/` with sample config files:

```
C:\Users\<you>\.devops-agent\
    config.yaml              <-- you edit this
    repos.yaml               <-- you edit this
    environments.yaml        <-- you edit this
    notifications.yaml       <-- you edit this (optional)
    task-configs\            <-- task configs go here
    tasks\                   <-- runtime state (don't touch)
```

### 2.2 Edit config.yaml — add your login targets

Open `C:\Users\<you>\.devops-agent\config.yaml` in any editor.

The key section is `login_targets`. Add every URL you need the agent to be logged into.
Think about: where does the agent need to navigate during tasks?

**Example: Bitbucket pipelines**
```yaml
login_targets:
  - "https://bitbucket.org/dashboard/overview"                              # Bitbucket login (redirects to Atlassian SSO)
  - "https://bitbucket.org/<workspace>/<repo>/pipelines"                    # Verify repo access after login
```

**Example: Azure DevOps + Slack**
```yaml
login_targets:
  - "https://login.microsoftonline.com"                                     # Microsoft SSO
  - "https://dev.azure.com/<org>"                                           # Azure DevOps
  - "https://app.slack.com"                                                 # Slack workspace
```

**Example: GitHub + Teams**
```yaml
login_targets:
  - "https://github.com/login"                                              # GitHub login
  - "https://teams.microsoft.com"                                           # Teams
```

**Rule of thumb**: add the login/dashboard URL first (where SSO happens), then add the specific page URL the agent will visit, so you can visually confirm access during init.

### 2.3 Run init to authenticate

```bash
uv run devops-agent init
```

What happens:
1. Edge opens with each login target as a tab
2. **You log in to each tab** (SSO, username/password, 2FA — whatever your platform needs)
3. Come back to the terminal and press Enter
4. Agent saves the browser profile (cookies, sessions) to `~/.devops-agent/edge-profile/`
5. Agent runs a headless check to verify sessions are warm

**If the headless check shows a login redirect**: your session didn't stick. Common causes:
- Third-party cookies are being blocked (the agent already disables this, but some enterprise policies override it)
- The SSO flow requires an additional consent step you didn't complete
- Run `uv run devops-agent init` again and make sure each tab shows the logged-in page before pressing Enter

### 2.4 Verify auth works

```bash
uv run devops-agent doctor
```

All checks should pass.

---

## Phase 3: Configure your repos and environments

### 3.1 Edit repos.yaml

Open `C:\Users\<you>\.devops-agent\repos.yaml`.

Add each repository the agent will interact with. The short name is what task configs reference.

```yaml
repos:
  my-api:                                                                      # short name — use this in task configs
    clone_url: "https://bitbucket.org/myteam/my-api.git"                       # git clone URL
    platform: bitbucket                                                        # bitbucket | github | gitlab | azure_devops
    pr_create_url_template: "https://bitbucket.org/myteam/my-api/pull-requests/new?source=${branch_name}"
    pr_view_url_template: "https://bitbucket.org/myteam/my-api/pull-requests/${pr_id}"
    pr_template_path: ""                                                       # path inside repo to PR template (optional)
    title_convention: ""                                                       # regex for PR title validation (optional)
    default_reviewers: []                                                      # email list (optional)
    required_labels: []                                                        # label list (optional)
```

### 3.2 Edit environments.yaml

Open `C:\Users\<you>\.devops-agent\environments.yaml`.

Add each environment/pipeline the agent can trigger.

```yaml
environments:
  my-api-develop:                                                              # short name — use this in task configs
    deploy_portal_url: "https://bitbucket.org/myteam/my-api/pipelines"         # URL to the pipeline/deploy page
    deploy_trigger: portal_click                                               # portal_click | pipeline_url | cli
    required_params: {}                                                        # params the activation must supply (optional)
    health_checks: []                                                          # health check URLs to verify after deploy (optional)
    monitor_timeout_seconds: 600                                               # max seconds to wait for health checks
    repos:
      - my-api                                                                 # linked repo short name
```

### 3.3 Edit notifications.yaml (optional)

Only needed if you want the agent to post to Slack/Teams on task events.

```yaml
channels:
  dev-deploys:
    url: "https://app.slack.com/client/T12345/C12345"                          # Slack/Teams deep-link URL
    platform: slack                                                            # slack | teams

templates:
  task_blocked: "Task ${task_id} blocked: ${error_message}"
  task_complete: "Task ${task_id} completed"
```

### 3.4 Validate your configs

```bash
uv run devops-agent validate ~/.devops-agent/config.yaml
uv run devops-agent validate ~/.devops-agent/repos.yaml
uv run devops-agent validate ~/.devops-agent/environments.yaml
```

All should say "is valid".

---

## Phase 4: Connect your AI assistant

The agent exposes an MCP server that Cursor, Claude Code, or any MCP client can call.

### Claude Code

```bash
claude mcp add devops-agent -- uv run --directory /path/to/devops-agent devops-agent serve
```

### Cursor

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "devops-agent": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\devops-agent", "devops-agent", "serve"]
    }
  }
}
```

Restart Cursor after saving.

### Verify connection

- **Claude Code**: run `claude mcp list` — should show `devops-agent: ✓ Connected`
- **Cursor**: ask "List devops-agent task configs" — it should call the MCP tool

---

## Phase 5: Create your first task config

You have two options:

### Option A: Let the AI build it for you (recommended)

Tell your AI assistant:

> "I need a task config that triggers the develop pipeline for my-api on Bitbucket. Use the devops-agent MCP tools to figure out the right selectors and create a working config."

The AI will follow the workflow in `.cursorrules`:
1. Call `list_steps()` to see available primitives
2. Call `screenshot_url()` to see your pipeline page
3. Call `inspect_page()` to find selectors
4. Call `create_task_config()` to write the YAML
5. Call `run_task()` to test it
6. If it fails, call `debug_task()`, fix, and retry

### Option B: Write it yourself

Create a file in `~/.devops-agent/task-configs/my-task.yaml`:

```yaml
name: my-task
description: "What this task does"
references:
  repo: my-api                      # from repos.yaml
  env: my-api-develop               # from environments.yaml
steps:
  - step: browser.navigate
    name: "Open pipeline page"
    params:
      url: "https://bitbucket.org/myteam/my-api/pipelines"
      wait_until: "networkidle"

  - step: browser.screenshot
    name: "Capture page"
    params:
      filename: "page.png"
      full_page: true

  # ... more steps
```

See [docs/step-primitives.md](step-primitives.md) for all available steps.

Validate:
```bash
uv run devops-agent validate ~/.devops-agent/task-configs/my-task.yaml
```

---

## Phase 6: Run a task

### From CLI

Create an activation file (or use inline):

```yaml
# run-my-task.yaml
task_config: my-task
variables: {}
```

```bash
uv run devops-agent run run-my-task.yaml
```

### From your AI assistant

> "Run my-task"

### Check status

```bash
uv run devops-agent list                    # see all tasks
uv run devops-agent logs <task-id>          # full state JSON
```

### If a task fails

```bash
uv run devops-agent logs <task-id>          # see the error
```

Screenshots are saved in `~/.devops-agent/work/<task-id>/screenshots/` — open them to see what the browser saw.

To retry after fixing the task config:

```bash
uv run devops-agent resume <task-id>        # retry from the failed step
```

Or cancel and re-run:

```bash
uv run devops-agent cancel <task-id>
uv run devops-agent run run-my-task.yaml
```

---

## Real-World Example: Bitbucket Pipeline Trigger

Here's the complete setup we used to trigger a Bitbucket pipeline on the `develop` branch.

### config.yaml
```yaml
work_dir: "~/.devops-agent/work"
edge_profile_dir: "~/.devops-agent/edge-profile"
default_merge_detection: poll
poll_interval_seconds: 60
poll_timeout_seconds: 3600
default_notification_channels: []
log_level: INFO
log_json: true

login_targets:
  - "https://bitbucket.org/dashboard/overview"
  - "https://bitbucket.org/enetro-ai/enetro-mobile-app-apis/pipelines"
```

### repos.yaml
```yaml
repos:
  enetro-mobile-apis:
    clone_url: "https://bitbucket.org/enetro-ai/enetro-mobile-app-apis.git"
    platform: bitbucket
    pr_create_url_template: "https://bitbucket.org/enetro-ai/enetro-mobile-app-apis/pull-requests/new?source=${branch_name}"
    pr_view_url_template: "https://bitbucket.org/enetro-ai/enetro-mobile-app-apis/pull-requests/${pr_id}"
    pr_template_path: ""
    title_convention: ""
    default_reviewers: []
    required_labels: []
```

### environments.yaml
```yaml
environments:
  bitbucket-develop:
    deploy_portal_url: "https://bitbucket.org/enetro-ai/enetro-mobile-app-apis/pipelines"
    deploy_trigger: portal_click
    required_params: {}
    health_checks: []
    monitor_timeout_seconds: 600
    repos:
      - enetro-mobile-apis
```

### task-configs/mobile-app-develop-runner.yaml

This was built iteratively — the AI assistant used `screenshot_url` and `debug_task` to find the right selectors. Key learnings:

- Bitbucket uses Atlassian react-select components — `browser.click` can't reach them due to overlay elements
- Solution: `browser.eval` with JavaScript to focus inputs, type values, and click options
- The "Run" button has `data-testid="run-pipeline"` but stays disabled until both branch AND pipeline are selected
- Solution: select branch first, then open and select the pipeline dropdown, then force-click Run

```yaml
name: run-develop-pipeline
description: "Trigger Bitbucket pipeline for enetro-mobile-app-apis on develop"
references:
  repo: enetro-mobile-apis
  env: bitbucket-develop
steps:
  - step: browser.navigate
    params: { url: "https://bitbucket.org/enetro-ai/enetro-mobile-app-apis/pipelines", wait_until: "networkidle" }
  - step: browser.click
    params: { selector: "button:has-text('Run pipeline')", timeout: 15000 }
  - step: wait.sleep
    params: { seconds: 3 }
  - step: browser.eval
    name: "Select develop branch"
    params:
      expression: |
        (() => {
          const input = document.querySelector('[data-testid="branch-selector-select--select--input-container"] input');
          if (!input) return 'not found';
          input.focus();
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(input, 'develop');
          input.dispatchEvent(new Event('input', { bubbles: true }));
          return 'typed';
        })()
  - step: wait.sleep
    params: { seconds: 2 }
  - step: browser.eval
    name: "Click develop option"
    params:
      expression: |
        (() => {
          for (const opt of document.querySelectorAll('[id*="option"]')) {
            if (opt.textContent.trim() === 'develop') { opt.click(); return 'clicked'; }
          }
          return 'not found';
        })()
  - step: wait.sleep
    params: { seconds: 3 }
  - step: browser.eval
    name: "Open pipeline dropdown"
    params:
      expression: |
        (() => {
          const dialog = document.querySelector('[role="dialog"]');
          if (!dialog) return 'no dialog';
          for (const c of dialog.querySelectorAll('[data-testid*="--select--input-container"]')) {
            if (!c.getAttribute('data-testid').includes('branch-selector')) {
              const input = c.querySelector('input');
              if (input) { input.focus(); input.dispatchEvent(new MouseEvent('mousedown', { bubbles: true })); return 'opened'; }
            }
          }
          return 'not found';
        })()
  - step: wait.sleep
    params: { seconds: 2 }
  - step: browser.eval
    name: "Select first pipeline"
    params:
      expression: |
        (() => {
          const opts = document.querySelectorAll('[id*="option"]');
          if (opts.length > 0) { opts[0].click(); return 'selected: ' + opts[0].textContent.trim(); }
          return 'no options';
        })()
  - step: wait.sleep
    params: { seconds: 2 }
  - step: browser.eval
    name: "Click Run"
    params:
      expression: |
        (() => {
          const btn = document.querySelector('button[data-testid="run-pipeline"]');
          if (!btn) return 'not found';
          btn.removeAttribute('disabled');
          btn.click();
          return 'clicked';
        })()
  - step: wait.sleep
    params: { seconds: 5 }
  - step: browser.screenshot
    params: { filename: "pipeline_triggered.png", full_page: false }
```

### Running it

```bash
# Create activation file
echo "task_config: run-develop-pipeline" > run.yaml
echo "variables: {}" >> run.yaml

# Run
uv run devops-agent run run.yaml
```

Or via AI assistant: *"Run the develop pipeline"*

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `doctor` says Git Bash not found | Install Git for Windows |
| `doctor` says Edge not found | Edge should be pre-installed on Windows |
| Init auth doesn't persist | Make sure you fully log in on each tab before pressing Enter. Check that the final tab shows the authenticated page, not a login form. |
| "Repository not found" on private repos | Your Bitbucket/GitHub session expired. Run `uv run devops-agent init` again to re-authenticate. |
| Task fails with "element intercepts pointer events" | The page has overlay elements. Use `browser.eval` with JavaScript instead of `browser.click`. |
| Task fails with "element is not enabled" | A prerequisite wasn't met (e.g., dropdown not selected). Add more steps or use `browser.eval`. |
| Task fails with "No browser session" | The task config references browser steps but the Edge profile doesn't exist. Run `uv run devops-agent init`. |
| MCP server shows "Failed to connect" | The server process may be stale. Kill it (`taskkill /F /IM devops-agent.exe`), then restart. |
| Cursor modifies agent source code instead of using MCP tools | Make sure `.cursorrules` is in the repo root. It tells Cursor to use MCP tools, not edit source. |

---

## File Reference

| Path | What | Who edits |
|------|------|-----------|
| `~/.devops-agent/config.yaml` | Agent behavior + login targets | You (once) |
| `~/.devops-agent/repos.yaml` | Repository registry | You (per repo) |
| `~/.devops-agent/environments.yaml` | Deploy targets | You (per environment) |
| `~/.devops-agent/notifications.yaml` | Slack/Teams channels + templates | You (optional) |
| `~/.devops-agent/task-configs/*.yaml` | Task workflows | You or AI assistant |
| `~/.devops-agent/edge-profile/` | Browser cookies/sessions | Created by `init` |
| `~/.devops-agent/work/<task-id>/` | Task working trees + screenshots | Created at runtime |
| `~/.devops-agent/tasks/` | Task state files | Created at runtime |
| `<repo>/.cursorrules` | AI assistant behavior guide | Checked into repo |
