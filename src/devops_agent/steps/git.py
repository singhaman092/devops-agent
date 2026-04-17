"""Git step primitives — thin wrappers over shell.run with structured params."""

from __future__ import annotations

from typing import Any

from devops_agent.steps.base import Step, StepContext
from devops_agent.steps.registry import register_step
from devops_agent.steps.shell import ShellRun
from devops_agent.tasks.models import StepResult


async def _shell(ctx: StepContext, command: str, cwd: str | None = None) -> StepResult:
    """Helper to run a shell command via the ShellRun step."""
    shell = ShellRun()
    params: dict[str, Any] = {"command": command}
    if cwd:
        params["cwd"] = cwd
    return await shell.execute(ctx, params)


@register_step
class GitClone:
    @property
    def name(self) -> str:
        return "git.clone"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        url = ctx.resolve_var(params.get("url", ""))
        dest = ctx.resolve_var(params.get("dest", ""))
        if not url:
            result.mark_failed("No clone URL specified")
            return result
        if not dest:
            dest = str(ctx.work_dir / "repo")

        shell_result = await _shell(ctx, f'git clone "{url}" "{dest}"')
        if shell_result.status == "success":
            result.mark_success({"clone_dir": dest})
        else:
            result.mark_failed(shell_result.error_message, shell_result.stderr)
        return result


@register_step
class GitBranch:
    @property
    def name(self) -> str:
        return "git.branch"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        branch_name = ctx.resolve_var(params.get("branch", ""))
        cwd = ctx.resolve_var(params.get("cwd", str(ctx.work_dir)))
        base = ctx.resolve_var(params.get("base", ""))

        if not branch_name:
            result.mark_failed("No branch name specified")
            return result

        cmd = f"git checkout -b {branch_name}"
        if base:
            cmd = f"git fetch origin && git checkout -b {branch_name} origin/{base}"

        shell_result = await _shell(ctx, cmd, cwd)
        if shell_result.status == "success":
            result.mark_success({"branch_name": branch_name})
        else:
            result.mark_failed(shell_result.error_message, shell_result.stderr)
        return result


@register_step
class GitCommit:
    @property
    def name(self) -> str:
        return "git.commit"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        message = ctx.resolve_var(params.get("message", ""))
        cwd = ctx.resolve_var(params.get("cwd", str(ctx.work_dir)))
        add_all = params.get("add_all", True)

        if not message:
            result.mark_failed("No commit message specified")
            return result

        cmd = ""
        if add_all:
            cmd += "git add -A && "
        cmd += f'git commit -m "{message}"'

        shell_result = await _shell(ctx, cmd, cwd)
        if shell_result.status == "success":
            result.mark_success()
        else:
            result.mark_failed(shell_result.error_message, shell_result.stderr)
        return result


@register_step
class GitPush:
    @property
    def name(self) -> str:
        return "git.push"

    async def execute(self, ctx: StepContext, params: dict[str, Any]) -> StepResult:
        result = StepResult(step_name=self.name, params=params)
        result.mark_started()

        cwd = ctx.resolve_var(params.get("cwd", str(ctx.work_dir)))
        remote = params.get("remote", "origin")
        branch = ctx.resolve_var(params.get("branch", ""))
        set_upstream = params.get("set_upstream", True)

        cmd = f"git push {remote}"
        if branch:
            cmd += f" {branch}"
        if set_upstream:
            cmd = cmd.replace("git push", "git push -u", 1)

        shell_result = await _shell(ctx, cmd, cwd)
        if shell_result.status == "success":
            result.mark_success()
        else:
            result.mark_failed(shell_result.error_message, shell_result.stderr)
        return result
