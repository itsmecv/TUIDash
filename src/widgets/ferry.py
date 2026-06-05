"""Ferry widget for TUIDash."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, Label
from textual.reactive import reactive

from ..services.ferry_service import FerryService, FerrySchedule
from ..services.kitsap_ferry_service import KitsapFerryService
from ..config import Config


class FerryWidget(Static):
    """Widget displaying WSF and Kitsap Fast Ferry schedules."""

    DEFAULT_CSS = """
    FerryWidget {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    FerryWidget #ferry-content {
        height: 1fr;
    }

    FerryWidget .ferry-title {
        text-style: bold;
        color: $text;
        text-align: center;
        margin-bottom: 1;
    }

    FerryWidget .ferry-section {
        text-style: bold;
        color: $text;
        margin-top: 1;
    }

    FerryWidget .ferry-icon {
        text-align: center;
        color: $primary;
    }

    FerryWidget .ferry-direction {
        text-style: bold;
        color: $success;
    }

    FerryWidget .departure-row {
        height: auto;
    }

    FerryWidget .departure-time {
        width: 10;
        color: $warning;
    }

    FerryWidget .departure-countdown {
        color: $text-muted;
    }

    FerryWidget .departure-delayed {
        color: $error;
    }

    FerryWidget .departure-cancelled {
        color: $error;
        text-style: strike;
    }

    FerryWidget .vessel-status {
        color: $primary;
    }

    FerryWidget .vessel-eta {
        color: $text-muted;
    }

    FerryWidget .progress-bar {
        color: $success;
    }

    FerryWidget .ferry-alert {
        color: $error;
    }

    FerryWidget .ferry-error {
        color: $error;
        text-align: center;
    }

    FerryWidget .ferry-loading {
        color: $text-muted;
        text-align: center;
    }

    FerryWidget .ferry-no-api {
        color: $warning;
    }
    """

    data: reactive[FerrySchedule | None] = reactive(None)
    error: reactive[str | None] = reactive(None)
    loading: reactive[bool] = reactive(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = FerryService(Config.WSDOT_API_KEY, Config.FERRY_ROUTE)
        self.kitsap_service = KitsapFerryService()

    def compose(self) -> ComposeResult:
        yield Label("⛴️  Ferry", classes="ferry-title")
        yield VerticalScroll(id="ferry-content")

    def watch_data(self, data: FerrySchedule | None) -> None:
        self._update_display()

    def watch_error(self, error: str | None) -> None:
        self._update_display()

    def watch_loading(self, loading: bool) -> None:
        self._update_display()

    def _update_display(self) -> None:
        """Update the widget content."""
        content = self.query_one("#ferry-content", VerticalScroll)
        content.remove_children()

        if self.loading:
            content.mount(Label("Loading...", classes="ferry-loading"))
            return

        if self.error and not self.data:
            content.mount(Label(f"⚠️ {self.error}", classes="ferry-error"))
            return

        # WSF Edmonds-Kingston
        if self.data and self.data.departures:
            content.mount(Label("WSF Edmonds-Kingston", classes="ferry-section"))
            
            departures_by_terminal: dict[str, list] = {}
            for dep in self.data.departures:
                terminal = dep.departing_terminal
                if terminal not in departures_by_terminal:
                    departures_by_terminal[terminal] = []
                departures_by_terminal[terminal].append(dep)

            for terminal, departures in departures_by_terminal.items():
                next_deps = [d for d in departures if d.time_until().total_seconds() > 0][:2]
                if not next_deps:
                    continue

                content.mount(Label(f"From {terminal}:", classes="ferry-direction"))

                for dep in next_deps:
                    row = Horizontal(classes="departure-row")
                    content.mount(row)
                    
                    # Time with delay indicator
                    if dep.is_cancelled:
                        time_class = "departure-cancelled"
                        row.mount(Label(dep.time_display, classes=time_class))
                    elif dep.is_delayed:
                        row.mount(Label(f"{dep.time_display} +{dep.delay_minutes}m", classes="departure-delayed"))
                    else:
                        row.mount(Label(dep.time_display, classes="departure-time"))
                    
                    row.mount(Label(f"({dep.time_until_display()})", classes="departure-countdown"))
                    
                    # Show vessel status if available
                    if dep.vessel_position:
                        v = dep.vessel_position
                        dest = v.arriving_terminal[:3] if v.arriving_terminal else dep.arriving_terminal[:3]
                        progress_bar = v.progress_bar(22)
                        if progress_bar:
                            content.mount(Label(f"  {v.departing_terminal[:3]} {progress_bar} {dest}", classes="progress-bar"))
                            if v.at_dock:
                                content.mount(Label(f"  ⛴ {v.vessel_name} loading", classes="vessel-status"))
                            elif v.eta:
                                content.mount(Label(f"  ETA {v.eta_display} ({v.speed:.1f} kts)", classes="vessel-eta"))
        elif not Config.WSDOT_API_KEY:
            content.mount(Label("WSF: API key not set", classes="ferry-no-api"))

        # Kitsap Fast Ferry Kingston-Seattle
        content.mount(Label("Fast Ferry Kingston-Seattle", classes="ferry-section"))
        
        # Get departures grouped by direction
        next_to_seattle = self.kitsap_service.next_to_seattle(count=2)
        next_to_kingston = self.kitsap_service.next_to_kingston(count=2)
        current_sailing = self.kitsap_service.current_sailing()
        
        # From Kingston (to Seattle)
        if next_to_seattle or (current_sailing and current_sailing.direction == "to_seattle"):
            content.mount(Label("From Kingston:", classes="ferry-direction"))
            
            # Show en-route ferry first if heading to Seattle
            if current_sailing and current_sailing.direction == "to_seattle":
                progress_bar = current_sailing.progress_bar(22)
                if progress_bar:
                    content.mount(Label(f"  KNG {progress_bar} SEA", classes="progress-bar"))
                content.mount(Label(f"  ETA {current_sailing.arrival_display} ({current_sailing.eta_display})", classes="vessel-eta"))
            
            for dep in next_to_seattle:
                row = Horizontal(classes="departure-row")
                content.mount(row)
                row.mount(Label(dep.time_display, classes="departure-time"))
                row.mount(Label(f"({dep.time_until_display()})", classes="departure-countdown"))
        
        # From Seattle (to Kingston)
        if next_to_kingston or (current_sailing and current_sailing.direction == "to_kingston"):
            content.mount(Label("From Seattle:", classes="ferry-direction"))
            
            # Show en-route ferry first if heading to Kingston
            if current_sailing and current_sailing.direction == "to_kingston":
                progress_bar = current_sailing.progress_bar(22)
                if progress_bar:
                    content.mount(Label(f"  SEA {progress_bar} KNG", classes="progress-bar"))
                content.mount(Label(f"  ETA {current_sailing.arrival_display} ({current_sailing.eta_display})", classes="vessel-eta"))
            
            for dep in next_to_kingston:
                row = Horizontal(classes="departure-row")
                content.mount(row)
                row.mount(Label(dep.time_display, classes="departure-time"))
                row.mount(Label(f"({dep.time_until_display()})", classes="departure-countdown"))
        
        # No service message
        if not next_to_seattle and not next_to_kingston and not current_sailing:
            content.mount(Label("No service today", classes="ferry-no-api"))

    async def refresh_data(self) -> None:
        """Fetch fresh ferry data."""
        self.loading = True
        self.error = None

        try:
            if Config.WSDOT_API_KEY:
                self.data = await self.service.get_schedule(both_directions=True)
            else:
                self.data = None
        except Exception as e:
            self.error = str(e)[:50]
        finally:
            self.loading = False
            self._update_display()  # Also refresh Kitsap which doesn't need API
