from fastapi import APIRouter
from app.backend.models.schemas import AskRequest, AskResponse
from app.backend.llm.client import GeminiClient
from app.backend.llm.sql_guard import validate_sql
from app.backend.core.duckdb_client import DuckDBClient

router = APIRouter()

@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """Answer natural language questions about the data."""
    llm = GeminiClient()
    sql = llm.to_sql(req.question, req.filters)
    validate_sql(sql, allowed_tables=["licencias"])
    db = DuckDBClient()
    df = db.query(sql)
    data = df.to_dict(orient="records")
    summary = llm.summarize(str(df))
    return AskResponse(data=data, spec={"type": "table"}, summary=summary)
