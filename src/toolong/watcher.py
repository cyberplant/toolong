from __future__ import annotations

import rich.repr

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import os
import platform
from threading import Event, Thread
from typing import Callable, IO, TYPE_CHECKING


def get_watcher() -> WatcherBase:
    """Return a Watcher appropriate for the OS."""

    if platform.system() == "Darwin":
        from toolong.selector_watcher import SelectorWatcher

        return SelectorWatcher()
    else:
        from toolong.poll_watcher import PollWatcher

        return PollWatcher()


if TYPE_CHECKING:
    from .log_file import LogFile


@dataclass
@rich.repr.auto
class WatchedFile:
    """A currently watched file, with its own dedicated file handle for tailing."""

    log_file: LogFile
    callback: Callable[[int, list[int]], None]
    error_callback: Callable[[Exception], None]
    watch_file: IO[bytes]  # dedicated file handle, separate from the reader's handle


class WatcherBase(ABC):
    """Watches files for changes."""

    def __init__(self) -> None:
        # Keyed by the watch_file's fileno (not the reader's fileno)
        self._watched_files: dict[int, WatchedFile] = {}
        self._thread: Thread | None = None
        self._exit_event = Event()
        super().__init__()

    @classmethod
    def scan_chunk(cls, chunk: bytes, position: int) -> list[int]:
        """Scan line breaks in a binary chunk.

        Args:
            chunk: A binary chunk.
            position: Offset within the file.

        Returns:
            A list of indices of newline characters.
        """
        breaks: list[int] = []
        offset = 0
        append = breaks.append
        while (offset := chunk.find(b"\n", offset)) != -1:
            append(position + offset)
            offset += 1
        return breaks

    def close(self) -> None:
        """Signal watcher thread to exit and close all dedicated watch file handles."""
        if not self._exit_event.is_set():
            self._exit_event.set()
        for watched in list(self._watched_files.values()):
            try:
                watched.watch_file.close()
            except OSError:
                pass
        self._watched_files.clear()
        self._thread = None

    def start(self) -> None:
        assert self._thread is None
        self._thread = Thread(target=self.run, name=repr(self))
        self._thread.start()

    def add(
        self,
        log_file: LogFile,
        callback: Callable[[int, list[int]], None],
        error_callback: Callable[[Exception], None],
    ) -> None:
        """Add a file to the watcher.

        Opens a **separate** read-only file handle dedicated to watching so that
        the watcher's read position is completely independent from the reader's.
        """
        # Open a dedicated, independent file handle for tailing.
        watch_file: IO[bytes] = open(log_file.path, "rb", buffering=0)
        # Seek the dedicated handle to the current end of the file so we only
        # receive bytes appended in the future.
        watch_file.seek(log_file.size)
        watch_fileno = watch_file.fileno()
        self._watched_files[watch_fileno] = WatchedFile(
            log_file, callback, error_callback, watch_file
        )

    @abstractmethod
    def run(self) -> None:
        """Thread runner."""
