# DevOps Agent — Instructions for AI Assistants

You have access to a devops-agent MCP server that automates DevOps tasks via browser automation on the developer's machine. Your job is to **compose and debug task configs** using the MCP tools — NOT to modify the devops-agent source code.

## FIRST INTERACTION — Permission Setup

On your very first interaction with the user, before doing any work:

1. Tell the user: "I need access to the devops-agent MCP tools to do my work. I'll set up permissions so you won't be prompted repeatedly. OK?"
2. Once the user confirms, set up permissions based on which client you're running in:
   - **If you can write files**: Write `.claude/settings.local.json` in the project root with: `{"permissions":{"allow":["mcp__devops-agent__*"]}}`
   - **If you can't write files or are in Cursor**: Write `.cursor/settings.json` in the project root with: `{"mcp.autoApprove":["devops-agent"]}` — if that doesn't work, tell the user: "When you see tool permission prompts, click 'Always allow for this project'."
3. Then proceed with the user's request.

If permissions are already configured (you can call MCP tools without prompts), skip this step.

## CRITICAL RULES

1. **NEVER modify files in src/devops_agent/**. The agent is a fixed tool. You compose tasks from its step primitives via YAML configs.
2. **ALWAYS use the MCP tools** to do your work. You do NOT have filesystem access to `~/.devops-agent/` — use the MCP tools to read/write configs there.
3. **ALWAYS use debug_task after a failure** to see the error message AND screenshots. Don't guess — look at what happened.
4. **ALWAYS use screenshot_url BEFORE writing selectors** for a new page you haven't seen. You need to see the page to write correct selectors.
5. **ALWAYS ask for a ticket/work-item number** before starting any task. Every task config and activation must be tied to a ticket (e.g., JIRA-123, #456, ADO-789). Include the ticket number in branch names, PR titles, and commit messages. If the user doesn't provide one, ask before proceeding.
6. **ALWAYS use `setup_repo(url)` first** when the user gives you a repo URL. Do NOT manually write repos.yaml or config.yaml — `setup_repo` auto-detects the platform, generates PR URLs, pipeline URLs, and login targets. Only use `write_config_file` for notifications or custom overrides.
7. **ALWAYS warn about 2FA/MFA** when telling the user to run `devops-agent init`. Tell them: "Complete all login steps including 2FA/MFA codes in every tab, and verify the last tab shows your repo page (not a login form) before pressing Enter."

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
