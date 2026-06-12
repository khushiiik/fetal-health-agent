from abc import ABC, abstractmethod
from app.models.fetal_record import FetalRecord
from app.models.error_response import NotFound

class BaseDataSource(ABC):
    """Abstract base interface for all data source adapters."""

    @abstractmethod
    def get_record(self, fetus_id: str) -> FetalRecord | NotFound:
        """Retrieve a fetal record by fetus_id. Returns FetalRecord or NotFound."""
        ...

    @abstractmethod
    def get_schema(self) -> dict:
        """Returns the schema definition of the fetal records table."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Verifies the data source is reachable and readable."""
        ...