from __future__ import annotations

from selectors import DefaultSelector, EVENT_READ
from typing import Callable
import os

from toolong.log_file import LogFile
from toolong.watcher import WatcherBase


class SelectorWatcher(WatcherBase):
    """Watches files for changes using a selector (macOS/BSD kqueue-backed)."""

    def __init__(self) -> None:
        self._selector = DefaultSelector()
        super().__init__()

    def close(self) -> None:
        """Signal exit, close dedicated watch handles, and clean up the selector."""
        # Set exit event first so the run loop stops
        if not self._exit_event.is_set():
            self._exit_event.set()
        # Unregister all fds from the selector before closing
        for watch_fileno in list(self._watched_files.keys()):
            try:
                self._selector.unregister(watch_fileno)
            except Exception:
                pass
        # Delegate handle closing to base class
        super().close()

    def add(
        self,
        log_file: LogFile,
        callback: Callable[[int, list[int]], None],
        error_callback: Callable[[Exception], None],
    ) -> None:
        """Add a file to the watcher with a dedicated, independent file handle."""
        # Base class opens the dedicated watch file and seeks to EOF
        super().add(log_file, callback, error_callback)
        # Find the watch_fileno for this log_file (just added by super)
        watch_fileno = next(
            fd for fd, wf in self._watched_files.items() if wf.log_file is log_file
        )
        # Register the dedicated watch fd with the selector
        self._selector.register(watch_fileno, EVENT_READ)

    def run(self) -> None:
        """Thread runner."""
        chunk_size = 64 * 1024
        scan_chunk = self.scan_chunk

        while not self._exit_event.is_set():
            for key, mask in self._selector.select(timeout=0.1):
                if self._exit_event.is_set():
                    break
                if mask & EVENT_READ:
                    watch_fileno = key.fileobj
                    assert isinstance(watch_fileno, int)
                    watched_file = self._watched_files.get(watch_fileno)
                    if watched_file is None:
                        continue

                    try:
                        position = os.lseek(watch_fileno, 0, os.SEEK_CUR)
                        chunk = os.read(watch_fileno, chunk_size)
                        if chunk:
                            breaks = scan_chunk(chunk, position)
                            watched_file.callback(position + len(chunk), breaks)

                    except Exception as error:
                        watched_file.error_callback(error)
                        self._watched_files.pop(watch_fileno, None)
                        try:
                            self._selector.unregister(watch_fileno)
                        except Exception:
                            pass
                        try:
                            watched_file.watch_file.close()
                        except OSError:
                            pass
