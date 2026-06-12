from app.models.diagnostic_report import DiagnosticReport

def report_to_markdown(report: DiagnosticReport) -> str:
    """Renders the report as a readable markdown string"""
    lines = [
        "# Fetal Health Diagnostic Report",
        "",
        "## Header",
        f"- **Fetus ID:** {report.header.fetus_id}",
        f"- **Patient ID:** {report.header.patient_id or 'N/A'}",
        f"- **Scan Date:** {report.header.scan_date}",
        f"- **Gestational Age:** {report.header.gestational_age_weeks} weeks",
        f"- **Report Generated:** {report.header.report_generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Summary",
        f"{report.summary}",
        "",
        "## Vitals Breakdown",
        "| Vital | Value | Normal Range | Status |",
        "|---|---|---|---|",
    ]
    for row in report.vitals_breakdown:
        if row.reference_min is not None and row.reference_max is not None:
            ref_str = f"{row.reference_min}–{row.reference_max}"
        elif row.reference_min is not None:
            ref_str = f"≥ {row.reference_min}"
        elif row.reference_max is not None:
            ref_str = f"≤ {row.reference_max}"
        else:
            ref_str = "N/A"

        lines.append(
            f"| {row.vital_name} | {row.measured_value} {row.unit} "
            f"| {ref_str} {row.unit} "
            f"| {row.status.upper()} |"
        )
    lines += [
        "",
        "## Overall Classification",
        f"**{report.analysis.overall_classification.value.upper()}**",
        "",
        f"_{report.analysis.classification_reason}_",
        "",
        "## Notes",
        f"{report.notes or 'None'}",
    ]
    return "\n".join(lines)
