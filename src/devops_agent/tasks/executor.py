"""Task executor — runs a task through its step sequence."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog

from devops_agent.config.loader import (
    load_agent_config,
    load_all_task_configs,
    load_environments_config,
    load_notifications_config,
    load_repos_config,
)
from devops_agent.config.paths import get_config_dir, get_tasks_subdir
from devops_agent.config.schema import TaskPhase
from devops_agent.steps.base import StepContext
from devops_agent.steps.registry import get_step
from devops_agent.tasks.lifecycle import (
    find_task,
    move_to_done,
    move_to_failed,
    move_to_in_progress,
    move_to_waiting,
)
from devops_agent.tasks.models import StepResult, TaskState
from devops_agent.tasks.state_store import read_state, state_file_path, write_state

# Steps that require a browser session
BROWSER_STEPS = frozenset({
    "browser.navigate", "browser.click", "browser.fill",
    "browser.wait_for", "browser.screenshot",
    "pr.create", "pr.wait_merge", "deploy.trigger",
    "notify.send",
})

log = structlog.get_logger("executor")

# Simple file lock for single-task-at-a-time execution
_LOCK_FILE = get_tasks_subdir("in_progress") / ".lock"


def _acquire_lock() -> bool:
    """Acquire the single-task lock. Returns True if acquired."""
    try:
        _LOCK_FILE.touch(exist_ok=False)
        return True
    except FileExistsError:
        return False


def _release_lock() -> None:
    """Release the single-task lock."""
    _LOCK_FILE.unlink(missing_ok=True)


async def execute_task(task_id: str, resume: bool = False) -> TaskState:
    """Execute or resume a task through its step sequence.

    Returns the final TaskState.
    """
    # Load configs
    config_dir = get_config_dir()
    agent_config = load_agent_config(config_dir)
    repos = load_repos_config(config_dir)
    environments = load_environments_config(config_dir)
    notifications = load_notifications_config(config_dir)
    task_configs = load_all_task_configs(config_dir)

    # Find the task
    found = find_task(task_id)
    if found is None:
        raise ValueError(f"Task {task_id} not found")
    state, current_phase = found

    # If resuming from waiting, move back to in_progress
    if resume and current_phase == "waiting":
        src = get_tasks_subdir("waiting")
        dst = get_tasks_subdir("in_progress")
        src_path = state_file_path(src, task_id)
        if not src_path.exists():
            # Check archive pattern
            src_path = src / task_id / f"{task_id}.state.json"
        state = read_state(src_path)
        state.phase = TaskPhase.in_progress
        dst_path = state_file_path(dst, task_id)
        write_state(dst_path, state)
        src_path.unlink()
    elif current_phase == "pending":
        state = move_to_in_progress(task_id)
    elif current_phase != "in_progress":
        raise ValueError(f"Task {task_id} is in {current_phase}, cannot execute")

    # Acquire lock
    if not _acquire_lock():
        raise RuntimeError("Another task is already running. Single-task-at-a-time enforced.")

    browser_session = None  # Declare before try so finally can always access it

    try:
        # Look up the task config
        tc = task_configs.get(state.task_config_name)
        if tc is None:
            state.error_message = f"Task config '{state.task_config_name}' not found"
            state.phase = TaskPhase.failed
            move_to_failed(task_id)
            return state

        # Build step context
        repo_key = tc.references.get("repo")
        env_key = tc.references.get("env")

        work_dir = agent_config.work_dir / task_id
        work_dir.mkdir(parents=True, exist_ok=True)

        screenshot_dir = work_dir / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        ctx = StepContext(
            task_id=task_id,
            work_dir=work_dir,
            variables=state.variables,
            agent_config=agent_config,
            repo=repos.repos.get(repo_key) if repo_key else None,
            environment=environments.environments.get(env_key) if env_key else None,
            notifications=notifications,
            screenshot_dir=screenshot_dir,
        )

        # Start browser session if any step needs it
        browser_session = None
        needs_browser = any(s.step in BROWSER_STEPS for s in tc.steps)
        if needs_browser:
            browser_session = await _start_browser_session(agent_config.edge_profile_dir)
            ctx.browser_session = browser_session

        # Initialize step results if not already present
        if not state.step_results:
            state.step_results = [
                StepResult(
                    step_name=s.name or s.step,
                    step_index=i,
                    params=s.params,
                )
                for i, s in enumerate(tc.steps)
            ]

        # Determine start index
        start_index = state.resume_from_step if resume else state.current_step_index()
        ip_dir = get_tasks_subdir("in_progress")

        log.info("executing_task", task_id=task_id, start_step=start_index, total_steps=len(tc.steps))

        for i in range(start_index, len(tc.steps)):
            step_def = tc.steps[i]
            step_result = state.step_results[i]

            # Resolve params
            resolved_params = {
                k: ctx.resolve_var(str(v)) if isinstance(v, str) else v
                for k, v in step_def.params.items()
            }

            log.info("executing_step", step=step_def.step, index=i, params=resolved_params)

            # Get and execute the step
            try:
                step = get_step(step_def.step)
            except KeyError as e:
                step_result.mark_failed(str(e))
                state.resume_from_step = i
                write_state(state_file_path(ip_dir, task_id), state)
                state = move_to_waiting(task_id)
                _release_lock()
                return state

            step_result.mark_started()
            write_state(state_file_path(ip_dir, task_id), state)

            result = await step.execute(ctx, resolved_params)

            # Merge result back
            step_result.status = result.status
            step_result.finished_at = result.finished_at
            step_result.outputs = result.outputs
            step_result.screenshot_paths = result.screenshot_paths
            step_result.error_message = result.error_message
            step_result.stderr = result.stderr
            step_result.stdout = result.stdout

            # Accumulate outputs into context
            ctx.outputs.update(result.outputs)

            write_state(state_file_path(ip_dir, task_id), state)

            # Handle suspend mode (pr.wait_merge with mode=suspend)
            if result.outputs.get("_suspend"):
                log.info("task_suspended", step=step_def.step, task_id=task_id)
                state.resume_from_step = i + 1
                state.merge_context = _build_merge_context(result.outputs)
                write_state(state_file_path(ip_dir, task_id), state)
                state = move_to_waiting(task_id)
                return state

            if result.status == "failed":
                log.warning("step_failed", step=step_def.step, error=result.error_message)
                state.resume_from_step = i
                state.error_message = result.error_message

                # Best-effort failure notification
                await _notify_failure(ctx, state, step_def.step)

                write_state(state_file_path(ip_dir, task_id), state)
                state = move_to_waiting(task_id)
                return state

        # All steps completed
        log.info("task_completed", task_id=task_id)
        state = move_to_done(task_id)

    except Exception as e:
        log.error("task_execution_error", task_id=task_id, error=str(e))
        state.error_message = str(e)
        try:
            move_to_failed(task_id)
        except Exception:
            pass
        raise
    finally:
        # Tear down browser session
        if browser_session is not None:
            await _stop_browser_session(browser_session)
        _release_lock()

    return state


async def _start_browser_session(profile_dir: Path) -> Any:
    """Start a browser session for the task. Returns the active page."""
    try:
        from devops_agent.browser.session import BrowserSession

        session = BrowserSession(profile_dir)
        page = await session.start(headless=False)
        log.info("browser_session_started", profile_dir=str(profile_dir))
        return page
    except Exception as e:
        log.warning("browser_session_failed", error=str(e))
        return None


async def _stop_browser_session(page: Any) -> None:
    """Stop the browser session."""
    try:
        context = page.context
        await context.close()
        log.info("browser_session_stopped")
    except Exception as e:
        log.warning("browser_session_stop_failed", error=str(e))


def _build_merge_context(outputs: dict[str, Any]) -> Any:
    """Build a MergeContext from step outputs."""
    from devops_agent.tasks.models import MergeContext

    return MergeContext(
        pr_url=outputs.get("pr_url", ""),
        detected_status="waiting",
    )


async def _notify_failure(ctx: StepContext, state: TaskState, failed_step: str) -> None:
    """Best-effort notification on step failure. Never raises."""
    try:
        if ctx.notifications is None:
            return

        # Update context with failure info for template rendering
        ctx.outputs["failed_step"] = failed_step
        ctx.outputs["error_message"] = state.error_message
        ctx.outputs["task_config_name"] = state.task_config_name

        notify_step = get_step("notify.send")
        # Find the default notification channels from the task config or agent config
        channels = ctx.agent_config.default_notification_channels
        template = "task_blocked"

        for channel in channels:
            await notify_step.execute(ctx, {
                "channel": channel,
                "template": template,
            })
    except Exception as e:
        log.warning("failure_notification_failed", error=str(e))
