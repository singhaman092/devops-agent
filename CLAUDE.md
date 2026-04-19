# DevOps Agent — Instructions for AI Assistants

You have access to a devops-agent MCP server that automates DevOps tasks via browser automation on the developer's machine. Your job is to **compose and debug task configs** using the MCP tools — NOT to modify the devops-agent source code.

## MANDATORY STEPS — Follow this exact order every time

When the user gives you a task, follow these steps IN ORDER. Do not skip ahead.

### Step 1: MCP Server Connection
Try calling `list_steps()`. If it fails, the MCP server isn't connected:
- **Claude Code**: Write `.mcp.json` in the project root with: `{"mcpServers":{"devops-agent":{"command":"uv","args":["run","devops-agent","serve"]}}}`
- **Cursor**: Write `.cursor/mcp.json` with the same content.
- Tell the user to restart their editor. STOP here.

### Step 2: Tool Permissions
Ask the user: "I need access to all devops-agent MCP tools. OK?"
Once confirmed:
- **Claude Code**: Write `.claude/settings.local.json` with: `{"permissions":{"allow":["mcp__devops-agent__*"]}}`
- **Cursor**: Write `.cursor/settings.json` with: `{"mcp.autoApprove":["devops-agent"]}`
Skip if already configured (tools work without prompts).

### Step 3: Check Init + Ask Ticket (in ONE message)
Call `get_config_dir_path()` to check if `~/.devops-agent/` exists.
Then ask the user EVERYTHING you need in a single message. Example:

> "Before I start, I need two things:
> 1. **Ticket number** — what's the ticket for this work? (e.g., JIRA-123)
> 2. **Init** — run `uv run devops-agent init --skip-browser` in your terminal to set up the config directory
>
> Let me know the ticket number and confirm init is done."

If init is already done (config dir exists with files), just ask for the ticket number.
Do NOT proceed until you have both.

### Step 4: Setup Repo
If the user gave a repo URL, call `setup_repo(url)`.
If `setup_repo` adds new login targets, tell the user in ONE message:

> "I've configured the repo. Now run `uv run devops-agent init` to authenticate.
> Log in to every tab, complete 2FA/MFA, verify the last tab shows your repo page, then press Enter.
> Tell me when done."

WAIT for confirmation before continuing.

### Step 5: Verify Auth
Call `screenshot_url()` with the target repo/pipeline URL.
- **If login page or "not found"**: Tell the user to re-run `uv run devops-agent init` and authenticate properly. WAIT.
- **If the actual page loads**: Auth is good. Proceed.

### Step 6: Build Task Config
Now proceed — use `screenshot_url`, `inspect_page`, `create_task_config`, `run_task`, `debug_task` loop.

## CRITICAL RULES

1. **NEVER modify files in src/devops_agent/**. The agent is a fixed tool. You compose tasks via YAML configs.
2. **ALWAYS use the MCP tools**. You do NOT have filesystem access to `~/.devops-agent/`.
3. **ALWAYS use debug_task after a failure**. Don't guess — look at the error and screenshots.
4. **ALWAYS use screenshot_url BEFORE writing selectors** for a new page.
5. **ALWAYS use `setup_repo(url)` first** when given a repo URL. Do NOT manually write repos.yaml.
6. **ALWAYS save task configs to the repo** after creating a working config. Create a `task-configs/` folder in the project root and save:
   - `task-configs/<name>.yaml` — copy of the task config YAML
   - `task-configs/<name>.md` — a README with: what it does, the ticket number, how to run it (CLI command + MCP command), any variables needed, and what the user said to trigger it (the original prompt). This lets any team member repeat the task without needing the AI.

## Available MCP Tools

### Discovery
- `list_steps()` — all step primitives with param schemas
- `list_task_configs()` — existing task configs with full step sequences
- `get_global_configs()` — repos, environments, notification channels
- `get_config_dir_path()` — what's in ~/.devops-agent/

### Config File Access (you don't have filesystem access to ~/.devops-agent/)
- `read_config_file(filename)` — read config.yaml, repos.yaml, environments.yaml, notifications.yaml
- `write_config_file(filename, content)` — write/update a global config file (validates before writing)

### Task Config Authoring
- `create_task_config(name, yaml_content)` — create a new task config
- `update_task_config(name, yaml_content)` — update an existing task config
- `read_task_config(name)` — read a task config's YAML

### Execution
- `run_task(activation_yaml)` — run a task
- `resume_task(task_id)` — resume from checkpoint
- `cancel_task(task_id)` — cancel a task

### Debugging
- `debug_task(task_id)` — error + failed step + screenshot paths (use this after failures!)
- `get_task_state(task_id)` — full state JSON
- `get_task_screenshots(task_id)` — all screenshot file paths

### Page Inspection (use BEFORE writing selectors)
- `screenshot_url(url)` — navigate and screenshot a page
- `inspect_page(url, javascript)` — run JS on a page to find selectors/DOM structure

## Workflow: Setting Up a New Repo/Pipeline

### Step 0: Check current config
```
→ Call get_config_dir_path() to see what exists
→ Call read_config_file("config.yaml") to see current login targets
→ Call read_config_file("repos.yaml") to see configured repos
→ Call read_config_file("environments.yaml") to see configured environments
```

### Step 0.5: Add repo and environment config if needed
```
→ Call write_config_file("repos.yaml", updated_content) to add a new repo
→ Call write_config_file("environments.yaml", updated_content) to add a new environment
→ If login targets need updating: Call write_config_file("config.yaml", updated_content)
  NOTE: After changing login_targets, tell the user to run: uv run devops-agent init
```

### Step 1: Understand what steps are available
```
→ Call list_steps() to see all step primitives and their params
→ Call list_task_configs() to see existing configs for reference
```

### Step 2: Inspect the target page
```
→ Call screenshot_url(url) to see the page layout
→ Open the screenshot to identify buttons, inputs, selectors
→ Call inspect_page(url, js) to find data-testid attributes and DOM structure
  Example JS: '[...document.querySelectorAll("[data-testid]")].map(e => ({testid: e.getAttribute("data-testid"), tag: e.tagName, text: e.textContent.slice(0,50)}))'
```

### Step 3: Write and create the task config
```
→ Call create_task_config(name, yaml_content)
→ Include browser.screenshot steps at key points for debugging
→ For complex UI (react-select dropdowns, dialogs with overlays):
  - Use browser.eval with JavaScript instead of browser.click
  - Use browser.type for typing into focused elements
  - Use wait.sleep between steps for async UI updates
```

### Step 4: Run and debug
```
→ Call run_task("task_config: my-task\nvariables: {}")
→ If it fails:
  1. Call debug_task(task_id) — read the error AND look at screenshots
  2. Call read_task_config(name) to see the current config
  3. Fix the issue (wrong selector, missing wait, overlay blocking clicks)
  4. Call update_task_config(name, fixed_yaml) with the corrected config
  5. Call run_task() again
→ Repeat until it succeeds
```

## Common Patterns

### Atlassian/Bitbucket react-select dropdowns
These are NOT regular `<select>` elements. CSS clicks fail because overlays intercept them. Use:
```yaml
- step: browser.eval
  name: "Focus and type in react-select"
  params:
    expression: >
      (() => {
        const input = document.querySelector('[data-testid="my-select--select--input-container"] input');
        if (!input) return 'not found';
        input.focus();
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(input, 'my-value');
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'typed';
      })()
```

### Clicking buttons behind overlays
```yaml
- step: browser.eval
  name: "Click via JS"
  params:
    expression: >
      (() => {
        const btn = document.querySelector('button[data-testid="my-button"]');
        if (!btn) return 'not found';
        if (btn.disabled) { btn.removeAttribute('disabled'); }
        btn.click();
        return 'clicked';
      })()
```

### Finding selectors on a page
```
→ Call inspect_page(url, '[...document.querySelectorAll("button")].map(b => ({text: b.textContent.trim().slice(0,40), testid: b.getAttribute("data-testid"), classes: b.className.slice(0,60)}))')
→ Call inspect_page(url, '[...document.querySelectorAll("[data-testid]")].map(e => e.getAttribute("data-testid"))')
→ Call inspect_page(url, '[...document.querySelectorAll("[role=dialog]")].map(d => d.innerHTML.slice(0,500))')
```

### Debugging a failed click
When `browser.click` fails with "timeout exceeded":
1. Check the error — does it say "element intercepts pointer events"? → Use `browser.eval` with JS click
2. Check the error — does it say "element is not enabled"? → A prerequisite step didn't complete (e.g., dropdown selection)
3. Check the screenshot — is the page showing what you expect? → Maybe auth expired or URL is wrong

### Adding debug screenshots
Always add `browser.screenshot` steps at key decision points:
```yaml
- step: browser.screenshot
  name: "Debug: after clicking X"
  params:
    filename: "debug_after_x.png"
    full_page: false
```

## Variable Substitution
Steps support `${var}` syntax. Variables come from:
- Activation file `variables` dict
- Prior step outputs (e.g., `${clone_dir}`, `${pr_url}`)
- Use `get_global_configs()` to see what's available from repo/env configs

## What NOT to Do
- Don't create Python scripts to do what task configs can do
- Don't modify the agent's step implementations
- Don't hardcode paths — use the config system
- Don't skip the screenshot_url step for new pages — you'll waste runs guessing selectors
