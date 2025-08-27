from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import duckdb
from .normalizers import normalize_text, normalize_catalog
from .validators import validate_business_rules
from app.backend.core.config import settings


def run_etl(source_path: str | None = None) -> Path:
    """Read data from a CSV or Google Sheet and produce a Parquet dataset."""
    source = Path(source_path) if source_path else Path("data/raw/licencias.csv")
    df = pd.read_csv(source)
    df.columns = [normalize_text(c) for c in df.columns]
    # Standardize date columns
    for col in [c for c in df.columns if c.startswith("FECHA")]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    # Normalize municipio and subregion
    if "MUNICIPIO" in df.columns:
        df = normalize_catalog(df, "MUNICIPIO", "catalog/municipios.csv", code_width=5)
    if "SUBREGION" in df.columns:
        df = normalize_catalog(df, "SUBREGION", "catalog/subregiones.csv", catalog_col="nombre", code_col="codigo", code_width=2)
    issues = validate_business_rules(df)
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = processed_dir / "licencias.parquet"
    df.to_parquet(parquet_path, index=False)
    # Materialized view in DuckDB
    con = duckdb.connect(settings.duckdb_path)
    con.execute(f"CREATE OR REPLACE VIEW licencias AS SELECT * FROM parquet_scan('{parquet_path.as_posix()}')")
    con.close()
    # Write issues report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "etl_issues.json").write_text(json.dumps(issues, indent=2))
    return parquet_path

if __name__ == "__main__":
    run_etl()
