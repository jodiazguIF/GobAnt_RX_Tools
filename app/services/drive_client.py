import io
import os
import time
from typing import Dict, List

from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from docx import Document

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

class DriveClient:
    def __init__(self, drive_service):
        self.drive = drive_service

    def list_docx_in_folder(self, folder_id: str) -> List[Dict[str, any]]:
        q = f"'{folder_id}' in parents and mimeType='{DOCX_MIME}' and trashed=false"
        files = []
        token = None
        while True:
            resp = self.drive.files().list(
                q=q,
                spaces="drive",
                fields="nextPageToken, files(id, name, modifiedTime)",
                pageToken=token,
            ).execute()
            files.extend(resp.get("files", []))
            token = resp.get("nextPageToken")
            if not token:
                break
        return files

    def download_docx_text(self, file_id: str, retries: int = 3, backoff: int = 2) -> str:
        """Descarga un docx desde Drive y retorna su contenido de texto.

        Realiza reintentos exponenciales ante errores de conexión para
        manejar cierres abruptos de la conexión como WinError 10054.
        """
        for attempt in range(retries):
            try:
                request = self.drive.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                fh.seek(0)
                doc = Document(fh)
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception as e:  # noqa: BLE001
                if attempt == retries - 1:
                    raise
                wait = backoff ** attempt
                print(
                    f"[WARN] Falla al descargar {file_id}: {e}. Reintentando en {wait}s"
                )
                time.sleep(wait)

    def upload_docx(self, folder_id: str, file_path: str | os.PathLike[str]) -> Dict[str, any]:
        """Sube un documento .docx a la carpeta indicada."""

        if not folder_id:
            raise ValueError("No se ha configurado la carpeta de Drive (DRIVE_FOLDER_ID).")
        file_str = str(file_path)
        metadata = {
            "name": os.path.basename(file_str),
            "parents": [folder_id],
            "mimeType": DOCX_MIME,
        }
        media = MediaFileUpload(file_str, mimetype=DOCX_MIME, resumable=True)
        file = (
            self.drive.files()
            .create(body=metadata, media_body=media, fields="id, name")
            .execute()
        )
        return file
