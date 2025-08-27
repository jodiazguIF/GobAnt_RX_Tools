import duckdb
import pandas as pd
from .config import settings

class DuckDBClient:
    """Simple wrapper around a DuckDB connection."""

    def __init__(self, path: str | None = None):
        self.path = path or settings.duckdb_path
        self.con = duckdb.connect(self.path)

    def query(self, sql: str, params: dict | None = None) -> pd.DataFrame:
        """Execute a SQL query and return a DataFrame."""
        return self.con.execute(sql, params or {}).df()
