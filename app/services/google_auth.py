import base64
import json
import os
from typing import Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _load_info_from_source(source: str):
    """Devuelve las credenciales desde una ruta, JSON o base64."""
    if not source:
        return None

    # 1) Ruta a archivo
    if os.path.exists(source):
        return service_account.Credentials.from_service_account_file(
            source, scopes=SCOPES
        )

    # 2) JSON directo
    try:
        info = json.loads(source)
        if isinstance(info, dict):
            return service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
    except Exception:
        pass

    # 3) Base64 del JSON
    try:
        decoded = base64.b64decode(source).decode()
        info = json.loads(decoded)
        if isinstance(info, dict):
            return service_account.Credentials.from_service_account_info(
                info, scopes=SCOPES
            )
    except Exception:
        pass

    return None


def get_credentials(sa_source: str):
    creds = _load_info_from_source(sa_source)
    if creds:
        return creds

    raise FileNotFoundError(
        (
            "GOOGLE_APPLICATION_CREDENTIALS debe contener credenciales válidas de cuenta de servicio. "
            "Usa uno de estos formatos: ruta a un archivo .json descargado desde Google Cloud, "
            "el JSON completo pegado en la variable, su base64 o el nombre de otra variable con ese JSON/base64. "
            "Un token plano (ej. 'alajkqwejlknqdlknasn') no sirve: Google requiere el JSON estructurado del Service Account."
        )
    )


def build_clients(creds) -> Tuple[any, any]:
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    return drive, sheets
