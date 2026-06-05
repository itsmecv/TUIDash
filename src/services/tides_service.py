"""Tides service using NOAA Tides and Currents API."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx


@dataclass
class TideEvent:
    """A single tide event (high or low)."""

    time: datetime
    height: float  # in feet
    type: str  # "H" for high, "L" for low

    @property
    def type_display(self) -> str:
        """Human-readable tide type."""
        return "High" if self.type == "H" else "Low"

    @property
    def time_display(self) -> str:
        """Format time for display."""
        return self.time.strftime("%I:%M %p").lstrip("0")

    def time_until(self) -> timedelta:
        """Time remaining until this tide event."""
        return self.time - datetime.now()

    def time_until_display(self) -> str:
        """Human-readable time until event."""
        delta = self.time_until()
        if delta.total_seconds() < 0:
            return "now"

        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


@dataclass
class TidesData:
    """Container for tide predictions."""

    station_name: str
    predictions: list[TideEvent]
    updated_at: datetime

    def next_tide(self) -> TideEvent | None:
        """Get the next upcoming tide event."""
        now = datetime.now()
        for event in self.predictions:
            if event.time > now:
                return event
        return None

    def next_high(self) -> TideEvent | None:
        """Get the next high tide."""
        now = datetime.now()
        for event in self.predictions:
            if event.time > now and event.type == "H":
                return event
        return None

    def next_low(self) -> TideEvent | None:
        """Get the next low tide."""
        now = datetime.now()
        for event in self.predictions:
            if event.time > now and event.type == "L":
                return event
        return None


class TidesService:
    """Client for NOAA Tides and Currents API."""

    BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

    def __init__(self, station_id: str):
        self.station_id = station_id

    async def get_predictions(self, days: int = 2) -> TidesData:
        """Fetch tide predictions for the specified number of days."""
        today = datetime.now()
        begin_date = today.strftime("%Y%m%d")
        end_date = (today + timedelta(days=days)).strftime("%Y%m%d")

        params = {
            "begin_date": begin_date,
            "end_date": end_date,
            "station": self.station_id,
            "product": "predictions",
            "datum": "MLLW",  # Mean Lower Low Water
            "interval": "hilo",  # High/Low only
            "units": "english",  # feet
            "time_zone": "lst_ldt",  # Local time with DST
            "format": "json",
            "application": "TUIDash",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            predictions = []
            for pred in data.get("predictions", []):
                # Parse datetime: "2024-01-15 06:30"
                dt = datetime.strptime(pred["t"], "%Y-%m-%d %H:%M")
                predictions.append(
                    TideEvent(
                        time=dt,
                        height=float(pred["v"]),
                        type=pred["type"],
                    )
                )

            # Get station name from metadata endpoint
            station_name = await self._get_station_name(client)

            return TidesData(
                station_name=station_name,
                predictions=predictions,
                updated_at=datetime.now(),
            )

    async def _get_station_name(self, client: httpx.AsyncClient) -> str:
        """Fetch station metadata to get the station name."""
        url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{self.station_id}.json"
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            stations = data.get("stations", [])
            if stations:
                return stations[0].get("name", f"Station {self.station_id}")
        except Exception:
            pass
        return f"Station {self.station_id}"


def get_tide_icon(tide_type: str) -> str:
    """Return ASCII representation of tide type."""
    if tide_type == "H":
        return "▲ High"
    return "▼ Low"


def generate_tide_chart(predictions: list[TideEvent], width: int = 48, height: int = 8) -> str:
    """Generate ASCII wave chart for tides.
    
    Creates a visual representation showing the wave pattern over 48 hours
    with high/low markers, current position, and depth Y-axis.
    """
    if not predictions:
        return "No tide data available"
    
    from datetime import datetime, timedelta
    import math
    
    now = datetime.now()
    start_time = now - timedelta(hours=1)  # Start 1 hour ago for context
    end_time = start_time + timedelta(hours=48)  # Exactly 48 hours total
    
    # Filter predictions in our time range
    relevant = [p for p in predictions if start_time <= p.time <= end_time]
    if len(relevant) < 2:
        return "Insufficient tide data"
    
    # Find min/max heights for scaling
    min_height = min(p.height for p in relevant)
    max_height = max(p.height for p in relevant)
    height_range = max_height - min_height
    if height_range == 0:
        height_range = 1
    
    # Generate interpolated heights for each column
    hours_per_col = 48 / width
    heights = []
    markers = []  # (col, type, height, time) for H/L markers
    
    for col in range(width):
        col_time = start_time + timedelta(hours=col * hours_per_col)
        
        # Find surrounding tide events for interpolation
        prev_event = None
        next_event = None
        
        for pred in relevant:
            if pred.time <= col_time:
                prev_event = pred
            if pred.time > col_time and next_event is None:
                next_event = pred
                break
        
        # Interpolate height using cosine for smooth wave
        if prev_event and next_event:
            total_time = (next_event.time - prev_event.time).total_seconds()
            elapsed = (col_time - prev_event.time).total_seconds()
            t = elapsed / total_time if total_time > 0 else 0
            t_cos = (1 - math.cos(t * math.pi)) / 2
            h = prev_event.height + (next_event.height - prev_event.height) * t_cos
        elif prev_event:
            h = prev_event.height
        elif next_event:
            h = next_event.height
        else:
            h = (min_height + max_height) / 2
        
        heights.append(h)
        
        # Check if this column is near a tide event
        for pred in relevant:
            time_diff = abs((col_time - pred.time).total_seconds())
            if time_diff < hours_per_col * 3600 / 2:
                markers.append((col, pred.type, pred.height, pred.time))
    
    # Find NOW column
    now_col = max(0, min(width - 1, int((now - start_time).total_seconds() / 3600 / hours_per_col)))
    
    # Calculate which row each column's wave should be on
    wave_rows = []
    for h in heights:
        row = int((max_height - h) / height_range * (height - 1))
        row = max(0, min(height - 1, row))
        wave_rows.append(row)
    
    # Build the chart with Y-axis
    lines = []
    y_label_width = 5  # "9.9ft"
    
    for row in range(height):
        # Y-axis label (depth in feet) - show at top, middle, bottom
        if row == 0:
            label = f"{max_height:.1f}'"
        elif row == height - 1:
            label = f"{min_height:.1f}'"
        elif row == height // 2:
            mid_height = (max_height + min_height) / 2
            label = f"{mid_height:.1f}'"
        else:
            label = ""
        
        line = f"{label:>{y_label_width}}│"
        
        for col in range(width):
            # Check for H/L marker at this position
            marker_char = None
            for (mc, mt, mh, mtime) in markers:
                if mc == col:
                    marker_row = int((max_height - mh) / height_range * (height - 1))
                    marker_row = max(0, min(height - 1, marker_row))
                    if row == marker_row:
                        marker_char = "H" if mt == "H" else "L"
                        break
            
            # Check for NOW marker
            if col == now_col and row == wave_rows[col] and not marker_char:
                marker_char = "●"
            
            if marker_char:
                line += marker_char
            elif row == wave_rows[col]:
                # Draw wave line
                line += "~"
            else:
                line += " "
        
        lines.append(line)
    
    # Bottom axis
    lines.append(" " * y_label_width + "└" + "─" * width)
    
    # Time labels
    start_label = start_time.strftime("%I%p").lstrip("0").lower()
    end_label = end_time.strftime("%I%p").lstrip("0").lower()
    mid_time = start_time + timedelta(hours=24)
    mid_label = mid_time.strftime("%I%p").lstrip("0").lower()
    
    padding = " " * (y_label_width + 1)
    mid_pos = width // 2 - len(mid_label) // 2
    time_line = padding + start_label
    time_line += " " * (mid_pos - len(start_label))
    time_line += mid_label
    time_line += " " * (width - mid_pos - len(mid_label) - len(end_label))
    time_line += end_label
    lines.append(time_line)
    
    return "\n".join(lines)
