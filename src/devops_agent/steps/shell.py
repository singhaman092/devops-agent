"""shell.run step primitive — execute commands via Git Bash."""

from __future__ import annotations

import asyncio
from typing import Any

from devops_agent.config.paths import resolve_git_bash
from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.tasks.models import StepResult


@register_step
class ShellRun:
    """Execute a shell command via Git Bash, capture stdout/stderr/exit code."""

    @property
    def name(self) -> str:
        return "shell.run"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        command: str = params.get("command", "")
        if not command:
            result.mark_failed("No command specified")
            return result

        cwd = str(params.get("cwd", ctx.work_dir))
        timeout = int(params.get("timeout", 300))

        bash_path = resolve_git_bash()
        if bash_path is None:
            result.mark_failed("Git Bash not found. Install Git for Windows.")
            return result

        try:
            proc = await asyncio.create_subprocess_exec(
                str(bash_path),
                "-c",
                ctx.resolve_var(command),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode or 0

            result.stdout = stdout
            result.stderr = stderr

            if exit_code == 0:
                result.mark_success({"exit_code": exit_code, "stdout": stdout})
            else:
                result.mark_failed(
                    f"Command exited with code {exit_code}", stderr=stderr
                )

        except asyncio.TimeoutError:
            result.mark_failed(f"Command timed out after {timeout}s")
        except OSError as e:
            result.mark_failed(f"Failed to execute command: {e}")

        return result
