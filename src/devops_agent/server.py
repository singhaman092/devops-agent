"""FastMCP server — tools for AI agents to author, debug, and run DevOps task configs.

IMPORTANT FOR AI AGENTS:
- Your job is to CREATE and DEBUG task-config YAML files using these tools.
- DO NOT modify the devops-agent source code. The agent is a fixed tool — you compose tasks from its step primitives.
- Workflow: list_steps → create_task_config → run_task → debug_task (if failed) → update_task_config → re-run.
- Use screenshot_url to see what a page looks like before writing selectors.
- Use debug_task after failures to see error + screenshot together.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

from devops_agent.config.loader import (
    load_activation,
    load_agent_config,
    load_all_task_configs,
    validate_file,
)
from devops_agent.config.paths import get_config_dir, get_tasks_subdir


def create_server() -> FastMCP:
    """Create and configure the MCP server with all tool registrations."""
    mcp = FastMCP("devops-agent")

    # ── DISCOVERY TOOLS ────────────────────────────────────────────────────────

    @mcp.tool()
    def list_steps() -> list[dict[str, Any]]:
        """List all available step primitives with their parameter schemas.

        Use this FIRST to understand what building blocks are available
        before creating a task config. Each step has a name (used in YAML)
        and parameters it accepts.

        Returns a list of steps with name and accepted params.
        """
        import devops_agent.steps  # noqa: F401 — triggers registration

        step_docs: dict[str, dict[str, Any]] = {
            "shell.run": {
                "description": "Execute a shell command via Git Bash",
                "params": {"command": "required — shell command string", "cwd": "optional — working directory", "timeout": "optional — seconds (default 300)"},
                "outputs": ["exit_code", "stdout"],
            },
            "git.clone": {
                "description": "Clone a git repository",
                "params": {"url": "required — git clone URL", "dest": "optional — destination dir"},
                "outputs": ["clone_dir"],
            },
            "git.branch": {
                "description": "Create and checkout a new branch",
                "params": {"branch": "required — branch name", "cwd": "optional — repo dir", "base": "optional — base branch"},
                "outputs": ["branch_name"],
            },
            "git.commit": {
                "description": "Stage all and commit",
                "params": {"message": "required — commit message", "cwd": "optional — repo dir", "add_all": "optional — bool (default true)"},
            },
            "git.push": {
                "description": "Push to remote",
                "params": {"branch": "optional — branch name", "cwd": "optional — repo dir", "remote": "optional (default origin)", "set_upstream": "optional — bool (default true)"},
            },
            "browser.navigate": {
                "description": "Navigate to a URL in the Edge browser",
                "params": {"url": "required — URL to navigate to", "wait_until": "optional — domcontentloaded|networkidle|load|commit"},
                "outputs": ["url", "title"],
            },
            "browser.click": {
                "description": "Click a DOM element by CSS selector",
                "params": {"selector": "required — CSS selector", "timeout": "optional — ms (default 30000)", "force": "optional — bool, bypass overlay checks"},
            },
            "browser.fill": {
                "description": "Fill an input element with text",
                "params": {"selector": "required — CSS selector", "value": "required — text to fill", "timeout": "optional ms", "clear": "optional — bool (default true)"},
            },
            "browser.wait_for": {
                "description": "Wait for a selector or text to appear on page",
                "params": {"selector": "conditional — CSS selector", "text": "conditional — text to wait for", "state": "optional — visible|hidden|attached|detached", "timeout": "optional ms"},
            },
            "browser.screenshot": {
                "description": "Take a screenshot of the current page or element",
                "params": {"filename": "optional — output filename", "selector": "optional — element to capture", "full_page": "optional — bool (default true)"},
                "outputs": ["screenshot_path"],
            },
            "browser.eval": {
                "description": "Execute JavaScript in the browser page. Use this to interact with complex UI components (react-select, overlays, etc.) that CSS selectors can't reach.",
                "params": {"expression": "required — JavaScript expression to evaluate. Must be a self-contained IIFE returning a string."},
                "outputs": ["return_value"],
            },
            "browser.press": {
                "description": "Press a keyboard key in the browser",
                "params": {"key": "required — key name (Enter, Tab, ArrowDown, etc.)", "keys": "optional — list of keys to press in sequence"},
            },
            "browser.type": {
                "description": "Type text character by character in the browser (into the currently focused element)",
                "params": {"text": "required — text to type", "delay": "optional — ms between keystrokes (default 50)"},
            },
            "screenshot.capture": {
                "description": "OS-level screenshot via mss (full screen or region)",
                "params": {"mode": "optional — full|region|window", "filename": "optional", "region": "optional — {left, top, width, height}"},
                "outputs": ["screenshot_path"],
            },
            "ocr.find_text": {
                "description": "Find text on screen using OCR",
                "params": {"text": "required — text to search for", "image_path": "optional — image file to search"},
                "outputs": ["found", "text", "center_x", "center_y", "confidence", "bbox"],
            },
            "os.click": {
                "description": "Click at screen coordinates (PyAutoGUI)",
                "params": {"x": "required — int", "y": "required — int", "button": "optional — left|right|middle", "clicks": "optional — int"},
            },
            "os.type": {
                "description": "Type text via keyboard (PyAutoGUI)",
                "params": {"text": "required", "interval": "optional — seconds between keys"},
            },
            "os.hotkey": {
                "description": "Press a key combination (PyAutoGUI)",
                "params": {"keys": "required — list of key names"},
            },
            "pr.create": {
                "description": "Create a PR via browser automation (uses repo config for platform-specific selectors)",
                "params": {"title": "required", "description": "optional", "source_branch": "optional", "target_branch": "optional (default main)", "reviewers": "optional list", "labels": "optional list"},
                "outputs": ["pr_url", "pr_title", "source_branch", "target_branch"],
            },
            "pr.wait_merge": {
                "description": "Wait for a PR to be merged (poll or suspend mode)",
                "params": {"pr_url": "optional — from prior step output", "mode": "optional — poll|suspend", "interval_seconds": "optional", "timeout_seconds": "optional"},
                "outputs": ["pr_url", "merged", "elapsed_seconds"],
            },
            "deploy.trigger": {
                "description": "Trigger a deployment via configured method",
                "params": {"url": "optional override", "click_selectors": "optional list for portal_click", "pipeline_url": "optional for pipeline_url mode", "command": "optional for cli mode"},
                "outputs": ["deploy_url", "trigger_type"],
            },
            "monitor.http_check": {
                "description": "Poll a URL until expected status/body",
                "params": {"url": "required", "expected_status": "optional (default 200)", "expected_body": "optional", "interval_seconds": "optional (default 30)", "timeout_seconds": "optional (default 300)"},
                "outputs": ["status_code", "elapsed_seconds"],
            },
            "monitor.version_match": {
                "description": "Poll a version endpoint until it matches",
                "params": {"url": "required", "expected_version": "required", "json_path": "optional (default 'version')", "interval_seconds": "optional", "timeout_seconds": "optional"},
                "outputs": ["version", "elapsed_seconds"],
            },
            "notify.send": {
                "description": "Post a message to Slack/Teams via browser",
                "params": {"channel": "required — channel name from notifications.yaml", "message": "conditional — message text", "template": "conditional — template name"},
            },
            "wait.sleep": {
                "description": "Explicit delay",
                "params": {"seconds": "optional (default 5)"},
            },
        }

        return [
            {"name": name, **doc}
            for name, doc in step_docs.items()
        ]

    @mcp.tool()
    def list_task_configs() -> list[dict[str, Any]]:
        """List available task-configs with their full step sequences.

        Use this to see what tasks are already configured and how they work.
        Returns name, description, and the complete step list for each config.
        """
        configs = load_all_task_configs()
        results = []
        for tc in configs.values():
            results.append({
                "name": tc.name,
                "description": tc.description,
                "references": tc.references,
                "steps": [
                    {"step": s.step, "name": s.name, "params": s.params}
                    for s in tc.steps
                ],
            })
        return results

    @mcp.tool()
    def get_global_configs() -> dict[str, Any]:
        """Return the current global configuration (repos, environments, notifications).

        Use this to understand what repos, environments, and notification channels
        are available for use in task configs.
        """
        from devops_agent.config.loader import (
            load_repos_config,
            load_environments_config,
            load_notifications_config,
        )
        config_dir = get_config_dir()
        repos = load_repos_config(config_dir)
        envs = load_environments_config(config_dir)
        notifs = load_notifications_config(config_dir)
        return {
            "config_dir": str(config_dir),
            "repos": {k: v.model_dump() for k, v in repos.repos.items()},
            "environments": {k: v.model_dump() for k, v in envs.environments.items()},
            "notification_channels": list(notifs.channels.keys()),
            "notification_templates": list(notifs.templates.keys()),
        }

    # ── CONFIG FILE TOOLS ─────────────────────────────────────────────────────
    # These give the AI agent access to ~/.devops-agent/ config files
    # since the agent typically only has access to the repo directory.

    @mcp.tool()
    def read_config_file(filename: str) -> dict[str, Any]:
        """Read a global config file from ~/.devops-agent/.

        Use this to read config.yaml, repos.yaml, environments.yaml, or notifications.yaml.
        The AI agent may not have filesystem access to ~/.devops-agent/ — this tool provides it.

        Args:
            filename: One of: config.yaml, repos.yaml, environments.yaml, notifications.yaml
        """
        allowed = {"config.yaml", "repos.yaml", "environments.yaml", "notifications.yaml"}
        if filename not in allowed:
            return {"error": f"Invalid filename. Must be one of: {', '.join(sorted(allowed))}"}
        path = get_config_dir() / filename
        if not path.exists():
            return {"error": f"{filename} not found at {path}. Run 'devops-agent init' first."}
        return {
            "filename": filename,
            "path": str(path),
            "content": path.read_text(encoding="utf-8"),
        }

    @mcp.tool()
    def write_config_file(filename: str, content: str) -> dict[str, str]:
        """Write a global config file to ~/.devops-agent/.

        Use this to configure repos, environments, notifications, or agent settings.
        The AI agent may not have filesystem access to ~/.devops-agent/ — this tool provides it.

        Validates the content before writing. Will not overwrite with invalid YAML.

        Args:
            filename: One of: config.yaml, repos.yaml, environments.yaml, notifications.yaml
            content: The complete YAML content to write.
        """
        allowed = {"config.yaml", "repos.yaml", "environments.yaml", "notifications.yaml"}
        if filename not in allowed:
            return {"error": f"Invalid filename. Must be one of: {', '.join(sorted(allowed))}"}

        # Validate YAML syntax
        try:
            data = yaml.safe_load(content)
            if data is not None and not isinstance(data, dict):
                return {"status": "invalid", "error": "YAML must be a mapping (dict), not a list or scalar"}
        except yaml.YAMLError as e:
            return {"status": "invalid", "error": f"Invalid YAML: {e}"}

        # Validate against schema
        from devops_agent.config.schema import (
            AgentConfig,
            EnvironmentsConfig,
            NotificationsConfig,
            ReposConfig,
        )
        schema_map = {
            "config.yaml": AgentConfig,
            "repos.yaml": ReposConfig,
            "environments.yaml": EnvironmentsConfig,
            "notifications.yaml": NotificationsConfig,
        }
        try:
            model = schema_map[filename]
            if data:
                model(**data)
        except Exception as e:
            return {"status": "invalid", "error": str(e)}

        path = get_config_dir() / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"status": "written", "path": str(path)}

    @mcp.tool()
    def get_config_dir_path() -> dict[str, str]:
        """Return the path to the ~/.devops-agent/ config directory and list its contents.

        Useful for the AI agent to understand what's configured and where files live.
        """
        config_dir = get_config_dir()
        files: list[str] = []
        if config_dir.exists():
            for f in sorted(config_dir.iterdir()):
                if f.is_file():
                    files.append(f.name)
            tc_dir = config_dir / "task-configs"
            if tc_dir.exists():
                for f in sorted(tc_dir.glob("*.yaml")):
                    files.append(f"task-configs/{f.name}")
        return {
            "config_dir": str(config_dir),
            "exists": str(config_dir.exists()),
            "files": ", ".join(files) if files else "(empty)",
        }

    # ── TASK CONFIG AUTHORING TOOLS ────────────────────────────────────────────

    @mcp.tool()
    def create_task_config(name: str, yaml_content: str) -> dict[str, str]:
        """Create a new task-config YAML file.

        DO NOT modify devops-agent source code. Use this tool to create task configs instead.

        The YAML must have: name, description, steps (list of step primitives).
        Use list_steps() first to see available primitives and their params.
        Use screenshot_url() first to see the target page and find the right selectors.

        Args:
            name: Filename (without .yaml extension) for the task config.
            yaml_content: The complete YAML content for the task config.
        """
        tc_dir = get_config_dir() / "task-configs"
        tc_dir.mkdir(parents=True, exist_ok=True)
        path = tc_dir / f"{name}.yaml"

        # Validate before writing
        try:
            data = yaml.safe_load(yaml_content)
            from devops_agent.config.schema import TaskConfig
            TaskConfig(**data)
        except Exception as e:
            return {"status": "invalid", "error": str(e)}

        path.write_text(yaml_content, encoding="utf-8")
        return {"status": "created", "path": str(path)}

    @mcp.tool()
    def update_task_config(name: str, yaml_content: str) -> dict[str, str]:
        """Update an existing task-config YAML file.

        DO NOT modify devops-agent source code. Use this tool to fix task configs instead.
        Common after a failed run: fix selectors, adjust waits, add screenshots for debugging.

        Args:
            name: Filename (without .yaml extension) of the existing task config.
            yaml_content: The complete updated YAML content.
        """
        tc_dir = get_config_dir() / "task-configs"
        path = tc_dir / f"{name}.yaml"
        if not path.exists():
            return {"status": "error", "error": f"Task config '{name}' not found at {path}"}

        # Validate before writing
        try:
            data = yaml.safe_load(yaml_content)
            from devops_agent.config.schema import TaskConfig
            TaskConfig(**data)
        except Exception as e:
            return {"status": "invalid", "error": str(e)}

        path.write_text(yaml_content, encoding="utf-8")
        return {"status": "updated", "path": str(path)}

    @mcp.tool()
    def read_task_config(name: str) -> dict[str, Any]:
        """Read the raw YAML content of a task config file.

        Args:
            name: Filename (without .yaml extension) of the task config.
        """
        tc_dir = get_config_dir() / "task-configs"
        path = tc_dir / f"{name}.yaml"
        if not path.exists():
            return {"error": f"Task config '{name}' not found"}
        return {"name": name, "path": str(path), "content": path.read_text(encoding="utf-8")}

    # ── EXECUTION TOOLS ────────────────────────────────────────────────────────

    @mcp.tool()
    async def run_task(activation_yaml: str) -> dict[str, Any]:
        """Run a task from inline activation YAML.

        The activation YAML needs: task_config (name of a task config) and variables (dict).
        For zero-variable tasks: 'task_config: my-task\\nvariables: {}'

        After running, if the task fails, use debug_task to see what went wrong
        (error message + screenshot). Then use update_task_config to fix the
        config and re-run.

        Args:
            activation_yaml: Inline YAML with task_config and variables.
        """
        from devops_agent.config.schema import Activation
        from devops_agent.tasks.lifecycle import create_task
        from devops_agent.tasks.executor import execute_task

        # Parse activation
        path = Path(activation_yaml)
        if path.exists() and path.suffix in (".yaml", ".yml"):
            activation = load_activation(path)
        else:
            data = yaml.safe_load(activation_yaml)
            activation = Activation(**data)

        state = create_task(
            task_config_name=activation.task_config,
            activation_file=activation_yaml[:200],
            variables=activation.variables,
            task_id=activation.task_id or "",
        )

        final = await execute_task(state.task_id)

        # Build rich result
        result: dict[str, Any] = {
            "task_id": final.task_id,
            "phase": final.phase.value,
        }

        if final.error_message:
            result["error"] = final.error_message
            result["hint"] = "Use debug_task(task_id) to see the failure screenshot and full error details. Then use update_task_config to fix the config and re-run."

        # Include step summary
        result["steps"] = []
        for sr in final.step_results:
            step_info: dict[str, Any] = {
                "name": sr.step_name,
                "status": sr.status,
            }
            if sr.error_message:
                step_info["error"] = sr.error_message[:500]
            if sr.outputs:
                step_info["outputs"] = sr.outputs
            result["steps"].append(step_info)

        return result

    @mcp.tool()
    async def resume_task(task_id: str) -> dict[str, Any]:
        """Resume a waiting/blocked task from its checkpoint.

        Args:
            task_id: The task ID to resume.
        """
        from devops_agent.tasks.executor import execute_task
        from devops_agent.tasks.lifecycle import find_task

        final = await execute_task(task_id, resume=True)
        return {
            "task_id": final.task_id,
            "phase": final.phase.value,
            "error": final.error_message or None,
        }

    @mcp.tool()
    def cancel_task(task_id: str) -> dict[str, str]:
        """Cancel a running or waiting task.

        Args:
            task_id: The task ID to cancel.
        """
        from devops_agent.tasks.lifecycle import find_task, move_to_failed

        found = find_task(task_id)
        if found is None:
            return {"error": f"Task {task_id} not found"}
        _, phase = found
        if phase in ("done", "failed"):
            return {"status": f"Already {phase}"}
        move_to_failed(task_id, from_phase=phase)
        return {"status": "cancelled", "task_id": task_id}

    # ── DEBUGGING TOOLS ────────────────────────────────────────────────────────

    @mcp.tool()
    def debug_task(task_id: str) -> dict[str, Any]:
        """Get full debug info for a task: error details, failed step, and screenshot paths.

        Use this AFTER a failed run_task to understand what went wrong.
        Read the error message and look at the screenshots to determine
        what selectors need fixing in the task config.

        Then use update_task_config to fix the config and run_task again.

        Args:
            task_id: The task ID to debug.
        """
        from devops_agent.tasks.lifecycle import find_task

        found = find_task(task_id)
        if found is None:
            return {"error": f"Task {task_id} not found"}

        state, phase = found
        result: dict[str, Any] = {
            "task_id": task_id,
            "phase": phase,
            "task_config": state.task_config_name,
            "error": state.error_message or None,
            "resume_from_step": state.resume_from_step,
            "total_steps": len(state.step_results),
        }

        # All step results with details
        result["steps"] = []
        all_screenshots: list[str] = []
        for i, sr in enumerate(state.step_results):
            step_info: dict[str, Any] = {
                "index": i,
                "name": sr.step_name,
                "status": sr.status,
            }
            if sr.error_message:
                step_info["error"] = sr.error_message
            if sr.outputs:
                step_info["outputs"] = sr.outputs
            if sr.screenshot_paths:
                step_info["screenshots"] = sr.screenshot_paths
                all_screenshots.extend(sr.screenshot_paths)
            result["steps"].append(step_info)

        result["all_screenshots"] = all_screenshots

        # Include the failed step's error prominently
        if state.resume_from_step < len(state.step_results):
            failed = state.step_results[state.resume_from_step]
            result["failed_step"] = {
                "index": state.resume_from_step,
                "name": failed.step_name,
                "error": failed.error_message,
                "params": failed.params,
            }

        return result

    @mcp.tool()
    def get_task_state(task_id: str) -> dict[str, Any]:
        """Return the full state of a task.

        Args:
            task_id: The task ID.
        """
        from devops_agent.tasks.lifecycle import find_task

        found = find_task(task_id)
        if found is None:
            return {"error": f"Task {task_id} not found"}
        state, _ = found
        return state.model_dump()

    @mcp.tool()
    def get_task_screenshots(task_id: str) -> list[str]:
        """Return file paths of all screenshots captured during a task.

        Open these files to see what the browser looked like at each step.
        This is essential for debugging selector issues.

        Args:
            task_id: The task ID.
        """
        from devops_agent.tasks.lifecycle import find_task

        found = find_task(task_id)
        if found is None:
            return []
        state, _ = found
        paths: list[str] = []
        for sr in state.step_results:
            paths.extend(sr.screenshot_paths)
        return paths

    @mcp.tool()
    async def screenshot_url(url: str) -> dict[str, Any]:
        """Navigate to a URL and take a screenshot WITHOUT running a full task.

        Use this to inspect a page BEFORE writing a task config.
        See the page structure, identify buttons, selectors, and dialogs
        so you can write accurate step configs.

        The screenshot is saved to the work directory and the path is returned.

        Args:
            url: The URL to screenshot.
        """
        config = load_agent_config()
        from devops_agent.browser.profile import create_persistent_context, close_context

        profile_dir = config.edge_profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)

        try:
            context = await create_persistent_context(profile_dir, headless=False)
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # Save screenshot
            work_dir = config.work_dir / "_debug"
            work_dir.mkdir(parents=True, exist_ok=True)
            import time
            filename = f"debug_{int(time.time())}.png"
            path = work_dir / filename
            await page.screenshot(path=str(path), full_page=True)

            # Get page title and current URL
            title = await page.title()
            current_url = page.url

            await close_context(context)

            return {
                "screenshot_path": str(path),
                "url": current_url,
                "title": title,
                "hint": "Open the screenshot file to see the page. Use the visual layout to determine CSS selectors for browser.click/browser.fill steps.",
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    async def inspect_page(url: str, javascript: str) -> dict[str, Any]:
        """Navigate to a URL and run JavaScript to inspect the DOM.

        Use this to find selectors, data-testid attributes, element structure, etc.
        before writing a task config. Much more precise than just looking at screenshots.

        Example JS: 'document.querySelectorAll("button").length'
        Example JS: '[...document.querySelectorAll("[data-testid]")].map(e => e.getAttribute("data-testid"))'

        Args:
            url: The URL to inspect.
            javascript: JavaScript expression to evaluate on the page. Should return a serializable value.
        """
        config = load_agent_config()
        from devops_agent.browser.profile import create_persistent_context, close_context

        profile_dir = config.edge_profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)

        try:
            context = await create_persistent_context(profile_dir, headless=False)
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            result = await page.evaluate(javascript)
            current_url = page.url

            await close_context(context)

            return {
                "url": current_url,
                "result": result,
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def list_tasks(status: str = "all") -> list[dict[str, Any]]:
        """List tasks filtered by status.

        Args:
            status: One of pending, in_progress, waiting, done, failed, or all.
        """
        phases = (
            ["pending", "in_progress", "waiting", "done", "failed"]
            if status == "all"
            else [status]
        )
        results: list[dict[str, Any]] = []
        for phase in phases:
            d = get_tasks_subdir(phase)
            for s in list_states(d):
                results.append({
                    "task_id": s.task_id,
                    "task_config": s.task_config_name,
                    "phase": s.phase.value,
                    "created_at": s.created_at,
                    "error": s.error_message or None,
                })
            for subdir in d.iterdir():
                if subdir.is_dir():
                    for s in list_states(subdir):
                        results.append({
                            "task_id": s.task_id,
                            "task_config": s.task_config_name,
                            "phase": s.phase.value,
                            "created_at": s.created_at,
                            "error": s.error_message or None,
                        })
        return results

    @mcp.tool()
    def validate_config(path: str) -> dict[str, str]:
        """Validate any config or type-config file.

        Args:
            path: Path to the YAML file to validate.
        """
        try:
            validate_file(Path(path))
            return {"status": "valid", "path": path}
        except Exception as e:
            return {"status": "invalid", "error": str(e)}

    return mcp
