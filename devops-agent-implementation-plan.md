# DevOps MCP Agent — Implementation Plan

A local, Windows-only MCP tool that executes DevOps tasks composed by developers. Cursor (or any MCP-compatible client) is the calling agent.

---

## 1. Scope and principles

**What this is:** A local MCP tool running on a Windows dev laptop that executes DevOps tasks composed by the dev. Cursor (or any MCP-compatible client) is the calling agent.

**Non-negotiable principles:**

- Everything local. No inbound network connections. No exposed ports.
- All state on disk (YAML + JSON). Inspectable, diffable, debuggable.
- OSS throughout. No proprietary dependencies.
- Single-user, single-task-at-a-time. Concurrency is explicitly deferred.
- Pause-and-notify on failure. No silent retries.
- Credentials live in the browser profile and the dev's existing git setup. Never in config files.

---

## 2. Technology stack

- **Language:** Python 3.11
- **Package management:** uv
- **MCP framework:** Anthropic Python MCP SDK (FastMCP)
- **Browser automation:** Playwright (persistent context, Edge channel)
- **Screenshots:** mss (full/region), pywin32 PrintWindow (window-specific, occluded-safe)
- **OS input:** PyAutoGUI (with DPI awareness enabled at startup), pygetwindow (window enumeration)
- **OCR/vision:** RapidOCR (ONNX, local, no network)
- **Shell:** Git Bash (resolved from Git for Windows install)
- **Config validation:** Pydantic v2
- **YAML parsing:** PyYAML
- **File watching:** watchdog
- **Logging:** structlog (structured JSON)
- **HTTP:** httpx (for monitor health checks)
- **Dev tooling:** Ruff, mypy, pytest, pytest-playwright

**Platform:** Windows only. Mac deferred.

---

## 3. Project structure

```
devops-agent/
├── pyproject.toml
├── uv.lock
├── README.md
├── docs/
│   ├── getting-started.md          # dev-facing
│   ├── authoring-type-configs.md   # dev-facing
│   ├── authoring-globals.md        # platform-eng-facing
│   └── step-primitives.md          # reference for type-config authors
├── examples/
│   ├── globals/                    # example repos.yaml, environments.yaml, etc.
│   └── type-configs/               # example deploy-new-env, hotfix, rollback
├── src/devops_agent/
│   ├── __init__.py
│   ├── cli.py                      # devops-agent init/serve/resume/validate/list
│   ├── server.py                   # FastMCP registration entrypoint
│   ├── config/
│   │   ├── schema.py               # Pydantic models for all config files
│   │   ├── loader.py               # load + validate globals and type-configs
│   │   └── paths.py                # ~/.devops-agent/ resolution
│   ├── tasks/
│   │   ├── models.py               # Task, Activation, TaskState, StepResult
│   │   ├── lifecycle.py            # state machine, folder moves
│   │   ├── state_store.py          # read/write .state.json atomically
│   │   ├── watcher.py              # watchdog-based pending/ observer
│   │   └── executor.py             # runs a task through its step sequence
│   ├── steps/                      # step primitives, one module each
│   │   ├── base.py                 # Step protocol, StepContext, StepResult
│   │   ├── registry.py             # name -> Step class
│   │   ├── shell.py                # shell_run primitive
│   │   ├── git.py                  # clone, branch, commit, push (via shell)
│   │   ├── browser_navigate.py
│   │   ├── browser_click.py
│   │   ├── browser_fill.py
│   │   ├── browser_screenshot.py
│   │   ├── os_click.py
│   │   ├── os_type.py
│   │   ├── screenshot.py
│   │   ├── ocr_find.py
│   │   ├── pr_create.py            # composite: navigate + fill template + submit
│   │   ├── pr_wait_merge.py        # poll or suspend
│   │   ├── deploy_trigger.py       # navigate deploy portal + click
│   │   ├── monitor_http.py
│   │   ├── monitor_version.py
│   │   ├── notify.py               # post to Slack/Teams via browser
│   │   └── wait.py                 # explicit delays, rarely used
│   ├── browser/
│   │   ├── profile.py              # persistent context management
│   │   ├── session.py              # one active session per task
│   │   └── pr_fillers/             # per-platform PR page fillers
│   │       ├── azure_devops.py
│   │       ├── github.py
│   │       └── gitlab.py
│   ├── capture/
│   │   ├── mss_backend.py          # full + region screenshots
│   │   └── win_backend.py          # pywin32 PrintWindow
│   ├── vision/
│   │   └── ocr.py                  # RapidOCR wrapper, find-text-in-image
│   ├── os_control/
│   │   ├── input.py                # PyAutoGUI wrappers
│   │   ├── dpi.py                  # SetProcessDpiAwareness on startup
│   │   └── windows.py              # pygetwindow helpers
│   ├── notifications/
│   │   ├── templates.py            # render with ${} vars
│   │   ├── slack_web.py            # drive Slack web via browser
│   │   └── teams_web.py            # drive Teams web via browser
│   ├── resume/
│   │   └── resume.py               # re-entry logic from state file
│   └── utils/
│       ├── logging.py              # structlog config
│       └── paths.py
├── scripts/
│   └── install_playwright_browsers.py
└── tests/
    ├── unit/                       # config parsing, schema validation, etc.
    ├── integration/                # mocked browser flows
    └── fixtures/
```

---

## 4. Configuration model

Lives under `~/.devops-agent/` on each dev's laptop. Four global files (platform eng authored, often git-synced across team) plus a directory of dev-authored type-configs.

### `config.yaml` — global agent behavior

Contains: work directory root, Edge profile directory, default merge detection mode, default polling cadence and timeout, default notification channels, paths to other config files, logging verbosity.

### `repos.yaml` — repo registry

Keyed by short name. For each: clone URL, platform type (`azure_devops` | `github` | `gitlab`), PR creation URL template, PR view URL template, PR template path inside the repo, title convention pattern, default reviewers, required labels.

### `environments.yaml` — deploy target registry

Keyed by short name. For each: deploy portal URL, deploy trigger type (`portal_click` | `pipeline_url` | `cli`), required parameters, health check configuration (URLs, expected status/body), monitor timeout default, associated repo(s).

### `notifications.yaml` — channels and message templates

Channel definitions: named channels mapped to Slack/Teams web deep-link URLs and platform type. Templates: one string per event type with variable placeholders, rendered at send time. Per-channel formatting adapters (Slack mrkdwn vs Teams markdown).

### `task-configs/*.yaml` — dev-authored

Each file declares a task *type* plus its specific params and step sequence. Shape:

- `name` — unique identifier (used by activation files)
- `description` — human-readable purpose
- `references` — repo key, environment key (optional, depending on type)
- `merge_detection` — `poll` or `suspend`, with interval/timeout if poll
- `notifications` — per-event channel routing (overrides defaults)
- `steps` — ordered list of step invocations, each specifying a step primitive name and its parameters
- `on_failure` — defaults to "pause and notify," overridable per step if needed (but v1 keeps it uniform)

### `tasks/` — runtime folders

- `pending/` — activation files awaiting pickup
- `in_progress/` — currently executing (one at a time), with matching `.state.json`
- `waiting/` — paused for PR merge (suspend mode) or blocked by failure, with `.state.json`
- `done/<task_id>/` — completed tasks, archived with state, screenshots, logs
- `failed/<task_id>/` — abandoned tasks, same contents for post-mortem

### Activation file

What a dev drops into `pending/` to run something. Minimal YAML: references a task-config by name, supplies per-run variables (work item, summary, branch suffix, etc.). Agent merges activation + type-config + globals at execution time.

---

## 5. Step primitives

The agent ships a fixed, tested set of step primitives. Devs compose them in their type-configs. Each primitive:

- Has a stable name used in YAML (`shell.run`, `browser.navigate`, `pr.create`, etc.)
- Declares its parameter schema (Pydantic-validated)
- Returns a structured `StepResult` (status, outputs, screenshots, errors)
- Updates the task state file on completion
- Is individually testable

### v1 primitive list

- `shell.run` — Git Bash command, captures stdout/stderr/exit
- `git.clone`, `git.branch`, `git.commit`, `git.push` — thin wrappers over `shell.run` with structured params
- `browser.navigate` — goto a URL in the agent's Edge profile
- `browser.click`, `browser.fill`, `browser.wait_for` — DOM operations via Playwright
- `browser.screenshot` — full page or element-scoped
- `screenshot.capture` — OS-level full/region/window (mss + pywin32)
- `ocr.find_text` — locate text on screen, return bbox
- `os.click`, `os.type`, `os.hotkey` — PyAutoGUI primitives with DPI awareness
- `pr.create` — composite: navigates to repo's PR-create URL, loads repo's PR template from the cloned working tree, renders template with supplied fills, selects reviewers and labels, submits, returns PR URL and screenshot
- `pr.wait_merge` — poll mode (periodically re-navigates to PR URL, reads state) or suspend mode (moves task to `waiting/`, returns immediately)
- `deploy.trigger` — navigates to environment's deploy portal URL, performs the env-specific trigger action (declared in `environments.yaml`)
- `monitor.http_check` — polls a URL for expected status/body, records results in state
- `monitor.version_match` — polls a version endpoint until it returns the expected value
- `notify.send` — selects channel, renders template, drives Slack/Teams web to post, screenshots the posted message
- `wait.sleep` — explicit delay (rarely used, but available)

Each primitive's behavior is fully defined in `docs/step-primitives.md` so dev authors have a reliable reference.

---

## 6. Task execution engine

### Flow

1. Watcher detects a new file in `pending/`. Loads and validates as an activation. Looks up the referenced type-config, validates that too.
2. Executor acquires the single-task lock (simple file lock; commented hooks for future concurrency).
3. Moves activation file to `in_progress/`. Creates `.state.json` with initial state.
4. Merges activation vars + type-config + globals into a `TaskContext`.
5. Iterates the step sequence. For each step:
   - Logs entry (step name, params)
   - Invokes the primitive with context
   - Captures `StepResult` and updates state file atomically
   - On success: proceed to next step
   - On failure: stop, notify via `notify.send` with a `task_blocked` template, move task to `waiting/`, release lock, return control to caller
   - On special pause (e.g., `pr.wait_merge` in suspend mode): move task to `waiting/`, release lock, return control. Task resumes only on explicit `devops-agent resume <task-id>` (CLI or MCP tool call).
6. After final step: fire `task_complete` notification, move artifacts to `done/<task_id>/`, release lock.

### State file contents (`.state.json`)

- Task ID, activation file path, type-config name
- Current phase (`in_progress` | `waiting_merge` | `blocked` | `completed` | `failed`)
- Step-by-step log: each step's name, params, start/end timestamps, result status, outputs (PR URL, pipeline URL, version SHA), screenshot paths, error messages
- Merge context (PR URL, detected status, last check timestamp) when relevant
- Resume pointer (which step index to resume from)

### Atomicity

State file writes use temp-file-plus-rename. Any external reader sees either the old state or the fully-written new state, never a partial.

---

## 7. MCP tool surface

FastMCP exposes these tools to Cursor. All thin wrappers over the executor and state store — the MCP surface is intentionally small.

- `list_task_configs()` — return available type-configs by name, with description
- `list_tasks(status: pending|in_progress|waiting|done|failed)` — return task metadata
- `run_task(activation_path)` — enqueue an activation file (or accept inline YAML, write to `pending/`)
- `resume_task(task_id)` — resume a waiting task from its checkpoint
- `cancel_task(task_id)` — move from `waiting/` or `in_progress/` to `failed/`, release lock
- `get_task_state(task_id)` — return current state file contents
- `get_task_screenshots(task_id)` — return paths/images of captured screenshots
- `validate_config(path)` — validate any config or type-config file without running

Cursor uses these to: enumerate available tasks, trigger runs, check status, surface state to the dev, resume on dev instruction.

---

## 8. Browser profile management

### One-time setup via `devops-agent init`

- Reads `config.yaml` to determine profile directory (default: `C:\devops-agent\edge-profile`)
- Launches Edge with persistent context, `--no-first-run`, `--no-default-browser-check`
- Iterates a list of "login targets" (from config — SSO provider, each platform's repo host, each deploy portal, Slack workspace, Teams workspace)
- Opens each target in a new tab, waits for dev to authenticate
- On confirmation, closes the browser. Profile is warm.
- Runs sanity checks: re-launches headless, navigates to one known-authenticated URL, confirms no login redirect. Reports health.
- Verifies screenshot capture works (captures a test region, confirms non-black pixels). Reports.
- Verifies Git Bash is resolvable. Reports.
- Exits with clear green/red per check.

### Runtime usage

- Executor starts a browser session at task start, tears it down at task end (or on suspend). Session = one Playwright persistent context.
- Each browser primitive operates on the current session's context.
- On detected login redirect (any `browser.navigate` landing on `login.microsoftonline.com` or equivalent), primitive returns failure with reason `auth_required`. Task pauses and notifies dev to re-run init.
- DPI awareness (`SetProcessDpiAwareness(2)`) is set at process startup, before any browser or screenshot call.

---

## 9. Notifications

### Channel configuration

`notifications.yaml` defines named channels with Slack/Teams web deep-link URLs and a platform type tag. Channel names are referenced by task-configs and templates.

### Template rendering

Templates use `${var}` placeholders. Available variables are drawn from the task context (`task_id`, `repo`, `env`, `pr_url`, `deployed_version`, `error_message`, `failed_step`, `duration`, etc.) — the full variable list is documented and version-stable.

### Send flow

1. Template rendered against task context
2. Browser session opens a new tab to the channel's deep-link URL
3. Waits for message composer to be interactable (uses platform-specific selectors for Slack web / Teams web)
4. Clears composer (defensive), pastes or types message (paste for multi-line to avoid autocomplete nonsense)
5. Submits with platform-appropriate shortcut
6. Screenshots the posted message as evidence, stores path in state
7. Closes or backgrounds the tab

### Failure mode

If notification can't be delivered (composer not found, login redirect, etc.), logs the failed attempt to state file and moves on. Never fails the task because of notification issues.

### Rate limit

Defensive delays between rapid notifications (e.g., after a successful deploy, the three-event burst of `pr_merged → deploy_succeeded → task_complete` gets spread out naturally by the click-driven flow, but a minimum interval is enforced).

---

## 10. Failure handling — uniform "pause and notify"

Every step primitive can return failure. The executor's response is uniform in v1:

1. Capture full context: step name, params, error, stderr, screenshots at time of failure
2. Write all of the above to state file
3. Render `task_blocked` notification template, send via `notify.send` (best-effort; if this also fails, just log locally)
4. Move task file from `in_progress/` to `waiting/` with state file intact
5. Release task lock
6. Return from executor; MCP tool surfaces the failure to Cursor

### Recovery options for the dev

- `devops-agent resume <task-id>` — retry from the failed step (state file's resume pointer)
- `devops-agent cancel <task-id>` — give up, move to `failed/`
- Edit the activation or type-config and resume — agent re-validates before resuming
- Manual fix outside the agent, then resume

This design keeps the agent dumb about recovery — the human decides every non-trivial recovery step. Consistent with "agent does execution, human does thinking."

---

## 11. CLI commands

Exposed via `devops-agent` entry point:

- `devops-agent init` — one-time setup (profile warmup, login targets, sanity checks)
- `devops-agent serve` — runs the MCP tool over stdio (what Cursor's MCP config points at)
- `devops-agent validate <path>` — validate any config/type-config/activation
- `devops-agent run <activation-file>` — CLI alternative to MCP `run_task`, useful for debugging
- `devops-agent resume <task-id>` — resume a waiting task
- `devops-agent cancel <task-id>` — move task to failed
- `devops-agent list [--status <status>]` — list tasks
- `devops-agent logs <task-id>` — pretty-print state file
- `devops-agent doctor` — re-run sanity checks (profile valid, screenshot works, bash resolvable, RapidOCR model present)

CLI and MCP tool share the same underlying executor. Everything scriptable, everything automatable.

---

## 12. Implementation phases

### Phase 1 — Foundations (week 1-2)

- Project scaffolding with uv + Ruff + mypy + pytest
- Config schemas (Pydantic) for all four globals and type-config/activation
- Config loader with clear validation errors
- CLI skeleton (argparse or typer), `validate`, `doctor`, `logs`
- Logging setup (structlog)

### Phase 2 — Core primitives (week 2-3)

- `shell.run` with Git Bash resolution
- Git primitives
- Screenshot backends (mss + pywin32)
- DPI awareness startup hook
- PyAutoGUI wrappers with DPI checks
- RapidOCR wrapper (model download script, `ocr.find_text`)

### Phase 3 — Browser layer (week 3-4)

- Playwright persistent context manager
- `devops-agent init` with login target walkthrough
- Sanity/doctor checks for profile health
- Browser primitives: navigate, click, fill, wait_for, screenshot
- Login-redirect detection

### Phase 4 — Task lifecycle (week 4-5)

- State file format and atomic read/write
- Task lifecycle state machine
- Watchdog-based pending folder watcher
- Single-task lock (commented concurrency hooks)
- Executor loop
- `run_task`, `resume_task`, `cancel_task` CLI commands

### Phase 5 — MCP surface (week 5)

- FastMCP registration
- Tool wrappers over executor
- Cursor config example
- End-to-end test with a toy task-config (just shell steps)

### Phase 6 — PR primitives (week 5-6)

- Repo platform detection and per-platform fillers
- `pr.create` composite
- `pr.wait_merge` (poll and suspend modes)
- PR template reading from cloned repo
- Integration test against a real test repo on each of ADO/GitHub/GitLab

### Phase 7 — Deploy and monitor (week 6-7)

- `deploy.trigger` with environment-declared actions
- `monitor.http_check` and `monitor.version_match`
- Screenshots interleaved with monitor polls

### Phase 8 — Notifications (week 7)

- Template rendering
- Slack web driver
- Teams web driver
- `notify.send` primitive
- Failure-mode handling (never block task)

### Phase 9 — Hardening (week 8)

- End-to-end integration test: full deploy-new-env flow on a test Azure DevOps repo + Azure staging env + test Slack channel
- Error-path tests: bad configs, auth expiry mid-task, deploy failure, notification failure
- Documentation: all dev-facing and platform-eng-facing docs in `docs/`
- Example configs and type-configs in `examples/`
- Internal pilot with one or two devs and one platform eng

### Phase 10 — v1 release

- Package for `uv tool install`
- Installation and init instructions
- Known-issues doc (UAC, lock screen, EDR, DPI edge cases)
- Feedback loop with pilot users

**Estimated calendar time:** 8-10 weeks of solid work for one engineer, faster with two.

---

## 13. Explicitly deferred to v2

- Concurrency (multiple tasks running in parallel). Code has commented hooks.
- Mac support. Stack choices keep it feasible (drop pywin32, add PyObjC/screencapture backend) but it's not v1.
- Credential automation (OS keychain, vault integration). All credential touchpoints carry TODO comments.
- Inbound webhook-driven triggers (e.g., resume on PR-merged webhook). Out of scope because of "no inbound" principle.
- Auto-generation of task-configs from dev intent. Out of scope per this iteration's decision.
- Type-config dependencies ("run only if X succeeded"). Schema leaves room.
- Partial-step retry with checkpoint granularity inside a step. v1 retries whole steps only.
- Centralized audit log shipping. Local artifacts only in v1.
- Other agents (Claude Code, Cline, Continue) — architecture supports them trivially since it's just MCP; no code changes needed, just documented MCP config for each.

---

## 14. Risks and mitigations

**EDR/antivirus interference on enterprise laptops.** Mitigation: engage security team before pilot, submit agent binary/behavior for whitelisting, document expected capabilities clearly. Single biggest non-technical risk.

**Playwright ↔ Edge version drift breaking browser driver.** Mitigation: pin Playwright version in `pyproject.toml`, test upgrades before rolling out, disable Edge auto-update in pilot via group policy if possible.

**Slack/Teams web UI changes breaking notification selectors.** Mitigation: selectors in a single module per platform, with fallback strategies (multiple selectors tried in order); notification failure never breaks a task; easy to patch in a point release.

**Login session expiry mid-task.** Mitigation: detected at browser primitive level, uniform auth-required failure mode, clear dev instruction to re-init. Resume picks up cleanly.

**Dev writes a type-config with an incorrect step sequence.** Mitigation: Pydantic validates step names and param shapes at load time; `validate` command pre-flights; failure at step runtime is "pause and notify" so no destructive action slips through.

**DPI scaling mismatch breaking PyAutoGUI clicks.** Mitigation: `SetProcessDpiAwareness(2)` at startup, documented as a known failure mode in doctor script if it can't be set.

**Windows lock screen during long waits.** Mitigation: detected as a distinct failure mode (`os_control` can identify `LockAppHost` foreground), task enters waiting state same as other blocks.

---

## 15. What this plan explicitly is and isn't

**It is:** a concrete, buildable Windows-only MCP tool that lets a DevOps-minded dev compose tasks from a set of tested primitives, run them semi-autonomously with browser + OS + shell automation, get notified via Slack/Teams, and resume/recover deterministically. Honest about the authoring burden it places on platform eng and devs; honest about where it saves time (execution attention) vs where it doesn't (total elapsed time).

**It isn't:** a zero-config "deploy anything" box. Setup work is real. It isn't cross-platform in v1. It doesn't do auto-retry or auto-recovery — humans decide recovery. It isn't an agent framework; it's a tool that agents call.
