"""Notes widget for TUIDash."""

from datetime import datetime
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, Label, TextArea
from textual.reactive import reactive


NOTES_FILE = Path("notes.md")


class NotesWidget(Static):
    """Widget for taking and displaying notes."""

    DEFAULT_CSS = """
    NotesWidget {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    NotesWidget .notes-title {
        text-style: bold;
        color: $text;
        text-align: center;
        margin-bottom: 1;
    }

    NotesWidget .notes-date {
        color: $text-muted;
        text-align: center;
        margin-bottom: 1;
    }

    NotesWidget .notes-editor {
        height: 1fr;
        min-height: 5;
    }

    NotesWidget .notes-hint {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }

    NotesWidget .notes-icon {
        text-align: center;
        color: $primary;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("📝  Notes", classes="notes-title")
        yield Container(id="notes-content")

    def on_mount(self) -> None:
        """Initialize the notes display."""
        self._update_display()
        self._load_notes()

    def _update_display(self) -> None:
        """Update the widget content."""
        content = self.query_one("#notes-content", Container)
        content.remove_children()

        # Date
        today = datetime.now().strftime("%A, %B %d")
        content.mount(Label(today, classes="notes-date"))

        # Editor
        editor = TextArea(id="notes-editor", classes="notes-editor")
        editor.show_line_numbers = False
        content.mount(editor)

        # Hint
        content.mount(Label("Esc to unfocus • Auto-saves", classes="notes-hint"))

    def _load_notes(self) -> None:
        """Load notes from file."""
        try:
            editor = self.query_one("#notes-editor", TextArea)
            if NOTES_FILE.exists():
                editor.text = NOTES_FILE.read_text()
        except Exception:
            pass

    def _save_notes(self) -> None:
        """Save notes to file."""
        try:
            editor = self.query_one("#notes-editor", TextArea)
            NOTES_FILE.write_text(editor.text)
        except Exception:
            pass

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Auto-save when text changes."""
        self._save_notes()

    async def refresh_data(self) -> None:
        """Notes don't need external refresh."""
        pass
