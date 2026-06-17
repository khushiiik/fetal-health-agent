import json
from typing import Optional

from loguru import logger

from app.core.config import settings
from app.models.diagnostic_report import (
    DiagnosticReport,
    ReportHeader,
    VitalsBreakdownRow,
)
from app.models.fetal_record import FetalRecord
from app.models.vitals_analysis import (
    HealthClassification,
    ReferenceRange,
    VitalResult,
    VitalsAnalysis,
    VitalStatus,
    VitalUnit,
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
    except Exception as e:
        logger.exception(f"Failed to lookup reference range for {vital_name}: {e}")
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


def format_list_with_and(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def get_vital_reason_phrase(name: str, value: float, status: VitalStatus) -> str:
    if status == VitalStatus.NORMAL:
        return ""
    if name == "fetal_heart_rate_bpm":
        if status == VitalStatus.ABNORMAL:
            return f"severe fetal heart rate deviation ({int(value)} bpm)"
        return f"borderline fetal heart rate ({int(value)} bpm)"
    elif name == "movement_count_per_hour":
        if status == VitalStatus.ABNORMAL:
            return f"severely decreased fetal movement ({int(value)} counts/hr)"
        return f"decreased fetal movement ({int(value)} counts/hr)"
    elif name == "amniotic_fluid_index_cm":
        if status == VitalStatus.ABNORMAL:
            return f"severe amniotic fluid deviation ({value} cm)"
        return f"mild amniotic fluid deviation ({value} cm)"
    elif name == "estimated_fetal_weight_g":
        return f"abnormal estimated fetal weight ({int(value)} g)"
    return ""


def get_vital_summary_phrase(
    name: str,
    value: float,
    status: VitalStatus,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> str:
    if status == VitalStatus.NORMAL:
        return ""
    if name == "fetal_heart_rate_bpm":
        if status == VitalStatus.ABNORMAL:
            return (
                f"severe fetal tachycardia ({int(value)} bpm)"
                if value > 180
                else f"severe fetal bradycardia ({int(value)} bpm)"
            )
        return (
            f"borderline fetal tachycardia ({int(value)} bpm)"
            if value > 160
            else f"borderline fetal bradycardia ({int(value)} bpm)"
        )
    elif name == "movement_count_per_hour":
        if status == VitalStatus.ABNORMAL:
            return f"severely decreased fetal movement ({int(value)} counts/hr)"
        return f"decreased fetal movement ({int(value)} counts/hr)"
    elif name == "amniotic_fluid_index_cm":
        if status == VitalStatus.ABNORMAL:
            return (
                f"severe polyhydramnios ({value} cm)"
                if value > 30.0
                else f"severe oligohydramnios ({value} cm)"
            )
        return (
            f"mild polyhydramnios ({value} cm)"
            if value > 25.0
            else f"mild oligohydramnios ({value} cm)"
        )
    elif name == "estimated_fetal_weight_g":
        if min_val is not None and value < min_val:
            return f"suspected fetal growth restriction ({int(value)} g)"
        if max_val is not None and value > max_val:
            return f"suspected macrosomia ({int(value)} g)"
        return f"abnormal estimated fetal weight ({int(value)} g)"
    return ""


def generate_classification_reason(
    vital_results: list[VitalResult], classification: HealthClassification
) -> str:
    if classification == HealthClassification.HEALTHY:
        return "All physiological parameters within normal boundaries."

    phrases = []
    for r in vital_results:
        phrase = get_vital_reason_phrase(r.vital_name, r.measured_value, r.status)
        if phrase:
            phrases.append(phrase)

    if not phrases:
        return "Elevated risk detected from vital deviations."

    joined = format_list_with_and(phrases)
    return joined[0].upper() + joined[1:] + "."


def generate_summary(
    classification: HealthClassification,
    vital_results: list[VitalResult],
    fetus_id: str,
) -> str:
    """Generate a clinician-focused summary based on vitals analysis."""
    if classification == HealthClassification.HEALTHY:
        return f"Normal fetal monitoring scan. Fetus {fetus_id} parameters are within the expected physiological range."

    phrases = []
    for r in vital_results:
        phrase = get_vital_summary_phrase(
            r.vital_name,
            r.measured_value,
            r.status,
            r.reference_range.min_value,
            r.reference_range.max_value,
        )
        if phrase:
            phrases.append(phrase)

    if not phrases:
        if classification == HealthClassification.CRITICAL:
            return f"CRITICAL status flagged for fetus {fetus_id}. Immediate clinical evaluation is strongly recommended."
        else:
            return f"AT-RISK status flagged for fetus {fetus_id}. Close monitoring is advised."

    joined = format_list_with_and(phrases)
    first_cap = joined[0].upper() + joined[1:]
    verb = "was" if len(phrases) == 1 else "were"

    if classification == HealthClassification.CRITICAL:
        return f"CRITICAL status identified. {first_cap} {verb} observed. Immediate clinical evaluation is strongly recommended."
    else:
        return f"AT-RISK status identified. {first_cap} {verb} observed. Close monitoring is recommended."


def format_report(
    analysis: VitalsAnalysis,
    summary: str,
    record: FetalRecord,
    vital_results: list[VitalResult],
) -> dict:
    """Assemble final diagnostic report structure."""
    header = ReportHeader(
        fetus_id=record.fetus_id,
        patient_id=record.patient_id,
        scan_date=record.scan_date,
        gestational_age_weeks=record.gestational_age_weeks,
    )

    breakdown = []
    for r in vital_results:
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
        "report_markdown": report_to_markdown(report),
    }


def run_fetal_analysis(record: FetalRecord) -> dict:
    """Analyze the provided fetal record and generate the final diagnostic report in Python."""
    results = analyse_vitals(record)
    classification = classify_health_status(results)
    reason = generate_classification_reason(results, classification)

    analysis = VitalsAnalysis(
        fetus_id=record.fetus_id,
        overall_classification=classification,
        classification_reason=reason,
    )
    summary = generate_summary(classification, results, record.fetus_id)
    return format_report(analysis, summary, record, results)
