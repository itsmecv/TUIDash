# TUIDash

An ambient daily dashboard TUI application showing weather, tides, ferry times, and your Outlook calendar.

![TUI Dashboard](https://via.placeholder.com/800x400?text=TUIDash+Screenshot)

## Features

- 🌤️ **Weather** - Current conditions from National Weather Service (Seattle)
- 🌊 **Tides** - High/low tide predictions from NOAA
- ⛴️ **Ferry** - Edmonds-Kingston ferry schedule from WSDOT
- 📅 **Calendar** - Outlook calendar events via Microsoft Graph API
- 🔄 **Auto-refresh** - Updates every 5 minutes
- ⌨️ **Keyboard shortcuts** - Quick navigation and controls

## Installation

### Prerequisites

- Python 3.11+
- pip or uv package manager

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd TUIDash
   ```

2. **Create virtual environment and install dependencies:**
   ```bash
   # Using pip
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/macOS
   pip install -e .

   # Or using uv (faster)
   uv venv
   uv pip install -e .
   ```

3. **Configure environment:**
   ```bash
   copy .env.example .env
   # Edit .env with your API keys (see Configuration below)
   ```

4. **Run the app:**
   ```bash
   python -m src.app
   # Or after install:
   tuidash
   ```

## Configuration

Copy `.env.example` to `.env` and configure:

### Required API Keys

#### WSDOT Ferries API (free)
1. Go to https://wsdot.wa.gov/traffic/api/
2. Register for an API access code
3. Add to `.env`: `WSDOT_API_KEY=your_key_here`

#### Azure AD App (for Outlook calendar)
1. Go to [Azure Portal](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
3. Name: `TUIDash` (or anything you like)
4. Supported account types: **Accounts in this organizational directory only**
5. Redirect URI: Leave blank (not needed for device code flow)
6. Click **Register**
7. Copy the **Application (client) ID** → `AZURE_CLIENT_ID`
8. Copy the **Directory (tenant) ID** → `AZURE_TENANT_ID`
9. Go to **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions**
10. Add: `Calendars.Read`, `User.Read`
11. Go to **Authentication** → Enable **Allow public client flows** → Save

### Optional Settings

```env
# Location (defaults to Seattle downtown)
LATITUDE=47.6062
LONGITUDE=-122.3321

# NOAA Tides station (defaults to Seattle)
TIDES_STATION_ID=9447130

# Ferry route (defaults to Edmonds-Kingston)
FERRY_ROUTE=ed-king

# Refresh interval in seconds (defaults to 300 = 5 minutes)
REFRESH_INTERVAL=300
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Manual refresh |
| `d` | Toggle dark/light mode |
| `?` | Show help |

## Project Structure

```
TUIDash/
├── src/
│   ├── app.py              # Main Textual app
│   ├── config.py           # Configuration management
│   ├── widgets/
│   │   ├── weather.py      # Weather widget
│   │   ├── tides.py        # Tides widget
│   │   ├── ferry.py        # Ferry schedule widget
│   │   └── calendar.py     # Outlook calendar widget
│   └── services/
│       ├── weather_service.py   # NWS API client
│       ├── tides_service.py     # NOAA API client
│       ├── ferry_service.py     # WSDOT API client
│       └── outlook_service.py   # Microsoft Graph client
├── .env.example
├── .gitignore
├── pyproject.toml
└── readme.md
```

## Data Sources

| Widget | API | Documentation |
|--------|-----|---------------|
| Weather | National Weather Service | https://www.weather.gov/documentation/services-web-api |
| Tides | NOAA Tides & Currents | https://api.tidesandcurrents.noaa.gov/api/prod/ |
| Ferry | WSDOT Traveler API | https://wsdot.wa.gov/traffic/api/ |
| Calendar | Microsoft Graph | https://learn.microsoft.com/en-us/graph/api/overview |

## First Run - Outlook Authentication

On first run, if Outlook is configured, you'll see a device code prompt:

```
============================================================
OUTLOOK AUTHENTICATION REQUIRED
============================================================

To sign in, open a browser and go to:
  https://microsoft.com/devicelogin

Enter this code: XXXXXXXX

Waiting for authentication...
============================================================
```

1. Open the URL in a browser
2. Enter the code shown
3. Sign in with your work/school account
4. Grant the requested permissions
5. Return to the terminal - authentication will complete automatically

Your token is cached locally, so you won't need to re-authenticate unless it expires.

## Troubleshooting

### Weather not loading
- The NWS API occasionally has issues. Wait and try manual refresh (`r`)

### Ferry widget shows "API key not set"
- Make sure `WSDOT_API_KEY` is set in your `.env` file

### Calendar shows "Authentication needed"
- Follow the device code flow in the terminal
- Make sure your Azure AD app has the correct permissions

### Tides showing wrong location
- Find your NOAA station ID at https://tidesandcurrents.noaa.gov/
- Update `TIDES_STATION_ID` in `.env`

## License

MIT
