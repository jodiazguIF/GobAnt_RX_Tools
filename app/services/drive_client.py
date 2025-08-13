from typing import List, Dict, Any
from googleapiclient.http import MediaIoBaseDownload
import io
from docx import Document

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

class DriveClient:
    def __init__(self, drive_service):
        self.drive = drive_service

    def list_docx_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
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

    def download_docx_text(self, file_id: str) -> str:
        request = self.drive.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        doc = Document(fh)
        return "\n".join(p.text for p in doc.paragraphs)