# app/utils/radicado.py
import re
from typing import Optional

# Acepta "Radicado: 123456", "RADICADO 123456", "Radicado-123456", etc.
RAD_RE_EXPL = re.compile(r"(?i)\bradicado\b[:\s\-#]*([0-9]{6,})")
RAD_RE_FILENAME = re.compile(r"([0-9]{6,})")

def extract_from_text(doc_text: str) -> Optional[str]:
    # Mirar solo las primeras líneas: ahí suele estar el radicado
    lines = doc_text.splitlines()
    head = "\n".join(lines[:50])  # primeras ~50 líneas
    m = RAD_RE_EXPL.search(head)
    if m:
        return m.group(1)
    # Fallback: número al inicio de una línea (encabezado)
    m2 = re.search(r"^\s*([0-9]{6,})\b", head, flags=re.MULTILINE)
    return m2.group(1) if m2 else None

def extract_from_filename(filename: str) -> Optional[str]:
    m = RAD_RE_FILENAME.search(filename)
    return m.group(1) if m else None

def resolve(doc_text: str, filename: str) -> Optional[str]:
    # Prioriza el nombre del archivo si ya trae el radicado; si no, intenta en el texto
    return extract_from_filename(filename) or extract_from_text(doc_text)
