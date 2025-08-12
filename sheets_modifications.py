import gspread
import json
import os
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

def leer_archivo_json(ruta_archivo):
    """
    Lee un archivo JSON y devuelve su contenido como un diccionario de Python.
    
    Args:
        ruta_archivo (str): La ruta completa al archivo JSON.
        
    Returns:
        dict: Un diccionario de Python con el contenido del archivo JSON.
    """
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo_json:
            datos = json.load(archivo_json)
            print(f" Archivo JSON en '{ruta_archivo}' leído exitosamente.")
            return datos
    except FileNotFoundError:
        print(f" Error: El archivo en la ruta '{ruta_archivo}' no fue encontrado.")
        return None
    except json.JSONDecodeError as e:
        print(f" Error al decodificar el JSON del archivo: {e}")
        return None

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

if __name__ == '__main__':
    # Bloque de ejemplo para probar la función
    datos_extraidos = leer_archivo_json("datos_extraidos.json")
    if datos_extraidos:
        subir_a_google_sheets(datos_extraidos)