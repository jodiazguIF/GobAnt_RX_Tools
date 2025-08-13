import os
import docx
import json
import re
from typing import Optional

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
    
def extract_radicado_from_text(doc_text: str) -> Optional[str]:
    """
    Captura un número al inicio del documento o línea inicial (radicado), 
    seguido de texto opcional. Ejemplos válidos:
    '123456 Informe ...', '202500123 - Solicitud ...'
    """
    # Primeras 3 líneas por seguridad
    head = "\n".join(doc_text.splitlines()[:3])
    m = re.search(r'^\s*(\d{6,})\b', head, flags=re.MULTILINE)
    return m.group(1) if m else None

def extract_radicado_from_filename(filename: str) -> Optional[str]:
    """
    Toma el primer bloque numérico largo dentro del nombre del archivo.
    Ej: '202500123_Informe.docx' -> '202500123'
    """
    m = re.search(r'(\d{6,})', filename)
    return m.group(1) if m else None

if __name__ == '__main__':
    # Bloque de ejemplo para probar la función
    datos_extraidos = leer_archivo_json("datos_extraidos.json")
