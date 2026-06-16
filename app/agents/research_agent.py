from google.adk import Agent
from app.core.config import get_llm
from app.tools.research_tools import (
    lookup_reference_range,
    analyse_vitals,
    classify_health_status,
    generate_summary,
    format_report,
)

research_agent = Agent(
    name="research_agent",
    description="Research Agent specialized in analyzing fetal vital signs against reference ranges, determining health classifications, and generating summaries.",
    model=get_llm(),
    instruction="You are a clinical research assistant. Your task is to analyze patient vitals. Step 1: Look up normal reference ranges for each vital sign using lookup_reference_range. Step 2: Compare patient values to these ranges using analyse_vitals. Step 3: Call classify_health_status to deterministically aggregate status (healthy, at-risk, critical). Step 4: Write a clinical text summary using generate_summary. Step 5: Format the final DiagnosticReport object by calling format_report with the analysis, summary, and record details. Step 6: Finally, return and output the exact 'report_markdown' text field returned by format_report as your final response, without any conversational filler or introductory/concluding remarks.",
    tools=[
        lookup_reference_range,
        analyse_vitals,
        classify_health_status,
        generate_summary,
        format_report,
    ],
)
