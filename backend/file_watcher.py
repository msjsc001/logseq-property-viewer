# -*- coding: utf-8 -*-
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Set

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

import core
from app_logging import get_logger


logger = get_logger("property_query.file_watcher")


class LogseqFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        graph_path: str,
        on_change_callback: Callable[[str, str], None],
    ):
        super().__init__()
        self.graph_path = graph_path
        self.on_change_callback = on_change_callback
        self._debounce_timer: Optional[threading.Timer] = None
        self._pending_changes: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._debounce_seconds = 1.5

    def _schedule_callback(self) -> None:
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                self._debounce_seconds,
                self._process_changes,
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _queue_change(self, path: str, event_type: str) -> None:
        if not core.is_path_in_graph_scope(self.graph_path, path):
            return
        with self._lock:
            self._pending_changes[path] = event_type
        self._schedule_callback()

    def _process_changes(self) -> None:
        with self._lock:
            changes = self._pending_changes.copy()
            self._pending_changes.clear()
            self._debounce_timer = None
        for file_path, event_type in changes.items():
            try:
                self.on_change_callback(file_path, event_type)
            except Exception as exc:
                logger.exception("Failed to process watcher change for %s: %s", file_path, exc)

    def close(self) -> None:
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            self._pending_changes.clear()

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory:
            self._queue_change(event.src_path, "modified")

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory:
            self._queue_change(event.src_path, "created")

    def on_deleted(self, event: FileDeletedEvent) -> None:
        if not event.is_directory:
            self._queue_change(event.src_path, "deleted")

    def on_moved(self, event: FileMovedEvent) -> None:
        if event.is_directory:
            return
        self._queue_change(event.src_path, "deleted")
        self._queue_change(event.dest_path, "created")


class FileWatcherService:
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._observer: Optional[Observer] = None
        self._handler: Optional[LogseqFileHandler] = None
        self._watching_path: Optional[str] = None
        self._enabled = False
        self._changed_files: Set[str] = set()
        self._changes_lock = threading.Lock()
        self._on_change_callbacks: list[Callable[[str, str], None]] = []
        self._last_apply_failures: list[str] = []

    def _handle_file_change(self, file_path: str, event_type: str) -> None:
        logger.info("Detected %s: %s", event_type, file_path)
        with self._changes_lock:
            self._changed_files.add(file_path)
        for callback in self._on_change_callbacks:
            try:
                callback(file_path, event_type)
            except Exception as exc:
                logger.exception("Watcher callback failed for %s: %s", file_path, exc)

    def start_watching(self, graph_path: str) -> bool:
        if not graph_path or not Path(graph_path).is_dir():
            logger.warning("Watcher received invalid graph path: %s", graph_path)
            return False

        if self._observer and self._watching_path == graph_path and self.is_watching():
            return True

        self.stop_watching()
        watch_roots = [root for root in core.discover_scan_roots(graph_path) if root.exists()]
        if not watch_roots:
            logger.warning("Watcher found no directories to observe for %s", graph_path)
            return False

        try:
            self._observer = Observer()
            self._handler = LogseqFileHandler(graph_path, self._handle_file_change)
            for root in watch_roots:
                self._observer.schedule(self._handler, str(root), recursive=True)
            self._observer.start()
            self._watching_path = graph_path
            self._enabled = True
            self.clear_pending_changes()
            self.set_last_apply_failures([])
            logger.info("Started watcher for %s", graph_path)
            return True
        except Exception as exc:
            logger.exception("Failed to start watcher for %s: %s", graph_path, exc)
            self._observer = None
            self._handler = None
            self._watching_path = None
            self._enabled = False
            return False

    def stop_watching(self) -> None:
        if self._handler:
            self._handler.close()
            self._handler = None
        if self._observer:
            try:
                if self._observer.is_alive():
                    self._observer.stop()
                    self._observer.join(timeout=3)
            except RuntimeError:
                logger.warning("Watcher stop skipped join because observer was not started")
            except Exception as exc:
                logger.exception("Error while stopping watcher: %s", exc)
            finally:
                self._observer = None
        self._watching_path = None
        self._enabled = False

    def get_pending_changes(self) -> Set[str]:
        with self._changes_lock:
            return set(self._changed_files)

    def clear_pending_changes(self) -> None:
        with self._changes_lock:
            self._changed_files.clear()

    def get_pending_count(self) -> int:
        with self._changes_lock:
            return len(self._changed_files)

    def is_enabled(self) -> bool:
        return self._enabled

    def is_watching(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    def set_last_apply_failures(self, failures: list[str]) -> None:
        self._last_apply_failures = failures

    def get_last_apply_failures(self) -> list[str]:
        return list(self._last_apply_failures)

    def get_status(self) -> dict:
        return {
            "enabled": self._enabled,
            "watching": self.is_watching(),
            "path": self._watching_path,
            "pending_count": self.get_pending_count(),
            "failed_count": len(self._last_apply_failures),
        }

    def register_callback(self, callback: Callable[[str, str], None]) -> None:
        if callback not in self._on_change_callbacks:
            self._on_change_callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str, str], None]) -> None:
        if callback in self._on_change_callbacks:
            self._on_change_callbacks.remove(callback)


file_watcher = FileWatcherService()
