from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class VitalStatus(str, Enum):
    NORMAL = "normal"
    BORDERLINE = "borderline"
    ABNORMAL = "abnormal"


class HealthClassification(str, Enum):
    HEALTHY = "healthy"
    AT_RISK = "at-risk"
    CRITICAL = "critical"

class VitalUnit(str, Enum):
    BPM = "bpm"
    CM = "cm"
    G = "g"
    COUNT = "count"
    COUNTS_HR = "counts/hr"

class ReferenceRange(BaseModel):
    vital_name: str
    min_value: float = Field(..., description="Minimum normal value")
    max_value: Optional[float] = Field(None, description="Maximum normal value")
    unit: VitalUnit = Field(..., description="Unit of measurement")


class VitalResult(BaseModel):
    vital_name: str
    measured_value: float
    reference_range: ReferenceRange
    status: VitalStatus
    deviation_note: Optional[str] = Field(
        None,
        description="Short note explaining why this vital is borderline or abnormal",
    )


class VitalsAnalysis(BaseModel):
    fetus_id: str
    vital_results: list[VitalResult]
    overall_classification: HealthClassification
    classification_reason: str = Field(
        ...,
        description="Human readable explanation of why this classification was assigned",
    )
