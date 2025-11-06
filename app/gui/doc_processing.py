"""Funciones para leer, actualizar y generar documentos de licencia."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from docx import Document
from docx.document import Document as DocumentType
from docx.table import _Cell, _Row
from docx.text.paragraph import Paragraph

from .constants import LABEL_TO_FIELD, CategoriaTipo, PersonaTipo
from .text_utils import apply_bold_text, normalize_label, normalize_value


@dataclass
class DocumentData:
    """Resultado del análisis de un documento fuente."""

    data: Dict[str, str]
    raw_labels: Dict[str, str]
    unmatched: Dict[str, str]
    persona: PersonaTipo | None
    categoria: CategoriaTipo | None


@dataclass
class RowEntry:
    """Representa una fila identificada dentro de una tabla."""

    label: str
    value: str
    label_cell: _Cell
    value_cell: _Cell
    inline: bool = False
    separator: str = ":"


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
    unmatched: Dict[str, str] = {}

    for table in document.tables:
        for row in table.rows:
            for entry in _parse_row_entries(row):
                label_norm = normalize_label(entry.label)
                raw_labels[label_norm] = entry.value
                key = LABEL_TO_FIELD.get(label_norm)
                if key:
                    data[key] = normalize_value(entry.value)
                else:
                    unmatched[entry.label] = entry.value

    persona = PersonaTipo.from_text(data.get("TIPO_SOLICITANTE", ""))
    categoria = CategoriaTipo.from_text(data.get("CATEGORIA", ""))
    if categoria is None:
        categoria = CategoriaTipo.from_text(data.get("TIPO_DE_EQUIPO", ""))

    return DocumentData(
        data=data,
        raw_labels=raw_labels,
        unmatched=unmatched,
        persona=persona,
        categoria=categoria,
    )


def update_source_document(path: Path, updated: Dict[str, str]) -> None:
    """Sobrescribe el documento fuente con los valores corregidos."""

    document = Document(str(path))
    for table in document.tables:
        for row in table.rows:
            for entry in _parse_row_entries(row):
                label_norm = normalize_label(entry.label)
                key = LABEL_TO_FIELD.get(label_norm)
                if not key:
                    continue
                value = updated.get(key)
                if value is None:
                    continue
                if entry.inline:
                    write_inline_cell(
                        entry.value_cell, entry.label, value, entry.separator
                    )
                else:
                    write_cell(entry.value_cell, value)
    document.save(str(path))


def write_cell(cell: _Cell, value: str) -> None:
    """Escribe el valor en una celda asegurando formato en mayúsculas y negrilla."""

    while cell.paragraphs:
        cell._element.remove(cell.paragraphs[0]._p)  # type: ignore[attr-defined]
    paragraph = cell.add_paragraph()
    run = paragraph.add_run()
    apply_bold_text(run, normalize_value(value))


def write_inline_cell(cell: _Cell, label: str, value: str, separator: str) -> None:
    """Actualiza celdas que contienen etiqueta y valor en el mismo bloque."""

    while cell.paragraphs:
        cell._element.remove(cell.paragraphs[0]._p)  # type: ignore[attr-defined]

    normalized_label = normalize_value(label)
    normalized_value = normalize_value(value)

    if separator == "\n":
        label_paragraph = cell.add_paragraph()
        label_run = label_paragraph.add_run(normalized_label)
        label_run.bold = True
        value_paragraph = cell.add_paragraph()
        value_run = value_paragraph.add_run()
        apply_bold_text(value_run, normalized_value)
        return

    paragraph = cell.add_paragraph()
    label_run = paragraph.add_run(normalized_label)
    label_run.bold = True
    separator_run = paragraph.add_run(f"{separator} ")
    separator_run.bold = True
    value_run = paragraph.add_run()
    apply_bold_text(value_run, normalized_value)


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


def _parse_row_entries(row: _Row) -> List[RowEntry]:
    """Descompone una fila en una o varias parejas etiqueta-valor."""

    cells = list(row.cells)
    if not cells:
        return []

    non_empty = [
        (idx, cell.text.strip(), cell)
        for idx, cell in enumerate(cells)
        if cell.text and cell.text.strip()
    ]
    if not non_empty:
        return []

    entries: List[RowEntry] = []
    total = len(non_empty)
    i = 0

    while i < total:
        idx, text, cell = non_empty[i]
        inline = _split_inline_cell(text)
        if inline:
            label_text, value_text, separator = inline
            entries.append(
                RowEntry(
                    label=label_text,
                    value=value_text,
                    label_cell=cell,
                    value_cell=cell,
                    inline=True,
                    separator=separator,
                )
            )
            i += 1
            continue

        label_norm = normalize_label(text)
        if not _looks_like_label(text, label_norm):
            i += 1
            continue

        value_text: Optional[str] = None
        value_cell = cell

        j = i + 1
        while j < total:
            _, candidate_text, candidate_cell = non_empty[j]
            candidate_inline = _split_inline_cell(candidate_text)
            candidate_norm = normalize_label(candidate_text)

            if candidate_inline:
                break

            if _looks_like_label(candidate_text, candidate_norm):
                break

            value_text = candidate_text
            value_cell = candidate_cell
            break

        if value_text:
            entries.append(
                RowEntry(
                    label=text,
                    value=value_text,
                    label_cell=cell,
                    value_cell=value_cell,
                    inline=False,
                    separator=":",
                )
            )
            i = j
        else:
            i += 1

    return entries


_LABEL_HINT_KEYWORDS = (
    "RADIC",
    "FECHA",
    "CATEG",
    "SOLICIT",
    "REPRESENT",
    "NIT",
    "CEDULA",
    "DIREC",
    "MUNIC",
    "SUBREG",
    "SEDE",
    "EQUIPO",
    "MARCA",
    "MODELO",
    "SERIE",
    "TUBO",
    "CONTROL",
    "OPR",
    "OBSERV",
)


def _looks_like_label(text: str, normalized: str) -> bool:
    """Determina si un bloque de texto se comporta como etiqueta."""

    if not text:
        return False

    if normalized in LABEL_TO_FIELD:
        return True

    stripped = text.strip()
    if not stripped:
        return False

    if ":" in stripped:
        return True

    for hint in _LABEL_HINT_KEYWORDS:
        if hint in normalized:
            return True

    return False


def _split_inline_cell(text: str) -> Optional[tuple[str, str, str]]:
    """Divide el contenido de una celda etiqueta:valor en línea."""

    if not text:
        return None
    stripped = text.strip()
    if not stripped:
        return None

    for separator in (":", "-", "–", "—", ";"):
        if separator in stripped:
            left, right = stripped.split(separator, 1)
            label = left.strip()
            value = right.strip()
            if label and value:
                return label, value, separator

    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(lines) >= 2:
        label = lines[0]
        value = " ".join(lines[1:])
        if label and value:
            return label, value, "\n"

    return None
