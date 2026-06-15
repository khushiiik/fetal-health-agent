from app.data_sources.provider import get_data_source
from app.models.fetal_record import FetalRecord
from app.models.error_response import NotFound

def get_schema() -> dict:
    """Fetch the schema of the fetal records database."""
    source = get_data_source()
    return source.get_schema()

def execute_sql_query(fetus_id: str) -> FetalRecord | NotFound:
    """Fetch the fetal record for a given fetus ID."""
    source = get_data_source()
    record = source.get_record(fetus_id)
    if hasattr(record, "model_dump"):
        return record.model_dump(mode="json")
    return record
