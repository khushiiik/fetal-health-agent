from google.adk import Agent

from app.core.config import get_llm
from app.tools.sql_tools import execute_sql_query, get_schema

sql_agent = Agent(
    name="sql_agent",
    description="SQL Agent specialized in querying the fetal health database schema and executing queries.",
    model=get_llm(),
    instruction="Retrieve the fetal record for the requested fetus ID.",
    tools=[get_schema, execute_sql_query],
)
