"""Ferry service using WSDOT Traveler API."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx


@dataclass
class VesselLocation:
    """Real-time vessel location and status."""
    
    vessel_id: int
    vessel_name: str
    departing_terminal: str
    arriving_terminal: str
    latitude: float
    longitude: float
    speed: float  # knots
    heading: int  # degrees
    in_service: bool
    at_dock: bool
    eta: datetime | None
    scheduled_departure: datetime | None
    
    @property
    def eta_display(self) -> str:
        """Format ETA for display."""
        if not self.eta:
            return ""
        return self.eta.strftime("%I:%M %p").lstrip("0")
    
    @property
    def progress_percent(self) -> float:
        """Estimate crossing progress (0-100)."""
        if self.at_dock:
            return 0.0
        if not self.scheduled_departure or not self.eta:
            return 50.0  # Unknown, assume midway
        
        now = datetime.now()
        total = (self.eta - self.scheduled_departure).total_seconds()
        elapsed = (now - self.scheduled_departure).total_seconds()
        
        if total <= 0:
            return 100.0
        return min(100.0, max(0.0, (elapsed / total) * 100))
    
    def progress_bar(self, width: int = 20) -> str:
        """ASCII progress bar for crossing with boat icon."""
        if self.at_dock:
            # Show boat at dock (position 0)
            return "⛴" + "─" * (width - 1)
        pct = self.progress_percent / 100
        boat_pos = int((width - 1) * pct)
        bar = ""
        for i in range(width):
            if i == boat_pos:
                bar += "⛴"
            elif i < boat_pos:
                bar += "═"
            else:
                bar += "─"
        return bar


@dataclass
class FerryDeparture:
    """A single ferry departure."""

    departure_time: datetime
    arrival_time: datetime | None
    vessel_name: str
    route_name: str
    departing_terminal: str
    arriving_terminal: str
    is_cancelled: bool = False
    is_delayed: bool = False
    delay_minutes: int = 0
    notes: str = ""
    vessel_position: VesselLocation | None = None

    @property
    def time_display(self) -> str:
        """Format departure time for display."""
        return self.departure_time.strftime("%I:%M %p").lstrip("0")

    def time_until(self) -> timedelta:
        """Time remaining until departure."""
        return self.departure_time - datetime.now()

    def time_until_display(self) -> str:
        """Human-readable time until departure."""
        delta = self.time_until()
        if delta.total_seconds() < 0:
            return "departed"

        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


@dataclass
class FerrySchedule:
    """Container for ferry schedule data."""

    route_name: str
    departures: list[FerryDeparture]
    alerts: list[str]
    updated_at: datetime

    def next_departures(self, count: int = 3) -> list[FerryDeparture]:
        """Get the next N upcoming departures."""
        now = datetime.now()
        upcoming = [d for d in self.departures if d.departure_time > now and not d.is_cancelled]
        return upcoming[:count]


class FerryService:
    """Client for WSDOT Ferries API."""

    BASE_URL = "https://www.wsdot.wa.gov/ferries/api/schedule/rest"
    VESSELS_URL = "https://www.wsdot.wa.gov/ferries/api/vessels/rest/vessellocations"
    
    # Terminal IDs for vessel tracking
    TERMINAL_IDS = {
        "Edmonds": 8,
        "Kingston": 12,
        "Seattle": 7,
        "Bainbridge Island": 3,
        "Bremerton": 4,
        "Mukilteo": 14,
        "Clinton": 5,
    }

    # Route codes
    ROUTES = {
        "ed-king": {
            "name": "Edmonds / Kingston",
            "terminals": ["Edmonds", "Kingston"],
            "vessel_route": "Edmonds / Kingston",
        },
        "sea-bain": {
            "name": "Seattle / Bainbridge Island",
            "terminals": ["Seattle", "Bainbridge Island"],
            "vessel_route": "Seattle / Bainbridge Island",
        },
        "sea-brem": {
            "name": "Seattle / Bremerton",
            "terminals": ["Seattle", "Bremerton"],
            "vessel_route": "Seattle / Bremerton",
        },
        "muk-clin": {
            "name": "Mukilteo / Clinton",
            "terminals": ["Mukilteo", "Clinton"],
            "vessel_route": "Mukilteo / Clinton",
        },
    }

    def __init__(self, api_key: str, route: str = "ed-king"):
        self.api_key = api_key
        self.route = route
        self._cache_date: str | None = None
        self._vessel_locations: dict[str, VesselLocation] = {}

    async def get_vessel_locations(self) -> list[VesselLocation]:
        """Fetch real-time vessel locations."""
        headers = {"Accept": "application/json"}
        params = {"apiaccesscode": self.api_key}
        
        route_info = self.ROUTES.get(self.route, self.ROUTES["ed-king"])
        route_terminals = set(route_info["terminals"])
        
        vessels = []
        
        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            try:
                response = await client.get(self.VESSELS_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                for v in data:
                    # Filter to vessels on our route
                    dep_terminal = v.get("DepartingTerminalName", "")
                    arr_terminal = v.get("ArrivingTerminalName", "")
                    
                    if dep_terminal not in route_terminals and arr_terminal not in route_terminals:
                        continue
                    
                    # Parse ETA
                    eta = None
                    eta_str = v.get("Eta", "")
                    if eta_str and "/Date(" in eta_str:
                        try:
                            timestamp_ms = int(eta_str.split("(")[1].split("-")[0].split("+")[0])
                            eta = datetime.fromtimestamp(timestamp_ms / 1000)
                        except (ValueError, IndexError):
                            pass
                    
                    # Parse scheduled departure
                    sched_dep = None
                    sched_str = v.get("ScheduledDeparture", "")
                    if sched_str and "/Date(" in sched_str:
                        try:
                            timestamp_ms = int(sched_str.split("(")[1].split("-")[0].split("+")[0])
                            sched_dep = datetime.fromtimestamp(timestamp_ms / 1000)
                        except (ValueError, IndexError):
                            pass
                    
                    vessel = VesselLocation(
                        vessel_id=v.get("VesselID", 0),
                        vessel_name=v.get("VesselName", "Unknown"),
                        departing_terminal=dep_terminal,
                        arriving_terminal=arr_terminal,
                        latitude=v.get("Latitude", 0.0),
                        longitude=v.get("Longitude", 0.0),
                        speed=v.get("Speed", 0.0),
                        heading=v.get("Heading", 0),
                        in_service=v.get("InService", False),
                        at_dock=v.get("AtDock", True),
                        eta=eta,
                        scheduled_departure=sched_dep,
                    )
                    vessels.append(vessel)
                    self._vessel_locations[vessel.vessel_name] = vessel
                    
            except httpx.HTTPError:
                pass
        
        return vessels

    async def get_schedule(self, both_directions: bool = True) -> FerrySchedule:
        """Fetch ferry schedule for the route."""
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")

        route_info = self.ROUTES.get(self.route, self.ROUTES["ed-king"])
        terminals = route_info["terminals"]

        headers = {"Accept": "application/json"}
        params = {"apiaccesscode": self.api_key}

        all_departures = []
        all_alerts = []

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            # Get schedule for each direction
            directions = terminals if both_directions else [terminals[0]]

            for departing_terminal in directions:
                arriving_terminal = terminals[1] if departing_terminal == terminals[0] else terminals[0]
                
                # Use terminal IDs for the API
                dep_id = self.TERMINAL_IDS.get(departing_terminal, 8)
                arr_id = self.TERMINAL_IDS.get(arriving_terminal, 12)

                url = f"{self.BASE_URL}/scheduletoday/{dep_id}/{arr_id}/true"

                try:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    # Parse schedule times from TerminalCombos structure
                    terminal_combos = data.get("TerminalCombos", [])
                    schedule_data = terminal_combos[0].get("Times", []) if terminal_combos else []
                    for item in schedule_data:
                        try:
                            # Parse departure time
                            dep_str = item.get("DepartingTime", "")
                            if not dep_str:
                                continue

                            # Handle the datetime format from WSDOT
                            # Format: "/Date(1234567890000-0800)/" or ISO format
                            if "/Date(" in dep_str:
                                # Extract milliseconds timestamp
                                timestamp_ms = int(dep_str.split("(")[1].split("-")[0].split("+")[0])
                                dep_time = datetime.fromtimestamp(timestamp_ms / 1000)
                            else:
                                dep_time = datetime.fromisoformat(dep_str.replace("Z", "+00:00"))

                            # Parse arrival time if available
                            arr_time = None
                            arr_str = item.get("ArrivingTime", "")
                            if arr_str:
                                if "/Date(" in arr_str:
                                    timestamp_ms = int(arr_str.split("(")[1].split("-")[0].split("+")[0])
                                    arr_time = datetime.fromtimestamp(timestamp_ms / 1000)
                                else:
                                    arr_time = datetime.fromisoformat(arr_str.replace("Z", "+00:00"))

                            all_departures.append(
                                FerryDeparture(
                                    departure_time=dep_time,
                                    arrival_time=arr_time,
                                    vessel_name=item.get("VesselName", "Unknown"),
                                    route_name=route_info["name"],
                                    departing_terminal=departing_terminal,
                                    arriving_terminal=arriving_terminal,
                                    is_cancelled=item.get("IsCancelled", False),
                                    notes=item.get("AnnotationIndexes", ""),
                                )
                            )
                        except (ValueError, KeyError, IndexError):
                            continue

                except httpx.HTTPError:
                    # Continue with other directions if one fails
                    continue

            # Get alerts
            try:
                alerts_url = f"{self.BASE_URL}/alerts"
                alerts_response = await client.get(alerts_url, params=params)
                if alerts_response.status_code == 200:
                    alerts_data = alerts_response.json()
                    for alert in alerts_data:
                        # Filter to relevant route
                        if route_info["name"].lower() in alert.get("BulletinTitle", "").lower():
                            all_alerts.append(alert.get("BulletinText", ""))
            except httpx.HTTPError:
                pass

        # Sort departures by time
        all_departures.sort(key=lambda d: d.departure_time)

        # Fetch vessel locations
        await self.get_vessel_locations()
        
        # Associate vessel positions with departures
        for dep in all_departures:
            if dep.vessel_name in self._vessel_locations:
                dep.vessel_position = self._vessel_locations[dep.vessel_name]

        return FerrySchedule(
            route_name=route_info["name"],
            departures=all_departures,
            alerts=all_alerts[:3],  # Limit alerts
            updated_at=datetime.now(),
        )


def get_ferry_icon(vessel_name: str = "FERRY") -> str:
    """Return ASCII art ferry icon with vessel name."""
    # Truncate/pad name to fit
    name = vessel_name[:10].center(10)
    return f"""     |\\         
_____|__\\________
| ⚓ {name}   |
~~~~~~~~~~~~~~~~~~"""
