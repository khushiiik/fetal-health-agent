from app.core.config import settings
from app.data_sources.base import BaseDataSource
from app.data_sources.mock_source import MockDataSource
from app.data_sources.bigquery_source import BigQueryDataSource
from loguru import logger

def get_data_source() -> BaseDataSource:
    """Get the configured data source with automatic fallback to mock mode."""
    if settings.DATA_SOURCE.lower() == "bigquery":
        if settings.BIGQUERY_PROJECT_ID and settings.BIGQUERY_DATASET and settings.BIGQUERY_TABLE:
            bq_source = BigQueryDataSource()
            if bq_source.health_check():
                logger.info("Using BigQuery data source.")
                return bq_source
            logger.warning("BigQuery health check failed. Falling back to Mock data source.")
        else:
            logger.warning("BigQuery configuration incomplete. Falling back to Mock data source.")
            
    logger.info("Using Mock data source.")
    return MockDataSource()
