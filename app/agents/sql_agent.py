from google.adk import Agent
from app.core.config import get_llm
from app.tools.sql_tools import get_schema, execute_sql_query

sql_agent = Agent(
    name="sql_agent",
    description="SQL Agent specialized in querying the fetal health database schema and executing queries.",
    model=get_llm(),
    instruction="You are a data access assistant. Retrieve the fetal health record for the requested fetus ID. First check the database schema if needed, then query the patient record using the execute_sql_query tool. Pass the retrieved record structure onward without changing its keys or shape.",
    tools=[get_schema, execute_sql_query],
)
