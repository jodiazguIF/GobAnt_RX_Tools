import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Tuple

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

def get_credentials(sa_path: str):
    if not os.path.exists(sa_path):
        raise FileNotFoundError(f"No se encontró el archivo de credenciales: {sa_path}")
    return service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)

def build_clients(creds) -> Tuple[any, any]:
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    return drive, sheets