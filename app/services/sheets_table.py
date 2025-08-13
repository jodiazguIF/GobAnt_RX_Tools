# app/services/sheets_table.py
from typing import Dict, Any, List, Optional
from datetime import datetime

class SheetsTable:
    def __init__(self, sheets_service, spreadsheet_id: str, sheet_name: str):
        self.service = sheets_service
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
                f"Faltan columnas en '{self.sheet_name}': {missing}. Encabezados: {self.headers}"
            )

    def _find_row_by_key(self, key_col: str, key_value: str, start_row: int = 2) -> Optional[int]:
        if key_col not in self.headers:
            raise ValueError(f"Columna clave '{key_col}' no existe")
        col_idx = self.headers.index(key_col) + 1
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

    def _get_row_as_dict(self, row_num: int) -> Dict[str, Any]:
        last_col = self._num_to_col(len(self.headers))
        rng = f"{self.sheet_name}!A{row_num}:{last_col}{row_num}"
        resp = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=rng
        ).execute()
        arr = resp.get("values", [[]])
        vals = arr[0] if arr and arr[0] else []
        vals += [""] * (len(self.headers) - len(vals))
        return {h: vals[i] for i, h in enumerate(self.headers)}

    def _update_row_from_dict(self, row_num: int, row_dict: Dict[str, Any]):
        last_col = self._num_to_col(len(self.headers))
        rng = f"{self.sheet_name}!A{row_num}:{last_col}{row_num}"
        values = [[row_dict.get(h, "") for h in self.headers]]
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=rng,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()

    def _append_row_from_dict(self, row_dict: Dict[str, Any]):
        rng = f"{self.sheet_name}!A1:{self._num_to_col(len(self.headers))}1"
        values = [[row_dict.get(h, "") for h in self.headers]]
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=rng,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()

    def fill_from_json_only_empty(self,
                                  json_data: Dict[str, Any],
                                  *,
                                  col_radicado: str,
                                  col_obs: str,
                                  col_archivo: Optional[str] = None,
                                  col_updated: Optional[str] = None,
                                  filename: Optional[str] = None,
                                  field_map: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Rellena SOLO celdas vacías en la fila identificada por col_radicado.
        Si no existe, crea la fila. Registra acciones en col_obs.
        """
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        field_map = field_map or {}

        # 1) Radicado
        rad = str(json_data.get("RADICADO") or json_data.get("radicado") or "").strip()
        if not rad:
            raise ValueError("JSON sin 'RADICADO'/'radicado' para ubicar la fila.")

        # 2) Construir columnas a aplicar desde el JSON
        to_apply: Dict[str, Any] = {}
        for k, v in json_data.items():
            col = field_map.get(k, k)
            to_apply[col] = v

        # 3) Buscar la fila existente
        row_num = self._find_row_by_key(col_radicado, rad)

        if row_num is None:
            # Crear fila nueva
            base = {h: "" for h in self.headers}
            if col_radicado in base:
                base[col_radicado] = rad
            if filename and col_archivo in self.headers:
                base[col_archivo] = filename
            if col_updated in self.headers:
                base[col_updated] = now

            filled, missing = [], []
            for col, val in to_apply.items():
                if col in base and str(val).strip() != "":
                    base[col] = val
                    filled.append(col)
                elif col not in self.headers:
                    missing.append(col)

            if col_obs in self.headers:
                obs = f"{now.replace('T',' ')}: Fila nueva. Llenadas: {', '.join(filled) or 'ninguna'}."
                if missing:
                    obs += f" Sin columna: {', '.join(missing)}."
                base[col_obs] = obs

            self._append_row_from_dict(base)
            return {"action": "append", "radicado": rad, "filled": filled, "missing": missing}

        # Fila existente → llenar solo vacíos
        current = self._get_row_as_dict(row_num)
        updated = dict(current)
        filled, skipped, missing = [], [], []

        for col, val in to_apply.items():
            if col not in self.headers:
                missing.append(col)
                continue
            curr = (current.get(col, "") or "").strip()
            new = str(val).strip()
            if curr == "" and new != "":
                updated[col] = val
                filled.append(col)
            else:
                skipped.append(col)

        if filename and col_archivo in self.headers and (current.get(col_archivo, "") or "").strip() == "":
            updated[col_archivo] = filename
            filled.append(col_archivo)
        if col_updated in self.headers:
            updated[col_updated] = now

        if col_obs in self.headers:
            prev = (current.get(col_obs, "") or "").strip()
            lines = []
            if filled:
                lines.append(f"Llenadas: {', '.join(sorted(set(filled)))}.")
            if skipped:
                lines.append(f"Saltadas: {', '.join(sorted(set(skipped)))}.")
            if missing:
                lines.append(f"Sin columna: {', '.join(sorted(set(missing)))}.")
            if lines:
                obs_line = f"{now.replace('T',' ')}: " + " ".join(lines)
                updated[col_obs] = (prev + "\n" + obs_line).strip() if prev else obs_line

        if updated != current:
            self._update_row_from_dict(row_num, updated)
            return {"action": "update", "radicado": rad, "row": row_num, "filled": filled, "skipped": skipped, "missing": missing}
        return {"action": "noop", "radicado": rad, "row": row_num, "filled": [], "skipped": skipped, "missing": missing}
