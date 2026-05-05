import json
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta

from google.cloud import storage

from extraction.gcs_loader import GCSLoader
from extraction.mlb_client import MLBApiClient
from extraction.schedule_extractor import GameRecord, ScheduleExtractor

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPipeline:
    """
    Orchestrates the full extraction flow:
    1. Pull schedule for a date range → get GameRecords
    2. Write raw schedule response to GCS
    3. Pull boxscore for each game → write raw boxscore to GCS
    """
    mlb_client: MLBApiClient
    loader: GCSLoader

    def run(self, start_date: str, end_date: str) -> None:
        logger.info("Pipeline starting for %s to %s", start_date, end_date)

        # Step 1: Extract schedule
        extractor = ScheduleExtractor(client=self.mlb_client)
        records = extractor.extract(start_date, end_date)

        if not records:
            logger.warning("No games found for %s to %s — exiting", start_date, end_date)
            return

        # Step 2: Write raw schedule response to GCS
        raw_schedule = self.mlb_client.get_schedule(start_date, end_date)
        self.loader.write_json(
            payload=raw_schedule,
            data_type="schedule",
            game_date=date.fromisoformat(start_date),
            filename="schedule.json",
        )

        # Step 3: Pull and persist boxscore for each game
        self._extract_boxscores(records)

        logger.info("Pipeline complete. Processed %d games.", len(records))

    def _extract_boxscores(self, records: list[GameRecord]) -> None:
        for record in records:
            try:
                logger.info("Fetching boxscore for game_pk=%d", record.game_pk)
                boxscore = self.mlb_client.get_boxscore(record.game_pk)

                self.loader.write_json(
                    payload=boxscore,
                    data_type="boxscores",
                    game_date=record.game_date,
                    filename=f"gamePk={record.game_pk}.json",
                )

            except Exception as e:
                # Log and continue — one failed boxscore should not abort the run
                # Failed game_pks are identifiable by absence in GCS
                logger.error("Failed to fetch boxscore for game_pk=%d: %s", record.game_pk, e)


def build_pipeline() -> ExtractionPipeline:
    """
    Factory function: constructs the pipeline with all dependencies.
    GH Actions and local runs both call this — credentials path
    is controlled via environment variable.
    """
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        raise EnvironmentError("GCS_BUCKET_NAME environment variable not set")

    gcs_client = storage.Client()
    return ExtractionPipeline(
        mlb_client=MLBApiClient(),
        loader=GCSLoader(bucket_name=bucket_name, client=gcs_client),
    )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    # Default to yesterday — this is what the daily GH Actions run will use
    yesterday = date.today() - timedelta(days=1)
    run_date = yesterday.isoformat()

    pipeline = build_pipeline()
    pipeline.run(start_date=run_date, end_date=run_date)

