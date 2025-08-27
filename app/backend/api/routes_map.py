from fastapi import APIRouter

router = APIRouter()

@router.post("/map/choropleth")
def choropleth(level: str) -> dict:
    """Return placeholder GeoJSON for choropleth maps."""
    return {"type": "FeatureCollection", "features": []}
