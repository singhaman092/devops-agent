"""Watchdog-based observer for the pending/ directory."""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog
from watchdog.events import FileCreatedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from devops_agent.config.loader import load_activation
from devops_agent.config.paths import get_tasks_subdir
from devops_agent.tasks.executor import execute_task
from devops_agent.tasks.lifecycle import create_task

log = structlog.get_logger("watcher")


class PendingHandler(FileSystemEventHandler):
    """Handles new files in the pending/ directory."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def on_created(self, event: FileCreatedEvent) -> None:  # type: ignore[override]
        if event.is_directory:
            return
        path = Path(str(event.src_path))
        if path.suffix not in (".yaml", ".yml"):
            return
        # Skip state files
        if path.name.endswith(".state.json"):
            return

        log.info("pending_file_detected", path=str(path))
        self._loop.call_soon_threadsafe(
            asyncio.ensure_future,
            self._handle_activation(path),
        )

    async def _handle_activation(self, path: Path) -> None:
        try:
            activation = load_activation(path)
            state = create_task(
                task_config_name=activation.task_config,
                activation_file=str(path),
                variables=activation.variables,
                task_id=activation.task_id or "",
            )
            log.info("task_created_from_watcher", task_id=state.task_id)
            await execute_task(state.task_id)
        except Exception as e:
            log.error("watcher_task_error", path=str(path), error=str(e))


def start_watcher() -> Observer:
    """Start watching the pending/ directory. Returns the observer (call .stop() to shut down)."""
    pending_dir = get_tasks_subdir("pending")
    loop = asyncio.get_event_loop()

    handler = PendingHandler(loop)
    observer = Observer()
    observer.schedule(handler, str(pending_dir), recursive=False)
    observer.start()

    log.info("watcher_started", dir=str(pending_dir))
    return observer
