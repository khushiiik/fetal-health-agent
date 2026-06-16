from google.adk import Agent

from app.core.config import get_llm
from app.tools.research_tools import run_fetal_analysis

research_agent = Agent(
    name="research_agent",
    description="Research Agent specialized in analyzing fetal vital signs against reference ranges, determining health classifications, and generating summaries.",
    model=get_llm(),
    instruction="Analyze the provided fetal record using the run_fetal_analysis tool and return the generated report.",
    tools=[run_fetal_analysis],
)
