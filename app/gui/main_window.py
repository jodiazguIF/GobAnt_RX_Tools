"""Ventana principal de la aplicación gráfica."""
from __future__ import annotations

import traceback
from pathlib import Path
from typing import Dict, Optional

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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import settings
from app.pipeline.ingest import IngestPipeline
from .config_store import GuiConfig, load_config, save_config
from .constants import CategoriaTipo, FIELDS, PersonaTipo
from .doc_processing import (
    build_output_name,
    extract_from_docx,
    generate_from_template,
    update_source_document,
)
from .text_utils import normalize_value
from .workers import Worker


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
        self.pipeline: Optional[IngestPipeline] = None
        self.license_log: Optional[QPlainTextEdit] = None
        self.pipeline_log: Optional[QPlainTextEdit] = None

        self._init_ui()

    # ------------------------------------------------------------------ UI
    def _init_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._build_license_tab(), "Generación de licencias")
        tabs.addTab(self._build_pipeline_tab(), "Carga automática (Drive/Sheets)")
        self.setCentralWidget(tabs)

    def _build_license_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        layout.addWidget(self._build_file_section())
        layout.addWidget(self._build_templates_section())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        form_container = QWidget()
        form_layout = QFormLayout(form_container)
        form_layout.setLabelAlignment(Qt.AlignRight)  # type: ignore[name-defined]

        for field in FIELDS:
            input_widget = self._create_input_for_field(field.key, field.multiline)
            self.field_inputs[field.key] = input_widget
            label = QLabel(field.label + (" *" if field.required else ""))
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            form_layout.addRow(label, input_widget)

        scroll.setWidget(form_container)
        layout.addWidget(scroll)

        layout.addWidget(self._build_actions_section())
        layout.addWidget(self._build_log_section("license_log", "Bitácora"))
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

    def _build_actions_section(self) -> QGroupBox:
        box = QGroupBox("Generación")
        layout = QHBoxLayout(box)

        self.chk_update_source = QCheckBox("Actualizar documento origen")
        self.chk_update_source.setChecked(True)
        layout.addWidget(self.chk_update_source)

        self.chk_upload_drive = QCheckBox("Subir licencia a Drive y ejecutar pipeline")
        layout.addWidget(self.chk_upload_drive)

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
        if key == "CATEGORIA":
            combo = QComboBox()
            combo.addItem("")
            combo.addItem(CategoriaTipo.CAT_1.value)
            combo.addItem(CategoriaTipo.CAT_2.value)
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

    def clear_form(self) -> None:
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
        self.log("Formulario limpio. Puedes ingresar valores manualmente.")

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
        self.source_path = path
        self.source_label.setText(str(path))
        for key, value in document_data.data.items():
            self._set_field(key, value)
        if document_data.persona:
            self._set_field("TIPO_SOLICITANTE", document_data.persona.value)
        if document_data.categoria:
            self._set_field("CATEGORIA", document_data.categoria.value)
        self.log(f"Se cargó el documento {path.name}.")

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

        persona = PersonaTipo.from_text(self.current_data.get("TIPO_SOLICITANTE", ""))
        categoria = CategoriaTipo.from_text(self.current_data.get("CATEGORIA", ""))
        if not persona:
            raise ValueError("Define si es PERSONA NATURAL o PERSONA JURIDICA.")
        if not categoria:
            raise ValueError("Selecciona si es CATEGORIA 1 o CATEGORIA 2.")

        template_path_str = self.config.templates.resolve_path(persona, categoria)
        if not template_path_str:
            raise ValueError("Configura la plantilla correspondiente en la sección de plantillas.")
        template_path = Path(template_path_str)
        if not template_path.exists():
            raise FileNotFoundError(f"No se encontró la plantilla {template_path}")

        radicado = self.current_data["RADICADO"]
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

        output_name = build_output_name(source_stub, radicado)
        output_path = output_dir / f"{output_name}.docx"

        generate_from_template(template_path, output_path, self.current_data)
        self.log(f"Se generó la licencia en {output_path}.")

        if self.chk_update_source.isChecked() and self.source_path:
            update_source_document(self.source_path, self.current_data)
            self.log("Documento origen actualizado con los nuevos valores.")

        if self.chk_upload_drive.isChecked():
            self.log("Subiendo a Drive y ejecutando pipeline…")
            worker = Worker(self._upload_and_process, output_path)
            worker.signals.finished.connect(lambda _: self.log("Proceso en Drive completado."))
            worker.signals.error.connect(lambda exc: self._show_worker_error("Drive", exc))
            self.thread_pool.start(worker)

    def _upload_and_process(self, path: Path) -> None:
        pipeline = self._ensure_pipeline()
        drive_file = pipeline.drive.upload_docx(settings.drive_folder_id, path)
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

    def _append_to_log(self, widget: Optional[QPlainTextEdit], message: str) -> None:
        if widget is None:
            return
        widget.appendPlainText(message)
        widget.ensureCursorVisible()
