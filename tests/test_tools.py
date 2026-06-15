from datetime import date
from app.models.fetal_record import FetalRecord, VitalsData
from app.models.vitals_analysis import VitalResult, VitalStatus, VitalUnit, HealthClassification, VitalsAnalysis, ReferenceRange
from app.models.error_response import NotFound
from app.tools.sql_tools import get_schema, execute_sql_query
from app.tools.research_tools import (
    lookup_reference_range,
    analyse_vitals,
    classify_health_status,
    generate_summary,
    format_report,
)


def test_get_schema():
    """Verify that get_schema returns a valid schema dict with expected fields."""
    schema = get_schema()
    assert isinstance(schema, dict)
    assert "fetus_id" in schema
    assert "vitals" in schema
    assert schema["fetus_id"]["type"] == "STRING"


def test_execute_sql_query_success():
    """Verify that execute_sql_query returns a FetalRecord for valid fetus IDs."""
    # FET-1001 is a known mock fetus ID (typically healthy)
    record = execute_sql_query("FET-1001")
    assert isinstance(record, FetalRecord)
    assert record.fetus_id == "FET-1001"
    assert record.patient_id == "PAT-2001"


def test_execute_sql_query_not_found():
    """Verify execute_sql_query returns NotFound for non-existent fetus IDs."""
    record = execute_sql_query("FET-NON-EXISTENT")
    assert isinstance(record, NotFound)
    assert record.fetus_id == "FET-NON-EXISTENT"


def test_lookup_reference_range():
    """Verify lookup_reference_range looks up the correct values and handles edge cases."""
    # Test standard range
    ref_fhr = lookup_reference_range("fetal_heart_rate_bpm")
    assert ref_fhr is not None
    assert ref_fhr.vital_name == "fetal_heart_rate_bpm"
    assert ref_fhr.min_value == 110
    assert ref_fhr.max_value == 160
    assert ref_fhr.unit == VitalUnit.BPM

    # Test gestational age dependent range (estimated fetal weight at week 32)
    ref_weight = lookup_reference_range("estimated_fetal_weight_g", gestational_age_weeks=32)
    assert ref_weight is not None
    assert ref_weight.vital_name == "estimated_fetal_weight_g"
    assert ref_weight.min_value == 1600
    assert ref_weight.max_value == 2100
    assert ref_weight.unit == VitalUnit.G

    # Test non-existent vital
    ref_invalid = lookup_reference_range("invalid_vital_name")
    assert ref_invalid is None


def test_analyse_vitals_healthy():
    """Verify vitals analysis flags healthy records as normal."""
    record = FetalRecord(
        fetus_id="FET-1001",
        patient_id="PAT-2031",
        gestational_age_weeks=32,
        scan_date=date(2026, 5, 14),
        vitals=VitalsData(
            fetal_heart_rate_bpm=140,  # normal
            movement_count_per_hour=12,  # normal
            amniotic_fluid_index_cm=12.5,  # normal
            estimated_fetal_weight_g=1850,  # normal for 32 weeks
        ),
        notes="Normal scan"
    )
    
    results = analyse_vitals(record)
    assert len(results) == 4
    for r in results:
        assert r.status == VitalStatus.NORMAL


def test_analyse_vitals_abnormal():
    """Verify vitals analysis flags critical records correctly."""
    record = FetalRecord(
        fetus_id="FET-1003",
        patient_id="PAT-2033",
        gestational_age_weeks=32,
        scan_date=date(2026, 5, 14),
        vitals=VitalsData(
            fetal_heart_rate_bpm=90,  # abnormal (bradycardia)
            movement_count_per_hour=3,  # abnormal (decreased movement)
            amniotic_fluid_index_cm=2.5,  # abnormal (oligohydramnios)
            estimated_fetal_weight_g=1200,  # abnormal (growth restriction)
        ),
        notes="Abnormal scan"
    )
    
    results = analyse_vitals(record)
    assert len(results) == 4
    for r in results:
        assert r.status == VitalStatus.ABNORMAL


def test_classify_health_status():
    """Test health classification logic based on individual vitals results."""
    normal_ref = ReferenceRange(vital_name="fhr", min_value=110, max_value=160, unit=VitalUnit.BPM)
    
    # 1. Healthy (all normal)
    results_healthy = [
        VitalResult(vital_name="fhr", measured_value=140, reference_range=normal_ref, status=VitalStatus.NORMAL)
    ]
    assert classify_health_status(results_healthy) == HealthClassification.HEALTHY

    # 2. At Risk (at least one borderline)
    results_at_risk = [
        VitalResult(vital_name="fhr", measured_value=165, reference_range=normal_ref, status=VitalStatus.BORDERLINE)
    ]
    assert classify_health_status(results_at_risk) == HealthClassification.AT_RISK

    # 3. Critical (at least one abnormal)
    results_critical = [
        VitalResult(vital_name="fhr", measured_value=165, reference_range=normal_ref, status=VitalStatus.BORDERLINE),
        VitalResult(vital_name="mv", measured_value=3, reference_range=normal_ref, status=VitalStatus.ABNORMAL),
    ]
    assert classify_health_status(results_critical) == HealthClassification.CRITICAL


def test_generate_summary():
    """Verify natural-language summaries for different classifications."""
    # Healthy summary
    analysis_healthy = VitalsAnalysis(
        fetus_id="FET-1001",
        vital_results=[],
        overall_classification=HealthClassification.HEALTHY,
        classification_reason="All normal"
    )
    summary_healthy = generate_summary(analysis_healthy)
    assert "Normal fetal monitoring scan" in summary_healthy

    # At Risk summary
    normal_ref = ReferenceRange(vital_name="fhr", min_value=110, max_value=160, unit=VitalUnit.BPM)
    analysis_at_risk = VitalsAnalysis(
        fetus_id="FET-1002",
        vital_results=[
            VitalResult(vital_name="movement_count_per_hour", measured_value=8, reference_range=normal_ref, status=VitalStatus.BORDERLINE)
        ],
        overall_classification=HealthClassification.AT_RISK,
        classification_reason="Borderline movement count"
    )
    summary_at_risk = generate_summary(analysis_at_risk)
    assert "AT-RISK status" in summary_at_risk
    assert "movement_count_per_hour" in summary_at_risk

    # Critical summary
    analysis_critical = VitalsAnalysis(
        fetus_id="FET-1003",
        vital_results=[
            VitalResult(vital_name="fetal_heart_rate_bpm", measured_value=90, reference_range=normal_ref, status=VitalStatus.ABNORMAL)
        ],
        overall_classification=HealthClassification.CRITICAL,
        classification_reason="Abnormal fetal heart rate"
    )
    summary_critical = generate_summary(analysis_critical)
    assert "CRITICAL status" in summary_critical
    assert "fetal_heart_rate_bpm" in summary_critical


def test_format_report():
    """Verify that the diagnostic report is correctly formatted."""
    record = FetalRecord(
        fetus_id="FET-1001",
        patient_id="PAT-2031",
        gestational_age_weeks=32,
        scan_date=date(2026, 5, 14),
        vitals=VitalsData(
            fetal_heart_rate_bpm=140,
            movement_count_per_hour=12,
            amniotic_fluid_index_cm=12.5,
            estimated_fetal_weight_g=1850,
        ),
        notes="Healthy patient scan"
    )

    results = analyse_vitals(record)
    analysis = VitalsAnalysis(
        fetus_id=record.fetus_id,
        vital_results=results,
        overall_classification=classify_health_status(results),
        classification_reason="All physiological parameters within normal boundaries"
    )
    
    summary = generate_summary(analysis)
    report = format_report(analysis, summary, record)

    assert report.header.fetus_id == "FET-1001"
    assert report.header.patient_id == "PAT-2031"
    assert report.header.gestational_age_weeks == 32
    assert report.summary == summary
    assert len(report.vitals_breakdown) == 4
    assert report.notes == "Healthy patient scan"
