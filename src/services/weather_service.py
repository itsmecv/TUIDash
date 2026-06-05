"""Weather service using the National Weather Service API."""

from dataclasses import dataclass
from datetime import datetime
import httpx


@dataclass
class WeatherData:
    """Weather data container."""

    temperature: int
    temperature_unit: str
    short_forecast: str
    detailed_forecast: str
    wind_speed: str
    wind_direction: str
    humidity: int | None
    icon_url: str
    is_daytime: bool
    updated_at: datetime

    @property
    def temp_display(self) -> str:
        """Format temperature for display."""
        return f"{self.temperature}°{self.temperature_unit}"


@dataclass
class HourlyForecast:
    """Hourly forecast data."""
    
    time: datetime
    temperature: int
    temperature_unit: str
    short_forecast: str
    wind_speed: str
    wind_direction: str
    chance_of_precipitation: int | None
    
    @property
    def temp_display(self) -> str:
        return f"{self.temperature}°"
    
    @property
    def time_display(self) -> str:
        return self.time.strftime("%I%p").lstrip("0").lower()
    
    @property
    def icon(self) -> str:
        """Simple icon for hourly display."""
        fc = self.short_forecast.lower()
        if "rain" in fc or "shower" in fc:
            return "🌧"
        if "cloud" in fc:
            return "☁"
        if "partly" in fc:
            return "⛅"
        if "sun" in fc or "clear" in fc:
            return "☀"
        return "•"


@dataclass
class ForecastPeriod:
    """A forecast period (day/night)."""
    
    name: str  # e.g., "Tonight", "Wednesday", "Wednesday Night"
    temperature: int
    temperature_unit: str
    short_forecast: str
    is_daytime: bool
    wind_speed: str
    chance_of_precipitation: int | None
    
    @property
    def temp_display(self) -> str:
        return f"{self.temperature}°{self.temperature_unit}"
    
    @property
    def day_name(self) -> str:
        """Extract day name without 'Night'."""
        return self.name.replace(" Night", "")
    
    @property
    def icon(self) -> str:
        """Weather icon for this period."""
        return get_weather_icon(self.short_forecast, self.is_daytime)


class WeatherService:
    """Client for the National Weather Service API."""

    BASE_URL = "https://api.weather.gov"
    USER_AGENT = "TUIDash/1.0 (github.com/user/tuidash)"

    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude
        self._forecast_url: str | None = None
        self._hourly_url: str | None = None

    async def _get_forecast_urls(self, client: httpx.AsyncClient) -> None:
        """Get the forecast URLs for the location."""
        if self._forecast_url:
            return

        url = f"{self.BASE_URL}/points/{self.latitude},{self.longitude}"
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        self._forecast_url = data["properties"]["forecast"]
        self._hourly_url = data["properties"]["forecastHourly"]

    async def get_current_weather(self) -> WeatherData:
        """Fetch current weather conditions."""
        headers = {"User-Agent": self.USER_AGENT, "Accept": "application/geo+json"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            await self._get_forecast_urls(client)

            response = await client.get(self._forecast_url)
            response.raise_for_status()
            data = response.json()

            # Get the current period (first one)
            period = data["properties"]["periods"][0]

            return WeatherData(
                temperature=period["temperature"],
                temperature_unit=period["temperatureUnit"],
                short_forecast=period["shortForecast"],
                detailed_forecast=period["detailedForecast"],
                wind_speed=period["windSpeed"],
                wind_direction=period["windDirection"],
                humidity=period.get("relativeHumidity", {}).get("value"),
                icon_url=period["icon"],
                is_daytime=period["isDaytime"],
                updated_at=datetime.now(),
            )

    async def get_hourly_forecast(self, hours: int = 5) -> list[HourlyForecast]:
        """Fetch hourly forecast."""
        headers = {"User-Agent": self.USER_AGENT, "Accept": "application/geo+json"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            await self._get_forecast_urls(client)

            response = await client.get(self._hourly_url)
            response.raise_for_status()
            data = response.json()

            result = []
            for period in data["properties"]["periods"][:hours]:
                # Parse the start time
                start_time = datetime.fromisoformat(period["startTime"].replace("Z", "+00:00"))
                
                # Get precipitation chance
                precip = period.get("probabilityOfPrecipitation", {})
                precip_chance = precip.get("value") if precip else None

                result.append(
                    HourlyForecast(
                        time=start_time,
                        temperature=period["temperature"],
                        temperature_unit=period["temperatureUnit"],
                        short_forecast=period["shortForecast"],
                        wind_speed=period["windSpeed"],
                        wind_direction=period["windDirection"],
                        chance_of_precipitation=precip_chance,
                    )
                )
            return result

    async def get_5day_forecast(self) -> list[ForecastPeriod]:
        """Fetch 5-day forecast (day/night periods)."""
        headers = {"User-Agent": self.USER_AGENT, "Accept": "application/geo+json"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            await self._get_forecast_urls(client)

            response = await client.get(self._forecast_url)
            response.raise_for_status()
            data = response.json()

            result = []
            # NWS returns 14 periods (7 days, day and night)
            for period in data["properties"]["periods"][:14]:
                precip = period.get("probabilityOfPrecipitation", {})
                precip_chance = precip.get("value") if precip else None

                result.append(
                    ForecastPeriod(
                        name=period["name"],
                        temperature=period["temperature"],
                        temperature_unit=period["temperatureUnit"],
                        short_forecast=period["shortForecast"],
                        is_daytime=period["isDaytime"],
                        wind_speed=period["windSpeed"],
                        chance_of_precipitation=precip_chance,
                    )
                )
            return result

    async def get_forecast(self, periods: int = 5) -> list[WeatherData]:
        """Fetch weather forecast for multiple periods."""
        headers = {"User-Agent": self.USER_AGENT, "Accept": "application/geo+json"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            await self._get_forecast_urls(client)

            response = await client.get(self._forecast_url)
            response.raise_for_status()
            data = response.json()

            result = []
            for period in data["properties"]["periods"][:periods]:
                result.append(
                    WeatherData(
                        temperature=period["temperature"],
                        temperature_unit=period["temperatureUnit"],
                        short_forecast=period["shortForecast"],
                        detailed_forecast=period["detailedForecast"],
                        wind_speed=period["windSpeed"],
                        wind_direction=period["windDirection"],
                        humidity=period.get("relativeHumidity", {}).get("value"),
                        icon_url=period["icon"],
                        is_daytime=period["isDaytime"],
                        updated_at=datetime.now(),
                    )
                )
            return result


def get_weather_icon(short_forecast: str, is_daytime: bool) -> str:
    """Return ASCII art icon based on weather condition."""
    forecast_lower = short_forecast.lower()

    if "thunder" in forecast_lower or "storm" in forecast_lower:
        return r"""
  ⛈️
 ╱  ╲
╱    ╲
 ⚡ ⚡
"""

    if "rain" in forecast_lower or "shower" in forecast_lower:
        return r"""
   ☁️
  ╱  ╲
 ╱    ╲
 ' ' '
"""

    if "snow" in forecast_lower:
        return r"""
   ☁️
  ╱  ╲
 ╱    ╲
 * * *
"""

    if "cloud" in forecast_lower or "overcast" in forecast_lower:
        return r"""
   ☁️
  ╱  ╲
 ╱    ╲
"""

    if "partly" in forecast_lower:
        if is_daytime:
            return r"""
 ☀️ ☁️
   ╲╱
"""
        else:
            return r"""
 🌙 ☁️
   ╲╱
"""

    if "fog" in forecast_lower or "mist" in forecast_lower:
        return r"""
 ≋≋≋≋≋
 ≋≋≋≋≋
 ≋≋≋≋≋
"""

    # Clear/sunny
    if is_daytime:
        return r"""
    ☀️
  ╲ │ ╱
 ── ○ ──
  ╱ │ ╲
"""
    else:
        return r"""
   🌙
  ⋆ ✦ ⋆
    ✦
"""
