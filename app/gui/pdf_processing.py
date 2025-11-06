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

from .text_utils import normalize_label, normalize_value


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
    "FECHA": "fecha_visita",
    "TIPO DE EQUIPO": "tipo_equipo",
    "EQUIPO": "tipo_equipo",
    "TIPO EQUIPO": "tipo_equipo",
    "NOMBRE DE LA INSTITUCION": "nombre_institucion",
    "NOMBRE DE LA INSTITUCIÓN": "nombre_institucion",
    "NOMBRE INSTITUCION": "nombre_institucion",
    "NOMBRE INSTITUCIÓN": "nombre_institucion",
    "INSTITUCION": "nombre_institucion",
    "INSTITUCIÓN": "nombre_institucion",
}

_NORMALIZED_LABELS = {normalize_label(label): field for label, field in _LABEL_TO_FIELD.items()}

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
