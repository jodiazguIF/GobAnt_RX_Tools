import gspread
import json
import os
from __future__ import annotations
from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/drive']
# --- CONFIGURACIÓN DE GOOGLE SHEETS --- #
creds = ServiceAccountCredentials.from_json_keyfile_name("Credentials\\credentials_editoria.json", scope)
client = gspread.authorize(creds)

# Reemplaza 'Nombre de tu hoja de cálculo' con el nombre exacto de tu archivo en Google Sheets
spreadsheet_name = "CONTROL DOCUMENTOS LICENCIAS RX FORMATO SHEETS"
spreadsheet_key = "1TrtZbZoUmnlaTdHFCH5rE5EZhPGiGxpleDf4cixR87A"
worksheet_name = "LICENCIAS ELABORADAS 2025"
worksheet = client.open_by_key(spreadsheet_key).worksheet(worksheet_name)

COL_RADICADO = "RADICADO"
COL_OBS = "OBSERVACIONES"
COL_ARCHIVO = "ARCHIVO"
COL_UPDATED = "Última Actualización"


def subir_a_google_sheets(datos_extraidos):
    """
    Convierte los datos extraídos en un formato de lista plana y los sube a Google Sheets.
    
    Args:
        datos_extraidos (dict): Un diccionario con los datos extraídos.
    """
    try:
        # Preparamos una lista para almacenar los valores en el orden correcto
        fila_de_datos = [
            datos_extraidos.get("ELABORA", ""),
            datos_extraidos.get("RADICADO", ""),
            datos_extraidos.get("FECHA", ""),
            datos_extraidos.get("NOMBRE O RAZON SOCIAL", ""),
            datos_extraidos.get("NIT O CC", ""),
            datos_extraidos.get("SEDE", ""),
            datos_extraidos.get("DIRECCION", ""),
            datos_extraidos.get("SUBREGION", ""),
            datos_extraidos.get("MUNICIPIO", ""),
            datos_extraidos.get("CORREO ELECTRONICO", ""),
            datos_extraidos.get("TIPO DE SOLICITUD", ""),
            datos_extraidos.get("TIPO DE EQUIPO", ""),
            datos_extraidos.get("CATEGORIA", ""),
            datos_extraidos.get("FECHA DE FABRICACION", ""),
            datos_extraidos.get("MARCA", ""),
            datos_extraidos.get("MODELO", ""),
            datos_extraidos.get("SERIE", ""),
            # Accedemos a los datos anidados del tubo de rayos X
            datos_extraidos.get("TUBO DE RX", {}).get("MARCA", ""),
            datos_extraidos.get("TUBO DE RX", {}).get("MODELO", ""),
            datos_extraidos.get("TUBO DE RX", {}).get("SERIE", ""),
            datos_extraidos.get("TUBO DE RX", {}).get("FECHA FABR", ""),
            datos_extraidos.get("CONTROL CALIDAD", "")
        ]

        # Añade la nueva fila a la hoja de cálculo
        worksheet.append_row(fila_de_datos)
        print("Datos subidos exitosamente a Google Sheets.")
    except Exception as e:
        print(f"Error al subir datos a Google Sheets: {e}")

class SheetsTable:
    def __init__(self, creds, spreadsheet_id: str, sheet_name: str = worksheet_name):
        self.service = build("sheets", "v4", credentials=creds)
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.headers: List[str] = []
        self._load_headers()

    @staticmethod
    def _num_to_col(n: int) -> str:
        s = ""
        while n:
            n, r = divmod(n - 1, 26)
            s = chr(65 + r) + s
        return s

    def _load_headers(self):
        rng = f"{self.sheet_name}!1:1"
        resp = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=rng
        ).execute()
        row = resp.get("values", [[]])
        self.headers = [h.strip() for h in row[0]] if row and row[0] else []

    def ensure_columns(self, cols: List[str]):
        missing = [c for c in cols if c not in self.headers]
        if missing:
            raise ValueError(
                f"Faltan columnas en la hoja '{self.sheet_name}': {missing}. "
                f"Encabezados actuales: {self.headers}"
            )

    def find_row_by_key(self, key_col: str, key_value: str, start_row: int = 2) -> Optional[int]:
        # Ubica la columna
        if key_col not in self.headers:
            raise ValueError(f"La columna clave '{key_col}' no existe en {self.headers}")
        col_idx = self.headers.index(key_col) + 1  # 1-based
        col_letter = self._num_to_col(col_idx)
        rng = f"{self.sheet_name}!{col_letter}{start_row}:{col_letter}"
        resp = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=rng
        ).execute()
        rows = resp.get("values", [])
        for i, row in enumerate(rows):
            val = row[0] if row else ""
            if str(val) == str(key_value):
                return start_row + i
        return None

    def get_row_as_dict(self, row_num: int) -> Dict[str, Any]:
        last_col_letter = self._num_to_col(len(self.headers))
        rng = f"{self.sheet_name}!A{row_num}:{last_col_letter}{row_num}"
        resp = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=rng
        ).execute()
        arr = resp.get("values", [[]])
        vals = arr[0] if arr and arr[0] else []
        vals = vals + [""] * (len(self.headers) - len(vals))
        return {h: vals[i] for i, h in enumerate(self.headers)}

    def update_row_from_dict(self, row_num: int, new_row: Dict[str, Any]):
        # Ordena según headers y sube toda la fila (manteniendo celdas no cambiadas)
        last_col_letter = self._num_to_col(len(self.headers))
        rng = f"{self.sheet_name}!A{row_num}:{last_col_letter}{row_num}"
        values = [[new_row.get(h, "") for h in self.headers]]
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=rng,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()

    def append_row_from_dict(self, new_row: Dict[str, Any]):
        rng = f"{self.sheet_name}!A1:{self._num_to_col(len(self.headers))}1"
        values = [[new_row.get(h, "") for h in self.headers]]
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=rng,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()


def fill_only_empty_cells_from_json(
    table: SheetsTable,
    json_data: Dict[str, Any],
    *,
    radicado: Optional[str] = None,
    filename: Optional[str] = None,
    field_map: Optional[Dict[str, str]] = None,
    extra_static_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    - Localiza la fila por Radicado.
    - Para cada par (clave_json → columna), SOLO escribe si la celda está vacía.
    - Agrega Observaciones con columnas llenadas/saltadas.
    - Si la fila no existe, crea una NUEVA y rellena todo lo disponible.

    json_data: dict con tu formato de extracción (ya lo tienes).
    field_map: mapea 'clave_json' -> 'Nombre exacto de columna en la hoja'.
               Si None, se asume que las claves del JSON ya coinciden con los encabezados.
    extra_static_fields: ej. { 'Archivo': filename }
    """
    # 1) Determinar radicado
    rad = (
        radicado
        or str(json_data.get("Radicado", "") or json_data.get("radicado", "")).strip()
    )
    if not rad:
        raise ValueError("No se encontró Radicado (ni en parámetro ni en JSON).")
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # 2) Preparar mapeo JSON->Columna
    field_map = field_map or {}  # si las claves ya coinciden con headers, field_map puede quedar vacío
    # Armamos un dict columna -> valor (solo para claves presentes en json_data)
    to_apply: Dict[str, Any] = {}
    for k, v in json_data.items():
        col = field_map.get(k, k)  # por defecto, misma clave
        # solo consideramos columnas que existan realmente en la hoja
        to_apply[col] = v

    # 3) Asegurar columnas mínimas
    cols_necesarias = [COL_RADICADO, COL_OBS]
    if COL_ARCHIVO in table.headers: cols_necesarias.append(COL_ARCHIVO)
    if COL_UPDATED in table.headers: cols_necesarias.append(COL_UPDATED)
    table.ensure_columns(cols_necesarias)

    # 4) Buscar la fila
    row_num = table.find_row_by_key(COL_RADICADO, rad)
    created = False

    if row_num is None:
        # Crear nueva fila: rellenamos lo que tengamos; celdas no mapeadas quedarán vacías
        base = {h: "" for h in table.headers}
        base[COL_RADICADO] = rad
        if filename and COL_ARCHIVO in base: base[COL_ARCHIVO] = filename
        if COL_UPDATED in base: base[COL_UPDATED] = now
        if extra_static_fields:
            for ck, cv in extra_static_fields.items():
                if ck in base:
                    base[ck] = cv

        # aplica todos los campos mapeados que existan como columnas
        filled_cols = []
        for col, val in to_apply.items():
            if col in base and str(val).strip() != "":
                base[col] = val
                filled_cols.append(col)

        # Observaciones
        obs = f"{now.replace('T',' ')}: Fila nueva creada. Columnas llenadas: {', '.join(filled_cols) or 'ninguna'}."
        if COL_OBS in base:
            base[COL_OBS] = obs

        table.append_row_from_dict(base)
        created = True
        return {"action": "append", "radicado": rad, "filled": filled_cols}

    # 5) La fila existe: rellenar SOLO vacíos
    current = table.get_row_as_dict(row_num)
    updated_row = dict(current)  # copia
    filled, skipped, missing = [], [], []
    for col, val in to_apply.items():
        if col not in table.headers:
            missing.append(col)
            continue
        # Solo llenar si está vacío y tenemos valor no vacío
        curr_val = str(current.get(col, "") or "").strip()
        new_val = str(val).strip()
        if curr_val == "" and new_val != "":
            updated_row[col] = val
            filled.append(col)
        else:
            skipped.append(col)

    # Campos estáticos útiles
    if filename and COL_ARCHIVO in table.headers:
        if (current.get(COL_ARCHIVO, "") or "").strip() == "":
            updated_row[COL_ARCHIVO] = filename
            if COL_ARCHIVO not in filled: filled.append(COL_ARCHIVO)
    if COL_UPDATED in table.headers:
        updated_row[COL_UPDATED] = now

    if extra_static_fields:
        for ck, cv in extra_static_fields.items():
            if ck in table.headers:
                # también solo si vacío
                if (current.get(ck, "") or "").strip() == "" and str(cv).strip() != "":
                    updated_row[ck] = cv
                    filled.append(ck)
                else:
                    skipped.append(ck)

    # Observaciones
    obs_prev = (current.get(COL_OBS, "") or "").strip()
    obs_lines = []
    if filled:
        obs_lines.append(f"Columnas llenadas: {', '.join(sorted(set(filled)))}.")
    # Solo informativo: columnas presentes en JSON pero no vacías en la hoja
    if skipped:
        obs_lines.append(f"Saltadas (ya tenían valor o no aplican): {', '.join(sorted(set(skipped)))}.")
    if missing:
        obs_lines.append(f"Claves sin columna en hoja: {', '.join(sorted(set(missing)))}.")
    if obs_lines:
        obs_line = f"{now.replace('T',' ')}: " + " ".join(obs_lines)
        updated_row[COL_OBS] = (obs_prev + "\n" + obs_line).strip() if obs_prev else obs_line

    # Subir cambios (si los hay)
    if updated_row != current:
        table.update_row_from_dict(row_num, updated_row)
        return {"action": "update", "radicado": rad, "row": row_num, "filled": filled, "skipped": skipped, "missing": missing}
    else:
        return {"action": "noop", "radicado": rad, "row": row_num, "filled": [], "skipped": skipped, "missing": missing}