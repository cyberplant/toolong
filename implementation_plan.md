# Implementation Plan - Separate Watcher File Handlers

To resolve conflicts where concurrent seek/read operations on the same file descriptor (by the watcher and the reader/scanner threads) corrupt the file pointer position, we will allocate a separate, dedicated file descriptor for watching file additions.

## User Review Required

> [!IMPORTANT]
> The watcher will now open its own read-only file descriptor of the log file, seek to the end, and poll/select on this separate descriptor. This completely isolates tailing from scanning/seeking.

## Proposed Changes

---

### Watcher Architecture

#### [MODIFY] [watcher.py](file:///Users/luar/dev/toolong/src/toolong/watcher.py)
- Import `IO` from `typing`.
- Update `WatchedFile` class to include `watch_file: IO[bytes] | None = None`.
- Update `WatcherBase.add` to:
  - Open a separate file descriptor `watch_file = open(log_file.path, "rb", buffering=0)`.
  - Seek to the end of `watch_file` so it only reads future additions.
  - Store the `watch_file` object in `WatchedFile` and index it using `watch_file.fileno()`.
- Update `WatcherBase.close` to close all open `watch_file` descriptors.

#### [MODIFY] [selector_watcher.py](file:///Users/luar/dev/toolong/src/toolong/selector_watcher.py)
- In `add`, call `super().add(...)` to create the isolated `watch_file`.
- Find the newly added `fileno` and register it with the selector.
- In `run`, when an error occurs, safely close the `watch_file`.

---

## Verification Plan

### Automated Tests
- Run unit tests to verify that basic operations compile and run without issues.

### Manual Verification
- Open a large log file.
- Move/seek around the file.
- Append lines to the file.
- Verify that pressing `[end]` takes you to the actual end of the file (including the newly appended lines) and tailing functions correctly.
