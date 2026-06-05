"""Weather widget for TUIDash."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Static, Label
from textual.reactive import reactive

from ..services.weather_service import WeatherService, WeatherData, HourlyForecast, ForecastPeriod
from ..config import Config


class WeatherWidget(Static):
    """Widget displaying current weather, hourly, and 5-day forecast."""

    DEFAULT_CSS = """
    WeatherWidget {
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    WeatherWidget .weather-title {
        text-style: bold;
        color: $text;
        text-align: center;
        margin-bottom: 1;
    }

    WeatherWidget .weather-temp-large {
        text-style: bold;
        color: $success;
        text-align: center;
    }

    WeatherWidget .weather-condition {
        color: $text-muted;
        text-align: center;
    }

    WeatherWidget .weather-details {
        color: $text-muted;
    }

    WeatherWidget .weather-icon {
        text-align: center;
        color: $warning;
    }

    WeatherWidget .weather-error {
        color: $error;
        text-align: center;
    }

    WeatherWidget .weather-loading {
        color: $text-muted;
        text-align: center;
    }

    WeatherWidget .section-header {
        text-style: bold;
        color: $text;
        margin-top: 1;
    }

    WeatherWidget .hourly-row {
        height: auto;
    }

    WeatherWidget .hourly-item {
        width: auto;
        padding: 0 1;
    }

    WeatherWidget .forecast-row {
        height: auto;
    }

    WeatherWidget .forecast-day {
        width: 12;
        color: $text;
    }

    WeatherWidget .forecast-high {
        width: 5;
        color: $warning;
    }

    WeatherWidget .forecast-low {
        width: 5;
        color: $primary;
    }

    WeatherWidget .forecast-cond {
        color: $text-muted;
    }
    """

    data: reactive[WeatherData | None] = reactive(None)
    hourly: reactive[list[HourlyForecast]] = reactive([])
    forecast: reactive[list[ForecastPeriod]] = reactive([])
    error: reactive[str | None] = reactive(None)
    loading: reactive[bool] = reactive(True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = WeatherService(Config.LATITUDE, Config.LONGITUDE)

    def compose(self) -> ComposeResult:
        yield Label("🌤️  Weather", classes="weather-title")
        yield Container(id="weather-content")

    def watch_data(self, data: WeatherData | None) -> None:
        self._update_display()

    def watch_hourly(self, hourly: list) -> None:
        self._update_display()

    def watch_forecast(self, forecast: list) -> None:
        self._update_display()

    def watch_error(self, error: str | None) -> None:
        self._update_display()

    def watch_loading(self, loading: bool) -> None:
        self._update_display()

    def _update_display(self) -> None:
        """Update the widget content."""
        content = self.query_one("#weather-content", Container)
        content.remove_children()

        if self.loading:
            content.mount(Label("Loading...", classes="weather-loading"))
            return

        if self.error:
            content.mount(Label(f"⚠️ {self.error}", classes="weather-error"))
            return

        if self.data:
            # Current weather
            content.mount(Label(f"{self.data.temp_display}  {self.data.short_forecast}", classes="weather-temp-large"))
            content.mount(
                Label(
                    f"Wind: {self.data.wind_speed} {self.data.wind_direction}",
                    classes="weather-details",
                )
            )

        # 5-hour forecast
        if self.hourly:
            content.mount(Label("Next 5 Hours:", classes="section-header"))
            hourly_row = Horizontal(classes="hourly-row")
            content.mount(hourly_row)
            for h in self.hourly[:5]:
                hourly_row.mount(Label(f"{h.time_display} {h.icon} {h.temp_display}", classes="hourly-item"))

        # 5-day forecast
        if self.forecast:
            content.mount(Label("5-Day Forecast:", classes="section-header"))
            # Group by day (skip current period if night, pair day/night)
            shown_days = 0
            i = 0
            while i < len(self.forecast) and shown_days < 5:
                period = self.forecast[i]
                if period.is_daytime:
                    # Find the matching night
                    night_temp = ""
                    if i + 1 < len(self.forecast) and not self.forecast[i + 1].is_daytime:
                        night_temp = f"{self.forecast[i + 1].temperature}°"
                    
                    row = Horizontal(classes="forecast-row")
                    content.mount(row)
                    row.mount(Label(period.day_name[:10], classes="forecast-day"))
                    row.mount(Label(f"{period.temperature}°", classes="forecast-high"))
                    row.mount(Label(night_temp, classes="forecast-low"))
                    row.mount(Label(period.short_forecast[:20], classes="forecast-cond"))
                    shown_days += 1
                i += 1

    async def refresh_data(self) -> None:
        """Fetch fresh weather data."""
        self.loading = True
        self.error = None

        try:
            self.data = await self.service.get_current_weather()
            self.hourly = await self.service.get_hourly_forecast(5)
            self.forecast = await self.service.get_5day_forecast()
        except Exception as e:
            self.error = str(e)[:50]
        finally:
            self.loading = False
