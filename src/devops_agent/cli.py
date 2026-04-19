"""CLI entrypoint — devops-agent init/serve/run/resume/cancel/validate/list/logs/doctor."""

from __future__ import annotations

import asyncio
import json
import sys
import warnings
from pathlib import Path

# Suppress noisy asyncio cleanup warnings on Windows during Playwright teardown
warnings.filterwarnings("ignore", message="unclosed transport", category=ResourceWarning)

# Patch asyncio event loop to suppress "Event loop is closed" RuntimeError on Windows
# This happens when Playwright's subprocess transports are garbage collected after the loop closes
_original_del = asyncio.proactor_events._ProactorBasePipeTransport.__del__  # type: ignore[attr-defined]

def _silenced_del(self: object, _warn: object = None) -> None:  # type: ignore[no-untyped-def]
    try:
        _original_del(self)
    except RuntimeError:
        pass

asyncio.proactor_events._ProactorBasePipeTransport.__del__ = _silenced_del  # type: ignore[attr-defined]

import typer
from rich.console import Console
from rich.table import Table

from devops_agent.config.loader import (
    ConfigError,
    load_activation,
    load_agent_config,
    load_all_task_configs,
    validate_file,
)
from devops_agent.config.paths import (
    ensure_dirs,
    get_config_dir,
    get_tasks_subdir,
    resolve_edge_binary,
    resolve_git_bash,
)
from devops_agent.tasks.lifecycle import (
    create_task,
    find_task,
    move_to_failed,
)
from devops_agent.tasks.state_store import list_states
from devops_agent.utils.logging import setup_logging

app = typer.Typer(
    name="devops-agent",
    help="Local Windows-only MCP tool for DevOps task execution.",
    no_args_is_help=True,
)
console = Console(highlight=False)

OK = "[green]OK[/green]"
FAIL = "[red]FAIL[/red]"
WARN = "[yellow]WARN[/yellow]"


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
    json_logs: bool = typer.Option(True, "--json-logs/--no-json-logs", help="JSON log output"),
) -> None:
    setup_logging(verbose=verbose, json_output=json_logs)


# ── sample configs ─────────────────────────────────────────────────────────────

SAMPLE_CONFIG = """\
# DevOps Agent — global configuration
# Docs: docs/authoring-globals.md

work_dir: "~/.devops-agent/work"                  # root dir for task working trees
edge_profile_dir: "~/.devops-agent/edge-profile"   # persistent Edge browser profile
default_merge_detection: poll                       # how to detect PR merges: poll | suspend
poll_interval_seconds: 60                           # seconds between PR merge checks
poll_timeout_seconds: 3600                          # max seconds to wait for PR merge
default_notification_channels: []                   # channel names to notify on failure (from notifications.yaml)
log_level: INFO                                     # logging verbosity: DEBUG | INFO | WARNING | ERROR
log_json: true                                      # true = structured JSON logs, false = human-readable

# URLs the dev must authenticate against during 'devops-agent init'.
# The agent opens each in Edge and waits for the dev to log in.
# Uncomment and add your URLs:
login_targets: []                                   # list of SSO / platform URLs to pre-authenticate
  # - "https://login.microsoftonline.com"           # Azure AD / Entra SSO
  # - "https://dev.azure.com"                       # Azure DevOps
  # - "https://app.slack.com"                       # Slack workspace
"""

SAMPLE_REPOS = """\
# Repository registry — one entry per repo the agent interacts with
# Docs: docs/authoring-globals.md
# Key each repo by a short name, then reference that name in task-configs.

repos: {}                                           # map of short-name -> repo config
  # my-service:                                     # short name used in task-config references
  #   clone_url: "https://dev.azure.com/org/project/_git/my-service"   # git clone URL
  #   platform: azure_devops                        # hosting platform: azure_devops | github | gitlab
  #   pr_create_url_template: "https://dev.azure.com/org/project/_git/my-service/pullrequestcreate?sourceRef=${branch_name}"  # URL to open PR creation page (${branch_name} substituted)
  #   pr_view_url_template: "https://dev.azure.com/org/project/_git/my-service/pullrequest/${pr_id}"  # URL to view a PR (${pr_id} substituted)
  #   pr_template_path: ".azuredevops/pull_request_template.md"  # path to PR template inside the repo
  #   title_convention: "^(feat|fix|chore)\\\\(.*\\\\): .+"      # regex PR titles must match (empty = no check)
  #   default_reviewers:                            # reviewers auto-added to every PR
  #     - "team-lead@example.com"
  #   required_labels:                              # labels auto-added to every PR
  #     - "auto-deploy"
"""

SAMPLE_ENVIRONMENTS = """\
# Deploy target registry — one entry per environment the agent can deploy to
# Docs: docs/authoring-globals.md
# Key each environment by a short name, then reference that name in task-configs.

environments: {}                                    # map of short-name -> environment config
  # staging:                                        # short name used in task-config references
  #   deploy_portal_url: "https://portal.azure.com/#resource/my-staging-app"  # URL to the deploy portal/page
  #   deploy_trigger: portal_click                  # how to trigger deploy: portal_click | pipeline_url | cli
  #   required_params:                              # params the dev must supply at activation time
  #     version: "Git SHA or tag to deploy"         # param name -> description
  #   health_checks:                                # list of endpoints to verify after deploy
  #     - url: "https://staging.example.com/health" # health check URL
  #       expected_status: 200                      # expected HTTP status code
  #       expected_body: "ok"                       # substring expected in response body (empty = skip)
  #       timeout_seconds: 300                      # max seconds to wait for healthy response
  #   monitor_timeout_seconds: 600                  # overall monitoring timeout after deploy trigger
  #   repos:                                        # which repos deploy to this environment
  #     - my-service
"""

SAMPLE_NOTIFICATIONS = """\
# Notification channels and message templates
# Docs: docs/authoring-globals.md
# Channels are keyed by name and referenced from task-configs.

channels: {}                                        # map of channel-name -> channel config
  # dev-deploys:                                    # channel name used in task-config notifications
  #   url: "https://app.slack.com/client/T12345/C12345"  # Slack/Teams web deep-link URL
  #   platform: slack                               # platform type: slack | teams
  # team-alerts:
  #   url: "https://teams.microsoft.com/l/channel/19%3Axyz/General"
  #   platform: teams

# Message templates — use ${var} placeholders.
# Available vars: task_id, task_config_name, repo, env, pr_url,
#                 deployed_version, error_message, failed_step, duration
templates:
  task_started: "Task ${task_id} started: ${task_config_name}"                        # sent when a task begins execution
  task_blocked: "Task ${task_id} blocked at step '${failed_step}': ${error_message}"  # sent when a step fails and task pauses
  task_complete: "Task ${task_id} completed successfully"                             # sent when all steps finish
  pr_created: "PR created: ${pr_url}"                                                # sent after pr.create succeeds
  deploy_triggered: "Deploy triggered for ${env}"                                    # sent after deploy.trigger succeeds
  deploy_succeeded: "Deploy to ${env} succeeded"                                     # sent after health checks pass
"""

SAMPLE_TASK_CONFIG = """\
# Example task config — uncomment and customize
# Docs: docs/authoring-type-configs.md
# See docs/step-primitives.md for all available steps and parameters.
#
# Place your task configs in this directory as .yaml files.
# Each file defines one reusable workflow composed from step primitives.
# Variables use ${var} syntax — supplied by the activation file or prior step outputs.
#
# name: deploy-hotfix                               # unique identifier for this task type
# description: "Clone, branch, fix, commit, push, PR"  # human-readable purpose
# references:
#   repo: my-service                                # key from repos.yaml — loads clone_url, platform, etc.
#   env: staging                                    # key from environments.yaml — loads deploy config
# steps:
#   - step: git.clone                               # clone the repo to work_dir
#     name: "Clone repository"                      # human-readable label (shown in logs)
#     params:
#       url: "${clone_url}"                         # from repo config via references
#
#   - step: git.branch                              # create and checkout a new branch
#     name: "Create hotfix branch"
#     params:
#       branch: "hotfix/${branch_suffix}"           # ${branch_suffix} from activation variables
#       cwd: "${clone_dir}"                         # output from git.clone step
#       base: main                                  # branch off origin/main
#
#   - step: shell.run                               # run any shell command via Git Bash
#     name: "Apply fix"
#     params:
#       command: "${fix_command}"                    # shell command from activation variables
#       cwd: "${clone_dir}"
#
#   - step: git.commit                              # stage all changes and commit
#     name: "Commit changes"
#     params:
#       message: "fix: ${commit_message}"           # commit message from activation variables
#       cwd: "${clone_dir}"
#
#   - step: git.push                                # push branch to remote
#     name: "Push branch"
#     params:
#       branch: "hotfix/${branch_suffix}"
#       cwd: "${clone_dir}"
#
#   - step: pr.create                               # open PR via browser automation
#     name: "Create pull request"
#     params:
#       title: "fix: ${pr_title}"                   # PR title (validated against repo title_convention)
#       source_branch: "hotfix/${branch_suffix}"    # branch to merge from
#       target_branch: main                         # branch to merge into
"""

_SAMPLE_FILES: dict[str, str] = {
    "config.yaml": SAMPLE_CONFIG,
    "repos.yaml": SAMPLE_REPOS,
    "environments.yaml": SAMPLE_ENVIRONMENTS,
    "notifications.yaml": SAMPLE_NOTIFICATIONS,
}


def _write_sample_configs(config_dir: Path) -> int:
    """Write sample config files if they don't already exist. Returns count written."""
    written = 0
    for filename, content in _SAMPLE_FILES.items():
        path = config_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            written += 1

    # Sample task-config
    tc_dir = config_dir / "task-configs"
    tc_dir.mkdir(parents=True, exist_ok=True)
    readme = tc_dir / "_example.yaml.sample"
    if not readme.exists():
        readme.write_text(SAMPLE_TASK_CONFIG, encoding="utf-8")
        written += 1

    return written


# ── init ───────────────────────────────────────────────────────────────────────


@app.command()
def init(
    skip_browser: bool = typer.Option(False, "--skip-browser", help="Skip browser profile warmup"),
) -> None:
    """One-time setup: create dirs, verify prerequisites, warm Edge profile."""
    console.print("[bold]DevOps Agent -- Init[/bold]\n")

    # Create directory structure
    ensure_dirs()
    console.print(f"{OK} Directory structure created")

    # Write sample configs
    config_dir = get_config_dir()
    count = _write_sample_configs(config_dir)
    if count > 0:
        console.print(f"{OK} {count} sample config(s) created in {config_dir}")
        console.print(f"    Edit them to match your environment, then re-run init.")
    else:
        console.print(f"{OK} Config files already exist")

    # Check Git Bash
    bash = resolve_git_bash()
    if bash:
        console.print(f"{OK} Git Bash found: {bash}")
    else:
        console.print(f"{FAIL} Git Bash not found. Install Git for Windows.")
        return

    # Check Edge
    edge = resolve_edge_binary()
    if edge:
        console.print(f"{OK} Microsoft Edge found: {edge}")
    else:
        console.print(f"{FAIL} Microsoft Edge not found.")
        return

    # Load config
    cfg = load_agent_config()

    # Browser profile warmup
    if skip_browser:
        console.print(f"{WARN} Skipping browser profile warmup")
    elif not cfg.login_targets:
        console.print(f"{WARN} No login_targets in config -- skipping browser warmup")
    else:
        console.print(f"\n[bold]Browser profile warmup[/bold]")
        console.print(f"Profile dir: {cfg.edge_profile_dir}")
        console.print(f"Login targets ({len(cfg.login_targets)}):")
        for url in cfg.login_targets:
            console.print(f"  - {url}")

        console.print(
            "\nEdge will open with each login target in a new tab."
            "\nLog in to each one, then return here and press Enter."
        )
        asyncio.run(_warmup_browser_profile(cfg))

    # Screenshot sanity check
    try:
        from devops_agent.capture.mss_backend import capture_full_screen

        test_path = get_config_dir() / "init_test_screenshot.png"
        capture_full_screen(test_path)
        # Verify non-zero file
        if test_path.stat().st_size > 0:
            console.print(f"{OK} Screenshot capture works")
            test_path.unlink(missing_ok=True)
        else:
            console.print(f"{FAIL} Screenshot capture produced empty file")
    except Exception as e:
        console.print(f"{WARN} Screenshot capture test: {e}")

    console.print(f"\n[bold]Init complete.[/bold] Run [cyan]devops-agent doctor[/cyan] for full checks.")


async def _warmup_browser_profile(cfg: "AgentConfig") -> None:  # type: ignore[name-defined]  # noqa: F821
    """Launch Edge with login targets for the dev to authenticate."""
    from devops_agent.browser.profile import create_persistent_context, close_context

    profile_dir = cfg.edge_profile_dir
    profile_dir.mkdir(parents=True, exist_ok=True)

    console.print("\nLaunching Edge...")
    context = await create_persistent_context(profile_dir, headless=False)

    try:
        # Open each login target in a new tab
        for i, url in enumerate(cfg.login_targets):
            if i == 0:
                page = context.pages[0] if context.pages else await context.new_page()
            else:
                page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                console.print(f"  Opened: {url}")
            except Exception as e:
                console.print(f"  {WARN} Could not load {url}: {e}")

        console.print(
            "\n[bold yellow]Authenticate in each tab, then come back here.[/bold yellow]"
        )
        input("Press Enter when done...")

    finally:
        await close_context(context)
        console.print(f"{OK} Browser closed. Profile saved to {profile_dir}")

    # Sanity check: headless re-launch + navigate to first login target
    if cfg.login_targets:
        console.print("Verifying session (headless)...")
        try:
            ctx2 = await create_persistent_context(profile_dir, headless=True)
            page = ctx2.pages[0] if ctx2.pages else await ctx2.new_page()
            await page.goto(cfg.login_targets[0], wait_until="domcontentloaded", timeout=15000)
            final_url = page.url
            await close_context(ctx2)

            if "login" in final_url.lower() or "signin" in final_url.lower():
                console.print(f"{WARN} Session check: landed on login page ({final_url})")
                console.print("  You may need to re-run init and authenticate again.")
            else:
                console.print(f"{OK} Session check passed (no login redirect)")
        except Exception as e:
            console.print(f"{WARN} Session verification failed: {e}")


# ── serve ──────────────────────────────────────────────────────────────────────


@app.command()
def serve() -> None:
    """Run the MCP tool over stdio (for Cursor/MCP client)."""
    from devops_agent.server import create_server

    server = create_server()
    server.run(transport="stdio")


# ── validate ───────────────────────────────────────────────────────────────────


@app.command()
def validate(path: Path = typer.Argument(..., help="Path to config/type-config/activation YAML")) -> None:
    """Validate any config file without running."""
    try:
        validate_file(path)
        console.print(f"{OK} {path} is valid")
    except ConfigError as e:
        console.print(f"{FAIL} {e}")
        raise typer.Exit(1)


# ── run ────────────────────────────────────────────────────────────────────────


@app.command(name="run")
def run_task(
    activation_file: Path = typer.Argument(None, help="Path to activation YAML file"),
    task_config: str = typer.Option(None, "--task-config", "-t", help="Task config name (shortcut — no activation file needed for zero-variable tasks)"),
) -> None:
    """Run a task from an activation file or by task-config name."""
    if task_config:
        # Shortcut: create activation inline from task-config name
        from devops_agent.config.schema import Activation
        activation = Activation(task_config=task_config)
    elif activation_file:
        try:
            activation = load_activation(activation_file)
        except ConfigError as e:
            console.print(f"{FAIL} Invalid activation file: {e}")
            raise typer.Exit(1)
    else:
        console.print(f"{FAIL} Provide either an activation file or --task-config name")
        raise typer.Exit(1)

    task_id = activation.task_id or ""
    state = create_task(
        task_config_name=activation.task_config,
        activation_file=str(activation_file or task_config),
        variables=activation.variables,
        task_id=task_id,
    )
    console.print(f"{OK} Task created: {state.task_id}")

    from devops_agent.tasks.executor import execute_task

    try:
        final_state = asyncio.run(execute_task(state.task_id))
        console.print(f"{OK} Task {state.task_id} finished: {final_state.phase.value}")
    except Exception as e:
        console.print(f"{FAIL} Task failed: {e}")
        raise typer.Exit(1)


# ── resume ─────────────────────────────────────────────────────────────────────


@app.command()
def resume(task_id: str = typer.Argument(..., help="Task ID to resume")) -> None:
    """Resume a waiting/blocked task from its checkpoint."""
    from devops_agent.tasks.executor import execute_task

    try:
        final_state = asyncio.run(execute_task(task_id, resume=True))
        console.print(f"{OK} Task {task_id} finished: {final_state.phase.value}")
    except Exception as e:
        console.print(f"{FAIL} Resume failed: {e}")
        raise typer.Exit(1)


# ── cancel ─────────────────────────────────────────────────────────────────────


@app.command()
def cancel(task_id: str = typer.Argument(..., help="Task ID to cancel")) -> None:
    """Move a task to failed state."""
    found = find_task(task_id)
    if found is None:
        console.print(f"{FAIL} Task {task_id} not found")
        raise typer.Exit(1)

    _, phase = found
    if phase in ("done", "failed"):
        console.print(f"{WARN} Task {task_id} already in {phase}")
        return

    try:
        move_to_failed(task_id, from_phase=phase)
        console.print(f"{OK} Task {task_id} moved to failed")
    except Exception as e:
        console.print(f"{FAIL} Cancel failed: {e}")
        raise typer.Exit(1)


# ── list ───────────────────────────────────────────────────────────────────────


@app.command(name="list")
def list_tasks(
    status: str = typer.Option("all", "--status", "-s", help="Filter by status: pending|in_progress|waiting|done|failed|all"),
) -> None:
    """List tasks."""
    table = Table(title="Tasks")
    table.add_column("Task ID", style="cyan")
    table.add_column("Config", style="green")
    table.add_column("Phase", style="yellow")
    table.add_column("Created")
    table.add_column("Error", style="red", max_width=40)

    phases = ["pending", "in_progress", "waiting", "done", "failed"] if status == "all" else [status]

    for phase in phases:
        d = get_tasks_subdir(phase)
        states = list_states(d)
        # Also check archive subdirs
        for subdir in d.iterdir():
            if subdir.is_dir():
                states.extend(list_states(subdir))
        for s in states:
            table.add_row(s.task_id, s.task_config_name, s.phase.value, s.created_at[:19], s.error_message[:40] if s.error_message else "")

    console.print(table)


# ── logs ───────────────────────────────────────────────────────────────────────


@app.command()
def logs(task_id: str = typer.Argument(..., help="Task ID")) -> None:
    """Pretty-print a task's state file."""
    found = find_task(task_id)
    if found is None:
        console.print(f"{FAIL} Task {task_id} not found")
        raise typer.Exit(1)

    state, phase = found
    console.print_json(state.model_dump_json(indent=2))


# ── doctor ─────────────────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
    """Run sanity checks."""
    console.print("[bold]DevOps Agent — Doctor[/bold]\n")
    all_ok = True

    # Git Bash
    bash = resolve_git_bash()
    if bash:
        console.print(f"{OK} Git Bash: {bash}")
    else:
        console.print(f"{FAIL} Git Bash not found")
        all_ok = False

    # Edge
    edge = resolve_edge_binary()
    if edge:
        console.print(f"{OK} Edge: {edge}")
    else:
        console.print(f"{FAIL} Edge not found")
        all_ok = False

    # Config dir
    config_dir = get_config_dir()
    if config_dir.exists():
        console.print(f"{OK} Config dir: {config_dir}")
    else:
        console.print(f"{FAIL} Config dir missing: {config_dir}")
        all_ok = False

    # Config file
    try:
        cfg = load_agent_config()
        console.print(f"{OK} Agent config loaded (work_dir: {cfg.work_dir})")
    except Exception as e:
        console.print(f"{FAIL} Agent config: {e}")
        all_ok = False

    # Task configs
    try:
        tcs = load_all_task_configs()
        console.print(f"{OK} Task configs: {len(tcs)} loaded")
    except Exception as e:
        console.print(f"{FAIL} Task configs: {e}")
        all_ok = False

    # RapidOCR
    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-untyped]
        console.print(f"{OK} RapidOCR available")
    except ImportError:
        console.print(f"{FAIL} RapidOCR not available")
        all_ok = False

    # DPI awareness
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
        console.print(f"{OK} DPI awareness set (per-monitor v2)")
    except Exception as e:
        console.print(f"{WARN} DPI awareness: {e}")

    if all_ok:
        console.print("\n[bold green]All checks passed.[/bold green]")
    else:
        console.print("\n[bold red]Some checks failed.[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
