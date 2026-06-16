from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Vertical, Center
from textual.widgets import Label, Button

if TYPE_CHECKING:
    from textual.worker import Worker


class SeekingScreen(ModalScreen):
    DEFAULT_CSS = """
    SeekingScreen {
        background: rgba(0, 0, 0, 0.65);
        align: center middle;
    }
    
    #seeking-dialog {
        width: 44;
        height: auto;
        border: thick $accent;
        background: $panel;
        padding: 1 3;
    }
    
    #seeking-dialog Label {
        width: 100%;
        text-align: center;
        margin: 1 0;
        color: $text;
        text-style: bold;
    }
    
    #seeking-dialog Button {
        margin-top: 1;
        width: auto;
        min-width: 16;
    }
    """

    def __init__(self, worker: Worker) -> None:
        self.worker = worker
        super().__init__()

    def compose(self) -> ComposeResult:
        with Vertical(id="seeking-dialog") as container:
            container.border_title = "Seeking Log File"
            yield Label("Seeking by date...")
            with Center():
                yield Button("Cancel", variant="error", id="cancel-seek")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-seek":
            self.worker.cancel()
            self.dismiss()
