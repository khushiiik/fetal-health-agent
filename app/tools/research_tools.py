import json
from typing import Optional
from app.core.config import settings
from app.models.fetal_record import FetalRecord
from app.models.vitals_analysis import (
    ReferenceRange,
    VitalResult,
    VitalStatus,
    VitalUnit,
    HealthClassification,
    VitalsAnalysis,
)
from app.models.diagnostic_report import (
    DiagnosticReport,
    ReportHeader,
    VitalsBreakdownRow,
)
from app.services.report_formatter import report_to_markdown


def lookup_reference_range(
    vital_name: str, gestational_age_weeks: Optional[int] = None
) -> ReferenceRange | None:
    """Lookup reference range for a vital sign, optionally considering gestational age."""
    try:
        with open(settings.CLINICAL_DATA_PATH, "r", encoding="utf-8") as f:
            ranges = json.load(f)

        if vital_name == "estimated_fetal_weight_g":
            weight_ranges = ranges.get("estimated_fetal_weight_g_by_week", {})
            week_key = str(gestational_age_weeks)
            if week_key in weight_ranges:
                limits = weight_ranges[week_key]
                return ReferenceRange(
                    vital_name=vital_name,
                    min_value=limits["min_normal"],
                    max_value=limits["max_normal"],
                    unit=VitalUnit.G,
                )
            return None

        if vital_name in ranges:
            limits = ranges[vital_name]
            unit_val = limits.get("unit")
            unit_enum = (
                VitalUnit(unit_val)
                if unit_val in [u.value for u in VitalUnit]
                else VitalUnit.COUNT
            )

            return ReferenceRange(
                vital_name=vital_name,
                min_value=limits["min_normal"],
                max_value=limits.get("max_normal"),
                unit=unit_enum,
            )
    except Exception:
        pass
    return None


def analyse_vitals(record: FetalRecord) -> list[VitalResult]:
    """Compare fetal vital signs against their clinical reference ranges."""
    results = []
    vitals_dict = record.vitals.model_dump()

    for name, value in vitals_dict.items():
        ref = lookup_reference_range(name, record.gestational_age_weeks)
        if not ref:
            continue

        status = VitalStatus.NORMAL
        note = None

        if name == "fetal_heart_rate_bpm":
            if value < 100 or value > 180:
                status = VitalStatus.ABNORMAL
                note = "Severe tachycardia" if value > 180 else "Severe bradycardia"
            elif value < 110 or value > 160:
                status = VitalStatus.BORDERLINE
                note = "Mild tachycardia" if value > 160 else "Mild bradycardia"

        elif name == "movement_count_per_hour":
            if value < 5:
                status = VitalStatus.ABNORMAL
                note = "Severely decreased movement"
            elif value < 10:
                status = VitalStatus.BORDERLINE
                note = "Decreased movement"

        elif name == "amniotic_fluid_index_cm":
            if value < 3.0 or value > 30.0:
                status = VitalStatus.ABNORMAL
                note = (
                    "Severe polyhydramnios"
                    if value > 30.0
                    else "Severe oligohydramnios"
                )
            elif value < 5.0 or value > 25.0:
                status = VitalStatus.BORDERLINE
                note = "Mild polyhydramnios" if value > 25.0 else "Mild oligohydramnios"

        elif name == "estimated_fetal_weight_g":
            if value < ref.min_value:
                status = VitalStatus.ABNORMAL
                note = "Suspected fetal growth restriction"
            elif ref.max_value and value > ref.max_value:
                status = VitalStatus.ABNORMAL
                note = "Suspected macrosomia"

        results.append(
            VitalResult(
                vital_name=name,
                measured_value=value,
                reference_range=ref,
                status=status,
                deviation_note=note,
            )
        )

    return results


def classify_health_status(vital_results: list[VitalResult]) -> HealthClassification:
    """Determine overall health classification based on individual vital results."""
    statuses = [res.status for res in vital_results]
    if VitalStatus.ABNORMAL in statuses:
        return HealthClassification.CRITICAL
    if VitalStatus.BORDERLINE in statuses:
        return HealthClassification.AT_RISK
    return HealthClassification.HEALTHY


def generate_summary(analysis: VitalsAnalysis) -> str:
    """Generate a clinician-focused summary based on vitals analysis."""
    critical_vitals = [
        r.vital_name for r in analysis.vital_results if r.status == VitalStatus.ABNORMAL
    ]
    borderline_vitals = [
        r.vital_name
        for r in analysis.vital_results
        if r.status == VitalStatus.BORDERLINE
    ]

    if analysis.overall_classification == HealthClassification.CRITICAL:
        return f"CRITICAL status flagged for fetus {analysis.fetus_id}. Fetal distress suspected due to abnormal findings in: {', '.join(critical_vitals)}. Immediate clinical evaluation is strongly recommended."
    elif analysis.overall_classification == HealthClassification.AT_RISK:
        return f"AT-RISK status flagged for fetus {analysis.fetus_id}. Close monitoring is advised due to borderline findings in: {', '.join(borderline_vitals)}."

    return f"Normal fetal monitoring scan. Fetus {analysis.fetus_id} parameters are within the expected physiological range."


def format_report(
    analysis: VitalsAnalysis, summary: str, record: FetalRecord
) -> DiagnosticReport:
    """Assemble final diagnostic report structure."""
    header = ReportHeader(
        fetus_id=record.fetus_id,
        patient_id=record.patient_id,
        scan_date=record.scan_date,
        gestational_age_weeks=record.gestational_age_weeks,
    )

    breakdown = []
    for r in analysis.vital_results:
        breakdown.append(
            VitalsBreakdownRow(
                vital_name=r.vital_name,
                measured_value=r.measured_value,
                unit=r.reference_range.unit.value,
                reference_min=r.reference_range.min_value,
                reference_max=r.reference_range.max_value,
                status=r.status.value,
                deviation_note=r.deviation_note,
            )
        )

    report = DiagnosticReport(
        header=header,
        summary=summary,
        vitals_breakdown=breakdown,
        analysis=analysis,
        notes=record.notes,
    )
    return {
        "report": report.model_dump(mode="json"),
        "report_markdown": report_to_markdown(report)
    }
