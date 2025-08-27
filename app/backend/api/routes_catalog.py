import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

@router.get("/catalog")
def get_catalog() -> dict:
    """Return the data catalog used for NL queries."""
    path = Path("catalog/data_catalog.json")
    with path.open(encoding="utf-8") as f:
        return json.load(f)
