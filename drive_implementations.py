import io
import os
import docx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

# --- CONFIGURACIÓN Y AUTENTICACIÓN ---
# Si modificas los SCOPES, elimina el archivo token.json y vuelve a ejecutar
SCOPES = ['https://www.googleapis.com/auth/drive.readonly'] # Este scope limita a lectura y descarga de archivos de la carpeta de drive, evita modificaciones indeseadas

load_dotenv()   #Cargamos la credencial de gemini

# La carpeta local donde se guardarán los archivos
local_word_folder = "Revision_Licencias"

def obtener_servicio_drive():
    """
    Autentica con la API de Google Drive y devuelve el objeto de servicio.
    """
    creds = None
    # El token_drive.json guarda el token de usuario de la sesión previa
    if os.path.exists('Credentials\token_drive.json'):
        creds = Credentials.from_authorized_user_file('Credentials\token_drive.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('Credentials\credentials_google_drive.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guarda el token para futuras ejecuciones
        with open('token_drive.json', 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def leer_y_extraer_texto(ruta_archivo):
    """
    Lee un archivo .docx y extrae todo el texto de sus párrafos.
    (Esta es la misma función del paso anterior)
    """
    try:
        doc = docx.Document(ruta_archivo)
        texto_completo = [parrafo.text for parrafo in doc.paragraphs]
        return "\n".join(texto_completo)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None
    
def descargar_archivos_de_drive(servicio, nombre_carpeta_drive):
    """
    Busca archivos .docx en una carpeta de Drive, los descarga y extrae su texto.
    """
    # 1. Buscar la carpeta por su nombre en Drive
    query = f"name='{nombre_carpeta_drive}' and mimeType='application/vnd.google-apps.folder'"
    resultados = servicio.files().list(q=query, spaces='drive').execute()
    carpetas = resultados.get('files', [])

    if not carpetas:
        print(f"Error: No se encontró la carpeta '{nombre_carpeta_drive}' en Google Drive.")
        return

    folder_id = carpetas[0]['id']
    print(f"Carpeta '{nombre_carpeta_drive}' encontrada.")

    # 2. Listar archivos .docx dentro de esa carpeta
    query = f"'{folder_id}' in parents"
    resultados = servicio.files().list(q=query, spaces='drive', fields='files(id, name, mimeType)').execute()
    elementos = resultados.get('files', [])

    if not elementos:
        print(f"No se encontraron archivos de Word en la carpeta '{nombre_carpeta_drive}'.")
        return

    # 3. Descargar cada archivo y extraer su texto
    if not os.path.exists(local_word_folder):
        os.makedirs(local_word_folder)

    for item in elementos:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        print(f"Descargando '{file_name}' ({mime_type})...")
        file_path = os.path.join(local_word_folder, file_name)

        try:
            request = servicio.files().get_media(fileId=file_id)
            fh = io.FileIO(file_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            print(f"'{file_name}' descargado.")
        except Exception as e:
            print(f"Error al descargar '{file_name}': {e}")
            
def descargar_archivo_por_nombre(servicio, nombre_carpeta_drive, nombre_archivo):
    """
    Descarga un único archivo .docx por su nombre desde una carpeta de Drive.
    """
    # Buscar la carpeta
    query = f"name='{nombre_carpeta_drive}' and mimeType='application/vnd.google-apps.folder'"
    resultados = servicio.files().list(q=query, spaces='drive').execute()
    carpetas = resultados.get('files', [])
    if not carpetas:
        print(f"No se encontró la carpeta '{nombre_carpeta_drive}'.")
        return
    folder_id = carpetas[0]['id']

    # Buscar el archivo por nombre
    query = (
        f"'{folder_id}' in parents and "
        f"name='{nombre_archivo}' and "
        f"mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'"
    )
    resultados = servicio.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    archivos = resultados.get('files', [])
    if not archivos:
        print(f"No se encontró el archivo '{nombre_archivo}' en la carpeta '{nombre_carpeta_drive}'.")
        return

    file_id = archivos[0]['id']
    file_path = os.path.join(local_word_folder, nombre_archivo)
    if not os.path.exists(local_word_folder):
        os.makedirs(local_word_folder)

    print(f"Descargando '{nombre_archivo}'...")
    try:
        request = servicio.files().get_media(fileId=file_id)
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        print(f"'{nombre_archivo}' descargado.")
    except Exception as e:
        print(f"Error al descargar '{nombre_archivo}': {e}")

    texto_extraido = leer_y_extraer_texto(file_path)
    if texto_extraido:
        print(f"\n--- Texto extraído de '{nombre_archivo}' ---\n{texto_extraido[:500]}...")
        print("-" * 50)


# --- EJECUCIÓN PRINCIPAL ---
if __name__ == '__main__':
    # Reemplaza 'Nombre de la carpeta de licencias' con el nombre exacto de la carpeta en tu Google Drive
    nombre_carpeta_en_drive = 'LICENCIAS EXPEDIDAS'
    nombre_archivo_en_drive = '2024010240918_ANGIOSUR SAS.docx'
    ruta_archivo_local = os.path.join(local_word_folder, nombre_archivo_en_drive)

    drive_service = obtener_servicio_drive()
    descargar_archivos_de_drive(drive_service, nombre_carpeta_en_drive)
    #leer_y_extraer_texto(ruta_archivo_local)