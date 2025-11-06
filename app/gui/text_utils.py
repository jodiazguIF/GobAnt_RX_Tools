"""Utilidades para normalizar y formatear texto."""
from __future__ import annotations

import re
import unicodedata
from docx.text.run import Run


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


def apply_bold_text(run: Run, value: str) -> None:
    """Escribe el texto en el run garantizando negrilla."""

    run.text = value
    run.bold = True
