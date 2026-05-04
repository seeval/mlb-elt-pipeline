import json
import logging
from dataclasses import dataclass
from datetime import date

from google.cloud import storage

logger = logging.getLogger(__name__)

@dataclass
class GCSLoader:
    """
    Writes raw API response payloads to GCS under Hive-partitioned paths.
    """
    bucket_name: str
    client: storage.Client

    def _build_path(self, data_type: str, game_date: date, filename: str) -> str:
        """
        Constructs a Hive-partitioned GCS path.
        Example output: schedule/year=2026/month=05/day=04/schedule.json
        """
        return (
                f"{data_type}/"
                f"year={game_date.year}/"
                f"month={game_date.month:02d}/"
                f"day={game_date.day:02d}/"
                f"{filename}"
                )

    def write_json(self, payload: dict, data_type: str, game_date: date, filename: str) -> str:
        """
        Serliazes payload to JSON and writes to GCS. 
        Overwrites if the object already exists.
        Returns full GCS URI of the written object.
        """
        path = self._build_path(data_type, game_date, filename)
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(path)

        blob.upload_from_string(
                data=json.dumps(payload, indent=2),
                content_type="application/json"
                )

        uri = f"gs://{self.bucket_name}/{path}"
        logger.info("Written to %s", uri)
        return uri
