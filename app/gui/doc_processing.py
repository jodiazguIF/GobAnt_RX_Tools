"""Funciones para leer, actualizar y generar documentos de licencia."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

from docx import Document
from docx.document import Document as DocumentType
from docx.table import _Cell
from docx.text.paragraph import Paragraph

from .constants import LABEL_TO_FIELD, CategoriaTipo, PersonaTipo
from .text_utils import apply_bold_text, normalize_label, normalize_value


@dataclass
class DocumentData:
    """Resultado del análisis de un documento fuente."""

    data: Dict[str, str]
    raw_labels: Dict[str, str]
    persona: PersonaTipo | None
    categoria: CategoriaTipo | None


def iter_paragraphs(doc: DocumentType) -> Iterable[Paragraph]:
    """Itera todos los párrafos del documento, incluyendo los de tablas."""

    for paragraph in doc.paragraphs:
        yield paragraph
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph


def extract_from_docx(path: Path) -> DocumentData:
    """Lee un documento de origen y obtiene los campos relevantes."""

    document = Document(str(path))
    data: Dict[str, str] = {}
    raw_labels: Dict[str, str] = {}

    for table in document.tables:
        for row in table.rows:
            if len(row.cells) < 2:
                continue
            label_raw = row.cells[0].text.strip()
            value_raw = row.cells[1].text.strip()
            if not label_raw:
                continue
            label_norm = normalize_label(label_raw)
            raw_labels[label_norm] = value_raw
            key = LABEL_TO_FIELD.get(label_norm)
            if key:
                data[key] = normalize_value(value_raw)

    persona = PersonaTipo.from_text(data.get("TIPO_SOLICITANTE", ""))
    categoria = CategoriaTipo.from_text(data.get("CATEGORIA", ""))
    if categoria is None:
        categoria = CategoriaTipo.from_text(data.get("TIPO_DE_EQUIPO", ""))

    return DocumentData(data=data, raw_labels=raw_labels, persona=persona, categoria=categoria)


def update_source_document(path: Path, updated: Dict[str, str]) -> None:
    """Sobrescribe el documento fuente con los valores corregidos."""

    document = Document(str(path))
    for table in document.tables:
        for row in table.rows:
            if len(row.cells) < 2:
                continue
            label_norm = normalize_label(row.cells[0].text)
            key = LABEL_TO_FIELD.get(label_norm)
            if not key:
                continue
            value = updated.get(key)
            if value is None:
                continue
            write_cell(row.cells[1], value)
    document.save(str(path))


def write_cell(cell: _Cell, value: str) -> None:
    """Escribe el valor en una celda asegurando formato en mayúsculas y negrilla."""

    while cell.paragraphs:
        cell._element.remove(cell.paragraphs[0]._p)  # type: ignore[attr-defined]
    paragraph = cell.add_paragraph()
    run = paragraph.add_run()
    apply_bold_text(run, normalize_value(value))


def replace_placeholders(document: DocumentType, data: Dict[str, str]) -> None:
    """Reemplaza cada marcador `{{CLAVE}}` por su valor correspondiente."""

    placeholders = {f"{{{{{key}}}}}": normalize_value(value) for key, value in data.items() if value}
    for paragraph in iter_paragraphs(document):
        replace_in_paragraph(paragraph, placeholders)


def replace_in_paragraph(paragraph: Paragraph, placeholders: Dict[str, str]) -> None:
    """Reemplaza marcadores dentro de un párrafo conservando formato."""

    if not placeholders:
        return
    text = paragraph.text
    matches = [token for token in placeholders if token in text]
    if not matches:
        return
    for run in paragraph.runs:
        for token in matches:
            if token in run.text:
                run.text = run.text.replace(token, placeholders[token])
                run.bold = True


def generate_from_template(template_path: Path, output_path: Path, data: Dict[str, str]) -> Path:
    """Crea un documento a partir de la plantilla y lo guarda."""

    document = Document(str(template_path))
    replace_placeholders(document, data)
    document.save(str(output_path))
    return output_path


def build_output_name(source_file: Path, radicado: str) -> str:
    """Genera el nombre final del archivo de licencia."""

    base = source_file.stem
    parts = base.split("_")
    if len(parts) >= 3:
        parts[-1] = "LICENCIA"
        new_name = "_".join(parts)
    else:
        new_name = f"{base}_LICENCIA"
    return f"{normalize_value(radicado)}_{new_name.split('_', 1)[-1]}"
