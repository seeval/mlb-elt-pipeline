import logging
from dataclasses import dataclass, field
from datetime import date

from extraction.mlb_client import MLBApiClient

logger = logging.getLogger(__name__)

@dataclass
class GameRecord:
    """
    Represents a single game extracted from the schedule endpoint.
    This is the unit passed to the boxscore extractor.
    """
    game_pk: int
    game_date: date
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    series_game_number: int
    games_in_series: int
    series_start_date:date


@dataclass
class ScheduleExtractor:
    """
    Extracts game records from the MLB schedule endpoint. 
    Responsible for: parsing schedule response, inferring series start date, 
    and returning a flat list of GameRecord objects.
    """
    client: MLBApiClient
    _records: list[GameRecord] = field(default_factory=list, init=False)

    def extract(self, start_date: str, end_date:str) -> list[GameRecord]:
        """
        Pull schedule for date range and return parsed GameRecord list. 
        start_date and end_date must be YYYY-MM-DD strings.
        """
        logger.info("Extracting schedule from %s to %s", start_date, end_date)
        raw = self.client.get_schedule(start_date, end_date)
        self._records = self._parse(raw)
        logger.info("Extracted %d game records", len(self._records))
        return self._records

    def _parse(self, raw:dict) -> list[GameRecord]:
        records: list[GameRecord] = []

        for date_entry in raw.get("dates", []):
            game_date = date.fromisoformat(date_entry["date"])

            for game in date_entry.get("games", []):
                series_game_number = game.get("seriesGameNumber", 1)
                games_in_series = game.get("gamesInSeries", 1)
                
                # infer series start date from current date and series position
                # e.g. if today is game 3 of 3, series started 2 days ago
                # this is approx - series can span off days
                # dbt logic reconciles more precisely
                series_start_date = date.fromordinal(
                        game_date.toordinal() - (series_game_number - 1)
                        )

                records.append(
                        GameRecord(
                            game_pk=game["gamePk"],
                            game_date=game_date,
                            home_team_id=game["teams"]["home"]["team"]["id"],
                            home_team_name=game["teams"]["home"]["team"]["name"],
                            away_team_id=game["teams"]["away"]["team"]["id"],
                            away_team_name=game["teams"]["away"]["team"]["name"],
                            series_game_number=series_game_number,
                            games_in_series=games_in_series,
                            series_start_date=series_start_date,
                            )
                        )
                
        return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    client = MLBApiClient()
    extractor = ScheduleExtractor(client=client)
    records = extractor.extract("2026-04-30", "2026-05-01")
    for r in records:
        print(r)
