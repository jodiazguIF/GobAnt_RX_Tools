import os
from dataclasses import dataclass

# Carga variables del .env si usas python-dotenv
from dotenv import load_dotenv
load_dotenv()


def get_relative_path(path: str) -> str:
    """
    Calcula la ruta relativa al directorio raíz del proyecto.
    Si el usuario proporciona una ruta absoluta (incluidas rutas Windows como
    "C:\\..."), se respeta tal cual para evitar concatenarla con la raíz.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if os.path.isabs(path) or ":" in os.path.splitdrive(path)[0]:
        return os.path.normpath(path)

    return os.path.normpath(os.path.join(base_dir, path))


def resolve_service_account_source(value: str) -> str:
    """
    Devuelve la ruta o el JSON/base64 original de credenciales.

    * Si el valor parece un JSON (o su base64), se devuelve tal cual para que
      el cargador use `from_service_account_info`.
    * Si el valor apunta al nombre de otra variable de entorno con el JSON/base64
      (ej. `GOOGLE_APPLICATION_CREDENTIALS=Credencial` y `Credencial` guarda el
      secreto), se usa ese contenido.
    * Para rutas, se normaliza contra la raíz del proyecto.
    """
    raw = (value or "").strip()
    if not raw:
        return raw

    alias_value = os.environ.get(raw)
    candidate = alias_value.strip() if alias_value else raw

    # JSON directo
    if candidate.lstrip().startswith("{"):
        return candidate

    # Base64 que decodifica a JSON
    try:
        import base64, json

        decoded = base64.b64decode(candidate.encode()).decode()
        if decoded.lstrip().startswith("{") and json.loads(decoded):
            return candidate
    except Exception:
        pass

    return get_relative_path(candidate)


def normalize_model_identifier(model: str) -> str:
    """Asegura que el modelo tenga el prefijo completo `models/`.

    Google GenAI requiere el identificador completo (p. ej. `models/gemini-1.5-flash`).
    Si el usuario suministra el nombre corto ("gemini-1.5-flash"), se completa
    automáticamente el prefijo.
    """
    cleaned = (model or "").strip()
    if not cleaned:
        return ""
    return cleaned if cleaned.startswith("models/") else f"models/{cleaned}"

@dataclass(frozen=True)
class Settings:
    spreadsheet_id: str = os.environ.get("SPREADSHEET_ID", "")
    worksheet_name: str = os.environ.get("WORKSHEET_NAME", "Base_Maestra")
    drive_folder_id: str = os.environ.get("DRIVE_FOLDER_ID", "")
    service_account_source: str = resolve_service_account_source(
        os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials_google_drive.json")
    )

    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    gemini_model: str = normalize_model_identifier(
        os.environ.get("GEMINI_MODEL", "models/gemini-1.5-flash")
    )

    out_dir: str = os.environ.get("OUT_DIR", "out_json")

    # Columnas de la hoja
    col_radicado: str = os.environ.get("COL_RADICADO", "RADICADO")
    col_obs: str = os.environ.get("COL_OBS", "ETIQUETA IA")
    col_archivo: str = os.environ.get("COL_ARCHIVO", "ARCHIVO")
    col_updated: str = os.environ.get("COL_UPDATED", "Última actualización")

settings = Settings()
