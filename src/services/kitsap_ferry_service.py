"""Kitsap Fast Ferry service - Kingston/Seattle route.

Uses static schedule since Kitsap Transit doesn't have a public real-time API.
Schedule effective May 2, 2026 from kitsaptransit.com
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, time


# Kingston-Seattle Fast Ferry Schedule (weekday)
# Source: https://www.kitsaptransit.com/service/fast-ferry/kingston-fast-ferry
WEEKDAY_SCHEDULE = {
    "to_seattle": [
        time(5, 25), time(7, 5), time(8, 45),  # Morning
        time(14, 30), time(16, 10), time(17, 55),  # Afternoon
    ],
    "to_kingston": [
        time(6, 15), time(7, 55), time(10, 45),  # Morning
        time(15, 20), time(17, 0), time(18, 45),  # Afternoon
    ],
}

# Saturday service (May through September)
WEEKEND_SCHEDULE = {
    "to_seattle": [
        time(9, 20), time(11, 0), time(12, 45), time(14, 25),
        time(17, 20), time(19, 5), time(20, 45), time(22, 25),
    ],
    "to_kingston": [
        time(10, 10), time(11, 50), time(13, 35), time(16, 25),
        time(18, 15), time(19, 55), time(21, 35), time(23, 10),
    ],
}

# Crossing time is approximately 40 minutes
CROSSING_MINUTES = 40


@dataclass
class FastFerryDeparture:
    """A Kitsap Fast Ferry departure."""
    
    departure_time: datetime
    arrival_time: datetime
    direction: str  # "to_seattle" or "to_kingston"
    
    @property
    def departing_terminal(self) -> str:
        return "Kingston" if self.direction == "to_seattle" else "Seattle"
    
    @property
    def arriving_terminal(self) -> str:
        return "Seattle" if self.direction == "to_seattle" else "Kingston"
    
    @property
    def time_display(self) -> str:
        return self.departure_time.strftime("%I:%M %p").lstrip("0")
    
    @property
    def arrival_display(self) -> str:
        return self.arrival_time.strftime("%I:%M %p").lstrip("0")
    
    def time_until(self) -> timedelta:
        return self.departure_time - datetime.now()
    
    def time_until_display(self) -> str:
        delta = self.time_until()
        if delta.total_seconds() < 0:
            return "departed"
        
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    
    @property
    def is_en_route(self) -> bool:
        """Check if ferry is currently en route."""
        now = datetime.now()
        return self.departure_time <= now <= self.arrival_time
    
    @property
    def progress_percent(self) -> float:
        """Estimate crossing progress based on time."""
        if not self.is_en_route:
            return 0.0 if datetime.now() < self.departure_time else 100.0
        
        now = datetime.now()
        total = (self.arrival_time - self.departure_time).total_seconds()
        elapsed = (now - self.departure_time).total_seconds()
        
        return min(100.0, max(0.0, (elapsed / total) * 100))
    
    @property
    def eta_display(self) -> str:
        """Time until arrival."""
        if not self.is_en_route:
            return ""
        
        remaining = self.arrival_time - datetime.now()
        minutes = int(remaining.total_seconds() / 60)
        return f"{minutes}m"
    
    def progress_bar(self, width: int = 20) -> str:
        """ASCII progress bar for crossing with boat icon."""
        if not self.is_en_route:
            return ""
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


class KitsapFerryService:
    """Service for Kitsap Fast Ferry schedule."""
    
    def __init__(self):
        pass
    
    def _get_schedule(self) -> dict[str, list[time]]:
        """Get the appropriate schedule for today.
        
        Saturday service operates May through September.
        No Sunday service.
        """
        today = datetime.now()
        weekday = today.weekday()
        month = today.month
        
        # Sunday - no service
        if weekday == 6:
            return {"to_seattle": [], "to_kingston": []}
        
        # Saturday - only May through September
        if weekday == 5:
            if 5 <= month <= 9:
                return WEEKEND_SCHEDULE
            else:
                return {"to_seattle": [], "to_kingston": []}
        
        return WEEKDAY_SCHEDULE
    
    def get_departures(self) -> list[FastFerryDeparture]:
        """Get today's departures."""
        today = datetime.now().date()
        schedule = self._get_schedule()
        
        departures = []
        
        for direction, times in schedule.items():
            for t in times:
                dep_dt = datetime.combine(today, t)
                arr_dt = dep_dt + timedelta(minutes=CROSSING_MINUTES)
                
                departures.append(FastFerryDeparture(
                    departure_time=dep_dt,
                    arrival_time=arr_dt,
                    direction=direction,
                ))
        
        departures.sort(key=lambda d: d.departure_time)
        return departures
    
    def next_departures(self, direction: str | None = None, count: int = 3) -> list[FastFerryDeparture]:
        """Get next upcoming departures."""
        now = datetime.now()
        departures = self.get_departures()
        
        upcoming = [
            d for d in departures 
            if d.departure_time > now 
            and (direction is None or d.direction == direction)
        ]
        
        return upcoming[:count]
    
    def next_to_seattle(self, count: int = 2) -> list[FastFerryDeparture]:
        """Get next departures to Seattle."""
        return self.next_departures("to_seattle", count)
    
    def next_to_kingston(self, count: int = 2) -> list[FastFerryDeparture]:
        """Get next departures to Kingston."""
        return self.next_departures("to_kingston", count)
    
    def current_sailing(self) -> FastFerryDeparture | None:
        """Get currently en-route ferry, if any."""
        departures = self.get_departures()
        for dep in departures:
            if dep.is_en_route:
                return dep
        return None
