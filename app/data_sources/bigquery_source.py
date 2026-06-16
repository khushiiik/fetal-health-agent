from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery
from loguru import logger

from app.core.config import settings
from app.data_sources.base import BaseDataSource
from app.models.error_response import NotFound
from app.models.fetal_record import FetalRecord


class BigQueryDataSource(BaseDataSource):
    """Google Cloud BigQuery data source adapter."""

    def __init__(self) -> None:
        self._client = None
        self._table_ref = (
            f"{settings.BIGQUERY_PROJECT_ID}."
            f"{settings.BIGQUERY_DATASET}."
            f"{settings.BIGQUERY_TABLE}"
        )
        try:
            self._client = bigquery.Client()
        except DefaultCredentialsError as e:
            logger.warning(f"BigQuery credentials error: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize BigQuery client: {e}")

    def get_record(self, fetus_id: str) -> FetalRecord | NotFound:
        """Retrieve a fetal record from BigQuery table."""
        if not self._client:
            return NotFound(
                fetus_id=fetus_id, message="BigQuery client not initialized"
            )
        try:
            logger.bind(fetus_id=fetus_id).info("Fetching fetal record")
            query = (
                f"SELECT * FROM `{self._table_ref}` WHERE fetus_id = @fetus_id LIMIT 1"
            )

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("fetus_id", "STRING", fetus_id)
                ]
            )
            query_job = self._client.query(query, job_config=job_config)
            rows = list(query_job.result())

            if not rows:
                return NotFound(fetus_id=fetus_id)

            row_dict = dict(rows[0].items())
            return FetalRecord.model_validate(row_dict)
        except Exception as e:
            logger.exception("Failed to query BigQuery record")
            return NotFound(
                fetus_id=fetus_id, message=f"BigQuery query error: {str(e)}"
            )

    def get_schema(self) -> dict:
        """Retrieve schema from BigQuery table metadata."""
        if not self._client:
            return {}
        try:
            table = self._client.get_table(self._table_ref)
            schema_dict = {}
            for field in table.schema:
                schema_dict[field.name] = {
                    "type": field.field_type,
                    "description": field.description,
                    "required": field.mode == "REQUIRED",
                }
                if field.field_type == "RECORD" and field.fields:
                    schema_dict[field.name]["fields"] = {
                        sub.name: {
                            "type": sub.field_type,
                            "description": sub.description,
                            "required": sub.mode == "REQUIRED",
                        }
                        for sub in field.fields
                    }
            return schema_dict
        except Exception:
            logger.exception("Schema retrieval failed")
            return {}

    def health_check(self) -> bool:
        """Check if BigQuery client connects and dataset exists."""
        if not self._client or not settings.BIGQUERY_DATASET:
            return False
        try:
            dataset_ref = self._client.dataset(
                settings.BIGQUERY_DATASET, project=settings.BIGQUERY_PROJECT_ID
            )
            self._client.get_dataset(dataset_ref)
            return True
        except Exception:
            return False
