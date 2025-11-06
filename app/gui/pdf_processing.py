"""Extracción de datos desde reportes PDF de control de calidad."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List

try:
    import pdfplumber  # type: ignore[import-not-found]
except ModuleNotFoundError as exc:  # pragma: no cover - entorno sin dependencia
    pdfplumber = None  # type: ignore[assignment]
    _PDFPLUMBER_ERROR = exc
else:  # pragma: no cover - import correcto
    _PDFPLUMBER_ERROR = None

from .text_utils import normalize_label, normalize_value, strip_accents


@dataclass
class QualityReportResult:
    """Información relevante extraída de un PDF de control de calidad."""

    path: Path
    identifier: str
    fecha_visita: str = ""
    tipo_equipo: str = ""
    nombre_institucion: str = ""
    warnings: List[str] = field(default_factory=list)

    def set_value(self, key: str, value: str) -> None:
        normalized = normalize_value(value)
        setattr(self, key, normalized)

    def to_dict(self) -> Dict[str, str]:
        return {
            "archivo": self.path.name,
            "ruta": str(self.path),
            "identificador": self.identifier,
            "fecha_visita": self.fecha_visita,
            "tipo_equipo": self.tipo_equipo,
            "nombre_institucion": self.nombre_institucion,
        }


_LABEL_TO_FIELD = {
    "FECHA DE LA VISITA": "fecha_visita",
    "FECHA VISITA": "fecha_visita",
    "FECHA DE VISITA": "fecha_visita",
    "FECHA DE LA EVALUACION": "fecha_visita",
    "FECHA DE LA EVALUACIÓN": "fecha_visita",
    "FECHA DE EVALUACION": "fecha_visita",
    "FECHA DE EVALUACIÓN": "fecha_visita",
    "FECHA EVALUACION": "fecha_visita",
    "FECHA EVALUACIÓN": "fecha_visita",
    "FECHA": "fecha_visita",
    "TIPO DE EQUIPO": "tipo_equipo",
    "TIPO EQUIPO": "tipo_equipo",
    "EQUIPO": "tipo_equipo",
    "NOMBRE DE LA INSTITUCION": "nombre_institucion",
    "NOMBRE DE LA INSTITUCIÓN": "nombre_institucion",
    "NOMBRE INSTITUCION": "nombre_institucion",
    "NOMBRE INSTITUCIÓN": "nombre_institucion",
    "INSTITUCION": "nombre_institucion",
    "INSTITUCIÓN": "nombre_institucion",
}

_NORMALIZED_LABELS = {normalize_label(label): field for label, field in _LABEL_TO_FIELD.items()}

_UPPER_LABELS: List[tuple[str, str, int]] = []
for raw_label, raw_field in _LABEL_TO_FIELD.items():
    normalized_label = strip_accents(raw_label).upper()
    _UPPER_LABELS.append((normalized_label, raw_field, len(normalized_label)))

_REQUIRED_KEYS: Iterable[str] = ("fecha_visita", "tipo_equipo", "nombre_institucion")


def parse_quality_folder(folder: Path) -> List[QualityReportResult]:
    """Analiza todos los PDF de la carpeta y devuelve sus datos relevantes."""

    _ensure_pdfplumber()
    results: List[QualityReportResult] = []
    for pdf_path in sorted(folder.glob("*.pdf")):
        results.append(extract_quality_report(pdf_path))
    return results


def extract_quality_report(path: Path) -> QualityReportResult:
    """Extrae información clave del PDF indicado."""

    _ensure_pdfplumber()
    identifier = _infer_identifier(path)
    result = QualityReportResult(path=path, identifier=identifier)

    try:
        text = _read_pdf_text(path)
    except Exception as exc:  # noqa: BLE001
        result.warnings.append(f"No se pudo leer el PDF: {exc}")
        return result

    if not text.strip():
        result.warnings.append("El PDF no contiene texto extraíble.")
        return result

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    pending_key: str | None = None
    for raw_line in lines:
        pairs = _extract_pairs_from_line(raw_line)
        if pairs:
            for key, value in pairs:
                result.set_value(key, value)
            pending_key = None
            continue

        normalized = normalize_label(raw_line)
        matched_key = _match_label(normalized)
        if matched_key:
            value = _extract_value(raw_line)
            if value:
                result.set_value(matched_key, value)
                pending_key = None
            else:
                pending_key = matched_key
            continue

        if pending_key and _looks_like_value(raw_line):
            result.set_value(pending_key, raw_line)
            pending_key = None

    for key in _REQUIRED_KEYS:
        if not getattr(result, key):
            result.warnings.append(f"Falta el campo {key.replace('_', ' ')}")

    return result


def _infer_identifier(path: Path) -> str:
    stem = path.stem
    prefix = stem.split("_", 1)[0]
    if prefix.isdigit():
        return normalize_value(prefix)
    return ""


def _extract_pairs_from_line(line: str) -> List[tuple[str, str]]:
    """Detecta pares etiqueta-valor dentro de una sola línea de texto."""

    if not line.strip():
        return []

    search_text = strip_accents(line).upper()
    matches = _find_label_matches(search_text)
    if not matches:
        return []

    pairs: List[tuple[str, str]] = []
    for position, (index, label, field) in enumerate(matches):
        value_start = index + len(label)
        value_start = _advance_over_separators(line, value_start)
        next_start = len(line)
        if position + 1 < len(matches):
            next_start = matches[position + 1][0]
        value = line[value_start:next_start].strip(" :.-\t\u2013\u2014")
        if value:
            pairs.append((field, value))
    return pairs


def _find_label_matches(text: str) -> List[tuple[int, str, str]]:
    """Ubica todas las etiquetas conocidas dentro de ``text``."""

    found: List[tuple[int, int, str, str]] = []
    for label, field, length in _UPPER_LABELS:
        start = text.find(label)
        while start != -1:
            if _has_word_boundaries(text, start, length):
                found.append((start, length, label, field))
            start = text.find(label, start + length)

    found.sort(key=lambda item: (item[0], -item[1]))

    filtered: List[tuple[int, str, str]] = []
    last_end = -1
    for start, length, label, field in found:
        if start < last_end:
            continue
        filtered.append((start, label, field))
        last_end = start + length

    return filtered


def _has_word_boundaries(text: str, start: int, length: int) -> bool:
    """Comprueba que la coincidencia esté delimitada por caracteres no alfanuméricos."""

    before = text[start - 1] if start > 0 else " "
    after_index = start + length
    after = text[after_index] if after_index < len(text) else " "
    return not before.isalnum() and not after.isalnum()


def _advance_over_separators(original: str, index: int) -> int:
    """Salta separadores comunes (espacios, dos puntos, guiones)."""

    while index < len(original) and original[index] in {":", " ", "-", "–", "—", "\t", "|", "/"}:
        index += 1
    return index


def _match_label(normalized_line: str) -> str | None:
    for label, field in _NORMALIZED_LABELS.items():
        if normalized_line.startswith(label) or f" {label}" in normalized_line:
            return field
    return None


def _extract_value(line: str) -> str:
    if ":" in line:
        after = line.split(":", 1)[1].strip()
        if after:
            return after
    return ""


def _looks_like_value(line: str) -> bool:
    return any(char.isalnum() for char in line)


def _read_pdf_text(path: Path) -> str:
    _ensure_pdfplumber()
    with pdfplumber.open(path) as pdf:  # type: ignore[union-attr]
        pages_text = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages_text)


def _ensure_pdfplumber() -> None:
    if pdfplumber is None:
        hint = (
            "Instala la dependencia opcional 'pdfplumber' con `pip install pdfplumber` "
            "o `pip install -r requirements.txt` para habilitar el análisis de PDFs."
        )
        raise RuntimeError(f"La funcionalidad de reportes requiere pdfplumber. {hint}") from _PDFPLUMBER_ERROR


def pdf_dependency_status() -> str:
    """Devuelve un mensaje descriptivo si pdfplumber no está disponible."""

    if pdfplumber is not None:
        return ""
    return (
        "La librería opcional 'pdfplumber' no está instalada. "
        "Ejecuta `pip install pdfplumber` o `pip install -r requirements.txt` "
        "para activar la pestaña de reportes de control de calidad."
    )
