"""TUIDash - Ambient daily dashboard TUI application."""

import asyncio
from datetime import datetime
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label

from .widgets import WeatherWidget, TidesWidget, FerryWidget, NotesWidget
from .config import Config


class StatusBar(Static):
    """Status bar showing last update time and refresh countdown."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }

    StatusBar .status-left {
        width: 50%;
    }

    StatusBar .status-right {
        width: 50%;
        text-align: right;
    }
    """

    def __init__(self):
        super().__init__()
        self.last_update: datetime | None = None
        self.next_refresh: int = 0

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("", id="status-left", classes="status-left")
            yield Label("", id="status-right", classes="status-right")

    def update_status(self, last_update: datetime, seconds_until_refresh: int) -> None:
        """Update the status bar."""
        self.last_update = last_update
        self.next_refresh = seconds_until_refresh

        left = self.query_one("#status-left", Label)
        right = self.query_one("#status-right", Label)

        left.update(f"Last update: {last_update.strftime('%I:%M:%S %p')}")

        minutes = seconds_until_refresh // 60
        seconds = seconds_until_refresh % 60
        right.update(f"Next refresh: {minutes}:{seconds:02d}")


class TUIDashApp(App):
    """Main TUIDash application."""

    TITLE = "TUIDash"
    SUB_TITLE = "Daily Dashboard"

    CSS = """
    Screen {
        background: $surface;
    }

    #main-grid {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
        height: 1fr;
    }

    #weather-container {
        row-span: 1;
        column-span: 1;
    }

    #tides-container {
        row-span: 1;
        column-span: 1;
    }

    #ferry-container {
        row-span: 1;
        column-span: 1;
    }

    #notes-container {
        row-span: 1;
        column-span: 1;
    }

    .widget-container {
        height: 100%;
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("?", "help", "Help", show=True),
        Binding("d", "toggle_dark", "Dark/Light", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.refresh_interval = Config.REFRESH_INTERVAL
        self._refresh_task: asyncio.Task | None = None
        self._countdown: int = self.refresh_interval

    def compose(self) -> ComposeResult:
        yield Header()

        with Container(id="main-grid"):
            with Container(id="weather-container", classes="widget-container"):
                yield WeatherWidget()

            with Container(id="tides-container", classes="widget-container"):
                yield TidesWidget()

            with Container(id="ferry-container", classes="widget-container"):
                yield FerryWidget()

            with Container(id="notes-container", classes="widget-container"):
                yield NotesWidget()

        yield StatusBar()
        yield Footer()

    async def on_mount(self) -> None:
        """Called when app is mounted."""
        # Initial data load
        await self._refresh_all_widgets()

        # Start auto-refresh loop
        self._refresh_task = asyncio.create_task(self._auto_refresh_loop())

    async def on_unmount(self) -> None:
        """Called when app is unmounted."""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

    async def _refresh_all_widgets(self) -> None:
        """Refresh all widgets in parallel."""
        weather = self.query_one(WeatherWidget)
        tides = self.query_one(TidesWidget)
        ferry = self.query_one(FerryWidget)
        notes = self.query_one(NotesWidget)

        # Refresh all widgets concurrently
        await asyncio.gather(
            weather.refresh_data(),
            tides.refresh_data(),
            ferry.refresh_data(),
            notes.refresh_data(),
            return_exceptions=True,
        )

        # Update status bar
        status = self.query_one(StatusBar)
        status.update_status(datetime.now(), self.refresh_interval)
        self._countdown = self.refresh_interval

    async def _auto_refresh_loop(self) -> None:
        """Background task for auto-refreshing data."""
        while True:
            try:
                # Update countdown every second
                await asyncio.sleep(1)
                self._countdown -= 1

                # Update status bar
                status = self.query_one(StatusBar)
                if hasattr(status, "last_update") and status.last_update:
                    status.update_status(status.last_update, self._countdown)

                # Time to refresh
                if self._countdown <= 0:
                    await self._refresh_all_widgets()

            except asyncio.CancelledError:
                break
            except Exception:
                # Don't crash on errors, just continue
                pass

    async def action_refresh(self) -> None:
        """Manual refresh action."""
        self.notify("Refreshing...")
        await self._refresh_all_widgets()
        self.notify("Refreshed!", severity="information")

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark

    def action_help(self) -> None:
        """Show help."""
        self.notify(
            "Keys: [q]uit, [r]efresh, [d]ark mode, [?]help",
            title="TUIDash Help",
            timeout=5,
        )


def main():
    """Entry point for the application."""
    # Validate configuration
    missing = Config.validate()
    if missing:
        print("⚠️  Missing configuration:")
        for item in missing:
            print(f"   - {item}")
        print("\nCopy .env.example to .env and fill in the required values.")
        print("The app will still run but some widgets may not work.\n")

    app = TUIDashApp()
    app.run()


if __name__ == "__main__":
    main()
