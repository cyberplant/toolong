from __future__ import annotations

from os import lseek, read, SEEK_CUR
import time


from toolong.watcher import WatcherBase


class PollWatcher(WatcherBase):
    """A watcher that simply polls."""

    def run(self) -> None:
        chunk_size = 64 * 1024
        scan_chunk = self.scan_chunk

        while not self._exit_event.is_set():
            successful_read = False
            # Iterate over the dedicated watch file descriptors (not the reader's)
            for watch_fileno, watched_file in list(self._watched_files.items()):
                try:
                    position = lseek(watch_fileno, 0, SEEK_CUR)
                    if chunk := read(watch_fileno, chunk_size):
                        successful_read = True
                        breaks = scan_chunk(chunk, position)
                        watched_file.callback(position + len(chunk), breaks)
                        position += len(chunk)
                except Exception as error:
                    watched_file.error_callback(error)
                    self._watched_files.pop(watch_fileno, None)
                    try:
                        watched_file.watch_file.close()
                    except OSError:
                        pass
                    break
            else:
                if not successful_read:
                    time.sleep(0.05)
