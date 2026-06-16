from app.data_sources.provider import get_data_source


def get_schema() -> dict:
    """Fetch the schema of the fetal records database."""
    source = get_data_source()
    return source.get_schema()


def execute_sql_query(fetus_id: str) -> dict:
    """Fetch the fetal record for a given fetus ID."""
    source = get_data_source()
    record = source.get_record(fetus_id)
    return record.model_dump(mode="json")
