"""Tides widget for TUIDash."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static, Label
from textual.reactive import reactive

from ..services.tides_service import TidesService, TidesData, get_tide_icon, generate_tide_chart
from ..config import Config


class TidesWidget(Static):
    """Widget displaying tide predictions with wave chart."""

    DEFAULT_CSS = """
    TidesWidget {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    TidesWidget .tides-title {
        text-style: bold;
        color: $text;
        text-align: center;
        margin-bottom: 1;
    }

    TidesWidget .tide-chart {
        color: $primary;
    }

    TidesWidget .tide-info {
        height: auto;
    }

    TidesWidget .tide-event {
        height: auto;
    }

    TidesWidget .tide-type-high {
        color: $success;
    }

    TidesWidget .tide-type-low {
        color: $primary;
    }

    TidesWidget .tide-time {
        color: $text-muted;
    }

    TidesWidget .tide-error {
        color: $error;
        text-align: center;
    }

    TidesWidget .tide-loading {
        color: $text-muted;
        text-align: center;
    }
    """

    data: reactive[TidesData | None] = reactive(None)
    error: reactive[str | None] = reactive(None)
    loading: reactive[bool] = reactive(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = TidesService(Config.TIDES_STATION_ID)

    def compose(self) -> ComposeResult:
        yield Label("🌊  Tides", classes="tides-title")
        yield Container(id="tides-content")

    def watch_data(self, data: TidesData | None) -> None:
        self._update_display()

    def watch_error(self, error: str | None) -> None:
        self._update_display()

    def watch_loading(self, loading: bool) -> None:
        self._update_display()

    def _update_display(self) -> None:
        """Update the widget content."""
        content = self.query_one("#tides-content", Container)
        content.remove_children()

        if self.loading:
            content.mount(Label("Loading...", classes="tide-loading"))
            return

        if self.error:
            content.mount(Label(f"⚠️ {self.error}", classes="tide-error"))
            return

        if self.data and self.data.predictions:
            # Generate and display wave chart (48 hours with depth Y-axis)
            chart = generate_tide_chart(self.data.predictions, width=52, height=12)
            content.mount(Static(chart, classes="tide-chart"))
            
            # Show upcoming tide events inline
            info = Horizontal(classes="tide-info")
            content.mount(info)
            
            for event in self.data.predictions[:4]:
                type_class = "tide-type-high" if event.type == "H" else "tide-type-low"
                icon = "▲" if event.type == "H" else "▼"
                info.mount(Label(
                    f"{icon}{event.time_display} {event.height:.1f}ft  ",
                    classes=f"tide-event {type_class}"
                ))

    async def refresh_data(self) -> None:
        """Fetch fresh tides data."""
        self.loading = True
        self.error = None

        try:
            self.data = await self.service.get_predictions(days=3)  # 3 days for 48h chart
        except Exception as e:
            self.error = str(e)[:50]
        finally:
            self.loading = False
