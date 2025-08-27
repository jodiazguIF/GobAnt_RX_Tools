from fastapi import FastAPI
from app.backend.api import routes_analysis, routes_map, routes_ask, routes_etl, routes_catalog

app = FastAPI(title="GobAnt RX Tools")

app.include_router(routes_analysis.router)
app.include_router(routes_map.router)
app.include_router(routes_ask.router)
app.include_router(routes_etl.router)
app.include_router(routes_catalog.router)

@app.get("/health")
def health() -> dict[str, str]:
    """Simple health check."""
    return {"status": "ok"}
