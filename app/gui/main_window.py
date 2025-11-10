"""Ventana principal de la aplicación gráfica."""
from __future__ import annotations

from collections import Counter
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import settings
from app.pipeline.ingest import IngestPipeline
from .config_store import GuiConfig, load_config, save_config
from .constants import (
    CategoriaTipo,
    EQUIPMENT_FIELD_KEYS,
    FIELDS,
    HIDDEN_KEYS,
    PersonaTipo,
)
from .doc_processing import (
    build_output_name,
    extract_from_docx,
    generate_from_template,
    update_source_document,
)
from .text_utils import format_today_date, normalize_value, split_resolution_date
from .workers import Worker
from .pdf_processing import (
    QualityReportResult,
    parse_quality_folder,
    pdf_dependency_status,
)


class LicenseGeneratorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GobAnt RX Tools - Licencias")
        self.resize(1100, 720)

        self.config: GuiConfig = load_config()
        self.thread_pool = QThreadPool()

        self.source_path: Optional[Path] = None
        self.field_inputs: Dict[str, QWidget] = {}
        self.current_data: Dict[str, str] = {field.key: "" for field in FIELDS}
        for key in HIDDEN_KEYS:
            self.current_data[key] = ""
        self.equipment_entries: List[Dict[str, str]] = []
        self.current_equipment_index: Optional[int] = None
        self.equipment_combo: Optional[QComboBox] = None
        self.equipment_count_label: Optional[QLabel] = None
        self.remove_equipment_button: Optional[QPushButton] = None
        self._loading_equipment = False
        self.pipeline: Optional[IngestPipeline] = None
        self.license_log: Optional[QPlainTextEdit] = None
        self.pipeline_log: Optional[QPlainTextEdit] = None
        self.qc_log: Optional[QPlainTextEdit] = None

        self.qc_table: Optional[QTableWidget] = None
        self.qc_folder_label: Optional[QLabel] = None

        self.qc_folder: Optional[Path] = None
        self.qc_results: List[QualityReportResult] = []

        self._init_ui()
        self._initialize_equipment_state()
        self._ensure_today_field()

    # ------------------------------------------------------------------ UI
    def _init_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_license_tab(), "Generación de licencias")
        tabs.addTab(self._build_qc_tab(), "Reportes control de calidad")
        tabs.addTab(self._build_pipeline_tab(), "Carga automática (Drive/Sheets)")
        self.setCentralWidget(tabs)

    def _build_license_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        layout.addWidget(self._build_file_section())
        layout.addWidget(self._build_templates_section())
        layout.addWidget(self._build_equipment_section())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        container_layout = QVBoxLayout(form_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        general_fields = [field for field in FIELDS if field.key not in EQUIPMENT_FIELD_KEYS]
        equipment_fields = [field for field in FIELDS if field.key in EQUIPMENT_FIELD_KEYS]

        general_box = QGroupBox("Datos generales del trámite")
        general_layout = QFormLayout(general_box)
        general_layout.setLabelAlignment(Qt.AlignRight)  # type: ignore[name-defined]
        for field in general_fields:
            input_widget = self._create_input_for_field(field.key, field.multiline)
            self.field_inputs[field.key] = input_widget
            label = QLabel(field.label + (" *" if field.required else ""))
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            general_layout.addRow(label, input_widget)

        equipment_box = QGroupBox("Datos del equipo seleccionado")
        equipment_layout = QFormLayout(equipment_box)
        equipment_layout.setLabelAlignment(Qt.AlignRight)  # type: ignore[name-defined]
        for field in equipment_fields:
            input_widget = self._create_input_for_field(field.key, field.multiline)
            self.field_inputs[field.key] = input_widget
            label = QLabel(field.label + (" *" if field.required else ""))
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            equipment_layout.addRow(label, input_widget)

        container_layout.addWidget(general_box)
        container_layout.addWidget(equipment_box)
        container_layout.addStretch(1)

        scroll.setWidget(form_container)
        layout.addWidget(scroll)

        layout.addWidget(self._build_actions_section())
        layout.addWidget(self._build_log_section("license_log", "Bitácora"))
        return container

    def _build_qc_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        layout.addWidget(self._build_qc_folder_section())
        layout.addWidget(self._build_qc_actions_section())
        layout.addWidget(self._build_qc_table())
        layout.addWidget(self._build_log_section("qc_log", "Bitácora"))
        return container

    def _build_file_section(self) -> QGroupBox:
        box = QGroupBox("Documento origen")
        layout = QHBoxLayout(box)
        self.source_label = QLabel("Sin archivo cargado")
        layout.addWidget(self.source_label, stretch=1)

        load_button = QPushButton("Cargar documento .docx")
        load_button.clicked.connect(self.load_source_document)
        layout.addWidget(load_button)

        clear_button = QPushButton("Ingresar datos manualmente")
        clear_button.clicked.connect(self.clear_form)
        layout.addWidget(clear_button)

        return box

    def _build_qc_folder_section(self) -> QGroupBox:
        box = QGroupBox("Carpeta de controles de calidad")
        layout = QHBoxLayout(box)
        self.qc_folder_label = QLabel("Sin carpeta seleccionada")
        layout.addWidget(self.qc_folder_label, stretch=1)

        select_btn = QPushButton("Seleccionar carpeta…")
        select_btn.clicked.connect(self.select_qc_folder)
        layout.addWidget(select_btn)

        return box

    def _build_qc_actions_section(self) -> QGroupBox:
        box = QGroupBox("Acciones")
        layout = QHBoxLayout(box)

        analyze_btn = QPushButton("Analizar PDFs")
        analyze_btn.clicked.connect(self.analyze_qc_reports)
        layout.addWidget(analyze_btn)

        export_btn = QPushButton("Exportar JSON")
        export_btn.clicked.connect(self.export_qc_json)
        layout.addWidget(export_btn)

        layout.addStretch(1)
        return box

    def _build_qc_table(self) -> QGroupBox:
        box = QGroupBox("Resultados")
        layout = QVBoxLayout(box)
        self.qc_table = QTableWidget(0, 5)
        self.qc_table.setHorizontalHeaderLabels(
            [
                "Archivo",
                "Identificador",
                "Fecha de evaluación",
                "Tipo de equipo",
                "Nombre de la institución",
            ]
        )
        header = self.qc_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.qc_table)
        return box

    def select_qc_folder(self) -> None:
        start_dir = self.config.last_qc_dir or str(Path.home())
        directory = QFileDialog.getExistingDirectory(
            self,
            "Selecciona la carpeta con PDFs",
            start_dir,
        )
        if not directory:
            return
        self.qc_folder = Path(directory)
        self.config.last_qc_dir = str(self.qc_folder)
        save_config(self.config)
        if self.qc_folder_label:
            self.qc_folder_label.setText(str(self.qc_folder))
        self.log_qc(f"Carpeta seleccionada: {self.qc_folder}")

    def analyze_qc_reports(self) -> None:
        missing_dep = pdf_dependency_status()
        if missing_dep:
            QMessageBox.warning(self, "Dependencia faltante", missing_dep)
            return
        if not self.qc_folder:
            QMessageBox.warning(self, "Sin carpeta", "Selecciona primero una carpeta con PDFs.")
            return
        self.log_qc("Analizando archivos PDF…")
        worker = Worker(parse_quality_folder, self.qc_folder)
        worker.signals.finished.connect(self._on_qc_analysis_finished)
        worker.signals.error.connect(lambda exc: self._show_worker_error("control de calidad", exc))
        self.thread_pool.start(worker)

    def _on_qc_analysis_finished(self, results: List[QualityReportResult]) -> None:
        self.qc_results = results
        self._populate_qc_table(results)
        self.log_qc(f"Se analizaron {len(results)} archivo(s).")
        for result in results:
            for warning in result.warnings:
                self.log_qc(f"{result.path.name}: {warning}")

    def _populate_qc_table(self, results: List[QualityReportResult]) -> None:
        if not self.qc_table:
            return
        self.qc_table.setRowCount(0)
        for result in results:
            row = self.qc_table.rowCount()
            self.qc_table.insertRow(row)
            values = [
                result.path.name,
                result.identifier,
                result.fecha_evaluacion,
                result.tipo_equipo,
                result.nombre_institucion,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.qc_table.setItem(row, column, item)

    def export_qc_json(self) -> None:
        if not self.qc_results:
            QMessageBox.information(self, "Sin datos", "Analiza primero una carpeta con PDFs.")
            return
        start_dir = self.config.last_qc_export_dir or (
            str(self.qc_folder) if self.qc_folder else str(Path.home())
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar resultados como JSON",
            str(Path(start_dir) / "control_calidad.json"),
            "Archivos JSON (*.json)",
        )
        if not file_path:
            return
        output_path = Path(file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = [result.to_dict() for result in self.qc_results]
        try:
            import json

            with output_path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo guardar el JSON: {exc}")
            self.log_qc(f"Error al guardar JSON: {exc}")
            return

        self.config.last_qc_export_dir = str(output_path.parent)
        save_config(self.config)
        self.log_qc(f"Resultados guardados en {output_path}")

    def _build_templates_section(self) -> QGroupBox:
        box = QGroupBox("Plantillas de licencia")
        layout = QFormLayout(box)

        self.template_inputs: Dict[str, QLineEdit] = {}
        mapping = {
            "Natural - Categoría I": "natural_cat1",
            "Natural - Categoría II": "natural_cat2",
            "Jurídica - Categoría I": "juridica_cat1",
            "Jurídica - Categoría II": "juridica_cat2",
        }
        for label_text, attr in mapping.items():
            path_edit = QLineEdit(getattr(self.config.templates, attr))
            path_edit.setPlaceholderText("Ruta de la plantilla (.docx)")
            browse_btn = QPushButton("Seleccionar…")
            browse_btn.clicked.connect(lambda _, a=attr: self._select_template_path(a))
            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.addWidget(path_edit)
            h_layout.addWidget(browse_btn)
            layout.addRow(label_text, container)
            self.template_inputs[attr] = path_edit
        save_btn = QPushButton("Guardar rutas de plantillas")
        save_btn.clicked.connect(self.save_template_paths)
        layout.addRow(save_btn)
        return box

    def _build_equipment_section(self) -> QGroupBox:
        box = QGroupBox("Equipos a licenciar")
        layout = QHBoxLayout(box)

        self.equipment_count_label = QLabel("Equipos detectados: 0")
        layout.addWidget(self.equipment_count_label)

        self.equipment_combo = QComboBox()
        self.equipment_combo.currentIndexChanged.connect(self._on_equipment_changed)
        layout.addWidget(QLabel("Equipo en edición:"))
        layout.addWidget(self.equipment_combo)

        add_btn = QPushButton("Agregar equipo")
        add_btn.clicked.connect(self.add_equipment_entry)
        layout.addWidget(add_btn)

        remove_btn = QPushButton("Eliminar equipo")
        remove_btn.clicked.connect(self.remove_equipment_entry)
        self.remove_equipment_button = remove_btn
        layout.addWidget(remove_btn)

        layout.addStretch(1)
        return box

    def _build_actions_section(self) -> QGroupBox:
        box = QGroupBox("Generación")
        layout = QHBoxLayout(box)

        self.chk_update_source = QCheckBox("Actualizar documento origen")
        self.chk_update_source.setChecked(True)
        layout.addWidget(self.chk_update_source)

        self.chk_upload_drive = QCheckBox("Subir licencia a Drive y ejecutar pipeline")
        layout.addWidget(self.chk_upload_drive)

        self.chk_resolution_paragraph = QCheckBox(
            "Incluir párrafo que deja sin efecto una resolución previa"
        )
        layout.addWidget(self.chk_resolution_paragraph)

        layout.addStretch(1)

        generate_button = QPushButton("Generar licencia")
        generate_button.clicked.connect(self.generate_license)
        layout.addWidget(generate_button)

        return box

    def _build_log_section(self, attr_name: str, title: str) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        widget = QPlainTextEdit()
        widget.setReadOnly(True)
        layout.addWidget(widget)
        setattr(self, attr_name, widget)
        return box

    def _build_pipeline_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        description = QLabel(
            "Ejecuta las tareas de carga automática sobre la carpeta configurada en settings."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        btn_all = QPushButton("Procesar todos")
        btn_all.clicked.connect(lambda: self.run_pipeline_task("process_folder"))
        buttons_layout.addWidget(btn_all)

        btn_new = QPushButton("Solo nuevos")
        btn_new.clicked.connect(lambda: self.run_pipeline_task("process_folder_only_new"))
        buttons_layout.addWidget(btn_new)

        btn_pending = QPushButton("Solo pendientes")
        btn_pending.clicked.connect(lambda: self.run_pipeline_task("process_folder_only_pending"))
        buttons_layout.addWidget(btn_pending)

        layout.addWidget(buttons_container)
        layout.addWidget(self._build_log_section("pipeline_log", "Bitácora"))
        return container

    # ------------------------------------------------------------------ Helpers
    def _create_input_for_field(self, key: str, multiline: bool) -> QWidget:
        if key == "TIPO_SOLICITANTE":
            combo = QComboBox()
            combo.addItem("")
            combo.addItem(PersonaTipo.NATURAL.value)
            combo.addItem(PersonaTipo.JURIDICA.value)
            combo.currentTextChanged.connect(lambda value, k=key: self._set_field(k, value))
            return combo
        if multiline:
            text_edit = QTextEdit()
            text_edit.textChanged.connect(lambda k=key, widget=text_edit: self._set_field(k, widget.toPlainText()))
            return text_edit
        line_edit = QLineEdit()
        line_edit.editingFinished.connect(lambda k=key, widget=line_edit: self._set_field(k, widget.text()))
        return line_edit

    def _set_field(self, key: str, value: str) -> None:
        normalized = normalize_value(value)
        self.current_data[key] = normalized
        if key in EQUIPMENT_FIELD_KEYS:
            self._update_equipment_entry_field(key, normalized)
        widget = self.field_inputs.get(key)
        if isinstance(widget, QLineEdit) and widget.text() != normalized:
            widget.blockSignals(True)
            widget.setText(normalized)
            widget.blockSignals(False)
        elif isinstance(widget, QTextEdit) and widget.toPlainText() != normalized:
            widget.blockSignals(True)
            widget.setPlainText(normalized)
            widget.blockSignals(False)
        elif isinstance(widget, QComboBox):
            if normalized and widget.currentText() != normalized:
                index = widget.findText(normalized)
                if index != -1:
                    widget.blockSignals(True)
                    widget.setCurrentIndex(index)
                    widget.blockSignals(False)
            elif not normalized and widget.currentIndex() != 0:
                widget.blockSignals(True)
                widget.setCurrentIndex(0)
                widget.blockSignals(False)

        if key == "FECHA_RESOLUCION":
            if normalized:
                self._fill_resolution_components(normalized)
            else:
                self._clear_resolution_components()
        if key == "FECHA_HOY" and not normalized:
            self._ensure_today_field(force=True)

    def _update_equipment_entry_field(self, key: str, value: str) -> None:
        if self._loading_equipment:
            return
        index = self.current_equipment_index
        if index is None:
            return
        if not (0 <= index < len(self.equipment_entries)):
            return
        self.equipment_entries[index][key] = value

    def _initialize_equipment_state(
        self, entries: Optional[List[Dict[str, str]]] = None
    ) -> None:
        normalized: List[Dict[str, str]] = []
        if entries:
            for entry in entries:
                normalized_entry = self._normalize_equipment_entry(entry)
                if any(normalized_entry.values()):
                    normalized.append(normalized_entry)
        if not normalized:
            normalized = [self._blank_equipment_entry()]
        self.equipment_entries = normalized
        self.current_equipment_index = 0
        self._load_equipment_into_form(0)
        self._refresh_equipment_combo()
        self._update_equipment_count_label()

    def _blank_equipment_entry(self) -> Dict[str, str]:
        return {key: "" for key in EQUIPMENT_FIELD_KEYS}

    def _normalize_equipment_entry(self, entry: Dict[str, str]) -> Dict[str, str]:
        return {key: normalize_value(entry.get(key, "")) for key in EQUIPMENT_FIELD_KEYS}

    def _refresh_equipment_combo(self) -> None:
        if not self.equipment_combo:
            return
        self.equipment_combo.blockSignals(True)
        self.equipment_combo.clear()
        for idx in range(len(self.equipment_entries)):
            self.equipment_combo.addItem(f"Equipo {idx + 1}")
        if self.current_equipment_index is not None and self.equipment_entries:
            self.equipment_combo.setCurrentIndex(self.current_equipment_index)
        self.equipment_combo.blockSignals(False)

    def _update_equipment_count_label(self) -> None:
        if self.equipment_count_label:
            self.equipment_count_label.setText(
                f"Equipos detectados: {len(self.equipment_entries)}"
            )
        if self.remove_equipment_button:
            self.remove_equipment_button.setEnabled(len(self.equipment_entries) > 1)

    def _load_equipment_into_form(self, index: int) -> None:
        if not self.equipment_entries:
            self.current_equipment_index = None
            return
        index = max(0, min(index, len(self.equipment_entries) - 1))
        entry = self.equipment_entries[index]
        self._loading_equipment = True
        for key in EQUIPMENT_FIELD_KEYS:
            self._set_field(key, entry.get(key, ""))
        self._loading_equipment = False
        self.current_equipment_index = index

    def _sync_form_to_equipment(self, index: Optional[int]) -> None:
        if index is None:
            return
        if not (0 <= index < len(self.equipment_entries)):
            return
        entry = self.equipment_entries[index]
        for key in EQUIPMENT_FIELD_KEYS:
            entry[key] = self.current_data.get(key, "")

    def _on_equipment_changed(self, index: int) -> None:
        if index < 0 or index >= len(self.equipment_entries):
            return
        if self.current_equipment_index == index:
            return
        self._sync_form_to_equipment(self.current_equipment_index)
        self._load_equipment_into_form(index)
        self._refresh_equipment_combo()

    def add_equipment_entry(self) -> None:
        self._sync_form_to_equipment(self.current_equipment_index)
        self.equipment_entries.append(self._blank_equipment_entry())
        self._load_equipment_into_form(len(self.equipment_entries) - 1)
        self._refresh_equipment_combo()
        self._update_equipment_count_label()
        self.log(
            f"Se agregó el equipo {self.current_equipment_index + 1}."
        )

    def remove_equipment_entry(self) -> None:
        if len(self.equipment_entries) <= 1:
            return
        current = self.current_equipment_index or 0
        self._sync_form_to_equipment(current)
        self.equipment_entries.pop(current)
        next_index = current
        if next_index >= len(self.equipment_entries):
            next_index = len(self.equipment_entries) - 1
        self._load_equipment_into_form(next_index)
        self._refresh_equipment_combo()
        self._update_equipment_count_label()
        self.log(f"Se eliminó el equipo {current + 1}.")

    def clear_form(self, _checked: bool = False, *, log_message: bool = True) -> None:
        self.source_path = None
        self.source_label.setText("Ingreso manual de datos")
        for key in self.current_data:
            self.current_data[key] = ""
        for widget in self.field_inputs.values():
            if isinstance(widget, QLineEdit):
                widget.blockSignals(True)
                widget.clear()
                widget.blockSignals(False)
            elif isinstance(widget, QTextEdit):
                widget.blockSignals(True)
                widget.clear()
                widget.blockSignals(False)
            elif isinstance(widget, QComboBox):
                widget.blockSignals(True)
                widget.setCurrentIndex(0)
                widget.blockSignals(False)
        self.chk_resolution_paragraph.setChecked(False)
        self._initialize_equipment_state()
        self._ensure_today_field(force=True)
        if log_message:
            self.log("Formulario limpio. Puedes ingresar valores manualmente.")

    def _fill_resolution_components(self, date_text: str) -> None:
        parts = split_resolution_date(date_text)
        if not parts:
            return
        day, month_name, year = parts
        self._set_field("DIA_EMISION", day)
        self._set_field("MES_EMISION", month_name)
        self._set_field("ANO_EMISION", year)

    def _clear_resolution_components(self) -> None:
        for key in ("DIA_EMISION", "MES_EMISION", "ANO_EMISION"):
            if self.current_data.get(key):
                self._set_field(key, "")

    def _collect_resolution_fields(
        self,
        base: Dict[str, str],
        entry: Optional[Dict[str, str]] = None,
        *,
        prefer_entry: bool = False,
    ) -> tuple[bool, Dict[str, str]]:
        """Combina los datos de resolución generales con los de un equipo."""

        fields: Dict[str, str] = {}
        for key in ("RESOLUCION", "FECHA_RESOLUCION", "DIA_EMISION", "MES_EMISION", "ANO_EMISION"):
            value = base.get(key, "")
            if value:
                fields[key] = value

        if entry:
            entry_resolution = (
                entry.get("RESOLUCION")
                or entry.get("RESOLUCION_EQUIPO", "")
            )
            entry_date = (
                entry.get("FECHA_RESOLUCION")
                or entry.get("FECHA_RESOLUCION_EQUIPO", "")
            )

            if prefer_entry:
                if entry_resolution:
                    fields["RESOLUCION"] = entry_resolution
                if entry_date:
                    fields["FECHA_RESOLUCION"] = entry_date
                    for component in ("DIA_EMISION", "MES_EMISION", "ANO_EMISION"):
                        fields.pop(component, None)
                for component in ("DIA_EMISION", "MES_EMISION", "ANO_EMISION"):
                    component_value = entry.get(component, "")
                    if component_value:
                        fields[component] = component_value
            else:
                if entry_resolution and not fields.get("RESOLUCION"):
                    fields["RESOLUCION"] = entry_resolution
                if entry_date and not fields.get("FECHA_RESOLUCION"):
                    fields["FECHA_RESOLUCION"] = entry_date
                for component in ("DIA_EMISION", "MES_EMISION", "ANO_EMISION"):
                    if fields.get(component):
                        continue
                    component_value = entry.get(component, "")
                    if component_value:
                        fields[component] = component_value

        date_value = fields.get("FECHA_RESOLUCION")
        if date_value:
            parts = split_resolution_date(date_value)
            if parts:
                day, month_name, year = parts
                fields.setdefault("DIA_EMISION", normalize_value(day))
                fields.setdefault("MES_EMISION", normalize_value(month_name))
                fields.setdefault("ANO_EMISION", normalize_value(year))

        complete = all(
            fields.get(key)
            for key in ("RESOLUCION", "DIA_EMISION", "MES_EMISION", "ANO_EMISION")
        )
        return complete, fields

    def load_source_document(self) -> None:
        start_dir = self.config.last_open_dir or str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona el documento de origen",
            start_dir,
            "Documentos Word (*.docx)",
        )
        if not file_path:
            return
        path = Path(file_path)
        self.config.last_open_dir = str(path.parent)
        save_config(self.config)
        try:
            document_data = extract_from_docx(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error al leer", str(exc))
            return
        self.clear_form(log_message=False)
        self.source_path = path
        self.source_label.setText(str(path))
        for key, value in document_data.data.items():
            if key in EQUIPMENT_FIELD_KEYS:
                continue
            self._set_field(key, value)
        if document_data.persona:
            self._set_field("TIPO_SOLICITANTE", document_data.persona.value)
        if document_data.categoria:
            self._set_field("CATEGORIA", document_data.categoria.value)
        self._initialize_equipment_state(document_data.equipment)
        self._ensure_today_field()
        self.log(f"Se cargó el documento {path.name}.")
        self.log(
            f"Equipos detectados: {len(self.equipment_entries)}."
        )
        if document_data.unmatched:
            etiquetas = ", ".join(sorted(document_data.unmatched.keys()))
            self.log(
                "Etiquetas sin mapeo automático: " + etiquetas + ". Revisa y completa manualmente."
            )

    def _select_template_path(self, attr: str) -> None:
        start_dir = str(Path(self.template_inputs[attr].text()).parent) if self.template_inputs[attr].text() else (self.config.last_save_dir or str(Path.home()))
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona la plantilla",
            start_dir,
            "Documentos Word (*.docx)",
        )
        if not file_path:
            return
        self.template_inputs[attr].setText(file_path)

    def save_template_paths(self) -> None:
        for attr, widget in self.template_inputs.items():
            setattr(self.config.templates, attr, widget.text())
        save_config(self.config)
        self.log("Rutas de plantillas guardadas.")

    def generate_license(self) -> None:
        try:
            self._generate_license_impl()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", str(exc))
            self.log("Error: " + str(exc))
            traceback.print_exc()

    def _generate_license_impl(self) -> None:
        missing = [field.label for field in FIELDS if field.required and not self.current_data.get(field.key)]
        if missing:
            raise ValueError("Faltan datos obligatorios: " + ", ".join(missing))

        self._ensure_today_field(force=True)
        self._sync_form_to_equipment(self.current_equipment_index)

        persona = PersonaTipo.from_text(self.current_data.get("TIPO_SOLICITANTE", ""))

        def resolve_category(*texts: str) -> CategoriaTipo | None:
            for text in texts:
                if not text:
                    continue
                category = CategoriaTipo.from_text(text)
                if category:
                    return category
            return None

        normalized_equipment = [
            self._normalize_equipment_entry(entry)
            for entry in self.equipment_entries
        ]
        if normalized_equipment:
            self.equipment_entries = normalized_equipment

        primary_radicado = self.current_data.get("RADICADO", "")
        if normalized_equipment and not primary_radicado:
            first_entry = normalized_equipment[0]
            primary_radicado = (
                first_entry.get("RADICADO")
                or first_entry.get("RADICADO_EQUIPO")
                or ""
            )
            if primary_radicado:
                self.current_data["RADICADO"] = primary_radicado

        categoria = resolve_category(
            self.current_data.get("CATEGORIA", ""),
            self.current_data.get("TIPO_DE_EQUIPO", ""),
            self.current_data.get("PRACTICA", ""),
        )
        if not categoria and normalized_equipment:
            first_entry = normalized_equipment[0]
            categoria = resolve_category(
                first_entry.get("CATEGORIA_EQUIPO", ""),
                first_entry.get("TIPO_DE_EQUIPO", ""),
                first_entry.get("PRACTICA", ""),
            )
        if not persona:
            raise ValueError("Define si es PERSONA NATURAL o PERSONA JURIDICA.")
        if not categoria:
            raise ValueError("Selecciona si es CATEGORIA 1 o CATEGORIA 2.")

        self.current_data["CATEGORIA"] = categoria.value

        radicado = primary_radicado or self.current_data.get("RADICADO", "")
        if not radicado:
            raise ValueError("El campo Radicado es obligatorio para nombrar el archivo.")

        if self.source_path:
            output_dir = self.source_path.parent
            source_stub = self.source_path
        else:
            directory = QFileDialog.getExistingDirectory(
                self,
                "Selecciona la carpeta destino",
                self.config.last_save_dir or str(Path.home()),
            )
            if not directory:
                return
            output_dir = Path(directory)
            self.config.last_save_dir = str(output_dir)
            save_config(self.config)
            solicitante = self.current_data.get("NOMBRE_SOLICITANTE", "SOLICITANTE") or "SOLICITANTE"
            source_stub = output_dir / f"{radicado}_{solicitante.replace(' ', '_')}_CHECKLIST.docx"

        include_resolution_flag = self.chk_resolution_paragraph.isChecked()

        def resolve_template_path(category: CategoriaTipo) -> Path:
            template_path_str = self.config.templates.resolve_path(persona, category)
            if not template_path_str:
                raise ValueError(
                    f"Configura la plantilla para {persona.value} / {category.value} en la sección de plantillas."
                )
            template_path = Path(template_path_str)
            if not template_path.exists():
                raise FileNotFoundError(f"No se encontró la plantilla {template_path}")
            return template_path

        equipment_categories = [
            resolve_category(
                entry.get("CATEGORIA_EQUIPO", ""),
                entry.get("TIPO_DE_EQUIPO", ""),
                entry.get("PRACTICA", ""),
                categoria.value if categoria else "",
            )
            for entry in normalized_equipment
        ]
        equipment_radicados = []
        for entry in normalized_equipment:
            equipment_rad = (
                entry.get("RADICADO_EQUIPO")
                or entry.get("RADICADO")
                or radicado
            )
            if equipment_rad:
                entry.setdefault("RADICADO_EQUIPO", equipment_rad)
            equipment_radicados.append(equipment_rad)

        unique_radicados = {rad for rad in equipment_radicados if rad}
        should_split = len(normalized_equipment) > 1 and len(unique_radicados) > 1

        category_set = {cat.value for cat in equipment_categories if cat}
        if (
            not should_split
            and len(normalized_equipment) > 1
            and len(category_set) > 1
        ):
            self.log(
                "Se detectaron equipos con categorías distintas pero el mismo radicado; se generará una única licencia."
            )

        output_paths: List[Path] = []

        if not normalized_equipment:
            normalized_equipment = [self._blank_equipment_entry()]
            self.equipment_entries = normalized_equipment

        if should_split:
            radicado_counter = Counter(rad for rad in equipment_radicados if rad)
            for index, entry in enumerate(normalized_equipment, start=1):
                entry_category = equipment_categories[index - 1] or categoria
                if not entry_category:
                    raise ValueError(f"No se pudo determinar la categoría del equipo {index}.")
                entry_radicado = equipment_radicados[index - 1] or radicado
                if not entry_radicado:
                    raise ValueError(
                        "Define el radicado del equipo en el campo 'Radicado del equipo'."
                    )

                entry_data = dict(self.current_data)
                entry_data["CATEGORIA"] = entry_category.value
                entry_data["RADICADO"] = entry_radicado
                entry_data["RADICADO_EQUIPO"] = entry_radicado
                if entry.get("CATEGORIA_EQUIPO"):
                    entry_data["CATEGORIA_EQUIPO"] = entry.get("CATEGORIA_EQUIPO", "")
                else:
                    entry_data["CATEGORIA_EQUIPO"] = entry_category.value
                for key in EQUIPMENT_FIELD_KEYS:
                    entry_data[key] = entry.get(key, "")
                if entry_data.get("RESOLUCION") and not entry_data.get("RESOLUCION_EQUIPO"):
                    entry_data["RESOLUCION_EQUIPO"] = entry_data["RESOLUCION"]
                if entry_data.get("FECHA_RESOLUCION") and not entry_data.get("FECHA_RESOLUCION_EQUIPO"):
                    entry_data["FECHA_RESOLUCION_EQUIPO"] = entry_data["FECHA_RESOLUCION"]

                template_path = resolve_template_path(entry_category)
                suffix = None
                if radicado_counter.get(entry_radicado, 0) > 1:
                    suffix = f"EQ{index}"
                output_name = build_output_name(source_stub, entry_radicado, suffix=suffix)
                output_path = output_dir / f"{output_name}.docx"

                complete_resolution, resolution_payload = self._collect_resolution_fields(
                    self.current_data,
                    entry,
                    prefer_entry=True,
                )
                entry_data.update(resolution_payload)
                include_resolution = include_resolution_flag and complete_resolution
                if include_resolution_flag and not complete_resolution:
                    self.log(
                        "Equipo"
                        f" {index}: faltan datos de resolución, se omitirá el párrafo que deja sin efecto la resolución previa."
                    )

                generate_from_template(
                    template_path,
                    output_path,
                    entry_data,
                    equipment_entries=[entry],
                    include_resolution_paragraph=include_resolution,
                )
                output_paths.append(output_path)
                self.log(f"Se generó la licencia del equipo {index} en {output_path}.")
        else:
            template_path = resolve_template_path(categoria)
            generation_data = dict(self.current_data)
            generation_data["CATEGORIA"] = categoria.value
            if normalized_equipment:
                first_equipment = normalized_equipment[0]
                for key in EQUIPMENT_FIELD_KEYS:
                    generation_data[key] = first_equipment.get(key, "")
                if (
                    generation_data.get("RESOLUCION")
                    and not generation_data.get("RESOLUCION_EQUIPO")
                ):
                    generation_data["RESOLUCION_EQUIPO"] = generation_data["RESOLUCION"]
                if (
                    generation_data.get("FECHA_RESOLUCION")
                    and not generation_data.get("FECHA_RESOLUCION_EQUIPO")
                ):
                    generation_data["FECHA_RESOLUCION_EQUIPO"] = generation_data["FECHA_RESOLUCION"]

            output_name = build_output_name(source_stub, radicado)
            output_path = output_dir / f"{output_name}.docx"
            reference_entry = normalized_equipment[0] if normalized_equipment else None
            complete_resolution, resolution_payload = self._collect_resolution_fields(
                self.current_data,
                reference_entry,
            )
            generation_data.update(resolution_payload)
            include_resolution = include_resolution_flag and complete_resolution
            if include_resolution_flag and not complete_resolution:
                self.log(
                    "Faltan datos de resolución, se omitirá el párrafo que deja sin efecto la resolución previa."
                )

            generate_from_template(
                template_path,
                output_path,
                generation_data,
                equipment_entries=normalized_equipment,
                include_resolution_paragraph=include_resolution,
            )
            output_paths.append(output_path)
            self.log(f"Se generó la licencia en {output_path}.")

        if len(output_paths) > 1:
            self.log(
                f"Se generaron {len(output_paths)} licencias (una por equipo detectado)."
            )

        if self.chk_update_source.isChecked() and self.source_path:
            update_source_document(self.source_path, self.current_data)
            self.log("Documento origen actualizado con los nuevos valores.")

        if self.chk_upload_drive.isChecked():
            self.log("Subiendo a Drive y ejecutando pipeline…")
            worker = Worker(self._upload_and_process, output_paths)
            worker.signals.finished.connect(lambda _: self.log("Proceso en Drive completado."))
            worker.signals.error.connect(lambda exc: self._show_worker_error("Drive", exc))
            self.thread_pool.start(worker)

    def _upload_and_process(self, paths: Sequence[Path] | Path) -> None:
        pipeline = self._ensure_pipeline()
        if isinstance(paths, Path):
            path_list = [paths]
        else:
            path_list = list(paths)
        for doc_path in path_list:
            drive_file = pipeline.drive.upload_docx(settings.drive_folder_id, doc_path)
            pipeline.process_one(drive_file["id"], drive_file["name"])

    def _ensure_pipeline(self) -> IngestPipeline:
        if not self.pipeline:
            self.pipeline = IngestPipeline()
        return self.pipeline

    def _show_worker_error(self, context: str, exc: Exception) -> None:
        message = f"Error en {context}: {exc}"
        if context == "pipeline":
            self.log_pipeline(message)
        else:
            self.log(message)
        QMessageBox.critical(self, "Error", message)

    def run_pipeline_task(self, method_name: str) -> None:
        self.log_pipeline(f"Ejecutando {method_name}…")
        worker = Worker(self._run_pipeline_method, method_name)
        worker.signals.finished.connect(lambda _: self.log_pipeline("Tarea finalizada."))
        worker.signals.error.connect(lambda exc: self._show_worker_error("pipeline", exc))
        self.thread_pool.start(worker)

    def _run_pipeline_method(self, method_name: str) -> None:
        pipeline = self._ensure_pipeline()
        method = getattr(pipeline, method_name)
        method()

    def log(self, message: str) -> None:
        self._append_to_log(self.license_log, message)

    def log_pipeline(self, message: str) -> None:
        self._append_to_log(self.pipeline_log, message)

    def log_qc(self, message: str) -> None:
        self._append_to_log(self.qc_log, message)

    def _append_to_log(self, widget: Optional[QPlainTextEdit], message: str) -> None:
        if widget is None:
            return
        widget.appendPlainText(message)
        widget.ensureCursorVisible()

    def _ensure_today_field(self, force: bool = False) -> None:
        desired_raw = format_today_date()
        desired = normalize_value(desired_raw)
        current = self.current_data.get("FECHA_HOY", "")
        if current and not force:
            return

        self.current_data["FECHA_HOY"] = desired
        widget = self.field_inputs.get("FECHA_HOY")
        if isinstance(widget, QLineEdit):
            if widget.text() != desired:
                widget.blockSignals(True)
                widget.setText(desired)
                widget.blockSignals(False)
        elif isinstance(widget, QTextEdit):
            if widget.toPlainText() != desired:
                widget.blockSignals(True)
                widget.setPlainText(desired)
                widget.blockSignals(False)
