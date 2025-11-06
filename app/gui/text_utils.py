"""Utilidades para normalizar y formatear texto."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional, Tuple

from docx.text.run import Run

MONTH_NAMES_ES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}


def strip_accents(value: str) -> str:
    """Elimina acentos y devuelve el texto en mayúsculas."""

    normalized = unicodedata.normalize("NFD", value)
    without_accents = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return unicodedata.normalize("NFC", without_accents)


def normalize_label(value: str) -> str:
    """Normaliza etiquetas para facilitar su comparación."""

    upper = strip_accents(value).upper().replace("\n", " ")
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", upper)
    return " ".join(part for part in cleaned.split())


def normalize_value(value: str) -> str:
    """Normaliza valores ingresados por el usuario."""

    cleaned = value.strip()
    if not cleaned:
        return ""
    return cleaned.upper()


_PLACEHOLDER_CHARS_RE = re.compile(r"[^A-Z0-9]+")


def normalize_placeholder_key(value: str) -> str:
    """Convierte la clave de un marcador a MAYÚSCULAS_CON_GUIONES."""

    cleaned = strip_accents(value).upper()
    replaced = _PLACEHOLDER_CHARS_RE.sub("_", cleaned)
    return replaced.strip("_")


def apply_bold_text(run: Run, value: str) -> None:
    """Escribe el texto en el run garantizando negrilla."""

    run.text = value
    run.bold = True


_RESOLUTION_DATE_RE = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$")


def split_resolution_date(value: str) -> Optional[Tuple[str, str, str]]:
    """Descompone una fecha dd/mm/aaaa en día, mes (texto) y año.

    El mes se devuelve con el nombre en español en mayúsculas y sin tildes.
    Si el valor no coincide con el patrón esperado, se devuelve ``None``.
    """

    cleaned = value.strip()
    if not cleaned:
        return None

    match = _RESOLUTION_DATE_RE.match(cleaned)
    if not match:
        return None

    day_raw, month_raw, year_raw = match.groups()

    day = str(int(day_raw))
    month_index = int(month_raw)
    if month_index not in MONTH_NAMES_ES:
        return None
    month_name = MONTH_NAMES_ES[month_index]

    year = year_raw
    if len(year) == 2:
        year = f"20{year}"

    return day, month_name, year
