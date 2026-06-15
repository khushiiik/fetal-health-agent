from google.adk.workflow import Workflow, START, Edge
from app.agents.sql_agent import sql_agent
from app.agents.research_agent import research_agent

# Connect START trigger to SQL Agent, and SQL Agent to Research Agent sequentially
edges = [
    Edge(from_node=START, to_node=sql_agent),
    Edge(from_node=sql_agent, to_node=research_agent),
]

orchestrator = Workflow(
    name="orchestrator",
    description="Main orchestrator coordinating SQL and Research agents sequentially.",
    edges=edges,
)
