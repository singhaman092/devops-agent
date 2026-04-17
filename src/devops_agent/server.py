"""FastMCP server — registers tools for Cursor/MCP clients."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from devops_agent.config.loader import (
    load_activation,
    load_agent_config,
    load_all_task_configs,
    validate_file,
)
from devops_agent.config.paths import get_config_dir, get_tasks_subdir
from devops_agent.tasks.lifecycle import create_task, find_task, move_to_failed
from devops_agent.tasks.state_store import list_states


def create_server() -> FastMCP:
    """Create and configure the MCP server with all tool registrations."""
    mcp = FastMCP("devops-agent")

    @mcp.tool()
    def list_task_configs() -> list[dict[str, str]]:
        """Return available task-configs by name, with description."""
        configs = load_all_task_configs()
        return [
            {"name": tc.name, "description": tc.description}
            for tc in configs.values()
        ]

    @mcp.tool()
    def list_tasks(status: str = "all") -> list[dict[str, Any]]:
        """Return task metadata filtered by status.

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
            # Check archive subdirs
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
    async def run_task(activation_yaml: str) -> dict[str, Any]:
        """Enqueue and execute a task from inline activation YAML or a file path.

        Args:
            activation_yaml: Either a file path to an activation YAML, or inline YAML content.
        """
        import yaml

        # Determine if it's a path or inline YAML
        path = Path(activation_yaml)
        if path.exists() and path.suffix in (".yaml", ".yml"):
            activation = load_activation(path)
        else:
            data = yaml.safe_load(activation_yaml)
            from devops_agent.config.schema import Activation
            activation = Activation(**data)

        state = create_task(
            task_config_name=activation.task_config,
            activation_file=activation_yaml[:200],
            variables=activation.variables,
            task_id=activation.task_id or "",
        )

        from devops_agent.tasks.executor import execute_task

        final = await execute_task(state.task_id)
        return {
            "task_id": final.task_id,
            "phase": final.phase.value,
            "error": final.error_message or None,
        }

    @mcp.tool()
    async def resume_task(task_id: str) -> dict[str, Any]:
        """Resume a waiting task from its checkpoint.

        Args:
            task_id: The task ID to resume.
        """
        from devops_agent.tasks.executor import execute_task

        final = await execute_task(task_id, resume=True)
        return {
            "task_id": final.task_id,
            "phase": final.phase.value,
            "error": final.error_message or None,
        }

    @mcp.tool()
    def cancel_task(task_id: str) -> dict[str, str]:
        """Move a task from waiting or in_progress to failed.

        Args:
            task_id: The task ID to cancel.
        """
        found = find_task(task_id)
        if found is None:
            return {"error": f"Task {task_id} not found"}
        _, phase = found
        if phase in ("done", "failed"):
            return {"status": f"Already {phase}"}
        move_to_failed(task_id, from_phase=phase)
        return {"status": "cancelled", "task_id": task_id}

    @mcp.tool()
    def get_task_state(task_id: str) -> dict[str, Any]:
        """Return the current state file contents for a task.

        Args:
            task_id: The task ID.
        """
        found = find_task(task_id)
        if found is None:
            return {"error": f"Task {task_id} not found"}
        state, _ = found
        return state.model_dump()

    @mcp.tool()
    def get_task_screenshots(task_id: str) -> list[str]:
        """Return paths of captured screenshots for a task.

        Args:
            task_id: The task ID.
        """
        found = find_task(task_id)
        if found is None:
            return []
        state, _ = found
        paths: list[str] = []
        for sr in state.step_results:
            paths.extend(sr.screenshot_paths)
        return paths

    @mcp.tool()
    def validate_config(path: str) -> dict[str, str]:
        """Validate any config or type-config file without running.

        Args:
            path: Path to the YAML file to validate.
        """
        try:
            validate_file(Path(path))
            return {"status": "valid", "path": path}
        except Exception as e:
            return {"status": "invalid", "error": str(e)}

    return mcp
