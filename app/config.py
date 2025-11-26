import os
from dataclasses import dataclass

# Carga variables del .env si usas python-dotenv
from dotenv import load_dotenv
load_dotenv()

def get_relative_path(path: str) -> str:
    # Calcula la ruta relativa al directorio raíz del proyecto.
    # Si el usuario proporciona una ruta absoluta (incluidas rutas Windows como
    # "C:\\..."), se respeta tal cual para evitar concatenarla con la raíz.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if os.path.isabs(path) or ":" in os.path.splitdrive(path)[0]:
        return os.path.normpath(path)

    return os.path.normpath(os.path.join(base_dir, path))

@dataclass(frozen=True)
class Settings:
    spreadsheet_id: str = os.environ.get("SPREADSHEET_ID", "")
    worksheet_name: str = os.environ.get("WORKSHEET_NAME", "Base_Maestra")
    drive_folder_id: str = os.environ.get("DRIVE_FOLDER_ID", "")
    service_account_path: str = get_relative_path(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials_google_drive.json"))

    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

    out_dir: str = os.environ.get("OUT_DIR", "out_json")

    # Columnas de la hoja
    col_radicado: str = os.environ.get("COL_RADICADO", "RADICADO")
    col_obs: str = os.environ.get("COL_OBS", "ETIQUETA IA")
    col_archivo: str = os.environ.get("COL_ARCHIVO", "ARCHIVO")
    col_updated: str = os.environ.get("COL_UPDATED", "Última actualización")

settings = Settings()