import json
import os

from loguru import logger

from app.core.config import settings
from app.data_sources.base import BaseDataSource
from app.models.error_response import NotFound
from app.models.fetal_record import FetalRecord


class MockDataSource(BaseDataSource):
    """Mock data source adapter reading local JSON records."""

    def __init__(self) -> None:
        self.records_path = os.path.join(settings.MOCK_DATA_PATH, "fetal_records.json")
        self.schema_path = os.path.join(settings.MOCK_DATA_PATH, "schema.json")

    def get_record(self, fetus_id: str) -> FetalRecord | NotFound:
        """Retrieve a fetal record from local JSON file."""
        if not os.path.exists(self.records_path):
            return NotFound(fetus_id=fetus_id, message="Mock records file not found")
        try:
            logger.bind(fetus_id=fetus_id).info("Fetching fetal record")
            with open(self.records_path, "r", encoding="utf-8") as f:
                records = json.load(f)
            for rec in records:
                if rec.get("fetus_id") == fetus_id:
                    return FetalRecord.model_validate(rec)
            return NotFound(fetus_id=fetus_id)
        except Exception as e:
            logger.exception("Failed to read mock records")
            return NotFound(
                fetus_id=fetus_id, message=f"Failed to read mock records: {str(e)}"
            )

    def get_schema(self) -> dict:
        """Returns the schema dictionary transformed from BigQuery JSON format."""
        if not os.path.exists(self.schema_path):
            return {}
        try:
            with open(self.schema_path, "r", encoding="utf-8") as f:
                bq_schema = json.load(f)
            schema_dict = {}
            for field in bq_schema:
                name = field.get("name")
                if name:
                    schema_dict[name] = {
                        "type": field.get("type"),
                        "description": field.get("description"),
                        "required": field.get("mode") == "REQUIRED",
                    }
                    if "fields" in field:
                        schema_dict[name]["fields"] = {
                            sub.get("name"): {
                                "type": sub.get("type"),
                                "description": sub.get("description"),
                                "required": sub.get("mode") == "REQUIRED",
                            }
                            for sub in field["fields"]
                        }
            return schema_dict
        except Exception:
            logger.exception("Schema retrieval failed")
            return {}

    def health_check(self) -> bool:
        """Check if local mock files exist and are readable."""
        return os.path.exists(self.records_path) and os.path.exists(self.schema_path)
