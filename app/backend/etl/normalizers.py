import pandas as pd
import unicodedata

def normalize_text(s: str) -> str | None:
    """Uppercase, trim and remove accents."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip().upper()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def normalize_catalog(df: pd.DataFrame, column: str, catalog_path: str, catalog_col: str = 'nombre', code_col: str = 'codigo_dane', code_width: int | None = None) -> pd.DataFrame:
    """Join df[column] with a catalog CSV to standardize names and add codes."""
    catalog = pd.read_csv(catalog_path)
    if code_width:
        catalog[code_col] = catalog[code_col].astype(str).str.zfill(code_width)
    else:
        catalog[code_col] = catalog[code_col].astype(str)
    catalog[catalog_col] = catalog[catalog_col].map(normalize_text)
    df[column] = df[column].map(normalize_text)
    df = df.merge(catalog[[catalog_col, code_col]], left_on=column, right_on=catalog_col, how='left')
    df = df.drop(columns=[catalog_col]).rename(columns={code_col: f"{column}_CODIGO"})
    return df
