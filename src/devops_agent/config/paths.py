"""Path resolution for ~/.devops-agent/ and Git Bash."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def get_config_dir() -> Path:
    """Return the root config directory (~/.devops-agent/)."""
    return Path.home() / ".devops-agent"


def get_task_configs_dir() -> Path:
    """Return the task-configs directory."""
    return get_config_dir() / "task-configs"


def get_tasks_dir() -> Path:
    """Return the runtime tasks directory."""
    return get_config_dir() / "tasks"


def get_tasks_subdir(name: str) -> Path:
    """Return a specific tasks subdirectory (pending, in_progress, waiting, done, failed)."""
    d = get_tasks_dir() / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def ensure_dirs() -> None:
    """Create all required directories if they don't exist."""
    dirs = [
        get_config_dir(),
        get_task_configs_dir(),
        get_tasks_dir(),
        get_tasks_subdir("pending"),
        get_tasks_subdir("in_progress"),
        get_tasks_subdir("waiting"),
        get_tasks_subdir("done"),
        get_tasks_subdir("failed"),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def resolve_git_bash() -> Path | None:
    """Find the Git Bash executable from Git for Windows install."""
    # Check PATH first
    bash = shutil.which("bash")
    if bash:
        bash_path = Path(bash)
        # Verify it's Git Bash (not WSL bash)
        if "git" in str(bash_path).lower():
            return bash_path

    # Check common install locations
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Git" / "bin" / "bash.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Git"
        / "bin"
        / "bash.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Git" / "bin" / "bash.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Try registry via where
    try:
        result = subprocess.run(
            ["where.exe", "git"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            git_path = Path(result.stdout.strip().splitlines()[0])
            bash_candidate = git_path.parent.parent / "bin" / "bash.exe"
            if bash_candidate.exists():
                return bash_candidate
    except (subprocess.TimeoutExpired, OSError):
        pass

    return None


def resolve_edge_binary() -> Path | None:
    """Find the Microsoft Edge executable."""
    candidates = [
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None
