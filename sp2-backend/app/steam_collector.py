from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from app.alerts import send_alert
    from app.pipeline_config import PIPELINE_LOG_PATH, PROJECT_ROOT
    from app.utils import retry, save_json, setup_logger
except ImportError:
    from app.alerts import send_alert
    from app.pipeline_config import PIPELINE_LOG_PATH, PROJECT_ROOT
    from app.utils import retry, save_json, setup_logger


# All logging goes through backend.utils.setup_logger(), so this script shares
# the same logs/pipeline.log file as the rest of the project.
LOGGER = setup_logger(str(PIPELINE_LOG_PATH))
OUTPUT_FILE = PROJECT_ROOT / "steam_data.json"
PLAYER_COUNT_URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

# Example "top games" to collect. Add or replace app IDs as your dashboard grows.
TOP_GAMES = [
    {"appid": "730", "name": "Counter-Strike 2"},
    {"appid": "570", "name": "Dota 2"},
    {"appid": "646570", "name": "Slay the Spire"},
]

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
STEAM_API_KEY_PLACEHOLDER = "YOUR_STEAM_API_KEY"


def _get_steam_api_key() -> str | None:
    """Load STEAM_API_KEY from .env without hardcoding it in Python."""
    load_dotenv()
    api_key = os.getenv("STEAM_API_KEY")
    if not api_key or api_key == STEAM_API_KEY_PLACEHOLDER:
        return None
    return api_key


def _skip_if_missing_steam_key() -> bool:
    """Return True and create empty output when Steam API key is missing."""
    if _get_steam_api_key():
        return False

    message = (
        "WARNING: STEAM_API_KEY is missing or incomplete in .env. "
        "Steam player-count collection will be skipped."
    )
    print(message)
    LOGGER.warning(message)
    save_json([], OUTPUT_FILE)
    return True


def fetch_player_count(appid: str) -> int:
    """Fetch the current number of players for one Steam app ID."""
    def request_player_count() -> int:
        api_key = _get_steam_api_key()
        if not api_key:
            raise ValueError("STEAM_API_KEY is missing")

        response = requests.get(
            PLAYER_COUNT_URL,
            params={"appid": appid, "key": api_key},
            timeout=15,
        )
        response.raise_for_status()

        payload = response.json()
        response_data = payload.get("response")
        if not isinstance(response_data, dict):
            raise ValueError("Steam player-count response is missing response object")
        return int(response_data.get("player_count", 0))

    LOGGER.info("Fetching player count for appid %s", appid)
    # Use the shared retry helper for Steam API requests instead of a local loop.
    try:
        return retry(request_player_count, retries=MAX_RETRIES, delay=int(RETRY_DELAY_SECONDS))
    except Exception as error:
        send_alert(
            "Module: steam_collector\n"
            f"Error: Steam API failed after all retries for appid {appid}\n"
            f"Details: {error}"
        )
        raise


def collect_steam_data(games: list[dict[str, str]] | None = None) -> list[dict[str, Any]]:
    """Collect Steam player-count data for the configured top games."""
    selected_games = games or TOP_GAMES
    steam_data: list[dict[str, Any]] = []

    for game in selected_games:
        appid = game["appid"]
        name = game["name"]

        LOGGER.info("Collecting Steam data for %s (%s)", name, appid)
        player_count = fetch_player_count(appid)

        # JSON structure written for each game:
        # {
        #   "appid": "Steam application ID",
        #   "name": "Human-readable game name",
        #   "player_count": current number of players
        # }
        steam_data.append(
            {
                "appid": appid,
                "name": name,
                "player_count": player_count,
            }
        )

    return steam_data


def run() -> list[dict[str, Any]]:
    """Entry point for pipeline_runner.py and direct script execution."""
    if _skip_if_missing_steam_key():
        return []

    try:
        LOGGER.info("Steam collector started")
        steam_data = collect_steam_data(TOP_GAMES)
        # Use the shared JSON writer so all modules handle output consistently.
        save_json(steam_data, OUTPUT_FILE)
        LOGGER.info("Steam collector completed successfully with %s games", len(steam_data))
        return steam_data
    except Exception as error:
        send_alert(
            "Module: steam_collector\n"
            "Error: Steam collector failed\n"
            f"Details: {error}"
        )
        raise


if __name__ == "__main__":
    run()
