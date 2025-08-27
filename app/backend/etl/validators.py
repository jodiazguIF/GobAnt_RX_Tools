import pandas as pd
from datetime import datetime
from typing import List, Dict


def validate_business_rules(df: pd.DataFrame) -> List[Dict]:
    """Check simple business rules and return list of issues."""
    issues: List[Dict] = []
    for col in ["FECHA", "FECHA CC", "FECHA DE FABRICACION"]:
        if col in df.columns:
            mask = (df[col] < pd.Timestamp("2000-01-01")) | (df[col] > pd.Timestamp("2100-12-31"))
            if mask.any():
                issues.append({"column": col, "rows": df[mask].index.tolist()})
    return issues
