# app/services/ingest.py
import os
import json
import glob
import time
from typing import Dict, Any, Optional, List
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
        self.sheets = SheetsTable(
            sheets_service, settings.spreadsheet_id, settings.worksheet_name
        )
        self.ai = AIClient(settings.gemini_api_key, settings.gemini_model)

    # ---------- Cache local (clave compuesta: radicado + prefijo de file_id) ----------
    def _cache_key(self, radicado: str, file_id: Optional[str], filename: Optional[str]) -> str:
        if file_id:
            return f"{radicado}__{file_id[:8]}"
        # Fallback por si algún día se procesa sin file_id
        base = os.path.splitext(os.path.basename(filename or ""))[0]
        safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in base)[:16]
        return f"{radicado}__{safe or 'local'}"

    def _json_path(self, cache_key: str) -> str:
        os.makedirs(settings.out_dir, exist_ok=True)
        return os.path.join(settings.out_dir, f"{cache_key}.json")

    def _load_json_if_exists(self, cache_key: str) -> Optional[Dict[str, Any]]:
        path = self._json_path(cache_key)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _save_json(self, cache_key: str, payload: Dict[str, Any]) -> str:
        path = self._json_path(cache_key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

    def _has_cache_for_file(self, file_id: str) -> bool:
        '''Revisa si existe un JSON local para el file_id dado.'''
        prefix = file_id[:8]
        pattern = os.path.join(settings.out_dir, f"*__{prefix}.json")
        return bool(glob.glob(pattern))
    # -------------------------------------------------------------------------------

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

    def process_folder_only_new(self) -> None:
        """Procesa solo los archivos que aún no tengan cache local."""
        files = self.drive.list_docx_in_folder(settings.drive_folder_id)
        if not files:
            print("No se encontraron .docx en la carpeta.")
            return
        print(f"Se encontraron {len(files)} archivo(s).")
        for f in files:
            try:
                if self._has_cache_for_file(f["id"]):
                    print(f"→ Cache encontrado, se omite: {f['name']} ({f['id']})")
                    continue
                self.process_one(f["id"], f["name"])
            except Exception as e:
                print(f"[ERROR] {f.get('name')}: {e}")

    def process_folder_only_pending(self) -> None:
        """Procesa únicamente archivos cuyo radicado no tenga aún información en la
        columna de observaciones (ETIQUETA IA) en la hoja."""
        files = self.drive.list_docx_in_folder(settings.drive_folder_id)
        if not files:
            print("No se encontraron .docx en la carpeta.")
            return
        print(f"Se encontraron {len(files)} archivo(s).")
        for f in files:
            try:
                file_id, filename = f["id"], f["name"]
                radicado: Optional[str] = None
                # Intentar obtener el radicado desde el cache local
                prefix = file_id[:8]
                pattern = os.path.join(settings.out_dir, f"*__{prefix}.json")
                matches = glob.glob(pattern)
                if matches:
                    try:
                        with open(matches[0], "r", encoding="utf-8") as fp:
                            cached = json.load(fp)
                        radicado = str(cached.get("RADICADO") or cached.get("radicado") or "").strip() or None
                    except Exception:
                        radicado = None
                # Fallback: radicado en el nombre del archivo
                if not radicado:
                    radicado = rad.extract_from_filename(filename)
                # Fallback final: extraer del contenido
                if not radicado:
                    text = self.drive.download_docx_text(file_id)
                    radicado = rad.extract_from_text(text)

                if radicado and self.sheets.has_value_in_column(
                    settings.col_radicado, radicado, settings.col_obs
                ):
                    print(f"→ Ya subido, se omite: {filename} ({radicado})")
                    continue

                self.process_one(file_id, filename)
            except Exception as e:
                print(f"[ERROR] {f.get('name')}: {e}")

    def _ensure_equipos_array(self, data: Dict[str, Any]) -> None:
        """
        Normaliza 'data' para que siempre tenga EQUIPOS: List[Dict[str, Any]].
        Mantiene retrocompatibilidad con JSON plano (un solo equipo).
        """
        if isinstance(data.get("EQUIPOS"), list) and data["EQUIPOS"]:
            return  # Ya está en formato esperado

        # Campos típicos de equipo que pueden venir en plano
        equipo_keys = [
            "TIPO DE EQUIPO",
            "FECHA DE FABRICACION",
            "FECHA DE FABRICACIÓN",
            "MARCA",
            "MODELO",
            "SERIE",
            "MARCA TUBO RX",
            "MODELO TUBO RX",
            "SERIE TUBO RX",
            "CONTROL CALIDAD",
            "FECHA CC",
        ]

        eq: Dict[str, Any] = {}
        for k in equipo_keys:
            if k in data and str(data[k]).strip() != "":
                eq[k] = data[k]

        # Si no hay nada de equipo, aún así crea un contenedor para que el pipeline avance
        if not eq:
            eq = {}

        data["EQUIPOS"] = [eq]

    def _rows_from_data(self, data: Dict[str, Any], filename: str) -> List[Dict[str, Any]]:
        """
        Convierte el JSON de licencia (con EQUIPOS[]) en filas listas para enviar a Sheets.
        Agrega 'ITEM' y 'ARCHIVO' por fila.
        """
        base = {k: v for k, v in data.items() if k != "EQUIPOS"}
        equipos = data.get("EQUIPOS", []) or [{}]
        rows: List[Dict[str, Any]] = []
        for i, eq in enumerate(equipos, start=1):
            row = dict(base)
            row.update(eq or {})
            row["ITEM"] = i
            row["ARCHIVO"] = filename
            rows.append(row)
        return rows

    def process_one(self, file_id: str, filename: str, skip_sheet_if_cached: bool = False) -> None:
        print(f"→ Procesando: {filename} ({file_id})")
        text = self.drive.download_docx_text(file_id)

        # 1) Radicado
        radicado = rad.resolve(text, filename)
        if not radicado:
            raise ValueError(f"No se pudo extraer Radicado de {filename}")

        # 2) Verificación previa (cache local por radicado+archivo)
        # Verifica si hay un archivo existente con el número de radicado
        cache_key = self._cache_key(radicado, file_id, filename)
        data = self._load_json_if_exists(cache_key)
        if data is None:
            print(f"   Sin cache para {radicado}. Ejecutando IA …")
            data = self.ai.summarize(text)
        else:
            print(f"   Cache JSON encontrado para {radicado} ({filename}). Omitiendo IA.")
            if skip_sheet_if_cached:
                print("   Omitiendo subida a Sheets por cache existente.")
                return

        # 3) Normalizaciones mínimas de licencia
        if "Radicado" in data and "RADICADO" not in data:
            data["RADICADO"] = data.pop("Radicado")
        if str(data.get("RADICADO") or "").strip() == "":
            data["RADICADO"] = radicado

        # 4) Normalizar a EQUIPOS[]
        self._ensure_equipos_array(data)

        # 5) Guardar/actualizar cache local (persistir normalizaciones)
        path = self._save_json(cache_key, data)
        print(f"   JSON: {path}")

        # 6) Expandir a filas y escribir en Sheets (solo vacíos)
        rows = self._rows_from_data(data, filename)
        results = []
        for row_json in rows:
            result = self.sheets.fill_from_json_only_empty(
                json_data=row_json,
                col_radicado=settings.col_radicado,   # "RADICADO"
                col_obs=settings.col_obs,             # "OBSERVACIONES"
                col_archivo=settings.col_archivo,     # "ARCHIVO" si existe; o None
                col_updated=settings.col_updated,     # "Última Actualización"
                filename=filename,
                field_map={
                    "ELABORA": "ELABORA",
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
                    "FECHA FABRICACIÓN TUBO RX": "FECHA FABRICACIÓN TUBO RX",
                    "CONTROL CALIDAD": "CONTROL CALIDAD",
                    "FECHA CC": "FECHA CC",
                    "OBSERVACIONES": "OBSERVACIONES",
                    "Ultima Actualizacion": "Ultima Actualizacion",
                    "ITEM": "ITEM",
                    "ARCHIVO": "ARCHIVO",
                },
            )
            results.append(result)
        print(f"   Sheets: {results}")
