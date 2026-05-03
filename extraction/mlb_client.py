import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

class MLBApiClient:
    """
    Facade over MLB Stats API.
    All HTTP concerns - bse url, retries, error handling.
    """

    BASE_URL = "https://statsapi.mlb.com/api/v1"
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 2

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, endpoint: str, params:dict[str, Any] | None = None) -> dict:
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(1, self.MAX_RETRIES+ 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                logger.error("HTTP error on attempt %d/%d: %s", attempt, self.MAX_RETRIES, e)
                if attempt == self.MAX_RETRIES:
                    raise
                time.sleep(self.RETRY_BACKOFF_SECONDS ** attempt)

            except requests.exceptions.ConnectionError as e:
                logger.error("Connection error on attempt %d/%d: %s", attempt, self.MAX_RETRIES, e)
                if attempt == self.MAX_RETRIES:
                    raise
                time.sleep(self.RETRY_BACKOFF_SECONDS ** attempt)

            except requests.exceptions.Timeout as e:
                logger.error("Timeout on attempt %d/%d: %s", attempt, self.MAX_RETRIES, e)
                if attempt == self.MAX_RETRIES:
                    raise
                time.sleep(self.RETRY_BACKOFF_SECONDS ** attempt)
        
        def get_schedule(self, start_date: str, end_date: str) -> dict:
            """
            Fetch game schedule for a date range.
            Dates must be in YYYY-MM-DD format.
            """
            return self._get(
                    "/schedule",
                    params={
                        "sportId": 1,
                        "startDate": start_date,
                        "endDate": end_date,
                        "gameType": "R", # regular season
                        "hydrate": "seriesStatus,team",
                        },
                    )

        def get_boxscore(self, game_pk: int) -> dict:
            """
            Fetch full boxscore for a single game.
            """
            return self._get(f"/game/{game_pk}/boxscore")
