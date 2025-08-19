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

    # ------- Búsquedas y utilidades de bloque por RADICADO -------

    def _find_rows_by_key(self, key_col: str, key_value: str, start_row: int = 2) -> List[int]:
        if key_col not in self.headers:
            raise ValueError(f"Columna clave '{key_col}' no existe")
        col_idx = self.headers.index(key_col) + 1
        col_letter = self._num_to_col(col_idx)
        rng = f"{self.sheet_name}!{col_letter}{start_row}:{col_letter}"
        resp = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=rng
        ).execute()
        rows = resp.get("values", [])
        matches: List[int] = []
        for i, row in enumerate(rows):
            val = row[0] if row else ""
            if str(val) == str(key_value):
                matches.append(start_row + i)
        return matches

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

    def _is_row_empty(self, row_num: int) -> bool:
        row = self._get_row_as_dict(row_num)
        return all(str((row.get(h) or "")).strip() == "" for h in self.headers)

    def _find_row_by_compound_key(
        self,
        primary_col: str,
        primary_value: str,
        extra_keys: Dict[str, str],
        start_row: int = 2
    ) -> Optional[int]:
        """
        Coincidencia exacta: RADICADO + (SERIE si informativa) + (ITEM si existe) + (ARCHIVO si existe).
        """
        candidates = self._find_rows_by_key(primary_col, primary_value, start_row)
        if not candidates:
            return None
        if not extra_keys:
            return candidates[0]
        for row_num in candidates:
            row = self._get_row_as_dict(row_num)
            ok = True
            for col, val in extra_keys.items():
                if col not in self.headers:
                    continue
                if str(row.get(col, "")).strip() != str(val).strip():
                    ok = False
                    break
            if ok:
                return row_num
        return None

    def _find_incomplete_row_in_block(
        self,
        rad_col: str,
        rad_value: str,
        to_apply: Dict[str, Any],
        start_row: int = 2
    ) -> Optional[int]:
        """
        Reutiliza una fila 'incompleta' del mismo RADICADO si existe.
        Criterios:
          1) SERIE o SERIE TUBO RX vacías/'NO REGISTRA', o
          2) ≥3 columnas destino vacías entre las que vamos a llenar.
        """
        candidates = self._find_rows_by_key(rad_col, rad_value, start_row)
        if not candidates:
            return None

        prefer_missing_cols = {"SERIE", "SERIE TUBO RX"}
        def is_empty(v: Any) -> bool:
            s = str(v or "").strip()
            return s == "" or s.upper() in {"NO REGISTRA", "NO REGISTRADA", "NO APLICA"}

        # Prioriza filas con series vacías
        for row_num in candidates:
            row = self._get_row_as_dict(row_num)
            if any((c in self.headers) and is_empty(row.get(c, "")) for c in prefer_missing_cols):
                return row_num

        # Si no, usa heurística de vacíos general
        for row_num in candidates:
            row = self._get_row_as_dict(row_num)
            empties = 0
            total = 0
            for col in to_apply.keys():
                if col not in self.headers:
                    continue
                total += 1
                if is_empty(row.get(col, "")):
                    empties += 1
            if total >= 4 and empties >= 3:
                return row_num

        return None

    def _first_free_row_after_block(self, rad_col: str, rad_value: str, start_row: int = 2) -> Optional[int]:
        """
        Retorna la primera fila completamente vacía justo debajo del bloque del RADICADO (si existe).
        """
        candidates = self._find_rows_by_key(rad_col, rad_value, start_row)
        if not candidates:
            return None
        probe = max(candidates) + 1
        return probe if self._is_row_empty(probe) else None

    # ------- Escritura -------

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

    # ------- API principal -------

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
        Rellena SOLO celdas vacías. Evita duplicados y coloca equipos en el bloque correcto:
        1) Coincidencia exacta por clave compuesta: RADICADO + (SERIE) + (ITEM) + (ARCHIVO) + respaldo (TIPO DE EQUIPO/MARCA/MODELO).
        2) Reutiliza una fila INCOMPLETA dentro del bloque del RADICADO.
        3) Usa la PRIMERA fila VACÍA disponible entre las vacías consecutivas bajo el bloque del RADICADO.
        4) Si nada de lo anterior, APPEND al final.
        """
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        field_map = field_map or {}

        # 1) Radicado
        rad = str(json_data.get("RADICADO") or json_data.get("radicado") or "").strip()
        if not rad:
            raise ValueError("JSON sin 'RADICADO'/'radicado' para ubicar la fila.")

        # 2) Mapeo JSON → encabezados
        to_apply: Dict[str, Any] = {}
        for k, v in json_data.items():
            col = field_map.get(k, k)
            to_apply[col] = v

        # 3) Llave compuesta (acumulativa)
        def _norm(s: Any) -> str:
            return str(s or "").strip()

        extra_keys: Dict[str, str] = {}
        serie_val = _norm(to_apply.get("SERIE"))
        serie_info = bool(serie_val) and serie_val.upper() not in {"NO REGISTRA", "NO REGISTRADA", "NO APLICA"}
        if "SERIE" in self.headers and serie_info:
            extra_keys["SERIE"] = serie_val
        if "ITEM" in self.headers and _norm(to_apply.get("ITEM")):
            extra_keys["ITEM"] = _norm(to_apply["ITEM"])
        if (col_archivo in self.headers if col_archivo else False) and filename:
            extra_keys[col_archivo] = filename
        # Respaldo cuando no hay serie/ítem: ayuda a no duplicar equipos típicos
        for bcol in ("TIPO DE EQUIPO", "MARCA", "MODELO"):
            if bcol in self.headers and _norm(to_apply.get(bcol)):
                extra_keys.setdefault(bcol, _norm(to_apply[bcol]))

        # 4) Coincidencia exacta dentro del bloque
        row_num = self._find_row_by_compound_key(col_radicado, rad, extra_keys)

        # 5) Si no hay, intenta reutilizar una fila INCOMPLETA del bloque
        if row_num is None:
            candidates = self._find_rows_by_key(col_radicado, rad, start_row=2)

            def is_empty_value(x: Any) -> bool:
                s = _norm(x)
                return s == "" or s.upper() in {"NO REGISTRA", "NO REGISTRADA", "NO APLICA"}

            reuse_candidate: Optional[int] = None
            for r in candidates:
                row = self._get_row_as_dict(r)
                # Preferencia: serie(s) vacías
                if ("SERIE" in self.headers and is_empty_value(row.get("SERIE"))) or \
                   ("SERIE TUBO RX" in self.headers and is_empty_value(row.get("SERIE TUBO RX"))):
                    reuse_candidate = r
                    break
            if reuse_candidate is None:
                # Heurística: si ≥3 de los campos destino están vacíos, reutiliza
                for r in candidates:
                    row = self._get_row_as_dict(r)
                    empties = 0
                    total = 0
                    for col in to_apply.keys():
                        if col not in self.headers:
                            continue
                        total += 1
                        if is_empty_value(row.get(col, "")):
                            empties += 1
                    if total >= 4 and empties >= 3:
                        reuse_candidate = r
                        break
            if reuse_candidate is not None:
                row_num = reuse_candidate

        # 6) Si no hay fila aún, usa una de las VACÍAS consecutivas debajo del bloque del RADICADO
        using_free_row = False
        if row_num is None:
            candidates = self._find_rows_by_key(col_radicado, rad, start_row=2)
            if candidates:
                probe = max(candidates) + 1
                # Avanza por todas las filas vacías consecutivas disponibles
                while True:
                    # Obtiene toda la fila y verifica si está completamente vacía
                    last_col = self._num_to_col(len(self.headers))
                    rng = f"{self.sheet_name}!A{probe}:{last_col}{probe}"
                    resp = self.service.spreadsheets().values().get(
                        spreadsheetId=self.spreadsheet_id, range=rng
                    ).execute()
                    vals = resp.get("values", [[]])
                    vals = vals[0] if vals and vals[0] else []
                    # Consideramos vacía si ninguna de las columnas de encabezado tiene valor
                    is_row_empty = len(vals) == 0 or all(_norm(x) == "" for x in vals)
                    if is_row_empty:
                        row_num = probe
                        using_free_row = True
                        break
                    else:
                        # Si encontramos otro RADICADO u otra data, no hay huecos; salimos
                        break

        # 7) Si todavía no hay fila, APPEND al final
        creating_new_row = row_num is None

        # 8) Escribir
        if creating_new_row or using_free_row:
            base = {h: "" for h in self.headers}
            # RADICADO, ARCHIVO, timestamp
            if col_radicado in base:
                base[col_radicado] = rad
            if filename and (col_archivo in self.headers if col_archivo else False):
                base[col_archivo] = filename
            if col_updated in self.headers if col_updated else False:
                base[col_updated] = now
            # Asentar claves de la llave
            for k_col, k_val in extra_keys.items():
                if k_col in base and _norm(k_val) != "":
                    base[k_col] = k_val
            # Volcar campos del JSON
            filled, missing = [], []
            for col, val in to_apply.items():
                if col in base and _norm(val) != "":
                    base[col] = val
                    filled.append(col)
                elif col not in self.headers:
                    missing.append(col)
            # Observaciones
            if col_obs in self.headers:
                obs = f"{now.replace('T',' ')}: Fila nueva. Llenadas: {', '.join(filled) or 'ninguna'}."
                if missing:
                    obs += f" Sin columna: {', '.join(missing)}."
                base[col_obs] = obs

            if using_free_row:
                self._update_row_from_dict(row_num, base)
                return {"action": "insert_at_free", "radicado": rad, "row": row_num, "filled": filled, "missing": missing}
            else:
                self._append_row_from_dict(base)
                return {"action": "append", "radicado": rad, "filled": filled, "missing": missing}

        # -------- Fila existente → llenar solo vacíos --------
        current = self._get_row_as_dict(row_num)
        updated = dict(current)
        filled, skipped, missing = [], [], []

        for col, val in to_apply.items():
            if col not in self.headers:
                missing.append(col)
                continue
            curr = _norm(current.get(col, ""))
            new = _norm(val)
            if curr == "" and new != "":
                updated[col] = val
                filled.append(col)
            else:
                skipped.append(col)

        # ARCHIVO y timestamp
        if filename and (col_archivo in self.headers if col_archivo else False):
            if _norm(current.get(col_archivo, "")) == "":
                updated[col_archivo] = filename
                filled.append(col_archivo)
        if col_updated in self.headers if col_updated else False:
            updated[col_updated] = now

        # Asentar columnas de la llave si estaban vacías
        for k_col, k_val in extra_keys.items():
            if k_col in self.headers and _norm(updated.get(k_col, "")) == "" and _norm(k_val) != "":
                updated[k_col] = k_val
                filled.append(k_col)

        if col_obs in self.headers:
            prev = _norm(current.get(col_obs, ""))
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

