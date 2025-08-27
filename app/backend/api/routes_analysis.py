from fastapi import APIRouter, Depends
from app.backend.core.duckdb_client import DuckDBClient

router = APIRouter()

@router.get("/metrics/overview")
def metrics_overview(db: DuckDBClient = Depends(DuckDBClient)) -> dict:
    """Return basic KPIs for dashboard."""
    try:
        df = db.query("SELECT COUNT(*) AS total FROM licencias")
        total = int(df.iloc[0]["total"])
    except Exception:
        total = 0
    return {"total_licencias": total}
