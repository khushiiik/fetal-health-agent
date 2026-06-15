from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional
from .vitals_analysis import VitalsAnalysis


class ReportHeader(BaseModel):
    fetus_id: str
    patient_id: Optional[str] = None
    scan_date: date
    gestational_age_weeks: int
    report_generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when the report was generated",
    )


class VitalsBreakdownRow(BaseModel):
    vital_name: str
    measured_value: float
    unit: str
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    status: str
    deviation_note: Optional[str] = None


class DiagnosticReport(BaseModel):
    header: ReportHeader
    summary: str
    vitals_breakdown: list[VitalsBreakdownRow]
    analysis: VitalsAnalysis
    notes: str | None = None
