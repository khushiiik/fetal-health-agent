from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import date


class VitalsData(BaseModel):

    fetal_heart_rate_bpm: int = Field(
        ..., ge=0, le=300, description="Fetal heart rate in beats per minute"
    )

    movement_count_per_hour: int = Field(
        ..., ge=0, description="Number of fetal movements per hour"
    )

    amniotic_fluid_index_cm: float = Field(
        ..., ge=0, description="Amniotic fluid index in centimeters"
    )

    estimated_fetal_weight_g: int = Field(
        ..., ge=0, description="Estimated fetal weight in grams"
    )


class FetalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fetus_id: str = Field(
        ..., description="Unique identifier for the fetus e.g FET-1001"
    )
    patient_id: str = Field(
        ..., description="Unique identifier for the patient e.g PAT-2031"
    )
    gestational_age_weeks: int = Field(
        ..., ge=1, le=42, description="Gestational age in weeks"
    )
    scan_date: date = Field(..., description="Date of the scan")
    vitals: VitalsData
    notes: Optional[str] = Field(None, description="Additional notes from the scan")

