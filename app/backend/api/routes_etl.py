from fastapi import APIRouter, BackgroundTasks
from app.backend.etl.sheets_to_parquet import run_etl

router = APIRouter()

@router.post("/etl/run")
def etl_run(background_tasks: BackgroundTasks) -> dict:
    """Trigger the ETL process in the background."""
    background_tasks.add_task(run_etl)
    return {"status": "started"}
