import json
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta

from google.cloud import bigquery, storage

from extraction.gcs_loader import GCSLoader
from extraction.mlb_client import MLBApiClient
from extraction.schedule_extractor import GameRecord, ScheduleExtractor
from loading.bq_loader import BQLoader

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPipeline:
    """
    Orchestrates the full extraction and loading flow:
    1. Pull schedule for a date range → get GameRecords
    2. Write raw schedule response to GCS
    3. Pull boxscore for each game → write raw boxscore to GCS
    4. Parse and load boxscore data into BigQuery raw tables
    """
    mlb_client: MLBApiClient
    gcs_loader: GCSLoader
    bq_loader: BQLoader

    def run(self, start_date: str, end_date: str) -> None:
        logger.info("Pipeline starting for %s to %s", start_date, end_date)

        extractor = ScheduleExtractor(client=self.mlb_client)
        records = extractor.extract(start_date, end_date)

        if not records:
            logger.warning("No games found for %s to %s — exiting", start_date, end_date)
            return

        raw_schedule = self.mlb_client.get_schedule(start_date, end_date)
        self.gcs_loader.write_json(
            payload=raw_schedule,
            data_type="schedule",
            game_date=date.fromisoformat(start_date),
            filename="schedule.json",
        )

        self._process_boxscores(records)
        logger.info("Pipeline complete. Processed %d games.", len(records))

    def _process_boxscores(self, records: list[GameRecord]) -> None:
        # Collect unique dates in this run
        unique_dates = {record.game_date for record in records}

        # Truncate partitions once per date before any inserts
        for game_date in unique_dates:
            self.bq_loader._truncate_partition("raw_team_game_stats", game_date)
            self.bq_loader._truncate_partition("raw_player_batting_stats", game_date)
            self.bq_loader._truncate_partition("raw_player_pitching_stats", game_date)

        for record in records:
            try:
                logger.info("Fetching boxscore for game_pk=%d", record.game_pk)
                boxscore = self.mlb_client.get_boxscore(record.game_pk)

                self.gcs_loader.write_json(
                    payload=boxscore,
                    data_type="boxscores",
                    game_date=record.game_date,
                    filename=f"gamePk={record.game_pk}.json",
                )

                self.bq_loader.load_boxscore(
                    game_pk=record.game_pk,
                    game_date=record.game_date,
                    raw=boxscore,
                )

            except Exception as e:
                logger.error(
                    "Failed to process game_pk=%d: %s",
                    record.game_pk,
                    e,
                    exc_info=True,
                )

def build_pipeline() -> ExtractionPipeline:
    """
    Factory function: constructs the full pipeline with all dependencies.
    Reads configuration from environment variables.
    """
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        raise EnvironmentError("GCS_BUCKET_NAME environment variable not set")

    project = os.environ.get("GCP_PROJECT_ID")
    if not project:
        raise EnvironmentError("GCP_PROJECT_ID environment variable not set")

    gcs_client = storage.Client()
    bq_client = bigquery.Client(project=project)

    return ExtractionPipeline(
        mlb_client=MLBApiClient(),
        gcs_loader=GCSLoader(bucket_name=bucket_name, client=gcs_client),
        bq_loader=BQLoader(client=bq_client, project=project, dataset="mlb_raw"),
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    yesterday = date.today() - timedelta(days=1)
    run_date = yesterday.isoformat()

    pipeline = build_pipeline()
    pipeline.run(start_date=run_date, end_date=run_date)
