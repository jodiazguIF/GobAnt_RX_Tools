import os
import json
from typing import Dict, Any
from app.config import settings
from app.services.google_auth import get_credentials, build_clients
from app.services.drive_client import DriveClient
from app.services.sheets_table import SheetsTable
from app.services.ai_client import AIClient
from app.utils import radicado as rad

class IngestPipeline:
    def __init__(self):
        self.creds = get_credentials(settings.service_account_path)
        drive_service, sheets_service = build_clients(self.creds)
        self.drive = DriveClient(drive_service)
        self.sheets = SheetsTable(sheets_service, settings.spreadsheet_id, settings.worksheet_name)
        self.ai = AIClient(settings.gemini_api_key, settings.gemini_model)

    def _save_json(self, radicado: str, payload: Dict[str, Any]) -> str:
        os.makedirs(settings.out_dir, exist_ok=True)
        path = os.path.join(settings.out_dir, f"{radicado}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def process_folder(self) -> None:
        files = self.drive.list_docx_in_folder(settings.drive_folder_id)
        if not files:
            print("No se encontraron .docx en la carpeta.")
            return
        print(f"Se encontraron {len(files)} archivo(s).")
        for f in files:
            try:
                self.process_one(f["id"], f["name"])  
            except Exception as e:
                print(f"[ERROR] {f.get('name')}: {e}")

    def process_one(self, file_id: str, filename: str) -> None:
        print(f"→ Procesando: {filename} ({file_id})")
        text = self.drive.download_docx_text(file_id)

        # Radicado
        radicado = rad.resolve(text, filename)
        if not radicado:
            raise ValueError(f"No se pudo extraer Radicado de {filename}")

        # IA → JSON
        # IA → JSON
        data = self.ai.summarize(text)

        # Normaliza posibles variantes que pueda devolver la IA
        if "Radicado" in data and "RADICADO" not in data:
            data["RADICADO"] = data.pop("Radicado")
        if "Archivo" not in data:
            data["Archivo"] = filename

        # Si la IA dejó RADICADO como null/""/espacios, fuerzo el radicado detectado
        if str(data.get("RADICADO") or "").strip() == "":
            data["RADICADO"] = radicado


        # Guardar JSON
        path = self._save_json(radicado, data)
        print(f"   JSON: {path}")

        # Subir a Sheets (solo vacíos)
        result = self.sheets.fill_from_json_only_empty(
            json_data=data,
            col_radicado=settings.col_radicado,   # "RADICADO"
            col_obs=settings.col_obs,             # "OBSERVACIONES"
            col_archivo=settings.col_archivo,     # None (no hay columna Archivo)
            col_updated=settings.col_updated,     # "Última Actualización"
            filename=filename,
            field_map={
                "NOMBRE": "NOMBRE",
                "RADICADO": "RADICADO",
                "FECHA": "FECHA",
                "NOMBRE O RAZON SOCIAL": "NOMBRE O RAZÓN SOCIAL",
                "NIT O CC": "NIT O CC",
                "SEDE": "SEDE",
                "DIRECCION": "DIRECCIÓN",
                "SUBREGION": "SUBREGIÓN",
                "MUNICIPIO": "MUNICIPIO",
                "CORREO ELECTRONICO": "CORREO ELECTRÓNICO",
                "TIPO DE SOLICITUD": "TIPO DE SOLICITUD",
                "TIPO DE EQUIPO": "TIPO DE EQUIPO",
                "CATEGORIA": "CATEGORÍA",
                "FECHA DE FABRICACION": "FECHA DE FABRICACIÓN",
                "MARCA": "MARCA",
                "MODELO": "MODELO",
                "SERIE": "SERIE",
                "MARCA TUBO RX": "MARCA TUBO RX",
                "MODELO TUBO RX": "MODELO TUBO RX",
                "SERIE TUBO RX": "SERIE TUBO RX",
                "CONTROL CALIDAD": "CONTROL CALIDAD",
                "FECHA CC": "FECHA CC",
                "OBSERVACIONES": "OBSERVACIONES",
                # "Archivo":  # tu hoja no tiene esta columna; lo omitimos
            },
        )
        print(f"   Sheets: {result}")