"""Configuration management for TUIDash."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Application configuration loaded from environment variables."""

    # Location settings (Seattle downtown)
    LATITUDE: float = float(os.getenv("LATITUDE", "47.6062"))
    LONGITUDE: float = float(os.getenv("LONGITUDE", "-122.3321"))

    # NOAA Tides station ID (Seattle)
    TIDES_STATION_ID: str = os.getenv("TIDES_STATION_ID", "9447130")

    # WSDOT Ferries API
    WSDOT_API_KEY: str = os.getenv("WSDOT_API_KEY", "")

    # Refresh interval in seconds (5 minutes)
    REFRESH_INTERVAL: int = int(os.getenv("REFRESH_INTERVAL", "300"))

    # Ferry route (Edmonds-Kingston)
    FERRY_ROUTE: str = os.getenv("FERRY_ROUTE", "ed-king")

    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return list of missing required values."""
        missing = []
        if not cls.WSDOT_API_KEY:
            missing.append("WSDOT_API_KEY")
        return missing
