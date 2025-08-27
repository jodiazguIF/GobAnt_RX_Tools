import re
from typing import Iterable

FORBIDDEN = {"DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE"}


def validate_sql(sql: str, allowed_tables: Iterable[str] | None = None) -> bool:
    """Basic static analysis to prevent dangerous SQL."""
    tokens = re.findall(r"[A-Z_]+", sql.upper())
    if any(tok in FORBIDDEN for tok in tokens):
        raise ValueError("Prohibited SQL statement")
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT statements are allowed")
    if allowed_tables:
        pattern = re.compile(r"FROM\s+([A-Z_]+)", re.IGNORECASE)
        for table in pattern.findall(sql):
            if table.lower() not in [t.lower() for t in allowed_tables]:
                raise ValueError("Table not allowed: " + table)
    return True
