import logging
from dataclasses import dataclass
from datetime import date

from google.cloud import bigquery

logger = logging.getLogger(__name__)

def _safe_float(value: str | int | float | None) -> float | None:
    """
    Converts API string values to float, returning None for placeholders.
    MLB API uses '-.--' '-.--' and similar strings for undefined ratios.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def _safe_int(value: str | int | None) -> int | None:
    """
    Converts batting order strings and similar fields to int.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

@dataclass
class BQLoader:
    """
    Parses raw MLB boxscore JSON and loads flattened rows into BigQuery.
    Responsibilities: field extraction, type coercion, schema enforcement, and BigQuery insert operations.
    """
    client: bigquery.Client
    project: str
    dataset: str

    def _table_ref(self, table_name: str) -> str:
        return f"{self.project}.{self.dataset}.{table_name}"

    def _truncate_partition(self, table_name: str, game_date: date) -> None:
        """
        Deletes all rows for a given game_date partition before inserting.
        """
        partition_id = game_date.strftime("%Y%m%d")
        query = f"""
            DELETE FROM `{self._table_ref(table_name)}`
            WHERE game_date = '{game_date.isoformat()}'
        """
        self.client.query(query).result()
        logger.info("Truncated partition %s in %s", partition_id, table_name)

    def _insert_rows(self, table_name: str, rows: list[dict]) -> None:
        if not rows:
            logger.warning("No rows to insert for %s", table_name)
            return

        errors = self.client.insert_rows_json(
            self._table_ref(table_name),
            rows,
        )

        if errors:
            for error in errors:
                logger.error("BQ insert error in %s: %s", table_name, error)
        else:
            logger.info("Inserted %d rows into %s", len(rows), table_name)


    def load_boxscore(self, game_pk: int, game_date: date, raw: dict) -> None:
        """
        Entry point for loading a single game's boxscore.
        Delegates to three private methods, one per target table.
        """
        teams = raw.get("teams", {})
        home = teams.get("home", {})
        away = teams.get("away", {})

        home_team_id = home.get("team", {}).get("id")
        away_team_id = away.get("team", {}).get("id")

        self._load_team_stats(game_pk, game_date, home, home_team_id, "home")
        self._load_team_stats(game_pk, game_date, away, away_team_id, "away")
        self._load_player_batting(game_pk, game_date, home, home_team_id, "home")
        self._load_player_batting(game_pk, game_date, away, away_team_id, "away")
        self._load_player_pitching(game_pk, game_date, home, home_team_id, "home")
        self._load_player_pitching(game_pk, game_date, away, away_team_id, "away")

    def _load_team_stats(
        self,
        game_pk: int,
        game_date: date,
        team_data: dict,
        team_id: int,
        team_side: str,
    ) -> None:
        ts = team_data.get("teamStats", {})
        b = ts.get("batting", {})
        p = ts.get("pitching", {})

        row = {
            "game_pk": game_pk,
            "game_date": game_date.isoformat(),
            "team_id": team_id,
            "team_side": team_side,
            # batting
            "b_fly_outs": _safe_int(b.get("flyOuts")),
            "b_ground_outs": _safe_int(b.get("groundOuts")),
            "b_runs": _safe_int(b.get("runs")),
            "b_doubles": _safe_int(b.get("doubles")),
            "b_triples": _safe_int(b.get("triples")),
            "b_home_runs": _safe_int(b.get("homeRuns")),
            "b_strikeouts": _safe_int(b.get("strikeOuts")),
            "b_walks": _safe_int(b.get("baseOnBalls")),
            "b_hits": _safe_int(b.get("hits")),
            "b_hit_by_pitch": _safe_int(b.get("hitByPitch")),
            "b_avg": _safe_float(b.get("avg")),
            "b_at_bats": _safe_int(b.get("atBats")),
            "b_obp": _safe_float(b.get("obp")),
            "b_slg": _safe_float(b.get("slg")),
            "b_ops": _safe_float(b.get("ops")),
            "b_plate_appearances": _safe_int(b.get("plateAppearances")),
            "b_rbi": _safe_int(b.get("rbi")),
            "b_left_on_base": _safe_int(b.get("leftOnBase")),
            "b_stolen_bases": _safe_int(b.get("stolenBases")),
            "b_caught_stealing": _safe_int(b.get("caughtStealing")),
            # pitching
            "p_fly_outs": _safe_int(p.get("flyOuts")),
            "p_ground_outs": _safe_int(p.get("groundOuts")),
            "p_runs": _safe_int(p.get("runs")),
            "p_earned_runs": _safe_int(p.get("earnedRuns")),
            "p_doubles": _safe_int(p.get("doubles")),
            "p_triples": _safe_int(p.get("triples")),
            "p_home_runs": _safe_int(p.get("homeRuns")),
            "p_strikeouts": _safe_int(p.get("strikeOuts")),
            "p_walks": _safe_int(p.get("baseOnBalls")),
            "p_hits": _safe_int(p.get("hits")),
            "p_hit_by_pitch": _safe_int(p.get("hitByPitch")),
            "p_number_of_pitches": _safe_int(p.get("numberOfPitches")),
            "p_era": _safe_float(p.get("era")),
            "p_innings_pitched": _safe_float(p.get("inningsPitched")),
            "p_whip": _safe_float(p.get("whip")),
            "p_batters_faced": _safe_int(p.get("battersFaced")),
            "p_outs": _safe_int(p.get("outs")),
            "p_strikes": _safe_int(p.get("strikes")),
            "p_balls": _safe_int(p.get("balls")),
        }

        self._insert_rows("raw_team_game_stats", [row])

    def _load_player_batting(
        self,
        game_pk: int,
        game_date: date,
        team_data: dict,
        team_id: int,
        team_side: str,
    ) -> None:
        players = team_data.get("players", {})
        rows = []

        for player_data in players.values():
            stats = player_data.get("stats", {})
            season = player_data.get("seasonStats", {})
            g = stats.get("batting", {})
            s = season.get("batting", {})

            # Skip players with no batting appearance in this game
            if not g or g.get("atBats") is None:
                continue

            batting_order_raw = _safe_int(player_data.get("battingOrder"))
            batting_order = batting_order_raw // 100 if batting_order_raw else None

            rows.append({
                "game_pk": game_pk,
                "game_date": game_date.isoformat(),
                "team_id": team_id,
                "team_side": team_side,
                "player_id": player_data.get("person", {}).get("id"),
                "player_name": player_data.get("person", {}).get("fullName"),
                "batting_order": batting_order,
                # game stats
                "g_at_bats": _safe_int(g.get("atBats")),
                "g_runs": _safe_int(g.get("runs")),
                "g_hits": _safe_int(g.get("hits")),
                "g_doubles": _safe_int(g.get("doubles")),
                "g_triples": _safe_int(g.get("triples")),
                "g_home_runs": _safe_int(g.get("homeRuns")),
                "g_rbi": _safe_int(g.get("rbi")),
                "g_walks": _safe_int(g.get("baseOnBalls")),
                "g_strikeouts": _safe_int(g.get("strikeOuts")),
                "g_left_on_base": _safe_int(g.get("leftOnBase")),
                "g_avg": _safe_float(g.get("avg")),
                "g_obp": _safe_float(g.get("obp")),
                "g_slg": _safe_float(g.get("slg")),
                "g_ops": _safe_float(g.get("ops")),
                "g_plate_appearances": _safe_int(g.get("plateAppearances")),
                "g_stolen_bases": _safe_int(g.get("stolenBases")),
                "g_caught_stealing": _safe_int(g.get("caughtStealing")),
                "g_hit_by_pitch": _safe_int(g.get("hitByPitch")),
                # season snapshot
                "s_games_played": _safe_int(s.get("gamesPlayed")),
                "s_at_bats": _safe_int(s.get("atBats")),
                "s_hits": _safe_int(s.get("hits")),
                "s_doubles": _safe_int(s.get("doubles")),
                "s_triples": _safe_int(s.get("triples")),
                "s_home_runs": _safe_int(s.get("homeRuns")),
                "s_rbi": _safe_int(s.get("rbi")),
                "s_walks": _safe_int(s.get("baseOnBalls")),
                "s_strikeouts": _safe_int(s.get("strikeOuts")),
                "s_avg": _safe_float(s.get("avg")),
                "s_obp": _safe_float(s.get("obp")),
                "s_slg": _safe_float(s.get("slg")),
                "s_ops": _safe_float(s.get("ops")),
                "s_plate_appearances": _safe_int(s.get("plateAppearances")),
                "s_stolen_bases": _safe_int(s.get("stolenBases")),
                "s_babip": _safe_float(s.get("babip")),
            })

        self._insert_rows("raw_player_batting_stats", rows)

    def _load_player_pitching(
        self,
        game_pk: int,
        game_date: date,
        team_data: dict,
        team_id: int,
        team_side: str,
    ) -> None:
        players = team_data.get("players", {})
        rows = []

        for player_data in players.values():
            stats = player_data.get("stats", {})
            season = player_data.get("seasonStats", {})
            g = stats.get("pitching", {})
            s = season.get("pitching", {})

            # Skip players with no pitching appearance in this game
            if not g or g.get("inningsPitched") is None:
                continue

            rows.append({
                "game_pk": game_pk,
                "game_date": game_date.isoformat(),
                "team_id": team_id,
                "team_side": team_side,
                "player_id": player_data.get("person", {}).get("id"),
                "player_name": player_data.get("person", {}).get("fullName"),
                # game stats
                "g_innings_pitched": _safe_float(g.get("inningsPitched")),
                "g_hits": _safe_int(g.get("hits")),
                "g_runs": _safe_int(g.get("runs")),
                "g_earned_runs": _safe_int(g.get("earnedRuns")),
                "g_walks": _safe_int(g.get("baseOnBalls")),
                "g_strikeouts": _safe_int(g.get("strikeOuts")),
                "g_home_runs": _safe_int(g.get("homeRuns")),
                "g_number_of_pitches": _safe_int(g.get("numberOfPitches")),
                "g_strikes": _safe_int(g.get("strikes")),
                "g_balls": _safe_int(g.get("balls")),
                "g_batters_faced": _safe_int(g.get("battersFaced")),
                "g_outs": _safe_int(g.get("outs")),
                "g_era": _safe_float(g.get("era")),
                "g_whip": _safe_float(g.get("whip")),
                "g_hit_by_pitch": _safe_int(g.get("hitByPitch")),
                "g_wild_pitches": _safe_int(g.get("wildPitches")),
                "g_balks": _safe_int(g.get("balks")),
                # season snapshot
                "s_games_played": _safe_int(s.get("gamesPlayed")),
                "s_games_started": _safe_int(s.get("gamesStarted")),
                "s_wins": _safe_int(s.get("wins")),
                "s_losses": _safe_int(s.get("losses")),
                "s_saves": _safe_int(s.get("saves")),
                "s_holds": _safe_int(s.get("holds")),
                "s_blown_saves": _safe_int(s.get("blownSaves")),
                "s_innings_pitched": _safe_float(s.get("inningsPitched")),
                "s_hits": _safe_int(s.get("hits")),
                "s_runs": _safe_int(s.get("runs")),
                "s_earned_runs": _safe_int(s.get("earnedRuns")),
                "s_walks": _safe_int(s.get("baseOnBalls")),
                "s_strikeouts": _safe_int(s.get("strikeOuts")),
                "s_home_runs": _safe_int(s.get("homeRuns")),
                "s_era": _safe_float(s.get("era")),
                "s_whip": _safe_float(s.get("whip")),
                "s_strikeouts_per_9": _safe_float(s.get("strikeoutsPer9Inn")),
                "s_walks_per_9": _safe_float(s.get("walksPer9Inn")),
                "s_hits_per_9": _safe_float(s.get("hitsPer9Inn")),
                "s_strikeout_walk_ratio": _safe_float(s.get("strikeoutWalkRatio")),
                "s_inherited_runners": _safe_int(s.get("inheritedRunners")),
                "s_inherited_runners_scored": _safe_int(s.get("inheritedRunnersScored")),
            })

        self._insert_rows("raw_player_pitching_stats", rows)
